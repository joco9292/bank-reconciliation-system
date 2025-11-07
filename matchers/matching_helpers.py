import re
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional, Set
from itertools import combinations

def identify_card_type(description: str) -> str:
    """
    Identify card type from transaction description using regex patterns.
    
    Args:
        description (str): Transaction description
        
    Returns:
        str: Identified card type or 'Unknown'
    """
    description_lower = description.lower()
    
    # Define patterns for each card type
    card_patterns = {
        'Debit Master': [r'debit.*master', r'master.*debit', r'dbt.*mc', r'mc.*dbt'],
        'Debit Visa': [r'debit.*visa', r'visa.*debit', r'dbt.*visa', r'visa.*dbt'],
        'Master Card': [r'(?<!debit\s)master(?!.*debit)', r'(?<!dbt\s)mc(?!.*dbt)', r'mastercard'],
        'Visa': [r'(?<!debit\s)visa(?!.*debit)', r'(?<!dbt\s)vs(?!.*dbt)'],
        'Discover': [r'discover', r'disc(?!.*debit)'],
        'Amex': [r'amex', r'american\s*express', r'amx'],
        'Other Cards': [r'other', r'misc'],
        'Cash': [r'GC'],
        'Check': [r'GC']
    }
    
    for card_type, patterns in card_patterns.items():
        for pattern in patterns:
            if re.search(pattern, description_lower):
                return card_type
    
    return 'Unknown'

def filter_by_card_type_and_date(transactions: pd.DataFrame, card_type: str, 
                                date: datetime, forward_days: int = 3) -> pd.DataFrame:
    """
    Filter 1: Get transactions matching card type within date range.
    Only considers CREDIT and BPAD transactions for credit card matching.
    """
    date_end = date + timedelta(days=forward_days)
    
    # Only consider transactions that are CREDIT or BPAD (money going out)
    # DEBIT transactions (money coming in) should not be matched against credit card summaries
    return transactions[
        (transactions['Card_Type'] == card_type) &
        (transactions['Date'] >= date) &
        (transactions['Date'] <= date_end) &
        (transactions['Transaction_Type'].isin(['CREDIT', 'BPAD']))
    ].copy()

def filter_exact_match(transactions: pd.DataFrame, expected_amount: float, 
                      tolerance: float = 0.01) -> Dict:
    """
    Filter 2: Look for exact matches within tolerance.
    """
    exact_matches = transactions[
        abs(transactions['Amount'] - expected_amount) < tolerance
    ]
    
    if len(exact_matches) > 0:
        actual_total = exact_matches['Amount'].sum()
        return {
            'matched': True,
            'match_type': 'exact',
            'transactions': exact_matches.to_dict('records'),
            'bank_rows': exact_matches['Bank_Row_Number'].tolist(),
            'actual_total': actual_total,
            'difference': actual_total - expected_amount
        }
    
    return {'matched': False}

def filter_sum_by_description(transactions: pd.DataFrame, expected_amount: float,
                            tolerance: float = 0.01) -> Dict:
    """
    Filter 3: Look for sums by description.
    """
    # Try complete description groups first
    description_groups = transactions.groupby('Description')
    
    for desc, group in description_groups:
        group_sum = group['Amount'].sum()
        if abs(group_sum - expected_amount) < tolerance:
            return {
                'matched': True,
                'match_type': 'sum_by_description',
                'description': desc,
                'transactions': group.to_dict('records'),
                'bank_rows': group['Bank_Row_Number'].tolist(),
                'actual_total': group_sum,
                'difference': group_sum - expected_amount
            }
    
    # Try partial combinations by description
    all_descriptions = transactions['Description'].unique()
    
    for desc in all_descriptions:
        desc_transactions = transactions[transactions['Description'] == desc]
        
        for r in range(1, min(len(desc_transactions) + 1, 6)):  # Limit to 5 transactions
            for combo in combinations(desc_transactions.index, r):
                combo_sum = desc_transactions.loc[list(combo), 'Amount'].sum()
                if abs(combo_sum - expected_amount) < tolerance:
                    selected_trans = desc_transactions.loc[list(combo)]
                    return {
                        'matched': True,
                        'match_type': 'partial_sum_by_description',
                        'description': desc,
                        'transactions': selected_trans.to_dict('records'),
                        'bank_rows': selected_trans['Bank_Row_Number'].tolist(),
                        'actual_total': combo_sum,
                        'difference': combo_sum - expected_amount
                    }
    
    return {'matched': False}

