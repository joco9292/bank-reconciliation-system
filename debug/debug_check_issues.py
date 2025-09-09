import pandas as pd
from datetime import datetime, timedelta
from preprocess_deposit_slip import preprocess_deposit_slip_dynamic
from preprocess_bank_statement import preprocess_bank_statement

def debug_missing_deposits(deposit_slip_path: str, bank_statement_path: str):
    """
    Find where the missing deposit transactions are.
    """
    print("=" * 80)
    print("MISSING DEPOSIT TRANSACTIONS DEBUG")
    print("=" * 80)
    
    # Load data
    deposit_slip, _ = preprocess_deposit_slip_dynamic(deposit_slip_path)
    bank_statement = preprocess_bank_statement(bank_statement_path)
    bank_statement['Bank_Row_Number'] = range(2, len(bank_statement) + 2)
    
    # 1. Show ALL GC 1416 transactions with dates
    print("\n1. ALL GC 1416 TRANSACTIONS IN BANK STATEMENT:")
    print("-" * 80)
    
    gc_1416_trans = bank_statement[
        bank_statement['Description'].str.contains('GC 1416', case=False, na=False) |
        bank_statement['Description'].str.contains('Cash/Check', case=False, na=False)
    ]
    
    if not gc_1416_trans.empty:
        gc_1416_trans = gc_1416_trans.sort_values('Date')
        for _, trans in gc_1416_trans.iterrows():
            print(f"   {trans['Date'].strftime('%Y-%m-%d')}: ${trans['Amount']:8.2f} "
                  f"(Row {trans['Bank_Row_Number']:3}) - {trans['Description'][:40]}")
        
        print(f"\n   Total GC 1416: ${gc_1416_trans['Amount'].sum():,.2f}")
    else:
        print("   NO GC 1416 transactions found!")
    
    # 2. Show deposit slip expectations by date
    print("\n2. DEPOSIT SLIP EXPECTATIONS BY DATE:")
    print("-" * 80)
    
    deposit_slip_sorted = deposit_slip.sort_values('Date')
    for _, row in deposit_slip_sorted.iterrows():
        cash = row.get('Cash', 0)
        check = row.get('Check', 0)
        if cash > 0 or check > 0:
            print(f"   {row['Date'].strftime('%Y-%m-%d')}: Cash=${cash:8.2f}, Check=${check:8.2f}, Total=${cash+check:8.2f}")
    
    print(f"\n   Total expected: ${deposit_slip['Cash'].sum() + deposit_slip['Check'].sum():,.2f}")
    
    # 3. Look for OTHER potential deposit transactions
    print("\n3. SEARCHING FOR OTHER POTENTIAL DEPOSIT TRANSACTIONS:")
    print("-" * 80)
    
    # Look for common deposit keywords
    deposit_keywords = ['DEPOSIT', 'DEP', 'CASH', 'CHECK', 'CHK', 'PAYMENT', 'PMT']
    
    potential_deposits = pd.DataFrame()
    for keyword in deposit_keywords:
        matches = bank_statement[
            bank_statement['Description'].str.contains(keyword, case=False, na=False)
        ]
        potential_deposits = pd.concat([potential_deposits, matches]).drop_duplicates()
    
    # Exclude already identified GC 1416
    if not gc_1416_trans.empty:
        potential_deposits = potential_deposits[
            ~potential_deposits['Bank_Row_Number'].isin(gc_1416_trans['Bank_Row_Number'])
        ]
    
    # Filter to only positive amounts (deposits)
    potential_deposits = potential_deposits[potential_deposits['Amount'] > 0]
    
    if not potential_deposits.empty:
        print(f"   Found {len(potential_deposits)} potential deposit transactions:")
        potential_deposits = potential_deposits.sort_values('Date')
        for _, trans in potential_deposits.head(20).iterrows():  # Show first 20
            print(f"      {trans['Date'].strftime('%Y-%m-%d')}: ${trans['Amount']:8.2f} "
                  f"(Row {trans['Bank_Row_Number']:3}) - {trans['Description'][:40]}")
        
        if len(potential_deposits) > 20:
            print(f"      ... and {len(potential_deposits) - 20} more")
        
        print(f"\n   Total potential deposits: ${potential_deposits['Amount'].sum():,.2f}")
    else:
        print("   No additional potential deposits found")
    
    # 4. Match deposits by amounts (regardless of date)
    print("\n4. MATCHING DEPOSITS BY AMOUNT (IGNORING DATES):")
    print("-" * 80)
    
    # Get all positive transactions
    all_deposits = bank_statement[bank_statement['Amount'] > 0].copy()
    
    matched_by_amount = []
    for _, deposit_row in deposit_slip.iterrows():
        date = deposit_row['Date']
        cash = deposit_row.get('Cash', 0)
        check = deposit_row.get('Check', 0)
        total = cash + check
        
        if total > 0:
            # Find exact matches for the total
            exact_matches = all_deposits[abs(all_deposits['Amount'] - total) < 0.01]
            if not exact_matches.empty:
                for _, match in exact_matches.iterrows():
                    days_diff = (match['Date'] - date).days
                    matched_by_amount.append({
                        'deposit_date': date,
                        'bank_date': match['Date'],
                        'days_diff': days_diff,
                        'amount': total,
                        'bank_row': match['Bank_Row_Number'],
                        'description': match['Description']
                    })
    
    if matched_by_amount:
        print("   Found amount matches (may be on different dates):")
        for match in matched_by_amount:
            print(f"      Deposit {match['deposit_date'].strftime('%Y-%m-%d')} (${match['amount']:.2f}) "
                  f"→ Bank {match['bank_date'].strftime('%Y-%m-%d')} "
                  f"({match['days_diff']:+d} days) - {match['description'][:30]}")
    else:
        print("   No exact amount matches found")
    
    # 5. Analyze date patterns
    print("\n5. DATE PATTERN ANALYSIS:")
    print("-" * 80)
    
    # Check if GC 1416 transactions cluster around certain dates
    if not gc_1416_trans.empty:
        gc_dates = gc_1416_trans['Date'].value_counts().sort_index()
        print("   GC 1416 transactions by date:")
        for date, count in gc_dates.items():
            amount = gc_1416_trans[gc_1416_trans['Date'] == date]['Amount'].sum()
            print(f"      {date.strftime('%Y-%m-%d')}: {count} transaction(s), total ${amount:.2f}")
    
    # 6. Check for transactions just outside the date range
    print("\n6. CHECKING FOR TRANSACTIONS OUTSIDE STANDARD DATE RANGE:")
    print("-" * 80)
    
    for _, deposit_row in deposit_slip.iterrows():
        date = deposit_row['Date']
        cash = deposit_row.get('Cash', 0)
        check = deposit_row.get('Check', 0)
        total = cash + check
        
        if total > 0:
            # Look 7 days before and after
            extended_start = date - timedelta(days=7)
            extended_end = date + timedelta(days=7)
            
            extended_matches = all_deposits[
                (all_deposits['Date'] >= extended_start) &
                (all_deposits['Date'] <= extended_end) &
                (abs(all_deposits['Amount'] - total) < 0.01)
            ]
            
            if not extended_matches.empty:
                for _, match in extended_matches.iterrows():
                    days_diff = (match['Date'] - date).days
                    if abs(days_diff) > 3:  # Outside normal range
                        print(f"   ⚠ {date.strftime('%Y-%m-%d')} (${total:.2f}): "
                              f"Found match {days_diff:+d} days away on {match['Date'].strftime('%Y-%m-%d')}")
                        print(f"      → {match['Description'][:50]}")
    
    # 7. Final recommendations
    print("\n7. ANALYSIS SUMMARY:")
    print("=" * 80)
    
    total_gc = gc_1416_trans['Amount'].sum() if not gc_1416_trans.empty else 0
    total_expected = deposit_slip['Cash'].sum() + deposit_slip['Check'].sum()
    total_potential = potential_deposits['Amount'].sum() if not potential_deposits.empty else 0
    
    print(f"   Expected deposits: ${total_expected:,.2f}")
    print(f"   GC 1416 found: ${total_gc:,.2f}")
    print(f"   Other potential deposits: ${total_potential:,.2f}")
    print(f"   GC 1416 + Other: ${total_gc + total_potential:,.2f}")
    print(f"   Still missing: ${total_expected - total_gc - total_potential:,.2f}")
    
    print("\n   LIKELY ISSUES:")
    if total_gc < total_expected:
        print("   1. Not all deposits are coded as 'GC 1416' in the bank statement")
        print("   2. Some deposits may use different descriptions")
        print("   3. Date mismatches - deposits appear on different dates than expected")
        
        if potential_deposits.empty:
            print("\n   ⚠ WARNING: No other deposit-like transactions found!")
            print("   Check if deposits are being processed differently in July")
    
    # Return for further analysis
    return {
        'gc_1416_transactions': gc_1416_trans,
        'potential_deposits': potential_deposits,
        'matched_by_amount': matched_by_amount
    }

if __name__ == "__main__":
    # Run enhanced debug
    results = debug_missing_deposits(
        deposit_slip_path='XYZ Storage Laird - MonthlyDepositSlip - 07-01-2025 - 07-31-2025 (5).xlsx',
        bank_statement_path='july 2025 bank statement.CSV'
    )