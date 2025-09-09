import pandas as pd
from datetime import datetime
from preprocess_bank_statement import preprocess_bank_statement
from preprocess_card_summary import preprocess_card_summary_dynamic
from matching_helpers import identify_card_type

def debug_matching_issues():
    """Debug why zero matches are occurring."""
    
    print("=== DEBUGGING MATCHING ISSUES ===\n")
    
    # Load data
    print("1. Loading data...")
    bank_statement = preprocess_bank_statement('july 2025 bank statement.CSV')
    card_summary, _ = preprocess_card_summary_dynamic('XYZ Storage Laird - CreditCardSummary - 07-01-2025 - 07-31-2025 (4).xlsx')
    
    # Add bank row numbers and card types
    bank_statement['Bank_Row_Number'] = range(2, len(bank_statement) + 2)
    bank_statement['Card_Type'] = bank_statement['Description'].apply(identify_card_type)
    
    # Check date ranges
    print("\n2. Date Range Analysis:")
    print(f"Bank Statement dates: {bank_statement['Date'].min()} to {bank_statement['Date'].max()}")
    print(f"Card Summary dates: {card_summary['Date'].min()} to {card_summary['Date'].max()}")
    
    # Check if dates overlap
    bank_dates = set(bank_statement['Date'].dt.date)
    card_dates = set(card_summary['Date'].dt.date)
    overlapping_dates = bank_dates.intersection(card_dates)
    
    print(f"\nOverlapping dates: {len(overlapping_dates)} days")
    if len(overlapping_dates) == 0:
        print("⚠️ WARNING: No overlapping dates between bank statement and card summary!")
        print("This is likely why no matches are found.")
        
        # Show some sample dates
        print("\nSample bank statement dates:")
        for date in sorted(bank_dates)[:5]:
            print(f"  {date}")
        print("\nSample card summary dates:")
        for date in sorted(card_dates)[:5]:
            print(f"  {date}")
    
    # Check card types
    print("\n3. Card Type Analysis:")
    
    # Card types in bank statement
    bank_card_types = bank_statement['Card_Type'].value_counts()
    print("\nBank statement card types:")
    for card_type, count in bank_card_types.items():
        print(f"  {card_type}: {count}")
    
    # Card types in card summary (columns)
    card_summary_types = [col for col in card_summary.columns 
                          if col not in ['Date', 'Total', 'Visa & MC'] 
                          and not col.startswith('Unnamed')]
    print(f"\nCard summary columns: {card_summary_types}")
    
    # Check for mismatches
    print("\n4. Card Type Matching Issues:")
    
    # Check if Cash and Check are in card summary but not properly identified in bank
    if 'Cash' in card_summary_types or 'Check' in card_summary_types:
        gc_1416_count = bank_statement[
            bank_statement['Description'].str.contains('GC 1416', case=False, na=False) |
            bank_statement['Description'].str.contains('Cash/Check', case=False, na=False)
        ].shape[0]
        print(f"  GC 1416/Cash/Check transactions in bank: {gc_1416_count}")
    
    # Show sample transactions for each card type
    print("\n5. Sample Transactions by Card Type:")
    for card_type in ['Visa', 'Master Card', 'Amex', 'Debit Visa', 'Cash']:
        if card_type in bank_card_types.index:
            sample = bank_statement[bank_statement['Card_Type'] == card_type].head(2)
            if not sample.empty:
                print(f"\n{card_type}:")
                for _, row in sample.iterrows():
                    print(f"  {row['Date'].strftime('%Y-%m-%d')}: {row['Description'][:40]} ${row['Amount']:.2f}")
    
    # Check specific date matching
    print("\n6. Specific Date Matching Test:")
    
    # Pick a date that should have matches
    test_date = None
    for date in card_summary['Date']:
        if card_summary[card_summary['Date'] == date]['Visa'].sum() > 0:
            test_date = date
            break
    
    if test_date:
        print(f"\nTesting date: {test_date.strftime('%Y-%m-%d')}")
        
        # Get expected amounts for this date
        card_row = card_summary[card_summary['Date'] == test_date].iloc[0]
        print(f"Expected amounts on this date:")
        for card_type in card_summary_types:
            amount = card_row[card_type]
            if amount > 0:
                print(f"  {card_type}: ${amount:.2f}")
        
        # Get bank transactions around this date
        from datetime import timedelta
        date_end = test_date + timedelta(days=3)
        
        nearby_trans = bank_statement[
            (bank_statement['Date'] >= test_date) &
            (bank_statement['Date'] <= date_end)
        ]
        
        print(f"\nBank transactions from {test_date.strftime('%Y-%m-%d')} to {date_end.strftime('%Y-%m-%d')}:")
        if nearby_trans.empty:
            print("  No transactions found in this date range!")
        else:
            for _, row in nearby_trans.head(10).iterrows():
                print(f"  {row['Date'].strftime('%Y-%m-%d')}: {row['Card_Type']:12} ${row['Amount']:8.2f} - {row['Description'][:30]}")
    
    # Check for potential file mismatch
    print("\n7. File Consistency Check:")
    
    # Check if bank statement has mostly Unknown card types
    unknown_pct = (bank_card_types.get('Unknown', 0) / len(bank_statement)) * 100
    if unknown_pct > 30:
        print(f"⚠️ WARNING: {unknown_pct:.1f}% of bank transactions have Unknown card type")
        print("This suggests the card type identification patterns may need adjustment")
        
        # Show some Unknown transactions
        print("\nSample 'Unknown' transactions:")
        unknown_sample = bank_statement[bank_statement['Card_Type'] == 'Unknown'].head(5)
        for _, row in unknown_sample.iterrows():
            print(f"  {row['Description']}")
    
    print("\n" + "="*50)
    print("DIAGNOSIS COMPLETE")
    print("="*50)

if __name__ == "__main__":
    debug_matching_issues()