def filter_by_amount_range(transactions: pd.DataFrame, expected_amount: float,
                          percentage_tolerance: float = 0.03) -> Dict:
    """
    Filter 4: Match within percentage range (e.g., 3% tolerance).
    """
    lower_bound = expected_amount * (1 - percentage_tolerance)
    upper_bound = expected_amount * (1 + percentage_tolerance)
    
    range_matches = transactions[
        (transactions['Amount'] >= lower_bound) &
        (transactions['Amount'] <= upper_bound)
    ]
    
    if len(range_matches) > 0:
        # Return the closest match
        range_matches = range_matches.copy()
        range_matches['Difference'] = abs(range_matches['Amount'] - expected_amount)
        closest_match = range_matches.nsmallest(1, 'Difference')
        actual_total = closest_match['Amount'].sum()
        
        return {
            'matched': True,
            'match_type': 'amount_range',
            'tolerance_used': percentage_tolerance,
            'transactions': closest_match.to_dict('records'),
            'bank_rows': closest_match['Bank_Row_Number'].tolist(),
            'actual_total': actual_total,
            'difference': actual_total - expected_amount
        }
    
    return {'matched': False}

def filter_split_transactions(transactions: pd.DataFrame, expected_amount: float,
                            max_transactions: int = 3, tolerance: float = 0.01) -> Dict:
    """
    Filter 5: Look for any combination of transactions that sum to expected amount.
    """
    # Limit to reasonable number of transactions to check
    if len(transactions) > 10:
        # Sort by amount descending to check larger transactions first
        transactions = transactions.nlargest(10, 'Amount')
    
    for r in range(2, min(len(transactions) + 1, max_transactions + 1)):
        for combo in combinations(transactions.index, r):
            combo_sum = transactions.loc[list(combo), 'Amount'].sum()
            if abs(combo_sum - expected_amount) < tolerance:
                selected_trans = transactions.loc[list(combo)]
                return {
                    'matched': True,
                    'match_type': 'split_transactions',
                    'transaction_count': len(combo),
                    'transactions': selected_trans.to_dict('records'),
                    'bank_rows': selected_trans['Bank_Row_Number'].tolist(),
                    'actual_total': combo_sum,
                    'difference': combo_sum - expected_amount
                }
    
    return {'matched': False}

