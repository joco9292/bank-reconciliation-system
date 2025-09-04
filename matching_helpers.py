import re
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional, Optional, Set
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
        'Other Cards': [r'other', r'misc']
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
    """
    date_end = date + timedelta(days=forward_days)
    return transactions[
        (transactions['Card_Type'] == card_type) &
        (transactions['Date'] >= date) &
        (transactions['Date'] <= date_end)
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


# make this have a hard cap otuside of just the percentage base
def filter_by_amount_range(transactions: pd.DataFrame, expected_amount: float,
                          percentage_tolerance: float = 0.03) -> Dict:
    """
    Filter 4: Match within percentage range (e.g., 5% tolerance).
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
    """
    def __init__(self):
        # Define the default filter pipeline
        self.default_filters = [
            ('exact_match', filter_exact_match),
            ('sum_by_description', filter_sum_by_description),
        ]
        
        # Define card-type-specific filters
        # Format: {card_type: [(filter_name, filter_func), ...]}
        self.card_specific_filters = {
            'Amex': [
                ('amount_range', filter_by_amount_range),
            ],
            # Add more card-specific filters here as needed
            # 'Discover': [
            #     ('split_transactions', filter_split_transactions),
            # ],
        }
        
        # Optional: Define filters to exclude for specific card types
        self.excluded_filters = {
            # Example: 'Debit Visa': ['sum_by_description']
        }
    
    def add_filter(self, name: str, filter_func: Callable, position: int = None, 
                   card_types: Optional[List[str]] = None):
        """
        Add a new filter to the pipeline.
        
        Args:
            name: Name of the filter
            filter_func: Filter function to apply
            position: Position in default pipeline (None = append to end)
            card_types: Optional list of card types this filter applies to.
                       If None, applies to all card types.
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
        
        Args:
            card_type: The card type to get filters for
            
        Returns:
            List of (filter_name, filter_func) tuples
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
    
    def match_transactions(self, card_summary: pd.DataFrame, bank_statement: pd.DataFrame, 
                          forward_days: int = 3, verbose: bool = False) -> Dict:
        """
        Match transactions using the filter pipeline with card-type-specific filters.
        
        Args:
            card_summary: DataFrame with expected transactions by card type
            bank_statement: DataFrame with actual bank transactions
            forward_days: Number of days forward to look for matches
            verbose: If True, print debug information about filter usage
        """
        results = {}
        matched_bank_rows = set()
        
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
        
        # PASS 2: Recalculate unmatched totals using only unmatched bank transactions
        if not verbose:
            print("\nPass 2: Calculating unmatched transaction totals...")
        
        for date, date_results in results.items():
            for card_type, unmatch_info in date_results['unmatched_by_card_type'].items():
                if 'date' in unmatch_info:  # Only process those that need recalculation
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
                    
                    # Update with accurate unmatched-only totals
                    date_results['unmatched_by_card_type'][card_type] = {
                        'expected': unmatch_info['expected'],
                        'found_transactions': len(unmatched_only),
                        'total_found': unmatched_only['Amount'].sum() if len(unmatched_only) > 0 else 0,
                        'reason': f"No match found after trying filters: {unmatch_info.get('filters_tried', [])}",
                        'bank_rows': unmatched_only['Bank_Row_Number'].tolist()
                    }
                    
                    # Debug output for significant unmatched amounts
                    if unmatch_info['expected'] > 1000 and not verbose:
                        print(f"  {unmatch_info['date'].strftime('%Y-%m-%d')} {card_type}: "
                              f"Expected ${unmatch_info['expected']:,.2f}, "
                              f"Found ${unmatched_only['Amount'].sum():,.2f} "
                              f"in {len(unmatched_only)} unmatched transactions")
        
        return results