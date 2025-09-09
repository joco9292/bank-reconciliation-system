import pandas as pd
from datetime import datetime
from preprocess_bank_statement import preprocess_bank_statement
from preprocess_card_summary import preprocess_card_summary_dynamic
from matching_helpers import identify_card_type, TransactionMatcher

def prepare_data_for_matching(card_summary: pd.DataFrame, bank_statement: pd.DataFrame) -> tuple:
    """Add additional columns needed for matching process."""
    bank_statement['Bank_Row_Number'] = range(2, len(bank_statement) + 2)
    bank_statement['Card_Type'] = bank_statement['Description'].apply(identify_card_type)
    return card_summary, bank_statement

def debug_mastercard_differences():
    """Find and display all Master Card matches with non-zero differences."""
    
    # Load data
    bank_statement = preprocess_bank_statement('june 2025 bank statement.CSV')
    card_summary, _ = preprocess_card_summary_dynamic('card summary june.xlsx')
    card_summary, bank_statement = prepare_data_for_matching(card_summary, bank_statement)
    
    # Run matching
    matcher = TransactionMatcher()
    results = matcher.match_transactions(card_summary, bank_statement, forward_days=3)
    
    print("=== MASTER CARD MATCHES WITH DIFFERENCES ===\n")
    
    total_mc_difference = 0
    problematic_matches = []
    
    for date, date_results in results.items():
        for card_type, match_info in date_results['matches_by_card_type'].items():
            if card_type == 'Master Card':
                diff = match_info.get('difference', 0)
                if abs(diff) > 0.01:  # Non-zero difference
                    problematic_matches.append({
                        'date': date,
                        'expected': match_info['expected'],
                        'actual_total': match_info.get('actual_total', match_info['expected']),
                        'difference': diff,
                        'match_type': match_info['match_type'],
                        'bank_rows': match_info['bank_rows'],
                        'transactions': match_info['transactions']
                    })
                    total_mc_difference += diff
    
    # Display problematic matches
    for match in problematic_matches:
        print(f"Date: {match['date'].strftime('%Y-%m-%d')}")
        print(f"  Match Type: {match['match_type']}")
        print(f"  Expected: ${match['expected']:,.2f}")
        print(f"  Actual Total: ${match['actual_total']:,.2f}")
        print(f"  Difference: ${match['difference']:,.2f}")
        print(f"  Bank Rows: {match['bank_rows']}")
        
        # Show the individual transactions that were matched
        print("  Transactions matched:")
        for trans in match['transactions']:
            print(f"    Row {trans['Bank_Row_Number']}: {trans['Date'].strftime('%Y-%m-%d')} "
                  f"{trans['Description'][:30]} ${trans['Amount']:,.2f}")
        print()
    
    print(f"\nTotal Master Card difference: ${total_mc_difference:,.2f}")
    print(f"Number of problematic matches: {len(problematic_matches)}")
    
    # Check if this is a systematic issue
    if len(problematic_matches) > 0:
        avg_diff = total_mc_difference / len(problematic_matches)
        print(f"Average difference per match: ${avg_diff:,.2f}")
        
        # Check if differences are consistent (possible fee or rounding issue)
        differences = [m['difference'] for m in problematic_matches]
        if len(set([round(d, 2) for d in differences])) == 1:
            print("\n⚠️ All differences are the same amount - possible systematic fee or conversion issue")
        elif all(d > 0 for d in differences):
            print("\n⚠️ All differences are positive - bank amounts consistently higher than expected")
        elif all(d < 0 for d in differences):
            print("\n⚠️ All differences are negative - bank amounts consistently lower than expected")

if __name__ == "__main__":
    debug_mastercard_differences()