class TransactionMatcher:
    """
    Extensible transaction matching engine with card-type-specific filtering.
    Now with exclusive transaction allocation for discrepancy calculations.
    """
    def __init__(self):
        # Define the default filter pipeline
        self.default_filters = [
            ('exact_match', filter_exact_match),
            ('sum_by_description', filter_sum_by_description),
        ]
        
        # Define card-type-specific filters
        self.card_specific_filters = {
            'Amex': [
                ('amount_range', filter_by_amount_range),
            ],
        }
        
        # Optional: Define filters to exclude for specific card types
        self.excluded_filters = {}
    
    def add_filter(self, name: str, filter_func: Callable, position: int = None, 
                   card_types: Optional[List[str]] = None):
        """
        Add a new filter to the pipeline.
        """
        if card_types is None:
            # Add to default pipeline
            if position is None:
                self.default_filters.append((name, filter_func))
            else:
                self.default_filters.insert(position, (name, filter_func))
        else:
            # Add to specific card types
            for card_type in card_types:
                if card_type not in self.card_specific_filters:
                    self.card_specific_filters[card_type] = []
                self.card_specific_filters[card_type].append((name, filter_func))
    
    def get_filters_for_card_type(self, card_type: str) -> List[tuple]:
        """
        Get the appropriate filter pipeline for a given card type.
        """
        # Start with default filters
        filters = self.default_filters.copy()
        
        # Remove any excluded filters for this card type
        if card_type in self.excluded_filters:
            excluded_names = self.excluded_filters[card_type]
            filters = [(name, func) for name, func in filters 
                      if name not in excluded_names]
        
        # Add card-specific filters
        if card_type in self.card_specific_filters:
            filters.extend(self.card_specific_filters[card_type])
        
        return filters
    
    def _attempt_cleanup_matching(self, leftover_transactions: pd.DataFrame, 
                                 results: Dict, forward_days: int, verbose: bool = False) -> Dict:
        """
        Attempt to match leftover transactions to cells that could benefit.
        Only looks forward within 1-2 extra days to avoid matching too far out.
        """
        cleanup_matches = {}
        
        # Group leftover transactions by card type
        leftover_by_card_type = leftover_transactions.groupby('Card_Type')
        
        for card_type, card_transactions in leftover_by_card_type:
            if card_type == 'Unknown':
                continue  # Skip unknown card types
            
            # Try to match these transactions to cells of the same card type
            for date, date_results in results.items():
                if card_type in date_results.get('unmatched_by_card_type', {}):
                    unmatched_info = date_results['unmatched_by_card_type'][card_type]
                    expected_amount = unmatched_info['expected']
                    
                    # Check if any leftover transactions could help this cell
                    # Use extended forward days (1-2 extra days) for cleanup
                    extended_forward_days = forward_days + 2
                    
                    # Filter transactions within extended date range
                    date_end = date + timedelta(days=extended_forward_days)
                    extended_transactions = card_transactions[
                        (card_transactions['Date'] >= date) &
                        (card_transactions['Date'] <= date_end)
                    ]
                    
                    if len(extended_transactions) == 0:
                        continue
                    
                    # Try to find a match using the same filters
                    filters_to_apply = self.get_filters_for_card_type(card_type)
                    
                    for filter_name, filter_func in filters_to_apply:
                        result = filter_func(extended_transactions, expected_amount)
                        
                        if result['matched']:
                            # Found a cleanup match!
                            cleanup_matches[(date, card_type)] = {
                                'expected': expected_amount,
                                'match_type': f'cleanup_{result["match_type"]}',
                                'transactions': result['transactions'],
                                'bank_rows': result['bank_rows'],
                                'actual_total': result.get('actual_total', expected_amount),
                                'difference': result.get('difference', 0),
                                'cleanup_extended_days': extended_forward_days,
                                **{k: v for k, v in result.items() 
                                   if k not in ['matched', 'match_type', 'transactions', 
                                               'bank_rows', 'actual_total', 'difference']}
                            }
                            
                            if verbose:
                                print(f"    Found cleanup match for {date.strftime('%Y-%m-%d')} {card_type}: "
                                      f"${result.get('actual_total', expected_amount):,.2f} "
                                      f"(extended to {extended_forward_days} days)")
                            
                            # Remove matched transactions from leftover pool
                            leftover_transactions = leftover_transactions[
                                ~leftover_transactions['Bank_Row_Number'].isin(result['bank_rows'])
                            ]
                            break  # Move to next cell
                    
                    # If we found a match for this cell, don't try other cells
                    if (date, card_type) in cleanup_matches:
                        break
        
        return cleanup_matches
    
    def match_transactions(self, card_summary: pd.DataFrame, bank_statement: pd.DataFrame, 
                          forward_days: int = 3, verbose: bool = False) -> Dict:
        """
        Match transactions using the filter pipeline with card-type-specific filters.
        Now ensures exclusive transaction allocation for discrepancy calculations.
        """
        results = {}
        matched_bank_rows = set()
        
        # NEW: Track which bank rows are allocated to which cell for discrepancy calculations
        allocated_for_discrepancy = {}  # {bank_row: (date, card_type)}
        
        # NEW: Track attempted but failed bank rows
        attempted_bank_rows = set()  # All rows that were candidates for matching
        
        # Card types to process
        card_types = [col for col in card_summary.columns 
                      if col not in ['Date', 'Total', 'Visa & MC'] and not col.startswith('Unnamed')]
        
        # PASS 1: Do all matching
        for _, card_row in card_summary.iterrows():
            date = card_row['Date']
            date_results = {
                'date': date,
                'matches_by_card_type': {},
                'unmatched_by_card_type': {}
            }
            
            for card_type in card_types:
                expected_amount = card_row[card_type]
                
                if pd.isna(expected_amount) or expected_amount == 0:
                    continue
                
                # Filter 1: Get relevant transactions
                filtered_transactions = filter_by_card_type_and_date(
                    bank_statement, card_type, date, forward_days
                )
                
                # Track all candidate bank rows as "attempted"
                if len(filtered_transactions) > 0:
                    candidate_rows = set(filtered_transactions['Bank_Row_Number'].tolist())
                    attempted_bank_rows.update(candidate_rows)
                
                if len(filtered_transactions) == 0:
                    date_results['unmatched_by_card_type'][card_type] = {
                        'expected': expected_amount,
                        'reason': 'No transactions found for card type in date range',
                        'bank_rows': [],
                        'found_transactions': 0,
                        'total_found': 0
                    }
                    continue
                
                # Get the appropriate filters for this card type
                filters_to_apply = self.get_filters_for_card_type(card_type)
                
                if verbose:
                    filter_names = [name for name, _ in filters_to_apply]
                    print(f"Processing {date.strftime('%Y-%m-%d')} {card_type}: "
                          f"Using filters: {filter_names}")
                
                # Run through the card-type-specific filter pipeline
                matched = False
                for filter_name, filter_func in filters_to_apply:
                    result = filter_func(filtered_transactions, expected_amount)
                    
                    if result['matched']:
                        date_results['matches_by_card_type'][card_type] = {
                            'expected': expected_amount,
                            'match_type': result['match_type'],
                            'transactions': result['transactions'],
                            'bank_rows': result['bank_rows'],
                            'actual_total': result.get('actual_total', expected_amount),
                            'difference': result.get('difference', 0),
                            **{k: v for k, v in result.items() 
                               if k not in ['matched', 'match_type', 'transactions', 
                                           'bank_rows', 'actual_total', 'difference']}
                        }
                        matched_bank_rows.update(result['bank_rows'])
                        matched = True
                        
                        if verbose:
                            print(f"  ✓ Matched with {filter_name}")
                        break
                
                if not matched:
                    # Store preliminary unmatched info - will update in Pass 2
                    date_results['unmatched_by_card_type'][card_type] = {
                        'expected': expected_amount,
                        'date': date,
                        'card_type': card_type,
                        'forward_days': forward_days,
                        'filters_tried': [name for name, _ in filters_to_apply]
                    }
                    
                    if verbose:
                        print(f"  ✗ No match found after trying {len(filters_to_apply)} filters")
            
            results[date] = date_results
        
        # PASS 2: Calculate EXCLUSIVE unmatched totals for discrepancy calculations
        # Each unmatched bank transaction is allocated to at most ONE cell
        if not verbose:
            print("\nPass 2: Calculating exclusive unmatched transaction totals...")
        
        # Sort unmatched cells by expected amount (descending) to prioritize larger discrepancies
        unmatched_cells = []
        for date, date_results in results.items():
            for card_type, unmatch_info in date_results['unmatched_by_card_type'].items():
                if 'date' in unmatch_info:
                    unmatched_cells.append((date, card_type, unmatch_info))
        
        unmatched_cells.sort(key=lambda x: x[2]['expected'], reverse=True)
        
        # Allocate unmatched bank transactions exclusively
        for date, card_type, unmatch_info in unmatched_cells:
            # Get transactions for this card type and date range
            filtered_transactions = filter_by_card_type_and_date(
                bank_statement, 
                unmatch_info['card_type'], 
                unmatch_info['date'], 
                unmatch_info['forward_days']
            )
            
            # Filter out already matched transactions
            unmatched_only = filtered_transactions[
                ~filtered_transactions['Bank_Row_Number'].isin(matched_bank_rows)
            ]
            
            # NEW: Also filter out transactions already allocated to other cells
            available_for_this_cell = []
            for _, trans in unmatched_only.iterrows():
                bank_row = trans['Bank_Row_Number']
                if bank_row not in allocated_for_discrepancy:
                    available_for_this_cell.append(trans)
                    # Mark this transaction as allocated to this cell
                    allocated_for_discrepancy[bank_row] = (date, card_type)
            
            available_df = pd.DataFrame(available_for_this_cell) if available_for_this_cell else pd.DataFrame()
            
            # Update with accurate EXCLUSIVE unmatched totals
            results[date]['unmatched_by_card_type'][card_type] = {
                'expected': unmatch_info['expected'],
                'found_transactions': len(available_df),
                'total_found': available_df['Amount'].sum() if len(available_df) > 0 else 0,
                'reason': f"No match found after trying filters: {unmatch_info.get('filters_tried', [])}",
                'bank_rows': available_df['Bank_Row_Number'].tolist() if len(available_df) > 0 else [],
                'exclusive_allocation': True  # Flag to indicate exclusive allocation was used
            }
            
            # Debug output for significant unmatched amounts
            if unmatch_info['expected'] > 1000 and not verbose:
                total_found = available_df['Amount'].sum() if len(available_df) > 0 else 0
                print(f"  {unmatch_info['date'].strftime('%Y-%m-%d')} {card_type}: "
                      f"Expected ${unmatch_info['expected']:,.2f}, "
                      f"Found ${total_found:,.2f} "
                      f"in {len(available_df)} EXCLUSIVELY allocated transactions")
        
        # PASS 3: Cleanup pass - try to match leftover transactions to cells that could benefit
        # This helps ensure no transactions are left behind
        if not verbose:
            print("\nPass 3: Cleanup pass - attempting to match leftover transactions...")
        
        # Find all unmatched bank transactions
        all_bank_rows = set(bank_statement['Bank_Row_Number'].tolist())
        leftover_bank_rows = all_bank_rows - matched_bank_rows - set(allocated_for_discrepancy.keys())
        
        if len(leftover_bank_rows) > 0:
            if verbose:
                print(f"Found {len(leftover_bank_rows)} leftover transactions to attempt cleanup matching")
            
            # Get leftover transactions
            leftover_transactions = bank_statement[
                bank_statement['Bank_Row_Number'].isin(leftover_bank_rows)
            ].copy()
            
            # Try to match leftover transactions to cells that could benefit
            cleanup_matches = self._attempt_cleanup_matching(
                leftover_transactions, results, forward_days, verbose
            )
            
            # Apply cleanup matches if any found
            if cleanup_matches:
                for (date, card_type), match_info in cleanup_matches.items():
                    if date in results and 'matches_by_card_type' in results[date]:
                        results[date]['matches_by_card_type'][card_type] = match_info
                        matched_bank_rows.update(match_info['bank_rows'])
                        
                        # Remove from unmatched if it was there
                        if card_type in results[date]['unmatched_by_card_type']:
                            del results[date]['unmatched_by_card_type'][card_type]
                        
                        if verbose:
                            print(f"  ✓ Cleanup match: {date.strftime('%Y-%m-%d')} {card_type} "
                                  f"matched ${match_info['actual_total']:,.2f}")
        
        # Add allocation info to results for reporting
        results['_allocated_for_discrepancy'] = allocated_for_discrepancy
        results['_attempted_bank_rows'] = attempted_bank_rows
        results['_cleanup_attempted'] = len(leftover_bank_rows) > 0
        
        return results