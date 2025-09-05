import pandas as pd

def calculate_total_discrepancies_by_card_type_exclusive(results: dict, bank_statement: pd.DataFrame, 
                                                        matched_bank_rows: set) -> dict:
    """
    Calculate total discrepancies with EXCLUSIVE transaction allocation.
    Each bank transaction is used at most once in discrepancy calculations.
    
    Returns:
        dict: Card type -> net discrepancy (positive = bank has more, negative = card summary expects more)
    """
    discrepancies_by_type = {}
    
    # Get the allocation mapping if available
    allocated_for_discrepancy = results.get('_allocated_for_discrepancy', {})
    
    # Find the first matched transaction date
    first_matched_date = find_first_matched_date(matched_bank_rows, bank_statement)
    
    # Track all bank rows that have been used in calculations
    used_bank_rows = set()
    
    # Step 1: Add matched bank rows to used set
    used_bank_rows.update(matched_bank_rows)
    
    # Step 2: Process unmatched card summary expectations
    # These subtract from the discrepancy (we expected money but didn't find it)
    for date, date_results in results.items():
        if isinstance(date, str) and date.startswith('_'):  # Skip metadata keys
            continue
            
        for card_type, unmatch_info in date_results['unmatched_by_card_type'].items():
            if card_type not in discrepancies_by_type:
                discrepancies_by_type[card_type] = 0
            
            # Subtract what we expected but didn't find
            expected = unmatch_info.get('expected', 0)
            discrepancies_by_type[card_type] -= expected
            
            # Add what we actually found (exclusively allocated)
            total_found = unmatch_info.get('total_found', 0)
            if total_found > 0:
                discrepancies_by_type[card_type] += total_found
                # Mark these bank rows as used
                bank_rows = unmatch_info.get('bank_rows', [])
                used_bank_rows.update(bank_rows)
    
    # Step 3: Add any remaining unmatched bank transactions
    # Only count transactions that haven't been used anywhere
    if first_matched_date:
        remaining_unmatched = bank_statement[
            (~bank_statement['Bank_Row_Number'].isin(used_bank_rows)) &
            (bank_statement['Date'] > first_matched_date)
        ]
    else:
        # If no matches at all, count all unused bank transactions
        remaining_unmatched = bank_statement[~bank_statement['Bank_Row_Number'].isin(used_bank_rows)]
    
    # Sum remaining unmatched by card type
    for card_type in remaining_unmatched['Card_Type'].unique():
        if card_type != 'Unknown':
            type_df = remaining_unmatched[remaining_unmatched['Card_Type'] == card_type]
            if card_type not in discrepancies_by_type:
                discrepancies_by_type[card_type] = 0
            # Add what we found but didn't expect
            discrepancies_by_type[card_type] += type_df['Amount'].sum()
    
    return discrepancies_by_type, first_matched_date

def find_first_matched_date(matched_bank_rows: set, bank_statement: pd.DataFrame) -> pd.Timestamp:
    """
    Find the date of the earliest matched transaction.
    """
    if not matched_bank_rows:
        return None
    
    matched_transactions = bank_statement[bank_statement['Bank_Row_Number'].isin(matched_bank_rows)]
    if matched_transactions.empty:
        return None
    
    return matched_transactions['Date'].min()

def print_matching_summary_with_exclusive_allocation(results: dict, discrepancies_by_type: dict, first_matched_date):
    """
    Print a summary of matching results with exclusive allocation details.
    """
    total_matches = 0
    total_unmatched = 0
    matches_by_type = {}
    exclusive_allocations = 0
    
    for date, date_results in results.items():
        # Skip metadata keys (strings starting with underscore)
        if isinstance(date, str) and date.startswith('_'):
            continue
            
        total_matches += len(date_results['matches_by_card_type'])
        total_unmatched += len(date_results['unmatched_by_card_type'])
        
        for match_info in date_results['matches_by_card_type'].values():
            match_type = match_info['match_type']
            matches_by_type[match_type] = matches_by_type.get(match_type, 0) + 1
        
        # Count exclusive allocations
        for unmatch_info in date_results['unmatched_by_card_type'].values():
            if unmatch_info.get('exclusive_allocation', False):
                exclusive_allocations += 1
    
    print("\n=== MATCHING SUMMARY (WITH EXCLUSIVE ALLOCATION) ===")
    print(f"Total matched: {total_matches}")
    print(f"Total unmatched: {total_unmatched}")
    print(f"Exclusive allocations made: {exclusive_allocations}")
    
    print(f"\nMatches by type:")
    for match_type, count in matches_by_type.items():
        print(f"  - {match_type}: {count}")
    
    # Print discrepancies by card type
    print("\n=== NET DISCREPANCIES BY CARD TYPE (EXCLUSIVE) ===")
    if first_matched_date:
        print(f"(Calculated from {first_matched_date.strftime('%Y-%m-%d')} onwards)")
        print("Note: Each bank transaction used at most once\n")
    
    total_discrepancy = 0
    for card_type, disc in sorted(discrepancies_by_type.items()):
        if abs(disc) > 0.01:  # Only show non-zero discrepancies
            if disc > 0:
                print(f"{card_type}: +${disc:,.2f} (bank has more than expected)")
            else:
                print(f"{card_type}: -${abs(disc):,.2f} (bank has less than expected)")
            total_discrepancy += disc
    
    print(f"\nTotal net discrepancy: ${total_discrepancy:,.2f}")
    if total_discrepancy > 0:
        print("(Positive = bank statement total exceeds card summary expectations)")
    elif total_discrepancy < 0:
        print("(Negative = card summary expects more than bank statement shows)")
    
    # Check if allocation info is available
    allocated_info = results.get('_allocated_for_discrepancy', {})
    if allocated_info:
        print(f"\n📌 Exclusive allocation details:")
        print(f"  - {len(allocated_info)} bank transactions exclusively allocated")
        print(f"  - Each transaction assigned to exactly one card summary cell")