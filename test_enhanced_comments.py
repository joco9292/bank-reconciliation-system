#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced commenting functionality for all transaction types.
This includes matched, unmatched, and GC (Cash & Check) transactions.
"""

import pandas as pd
import sys
import os
from datetime import datetime

# Add the current directory to the path
sys.path.append(os.path.dirname(__file__))

def create_comprehensive_test_data():
    """Create comprehensive test data with all transaction types."""
    # Bank statement with various transaction types
    bank_data = {
        'Date': ['2025-01-15', '2025-01-16', '2025-01-17', '2025-01-18', '2025-01-19', '2025-01-20'],
        'Description': [
            'VISA 1234 PURCHASE',           # Matched transaction
            'AMEX 5678 CHARGE',             # Matched transaction  
            'UNKNOWN TRANSACTION',          # Unmatched transaction
            'GC 1416-DEPOSIT',              # GC transaction
            'MASTERCARD 9999 DEBIT',        # Matched transaction
            'CASH/CHECK DEPOSIT'            # GC transaction
        ],
        'Amount': [150.00, 75.50, 200.25, 500.00, 300.75, 750.00],
        'Transaction_Type': ['CREDIT', 'CREDIT', 'CREDIT', 'CREDIT', 'CREDIT', 'CREDIT']
    }
    
    df = pd.DataFrame(bank_data)
    df['Bank_Row_Number'] = range(2, len(df) + 2)
    df['Card_Type'] = df['Description'].apply(lambda x: 
        'Visa' if 'VISA' in x else 
        'Amex' if 'AMEX' in x else 
        'Master Card' if 'MASTERCARD' in x else 
        'GC' if 'GC 1416' in x or 'CASH/CHECK' in x else 
        'Unknown'
    )
    
    df.to_csv('comprehensive_bank_statement.csv', index=False)
    return 'comprehensive_bank_statement.csv'

def create_comprehensive_matching_results():
    """Create comprehensive matching results with all transaction types."""
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
        },
        '2025-01-19': {
            'matches_by_card_type': {
                'Master Card': {
                    'expected': 300.75,
                    'actual_total': 300.75,
                    'difference': 0.00,
                    'match_type': 'exact',
                    'bank_rows': [6],  # Excel row 6
                    'transactions': [{
                        'Bank_Row_Number': 6,
                        'Date': '2025-01-19',
                        'Description': 'MASTERCARD 9999 DEBIT',
                        'Amount': 300.75,
                        'Card_Type': 'Master Card'
                    }]
                }
            },
            'unmatched_by_card_type': {}
        },
        '2025-01-20': {
            'matches_by_card_type': {},
            'unmatched_by_card_type': {}
        }
    }
    return results

def test_enhanced_commenting():
    """Test the enhanced commenting functionality."""
    print("=== Testing Enhanced Commenting for All Transaction Types ===\n")
    
    # Create test data
    bank_statement_path = create_comprehensive_test_data()
    print(f"✓ Created comprehensive test data: {bank_statement_path}")
    
    # Load the bank statement
    bank_statement = pd.read_csv(bank_statement_path)
    bank_statement['Bank_Row_Number'] = range(2, len(bank_statement) + 2)
    bank_statement['Card_Type'] = bank_statement['Description'].apply(lambda x: 
        'Visa' if 'VISA' in x else 
        'Amex' if 'AMEX' in x else 
        'Master Card' if 'MASTERCARD' in x else 
        'GC' if 'GC 1416' in x or 'CASH/CHECK' in x else 
        'Unknown'
    )
    
    # Create matching results
    results = create_comprehensive_matching_results()
    print("✓ Created comprehensive matching results")
    
    # Extract all transaction types
    from highlighting_functions import (
        create_highlighted_bank_statement,
        extract_transaction_details_for_comments,
        extract_unmatched_transactions_for_comments,
        extract_gc_transactions_for_comments
    )
    
    # Extract transaction details
    matched_bank_rows = {2, 3, 6}  # Rows 2, 3, and 6 are matched
    differences_by_row = {2: 0.00, 3: 0.00, 6: 0.00}
    
    transaction_details, match_type_info = extract_transaction_details_for_comments(results, bank_statement)
    unmatched_transactions = extract_unmatched_transactions_for_comments(results, bank_statement)
    gc_transactions = extract_gc_transactions_for_comments(results, bank_statement)
    
    print(f"✓ Extracted transaction details:")
    print(f"  - Matched transactions: {len(transaction_details)}")
    print(f"  - Unmatched transactions: {len(unmatched_transactions)}")
    print(f"  - GC transactions: {len(gc_transactions)}")
    
    # Create highlighted bank statement with all comment types
    output_path = 'comprehensive_bank_statement_highlighted_with_all_comments.xlsx'
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
    
    print(f"✓ Created comprehensive highlighted bank statement: {output_path}")
    
    # Show what comments were added
    print("\n=== Comments Added by Transaction Type ===")
    
    print("\n🟢 MATCHED TRANSACTIONS (Green highlighting):")
    for bank_row, details in transaction_details.items():
        print(f"  Row {bank_row}: {details['Description']} - ${details['Amount']:,.2f}")
        print(f"    Match Type: {match_type_info.get(bank_row, 'Unknown')}")
    
    print("\n🔴 UNMATCHED TRANSACTIONS (Red highlighting):")
    for bank_row, details in unmatched_transactions.items():
        print(f"  Row {bank_row}: {details['Description']} - ${details['Amount']:,.2f}")
        print(f"    Reason: {details['reason']}")
        print(f"    Filters Tried: {', '.join(details['filters_tried'])}")
    
    print("\n🔵 GC TRANSACTIONS (Blue highlighting):")
    for bank_row, details in gc_transactions.items():
        print(f"  Row {bank_row}: {details['Description']} - ${details['Amount']:,.2f}")
        print(f"    Transaction Type: {details['match_type']}")
        if 'allocation' in details:
            print(f"    Cash Allocation: ${details['allocation']['cash_amount']:,.2f}")
            print(f"    Check Allocation: ${details['allocation']['check_amount']:,.2f}")
    
    print(f"\n=== Instructions ===")
    print(f"1. Open the file '{output_path}' in Excel")
    print(f"2. Hover over the first cell of highlighted rows to see comments:")
    print(f"   - 🟢 Green rows: Matched transactions with match details")
    print(f"   - 🔴 Red rows: Unmatched transactions with failure reasons")
    print(f"   - 🔵 Blue rows: GC transactions with allocation details")
    print(f"3. Comments provide detailed information about each transaction type")
    print(f"4. This demonstrates comprehensive commenting for all transaction types")
    
    # Clean up
    try:
        os.remove(bank_statement_path)
        print(f"\n✓ Cleaned up test file: {bank_statement_path}")
    except:
        pass

if __name__ == "__main__":
    test_enhanced_commenting()
