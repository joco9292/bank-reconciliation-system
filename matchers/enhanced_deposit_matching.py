"""
Enhanced Deposit Matching Module
Handles complex deposit matching scenarios including:
1. Single GC 1416 transaction representing both Cash and Check
2. Multiple different transactions aggregating into Cash OR Check
3. Flexible transaction matching strategies
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from itertools import combinations

class EnhancedDepositMatcher:
    """
    Enhanced matcher for deposit slips with flexible transaction aggregation.
    Handles:
    - Single GC 1416 representing both Cash and Check
    - Multiple different transactions aggregating to Cash or Check
    - Various matching strategies
    """
    
    def __init__(self):
        self.gc_1416_identifier = 'GC 1416'
        self.cash_identifiers = ['CASH', 'GC 1416']
        self.check_identifiers = ['CHECK', 'CHK', 'GC 1416']
        
    def identify_possible_deposit_types(self, description: str) -> List[str]:
        """
        Identify possible deposit types from transaction description.
        More flexible than before - any transaction could potentially be Cash or Check.
        """
        description_upper = description.upper()
        
        # GC 1416 can be both
        if self.gc_1416_identifier in description_upper:
            return ['Cash', 'Check', 'Both']
        
        # Check for specific identifiers
        possible_types = []
        
        # Check for cash indicators
        if any(identifier in description_upper for identifier in self.cash_identifiers):
            possible_types.append('Cash')
        
        # Check for check indicators  
        if any(identifier in description_upper for identifier in self.check_identifiers):
            possible_types.append('Check')
        
        # If no specific identifier, could be either (for aggregation purposes)
        if not possible_types:
            possible_types = ['Cash', 'Check']
        
        return possible_types
    
    def try_single_transaction_split(self, transaction: pd.Series, 
                                    cash_expected: float, check_expected: float,
                                    tolerance: float = 0.01) -> Dict:
        """
        Try to match a single transaction (like GC 1416) to BOTH Cash and Check.
        This handles Situation 1: Single transaction representing both types.
        """
        trans_amount = transaction['Amount']
        total_expected = cash_expected + check_expected
        
        # Check if single transaction matches the sum of Cash + Check
        if abs(trans_amount - total_expected) < tolerance:
            return {
                'matched': True,
                'match_type': 'single_transaction_both_types',
                'cash_allocation': {
                    'amount': cash_expected,
                    'bank_rows': [transaction['Bank_Row_Number']],
                    'transactions': [{**transaction.to_dict(), 'allocated_amount': cash_expected}]
                },
                'check_allocation': {
                    'amount': check_expected,
                    'bank_rows': [transaction['Bank_Row_Number']],
                    'transactions': [{**transaction.to_dict(), 'allocated_amount': check_expected}]
                },
                'shared_transaction': True,
                'total_difference': 0
            }
        
        return {'matched': False}
    
    def try_multiple_transaction_aggregation(self, transactions: pd.DataFrame,
                                           target_amount: float, deposit_type: str,
                                           max_transactions: int = 5,
                                           tolerance: float = 0.01) -> Dict:
        """
        Try to find any combination of transactions that sum to target amount.
        This handles Situation 2: Multiple different transactions aggregating.
        """
        if transactions.empty:
            return {'matched': False}
        
        # Try exact single match first
        exact_matches = transactions[abs(transactions['Amount'] - target_amount) < tolerance]
        if not exact_matches.empty:
            best_match = exact_matches.iloc[0]
            return {
                'matched': True,
                'match_type': 'exact_single',
                'transactions': [best_match.to_dict()],
                'bank_rows': [best_match['Bank_Row_Number']],
                'total': best_match['Amount'],
                'difference': best_match['Amount'] - target_amount
            }
        
        # Try combinations
        n_trans = min(len(transactions), 10)  # Limit for performance
        
        for r in range(2, min(n_trans + 1, max_transactions + 1)):
            for combo in combinations(transactions.index, r):
                combo_sum = transactions.loc[list(combo), 'Amount'].sum()
                if abs(combo_sum - target_amount) < tolerance:
                    selected = transactions.loc[list(combo)]
                    return {
                        'matched': True,
                        'match_type': f'aggregation_{r}_transactions',
                        'transactions': selected.to_dict('records'),
                        'bank_rows': selected['Bank_Row_Number'].tolist(),
                        'total': combo_sum,
                        'difference': combo_sum - target_amount
                    }
        
        return {'matched': False}
    
    def match_deposit_with_flexibility(self, date: datetime, cash_expected: float,
                                      check_expected: float, bank_statement: pd.DataFrame,
                                      forward_days: int = 3, verbose: bool = False) -> Dict:
        """
        Flexible matching that tries multiple strategies:
        1. Single GC 1416 matching both Cash and Check
        2. Multiple GC 1416s split between Cash and Check
        3. Any transactions aggregating to match Cash or Check
        """
        date_end = date + timedelta(days=forward_days)
        results = {
            'cash_matched': False,
            'check_matched': False,
            'cash_result': None,
            'check_result': None,
            'matched_bank_rows': set()
        }
        
        # Get all transactions in date range
        # Only consider CREDIT transactions (money coming in) for deposit matching
        date_transactions = bank_statement[
            (bank_statement['Date'] >= date) &
            (bank_statement['Date'] <= date_end) &
            (bank_statement['Transaction_Type'] == 'CREDIT')
        ].copy()
        
        if date_transactions.empty:
            return results
        
        # Strategy 1: Check if single GC 1416 matches Cash + Check total
        gc_1416_trans = date_transactions[
            date_transactions['Description'].str.contains('GC 1416', case=False, na=False) |
            date_transactions['Description'].str.contains('Cash/Check', case=False, na=False)
        ]
        
        if len(gc_1416_trans) == 1 and cash_expected > 0 and check_expected > 0:
            single_split = self.try_single_transaction_split(
                gc_1416_trans.iloc[0], cash_expected, check_expected
            )
            if single_split['matched']:
                if verbose:
                    print(f"  ✓ Single GC 1416 split: Cash=${cash_expected:.2f}, Check=${check_expected:.2f}")
                
                results['cash_matched'] = True
                results['check_matched'] = True
                results['cash_result'] = single_split['cash_allocation']
                results['check_result'] = single_split['check_allocation']
                results['matched_bank_rows'].update(single_split['cash_allocation']['bank_rows'])
                results['shared_transaction'] = True
                return results
        
        # Strategy 2: Try traditional GC 1416 allocation
        if len(gc_1416_trans) > 0:
            allocation = self.allocate_gc_1416_optimally(
                gc_1416_trans, cash_expected, check_expected
            )
            if allocation['matched']:
                if cash_expected > 0:
                    results['cash_matched'] = True
                    results['cash_result'] = allocation['cash_allocation']
                    results['matched_bank_rows'].update(allocation['cash_allocation']['bank_rows'])
                
                if check_expected > 0:
                    results['check_matched'] = True
                    results['check_result'] = allocation['check_allocation']
                    results['matched_bank_rows'].update(allocation['check_allocation']['bank_rows'])
                
                if results['cash_matched'] or results['check_matched']:
                    return results
        
        # Strategy 3: Try aggregating ANY transactions to match Cash or Check
        available_trans = date_transactions[
            ~date_transactions['Bank_Row_Number'].isin(results['matched_bank_rows'])
        ]
        
        # Try to match Cash with any available transactions
        if cash_expected > 0 and not results['cash_matched']:
            cash_match = self.try_multiple_transaction_aggregation(
                available_trans, cash_expected, 'Cash'
            )
            if cash_match['matched']:
                results['cash_matched'] = True
                results['cash_result'] = cash_match
                results['matched_bank_rows'].update(cash_match['bank_rows'])
                
                # Remove used transactions from available
                available_trans = available_trans[
                    ~available_trans['Bank_Row_Number'].isin(cash_match['bank_rows'])
                ]
                
                if verbose:
                    print(f"  ✓ Cash matched via {cash_match['match_type']}: ${cash_match['total']:.2f}")
        
        # Try to match Check with remaining transactions
        if check_expected > 0 and not results['check_matched']:
            check_match = self.try_multiple_transaction_aggregation(
                available_trans, check_expected, 'Check'
            )
            if check_match['matched']:
                results['check_matched'] = True
                results['check_result'] = check_match
                results['matched_bank_rows'].update(check_match['bank_rows'])
                
                if verbose:
                    print(f"  ✓ Check matched via {check_match['match_type']}: ${check_match['total']:.2f}")
        
        return results
    
    def allocate_gc_1416_optimally(self, gc_1416_transactions: pd.DataFrame,
                                  cash_expected: float, check_expected: float,
                                  tolerance: float = 0.01) -> Dict:
        """
        Original optimal allocation method for multiple GC 1416 transactions.
        """
        if gc_1416_transactions.empty:
            return {'matched': False}
        
        total_gc = gc_1416_transactions['Amount'].sum()
        total_expected = cash_expected + check_expected
        
        # Try exact allocation
        if abs(total_gc - total_expected) < tolerance:
            for cash_combo_size in range(len(gc_1416_transactions) + 1):
                for cash_combo in combinations(gc_1416_transactions.index, cash_combo_size):
                    cash_indices = list(cash_combo)
                    check_indices = [idx for idx in gc_1416_transactions.index if idx not in cash_indices]
                    
                    cash_sum = gc_1416_transactions.loc[cash_indices, 'Amount'].sum() if cash_indices else 0
                    check_sum = gc_1416_transactions.loc[check_indices, 'Amount'].sum() if check_indices else 0
                    
                    if abs(cash_sum - cash_expected) < tolerance and abs(check_sum - check_expected) < tolerance:
                        return {
                            'matched': True,
                            'match_type': 'gc_1416_optimal_split',
                            'cash_allocation': {
                                'transactions': gc_1416_transactions.loc[cash_indices].to_dict('records') if cash_indices else [],
                                'bank_rows': gc_1416_transactions.loc[cash_indices, 'Bank_Row_Number'].tolist() if cash_indices else [],
                                'total': cash_sum,
                                'expected': cash_expected,
                                'difference': cash_sum - cash_expected
                            },
                            'check_allocation': {
                                'transactions': gc_1416_transactions.loc[check_indices].to_dict('records') if check_indices else [],
                                'bank_rows': gc_1416_transactions.loc[check_indices, 'Bank_Row_Number'].tolist() if check_indices else [],
                                'total': check_sum,
                                'expected': check_expected,
                                'difference': check_sum - check_expected
                            }
                        }
        
        return {'matched': False}


def process_deposit_slip_enhanced(deposit_slip_path: str, bank_statement_path: str,
                                 output_dir: str = '.', verbose: bool = False):
    """
    Enhanced deposit slip processing with flexible matching strategies.
    """
    from preprocess_deposit_slip import preprocess_deposit_slip_dynamic, create_highlighted_deposit_slip
    from preprocess_bank_statement import preprocess_bank_statement
    
    print("=== Enhanced Deposit Slip Matching ===\n")
    
    # Load data
    deposit_slip, structure_info = preprocess_deposit_slip_dynamic(deposit_slip_path)
    bank_statement = preprocess_bank_statement(bank_statement_path)
    
    # Add row numbers
    bank_statement['Bank_Row_Number'] = range(2, len(bank_statement) + 2)
    
    # Initialize matcher
    matcher = EnhancedDepositMatcher()
    
    # Results storage
    all_results = {}
    all_matched_bank_rows = set()
    matched_dates_and_types = {}
    unmatched_info = {}
    gc_1416_allocations = {}
    
    # Process each date
    for _, deposit_row in deposit_slip.iterrows():
        date = deposit_row['Date']
        cash_expected = deposit_row.get('Cash', 0)
        check_expected = deposit_row.get('Check', 0)
        
        if cash_expected == 0 and check_expected == 0:
            continue
        
        if verbose:
            print(f"\nProcessing {date.strftime('%Y-%m-%d')}: Cash=${cash_expected:.2f}, Check=${check_expected:.2f}")
        
        # Get available transactions (excluding already matched)
        available_bank = bank_statement[~bank_statement['Bank_Row_Number'].isin(all_matched_bank_rows)]
        
        # Run flexible matching
        match_results = matcher.match_deposit_with_flexibility(
            date, cash_expected, check_expected, available_bank,
            forward_days=3, verbose=verbose
        )
        
        # Process results
        date_results = {
            'date': date,
            'matches_by_type': {},
            'unmatched_by_type': {}
        }
        
        # Handle Cash results
        if match_results['cash_matched']:
            date_results['matches_by_type']['Cash'] = {
                'expected': cash_expected,
                'match_type': match_results['cash_result'].get('match_type', 'unknown'),
                'transactions': match_results['cash_result'].get('transactions', []),
                'bank_rows': match_results['cash_result'].get('bank_rows', []),
                'actual_total': match_results['cash_result'].get('total', cash_expected),
                'difference': match_results['cash_result'].get('difference', 0)
            }
            matched_dates_and_types.setdefault(date, []).append('Cash')
            
            # Store GC 1416 allocation info if applicable
            if 'shared_transaction' in match_results:
                gc_1416_allocations[(date, 'Cash')] = {
                    'amount': cash_expected,
                    'bank_rows': match_results['cash_result']['bank_rows'],
                    'shared': True
                }
        else:
            date_results['unmatched_by_type']['Cash'] = {
                'expected': cash_expected,
                'reason': 'No matching transactions found'
            }
            unmatched_info[(date, 'Cash')] = date_results['unmatched_by_type']['Cash']
        
        # Handle Check results
        if match_results['check_matched']:
            date_results['matches_by_type']['Check'] = {
                'expected': check_expected,
                'match_type': match_results['check_result'].get('match_type', 'unknown'),
                'transactions': match_results['check_result'].get('transactions', []),
                'bank_rows': match_results['check_result'].get('bank_rows', []),
                'actual_total': match_results['check_result'].get('total', check_expected),
                'difference': match_results['check_result'].get('difference', 0)
            }
            matched_dates_and_types.setdefault(date, []).append('Check')
            
            # Store GC 1416 allocation info if applicable
            if 'shared_transaction' in match_results:
                gc_1416_allocations[(date, 'Check')] = {
                    'amount': check_expected,
                    'bank_rows': match_results['check_result']['bank_rows'],
                    'shared': True
                }
        else:
            date_results['unmatched_by_type']['Check'] = {
                'expected': check_expected,
                'reason': 'No matching transactions found'
            }
            unmatched_info[(date, 'Check')] = date_results['unmatched_by_type']['Check']
        
        all_results[date] = date_results
        all_matched_bank_rows.update(match_results['matched_bank_rows'])
    
    # Generate reports and highlighted files
    print("\n=== Generating Reports ===")
    
    # Calculate discrepancies by deposit type
    from deposit_matching import calculate_deposit_discrepancies_by_type
    deposit_discrepancies = calculate_deposit_discrepancies_by_type(all_results, deposit_slip)
    
    # Create highlighted deposit slip
    from preprocess_deposit_slip import create_highlighted_deposit_slip
    create_highlighted_deposit_slip(
        deposit_slip_path=deposit_slip_path,
        matched_dates_and_types=matched_dates_and_types,
        output_path=f'{output_dir}/deposit_slip_enhanced_highlighted.xlsx',
        unmatched_info=unmatched_info,
        gc_1416_allocation=gc_1416_allocations,
        deposit_discrepancies=deposit_discrepancies
    )
    
    # Create highlighted bank statement
    from highlighting_functions import create_highlighted_bank_statement
    create_highlighted_bank_statement(
        bank_statement_path=bank_statement_path,
        matched_bank_rows=all_matched_bank_rows,
        output_path=f'{output_dir}/bank_statement_deposit_enhanced_highlighted.xlsx'
    )
    
    print(f"\n✓ Enhanced deposit matching complete")
    print(f"  - Matched bank rows: {len(all_matched_bank_rows)}")
    print(f"  - Files saved to {output_dir}/")
    
    return all_results