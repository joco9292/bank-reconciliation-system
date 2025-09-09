import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from itertools import combinations

class DepositMatcher:
    """
    Specialized matcher for deposit slips with GC 1416 transaction handling.
    GC 1416 transactions can match to either Cash or Check columns.
    """
    
    def __init__(self):
        self.gc_1416_identifier = 'GC 1416'
        
    def identify_deposit_type(self, description: str) -> List[str]:
        """
        Identify deposit type from transaction description.
        GC 1416 can be both Cash and Check.
        
        Returns:
            List of possible deposit types (usually one, but two for GC 1416)
        """
        description_upper = description.upper()
        
        if self.gc_1416_identifier in description_upper:
            return ['Cash', 'Check']  # Can be either
        
        # Add other specific identifiers if needed
        # For now, treat unknown transactions as potentially either
        return ['Cash', 'Check']
    
    def filter_by_deposit_type_and_date(self, transactions: pd.DataFrame, 
                                       deposit_types: List[str], date: datetime,
                                       forward_days: int = 7) -> pd.DataFrame:
        """
        Filter transactions that could match the given deposit types and date range.
        """
        date_end = date + timedelta(days=forward_days)
        
        # Get transactions in date range
        date_filtered = transactions[
            (transactions['Date'] >= date) &
            (transactions['Date'] <= date_end)
        ].copy()
        
        # Filter by deposit type
        type_filtered = []
        for _, trans in date_filtered.iterrows():
            possible_types = self.identify_deposit_type(trans['Description'])
            if any(dt in possible_types for dt in deposit_types):
                type_filtered.append(trans)
        
        if type_filtered:
            return pd.DataFrame(type_filtered)
        else:
            return pd.DataFrame()
    
    def allocate_gc_1416_optimally(self, gc_1416_transactions: pd.DataFrame,
                                  cash_expected: float, check_expected: float,
                                  tolerance: float = 0.01) -> Dict:
        """
        Optimally allocate GC 1416 transactions between Cash and Check to minimize discrepancy.
        
        This is the key differentiator - we need to decide how to split ambiguous transactions.
        """
        if gc_1416_transactions.empty:
            return {'matched': False, 'reason': 'No GC 1416 transactions found'}
        
        total_gc = gc_1416_transactions['Amount'].sum()
        total_expected = cash_expected + check_expected
        
        # Strategy 1: If total matches exactly, try to allocate proportionally
        if abs(total_gc - total_expected) < tolerance:
            # Try exact matching first
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
                            },
                            'total_difference': (cash_sum + check_sum) - total_expected
                        }
        
        # Strategy 2: Proportional allocation based on expected amounts
        if total_expected > 0:
            cash_ratio = cash_expected / total_expected
            
            # Sort transactions by amount to make allocation more stable
            sorted_trans = gc_1416_transactions.sort_values('Amount', ascending=False)
            
            cash_allocated = 0
            cash_indices = []
            check_indices = []
            
            for idx, trans in sorted_trans.iterrows():
                if cash_allocated < cash_expected * 0.95:  # Leave some buffer
                    cash_indices.append(idx)
                    cash_allocated += trans['Amount']
                else:
                    check_indices.append(idx)
            
            cash_sum = gc_1416_transactions.loc[cash_indices, 'Amount'].sum() if cash_indices else 0
            check_sum = gc_1416_transactions.loc[check_indices, 'Amount'].sum() if check_indices else 0
            
            return {
                'matched': True,
                'match_type': 'gc_1416_proportional_split',
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
                },
                'total_difference': (cash_sum + check_sum) - total_expected
            }
        
        return {'matched': False, 'reason': 'Could not allocate GC 1416 transactions optimally'}
    
    def match_deposit_transactions(self, deposit_slip: pd.DataFrame, 
                                bank_statement: pd.DataFrame,
                                forward_days: int = 14,
                                verbose: bool = False) -> Dict:
        """
        Match deposit slip entries with bank transactions using global optimization.
        First identifies all potential matches, then allocates optimally.
        """
        results = {}
        matched_bank_rows = set()
        
        # Add bank row numbers if not present
        if 'Bank_Row_Number' not in bank_statement.columns:
            bank_statement['Bank_Row_Number'] = range(2, len(bank_statement) + 2)
        
        # PHASE 1: Collect all potential matches for each deposit entry
        all_potential_matches = []
        
        for idx, deposit_row in deposit_slip.iterrows():
            date = deposit_row['Date']
            cash_expected = deposit_row.get('Cash', 0)
            check_expected = deposit_row.get('Check', 0)
            
            if cash_expected == 0 and check_expected == 0:
                continue
            
            # Find all GC 1416 transactions in date range
            date_end = date + timedelta(days=forward_days)
            
            gc_1416_trans = bank_statement[
                ((bank_statement['Description'].str.upper() == 'CASH/CHECK') |
                (bank_statement['Description'].str.contains('Cash/Check', case=False, na=False)) |
                (bank_statement['Description'].str.contains('GC 1416', case=False, na=False))) &
                (bank_statement['Date'] >= date) &
                (bank_statement['Date'] <= date_end)
            ].copy()
            
            if verbose:
                print(f"\nScanning {date.strftime('%Y-%m-%d')}: Cash=${cash_expected:,.2f}, Check=${check_expected:,.2f}")
                print(f"  Found {len(gc_1416_trans)} potential GC 1416 transactions")
            
            # Find best match for Cash if expected
            if cash_expected > 0 and len(gc_1416_trans) > 0:
                best_match = self.find_best_combination(
                    gc_1416_trans, cash_expected, tolerance=0.01, max_ratio=2.0
                )
                if best_match['combo_size'] > 0:
                    all_potential_matches.append({
                        'date': date,
                        'type': 'Cash',
                        'expected': cash_expected,
                        'match': best_match,
                        'priority': best_match['difference']  # Lower difference = higher priority
                    })
            
            # Find best match for Check if expected  
            if check_expected > 0 and len(gc_1416_trans) > 0:
                best_match = self.find_best_combination(
                    gc_1416_trans, check_expected, tolerance=0.01, max_ratio=2.0
                )
                if best_match['combo_size'] > 0:
                    all_potential_matches.append({
                        'date': date,
                        'type': 'Check',
                        'expected': check_expected,
                        'match': best_match,
                        'priority': best_match['difference']
                    })
        
        # PHASE 2: Sort by priority (exact matches first, then by smallest difference)
        all_potential_matches.sort(key=lambda x: (not x['match']['exact'], x['priority']))
        
        if verbose:
            print(f"\n=== PHASE 2: Allocating {len(all_potential_matches)} potential matches ===")
        
        # PHASE 3: Allocate matches, ensuring no transaction is used twice
        for match_info in all_potential_matches:
            date = match_info['date']
            deposit_type = match_info['type']
            best_match = match_info['match']
            
            # Check if any of these bank rows are already used
            available_rows = [r for r in best_match['bank_rows'] if r not in matched_bank_rows]
            
            if len(available_rows) == len(best_match['bank_rows']):
                # All rows available - we can use this match
                if date not in results:
                    results[date] = {
                        'date': date,
                        'matches_by_type': {},
                        'unmatched_by_type': {},
                        'best_matches': {}
                    }
                
                if best_match['exact']:
                    # Exact match
                    results[date]['matches_by_type'][deposit_type] = {
                        'expected': match_info['expected'],
                        'match_type': 'exact' if best_match['combo_size'] == 1 else f'exact_combo_{best_match["combo_size"]}',
                        'transactions': best_match['transactions'],
                        'bank_rows': best_match['bank_rows'],
                        'actual_total': best_match['total'],
                        'difference': best_match['difference']
                    }
                    matched_bank_rows.update(best_match['bank_rows'])
                    
                    if verbose:
                        print(f"  ✓ {date.strftime('%Y-%m-%d')} {deposit_type}: Exact match ${best_match['total']:,.2f}")
                else:
                    # Approximate match - still claim it to prevent reuse
                    results[date]['unmatched_by_type'][deposit_type] = {
                        'expected': match_info['expected'],
                        'reason': f'Best match: ${best_match["total"]:.2f} (diff: ${best_match["difference"]:.2f})',
                        'best_match': best_match
                    }
                    results[date]['best_matches'][deposit_type] = best_match
                    matched_bank_rows.update(best_match['bank_rows'])
                    
                    if verbose:
                        print(f"  ⚠ {date.strftime('%Y-%m-%d')} {deposit_type}: Approx match ${best_match['total']:,.2f} (diff: ${best_match['difference']:.2f})")
            else:
                # Some/all rows already used
                if verbose:
                    print(f"  ✗ {date.strftime('%Y-%m-%d')} {deposit_type}: Match unavailable (rows already used)")
        
        # PHASE 4: Mark remaining unmatched entries
        for _, deposit_row in deposit_slip.iterrows():
            date = deposit_row['Date']
            
            if date not in results:
                results[date] = {
                    'date': date,
                    'matches_by_type': {},
                    'unmatched_by_type': {},
                    'best_matches': {}
                }
            
            for deposit_type in ['Cash', 'Check']:
                expected = deposit_row.get(deposit_type, 0)
                if expected > 0:
                    if deposit_type not in results[date]['matches_by_type'] and \
                    deposit_type not in results[date]['unmatched_by_type']:
                        # No match found at all
                        results[date]['unmatched_by_type'][deposit_type] = {
                            'expected': expected,
                            'reason': 'No matching GC 1416 transactions found',
                            'best_match': None
                        }
        
        # CRITICAL: Add metadata - This is what was missing!
        results['_matched_bank_rows'] = matched_bank_rows
        results['_gc_1416_allocations'] = {}
        
        if verbose:
            print(f"\nDEBUG: Returning {len(matched_bank_rows)} matched bank rows")
        
        return results
    
    def find_best_combination(self, transactions: pd.DataFrame, target: float, 
                            tolerance: float = 0.01, max_ratio: float = 2.0) -> Dict:
        """
        Find the best combination of transactions that matches the target amount.
        Returns the closest match even if not exact.
        
        Args:
            transactions: DataFrame of available transactions
            target: Target amount to match
            tolerance: Tolerance for exact matching (default 0.01)
            max_ratio: Maximum ratio between match and target (default 2.0)
                    Rejects matches > 2x or < 0.5x the target
        """
        from itertools import combinations
        
        best_diff = float('inf')
        best_combo = None
        best_indices = None
        
        # Try all combinations from 1 to all transactions (max 10 for performance)
        max_combo_size = min(len(transactions), 10)
        
        for r in range(1, max_combo_size + 1):
            for combo_indices in combinations(transactions.index, r):
                combo_sum = transactions.loc[list(combo_indices), 'Amount'].sum()
                diff = abs(combo_sum - target)
                
                if diff < best_diff:
                    best_diff = diff
                    best_combo = list(combo_indices)
                    
                    # If exact match found, we can stop
                    if diff <= tolerance:
                        break
            
            # If exact match found, stop looking
            if best_diff <= tolerance:
                break
        
        # Build result
        if best_combo:
            selected_trans = transactions.loc[best_combo]
            total = selected_trans['Amount'].sum()
            
            # Sanity check - reject if match is way off
            if target > 0:
                ratio = total / target
                if ratio > max_ratio or ratio < (1/max_ratio):
                    # This match is too far off - return no match instead
                    return {
                        'exact': False,
                        'total': 0,
                        'difference': target,
                        'combo_size': 0,
                        'transactions': [],
                        'bank_rows': [],
                        'dates': []
                    }
            
            return {
                'exact': best_diff <= tolerance,
                'total': total,
                'difference': best_diff,
                'combo_size': len(best_combo),
                'transactions': selected_trans.to_dict('records'),
                'bank_rows': selected_trans['Bank_Row_Number'].tolist(),
                'dates': selected_trans['Date'].tolist()
            }
        
        # No combination found at all
        return {
            'exact': False,
            'total': 0,
            'difference': target,
            'combo_size': 0,
            'transactions': [],
            'bank_rows': [],
            'dates': []
        }
    
    def generate_deposit_report(self, results: dict, output_path: str = 'deposit_matching_report.xlsx'):
        """
        Generate Excel report for deposit matching results.
        """
        summary_data = []
        allocation_details = []
        
        # Extract GC 1416 allocations if present
        gc_1416_allocations = results.pop('_gc_1416_allocations', {})
        matched_bank_rows = results.pop('_matched_bank_rows', set())
        
        for date, date_results in results.items():
            # Process matches
            for deposit_type, match_info in date_results['matches_by_type'].items():
                summary_data.append({
                    'Date': date,
                    'Type': deposit_type,
                    'Expected': match_info['expected'],
                    'Actual': match_info['actual_total'],
                    'Difference': match_info['difference'],
                    'Match_Type': match_info['match_type'],
                    'Status': 'Matched',
                    'Bank_Rows': ', '.join(map(str, match_info['bank_rows']))
                })
                
                # Add transaction details
                for trans in match_info['transactions']:
                    allocation_details.append({
                        'Date': date,
                        'Deposit_Type': deposit_type,
                        'Bank_Row': trans['Bank_Row_Number'],
                        'Transaction_Date': trans['Date'],
                        'Description': trans['Description'],
                        'Amount': trans['Amount']
                    })
            
            # Process unmatched
            for deposit_type, unmatch_info in date_results['unmatched_by_type'].items():
                summary_data.append({
                    'Date': date,
                    'Type': deposit_type,
                    'Expected': unmatch_info['expected'],
                    'GC_1416_Found': unmatch_info.get('gc_1416_found', 0),
                    'Status': 'Unmatched',
                    'Reason': unmatch_info['reason']
                })
        
        # Write to Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            if summary_data:
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            if allocation_details:
                pd.DataFrame(allocation_details).to_excel(writer, sheet_name='GC_1416_Allocations', index=False)
        
        print(f"✓ Deposit matching report saved to: {output_path}")

