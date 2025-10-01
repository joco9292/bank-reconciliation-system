#!/usr/bin/env python3
"""
Test script to demonstrate the corrected commenting functionality.
Comments now show what the bank transaction matched FROM (card summary or deposit slip).
"""

import pandas as pd
import sys
import os
from datetime import datetime

# Add the current directory to the path
sys.path.append(os.path.dirname(__file__))

def create_test_data():
    """Create test data with bank statement and matching results."""
    # Bank statement
    bank_data = {
        'Date': ['2025-01-15', '2025-01-16', '2025-01-17', '2025-01-18'],
        'Description': [
            'VISA 1234 PURCHASE',           # Will match from card summary
            'AMEX 5678 CHARGE',             # Will match from card summary
            'UNKNOWN TRANSACTION',          # Will be unmatched
            'GC 1416-DEPOSIT'               # Will match from deposit slip
        ],
        'Amount': [150.00, 75.50, 200.25, 500.00],
        'Transaction_Type': ['CREDIT', 'CREDIT', 'CREDIT', 'CREDIT']
    }
    
    df = pd.DataFrame(bank_data)
    df['Bank_Row_Number'] = range(2, len(df) + 2)
    df['Card_Type'] = df['Description'].apply(lambda x: 
        'Visa' if 'VISA' in x else 
        'Amex' if 'AMEX' in x else 
        'GC' if 'GC 1416' in x else 
        'Unknown'
    )
    
    df.to_csv('test_bank_statement.csv', index=False)
    return 'test_bank_statement.csv'

def create_matching_results():
    """Create matching results that show what each bank transaction matched from."""
    results = {
        '2025-01-15': {
            'matches_by_card_type': {
                'Visa': {
                    'expected': 150.00,
                    'actual_total': 150.00,
                    'difference': 0.00,
                    'match_type': 'exact',
                    'bank_rows': [2],  # Excel row 2
                    'transactions': [{
                        'Bank_Row_Number': 2,
                        'Date': '2025-01-15',
                        'Description': 'VISA 1234 PURCHASE',
                        'Amount': 150.00,
                        'Card_Type': 'Visa'
                    }]
                }
            },
            'unmatched_by_card_type': {}
        },
        '2025-01-16': {
            'matches_by_card_type': {
                'Amex': {
                    'expected': 75.50,
                    'actual_total': 75.50,
                    'difference': 0.00,
                    'match_type': 'exact',
                    'bank_rows': [3],  # Excel row 3
                    'transactions': [{
                        'Bank_Row_Number': 3,
                        'Date': '2025-01-16',
                        'Description': 'AMEX 5678 CHARGE',
                        'Amount': 75.50,
                        'Card_Type': 'Amex'
                    }]
                }
            },
            'unmatched_by_card_type': {}
        },
        '2025-01-17': {
            'matches_by_card_type': {},
            'unmatched_by_card_type': {
                'Unknown': {
                    'expected': 200.25,
                    'found_transactions': 1,
                    'total_found': 200.25,
                    'reason': 'No matching card type found',
                    'filters_tried': ['exact_match', 'amount_range'],
                    'bank_rows': [4]  # Excel row 4
                }
            }
        },
        '2025-01-18': {
            'matches_by_card_type': {},
            'unmatched_by_card_type': {}
        }
    }
    return results

def test_source_comments():
    """Test the corrected commenting functionality."""
    print("=== Testing Source-Based Comments ===\n")
    print("Comments now show what the bank transaction matched FROM (card summary or deposit slip)\n")
    
    # Create test data
    bank_statement_path = create_test_data()
    print(f"✓ Created test bank statement: {bank_statement_path}")
    
    # Load the bank statement
    bank_statement = pd.read_csv(bank_statement_path)
    bank_statement['Bank_Row_Number'] = range(2, len(bank_statement) + 2)
    bank_statement['Card_Type'] = bank_statement['Description'].apply(lambda x: 
        'Visa' if 'VISA' in x else 
        'Amex' if 'AMEX' in x else 
        'GC' if 'GC 1416' in x else 
        'Unknown'
    )
    
    # Create matching results
    results = create_matching_results()
    print("✓ Created matching results")
    
    # Extract transaction details
    from highlighting_functions import (
        create_highlighted_bank_statement,
        extract_transaction_details_for_comments,
        extract_unmatched_transactions_for_comments,
        extract_gc_transactions_for_comments
    )
    
    matched_bank_rows = {2, 3}  # Rows 2 and 3 are matched
    differences_by_row = {2: 0.00, 3: 0.00}
    
    transaction_details, match_type_info = extract_transaction_details_for_comments(results, bank_statement)
    unmatched_transactions = extract_unmatched_transactions_for_comments(results, bank_statement)
    gc_transactions = extract_gc_transactions_for_comments(results, bank_statement)
    
    print(f"✓ Extracted transaction details:")
    print(f"  - Matched transactions: {len(transaction_details)}")
    print(f"  - Unmatched transactions: {len(unmatched_transactions)}")
    print(f"  - GC transactions: {len(gc_transactions)}")
    
    # Create highlighted bank statement with source-based comments
    output_path = 'test_bank_statement_with_source_comments.xlsx'
    create_highlighted_bank_statement(
        bank_statement_path=bank_statement_path,
        matched_bank_rows=matched_bank_rows,
        output_path=output_path,
        differences_by_row=differences_by_row,
        transaction_details=transaction_details,
        match_type_info=match_type_info,
        unmatched_transactions=unmatched_transactions,
        gc_transactions=gc_transactions
    )
    
    print(f"✓ Created highlighted bank statement: {output_path}")
    
    # Show what comments were added
    print("\n=== Source-Based Comments Added ===")
    
    print("\n🟢 MATCHED TRANSACTIONS (Green highlighting):")
    print("Comments show what they matched FROM the card summary:")
    for bank_row, details in transaction_details.items():
        print(f"  Row {bank_row}: {details['Description']} - ${details['Amount']:,.2f}")
        print(f"    → Matched from Card Summary: {details.get('Date', 'Unknown')} {details.get('Card_Type', 'Unknown')} ${details.get('Expected_Amount', 0):,.2f}")
    
    print("\n🔴 UNMATCHED TRANSACTIONS (Red highlighting):")
    print("Comments show what they tried to match FROM the card summary:")
    for bank_row, details in unmatched_transactions.items():
        print(f"  Row {bank_row}: {details['Description']} - ${details['Amount']:,.2f}")
        print(f"    → Tried to match from Card Summary: {details.get('Date', 'Unknown')} {details.get('Card_Type', 'Unknown')} ${details.get('expected', 0):,.2f}")
        print(f"    → Reason: {details.get('reason', 'Unknown')}")
    
    print("\n🔵 GC TRANSACTIONS (Blue highlighting):")
    print("Comments show what they matched FROM the deposit slip:")
    for bank_row, details in gc_transactions.items():
        print(f"  Row {bank_row}: {details['Description']} - ${details['Amount']:,.2f}")
        print(f"    → Matched from Deposit Slip: {details.get('Date', 'Unknown')} GC (Cash & Check) ${details.get('Amount', 0):,.2f}")
    
    print(f"\n=== Instructions ===")
    print(f"1. Open the file '{output_path}' in Excel")
    print(f"2. Hover over the first cell of highlighted rows to see comments")
    print(f"3. Comments now show what each bank transaction matched FROM:")
    print(f"   - 🟢 Green: 'Matched from Card Summary: [date] [card type] $[amount]'")
    print(f"   - 🔴 Red: 'Tried to match from Card Summary: [date] [card type] $[amount]'")
    print(f"   - 🔵 Blue: 'Matched from Deposit Slip: [date] [type] $[amount]'")
    print(f"4. This shows the source of each match, not just the bank transaction details")
    
    # Clean up
    try:
        os.remove(bank_statement_path)
        print(f"\n✓ Cleaned up test file: {bank_statement_path}")
    except:
        pass

if __name__ == "__main__":
    test_source_comments()