# Example usage function
def process_deposit_slip(deposit_slip_path: str, bank_statement_path: str,
                        output_dir: str = '.', verbose: bool = False):
    """
    Complete deposit slip processing workflow.
    """
    from processors.preprocess_deposit_slip import preprocess_deposit_slip_dynamic, create_highlighted_deposit_slip
    from processors.preprocess_bank_statement import preprocess_bank_statement
    
    print("=== Deposit Slip Matching System ===\n")
    
    # Load data
    print("Step 1: Loading data...")
    deposit_slip, structure_info = preprocess_deposit_slip_dynamic(deposit_slip_path)
    bank_statement = preprocess_bank_statement(bank_statement_path)
    
    print(f"✓ Loaded deposit slip: {len(deposit_slip)} days")
    print(f"✓ Loaded bank statement: {len(bank_statement)} transactions")
    
    # Run matching
    print("\nStep 2: Running deposit matching...")
    matcher = DepositMatcher()
    results = matcher.match_deposit_transactions(deposit_slip, bank_statement, 
                                                forward_days=14, verbose=verbose)
    
    # Extract info for highlighting
    gc_1416_allocations = results.get('_gc_1416_allocations', {})
    matched_bank_rows = results.get('_matched_bank_rows', set())
    
    # Create matched dates dict for highlighting
    matched_dates_and_types = {}
    unmatched_info = {}
    
    for date, date_results in results.items():
        if date == '_gc_1416_allocations' or date == '_matched_bank_rows':
            continue
        
        matched_types = []
        for deposit_type in date_results['matches_by_type'].keys():
            matched_types.append(deposit_type)
        
        if matched_types:
            matched_dates_and_types[date] = matched_types
        
        for deposit_type, unmatch_info in date_results['unmatched_by_type'].items():
            unmatched_info[(date, deposit_type)] = unmatch_info
    
    # Generate report
    print("\nStep 3: Generating reports...")
    report_path = f"{output_dir}/deposit_matching_report.xlsx"
    matcher.generate_deposit_report(results, report_path)
    
    # Create highlighted deposit slip
    highlighted_path = f"{output_dir}/deposit_slip_highlighted.xlsx"
    create_highlighted_deposit_slip(
        deposit_slip_path=deposit_slip_path,
        matched_dates_and_types=matched_dates_and_types,
        output_path=highlighted_path,
        unmatched_info=unmatched_info,
        gc_1416_allocation=gc_1416_allocations
    )
    
    # Create highlighted bank statement
    from highlighting_functions import create_highlighted_bank_statement
    bank_highlighted_path = f"{output_dir}/bank_statement_deposit_highlighted.xlsx"
    create_highlighted_bank_statement(
        bank_statement_path=bank_statement_path,
        matched_bank_rows=matched_bank_rows,
        output_path=bank_highlighted_path
    )
    
    print("\n=== DEPOSIT PROCESSING COMPLETE ===")
    print(f"Generated files:")
    print(f"  1. {report_path}")
    print(f"  2. {highlighted_path}")
    print(f"  3. {bank_highlighted_path}")
    
    return results

if __name__ == "__main__":
    # Test the deposit matcher
    results = process_deposit_slip(
        deposit_slip_path='XYZ Storage Laird - MonthlyDepositSlip - 06-01-2025 - 06-30-2025 (2).xlsx',
        bank_statement_path='june 2025 bank statement.CSV',
        verbose=True
    )