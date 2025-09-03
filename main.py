import pandas as pd
from datetime import datetime
from openpyxl.styles import PatternFill

# Import preprocessor functions
from preprocess_bank_statement import preprocess_bank_statement
from preprocess_card_summary import preprocess_card_summary

# Import helper functions and classes
from matching_helpers import (
    identify_card_type, 
    TransactionMatcher,
    filter_by_amount_range,
    filter_split_transactions
)

# Import the new highlighting functions
from highlighting_functions import (
    create_highlighted_bank_statement,
    create_highlighted_card_summary,
    extract_matched_info_from_results
)

def prepare_data_for_matching(card_summary: pd.DataFrame, bank_statement: pd.DataFrame) -> tuple:
    """
    Add additional columns needed for matching process.
    """
    # Add row numbers to bank statement (1-based to match Excel)
    bank_statement['Bank_Row_Number'] = range(2, len(bank_statement) + 2)
    
    # Identify card type for each bank transaction
    bank_statement['Card_Type'] = bank_statement['Description'].apply(identify_card_type)
    
    return card_summary, bank_statement

def generate_enhanced_report(results: dict, bank_statement: pd.DataFrame, 
                           output_path: str = 'matching_report_enhanced.xlsx'):
    """
    Generate report with bank row references and formatting.
    """
    summary_data = []
    detailed_matches = []
    unmatched_data = []
    
    for date, date_results in results.items():
        # Matched transactions
        for card_type, match_info in date_results['matches_by_card_type'].items():
            summary_data.append({
                'Date': date,
                'Card_Type': card_type,
                'Expected_Amount': match_info['expected'],
                'Match_Type': match_info['match_type'],
                'Status': 'Matched',
                'Bank_Rows': ', '.join(map(str, match_info['bank_rows'])),
                'Transaction_Count': len(match_info['transactions'])
            })
            
            # Detailed match information
            for trans in match_info['transactions']:
                detailed_matches.append({
                    'Match_Date': date,
                    'Card_Type': card_type,
                    'Match_Type': match_info['match_type'],
                    'Bank_Row': trans['Bank_Row_Number'],
                    'Transaction_Date': trans['Date'],
                    'Description': trans['Description'],
                    'Amount': trans['Amount']
                })
        
        # Unmatched transactions
        for card_type, unmatch_info in date_results['unmatched_by_card_type'].items():
            summary_data.append({
                'Date': date,
                'Card_Type': card_type,
                'Expected_Amount': unmatch_info['expected'],
                'Match_Type': 'Unmatched',
                'Status': 'Unmatched',
                'Bank_Rows': ', '.join(map(str, unmatch_info.get('bank_rows', []))),
                'Reason': unmatch_info['reason']
            })
            
            unmatched_data.append({
                'Date': date,
                'Card_Type': card_type,
                'Expected_Amount': unmatch_info['expected'],
                'Found_Transactions': unmatch_info.get('found_transactions', 0),
                'Total_Found': unmatch_info.get('total_found', 0),
                'Reason': unmatch_info['reason']
            })
    
    # Create Excel report with formatting
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Add formatting to highlight matched/unmatched
            worksheet = writer.sheets['Summary']
            green_fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')
            red_fill = PatternFill(start_color='FFB6C1', end_color='FFB6C1', fill_type='solid')
            
            for idx, row in enumerate(summary_df.itertuples(), start=2):
                if row.Status == 'Matched':
                    worksheet[f'E{idx}'].fill = green_fill
                else:
                    worksheet[f'E{idx}'].fill = red_fill
        
        if detailed_matches:
            pd.DataFrame(detailed_matches).to_excel(writer, sheet_name='Matched_Details', index=False)
        
        if unmatched_data:
            pd.DataFrame(unmatched_data).to_excel(writer, sheet_name='Unmatched', index=False)
        
        # Add bank statement reference sheet
        bank_ref = bank_statement[['Bank_Row_Number', 'Date', 'Description', 'Amount', 'Card_Type']]
        bank_ref.to_excel(writer, sheet_name='Bank_Statement_Reference', index=False)

def print_matching_summary(results: dict):
    """
    Print a summary of matching results.
    """
    total_matches = 0
    total_unmatched = 0
    matches_by_type = {}
    
    for date, date_results in results.items():
        total_matches += len(date_results['matches_by_card_type'])
        total_unmatched += len(date_results['unmatched_by_card_type'])
        
        for match_info in date_results['matches_by_card_type'].values():
            match_type = match_info['match_type']
            matches_by_type[match_type] = matches_by_type.get(match_type, 0) + 1
    
    print("\n=== MATCHING SUMMARY ===")
    print(f"Total matched: {total_matches}")
    print(f"Total unmatched: {total_unmatched}")
    print(f"\nMatches by type:")
    for match_type, count in matches_by_type.items():
        print(f"  - {match_type}: {count}")
    
    # Show some example matches
    print("\n=== EXAMPLE MATCHES ===")
    example_count = 0
    for date, date_results in results.items():
        for card_type, match_info in date_results['matches_by_card_type'].items():
            if example_count < 3:
                print(f"\nDate: {date.date()}, Card Type: {card_type}")
                print(f"Match Type: {match_info['match_type']}")
                print(f"Expected: ${match_info['expected']:.2f}")
                print(f"Bank Rows: {match_info['bank_rows']}")
                example_count += 1
            else:
                break
        if example_count >= 3:
            break

if __name__ == "__main__":
    print("=== Transaction Matching System ===\n")
    
    # Store file paths for later use
    BANK_STATEMENT_PATH = 'june 2025 bank statement.CSV'
    CARD_SUMMARY_PATH = 'card summary june.xlsx'
    
    # Step 1: Load and preprocess data
    print("Step 1: Loading and preprocessing data...")
    try:
        bank_statement = preprocess_bank_statement(BANK_STATEMENT_PATH)
        print(f"✓ Loaded bank statement: {len(bank_statement)} transactions")
    except Exception as e:
        print(f"✗ Error loading bank statement: {e}")
        exit(1)
    
    try:
        card_summary = preprocess_card_summary(CARD_SUMMARY_PATH)
        print(f"✓ Loaded card summary: {len(card_summary)} days")
    except Exception as e:
        print(f"✗ Error loading card summary: {e}")
        exit(1)
    
    # Step 2: Prepare data for matching
    print("\nStep 2: Preparing data for matching...")
    card_summary, bank_statement = prepare_data_for_matching(card_summary, bank_statement)
    
    # Show card type distribution
    print("\nCard types identified in bank statement:")
    print(bank_statement['Card_Type'].value_counts())
    
    # Step 3: Create matcher and optionally add filters
    print("\nStep 3: Setting up transaction matcher...")
    matcher = TransactionMatcher()
    
    # Uncomment to add additional filters:
    # matcher.add_filter('amount_range', filter_by_amount_range)
    # matcher.add_filter('split_transactions', filter_split_transactions)
    
    # Step 4: Run matching algorithm
    print("\nStep 4: Running matching algorithm...")
    results = matcher.match_transactions(card_summary, bank_statement, forward_days=3)
    
    # Step 5: Generate summary and report
    print("\nStep 5: Generating results...")
    print_matching_summary(results)
    
    # Generate Excel report
    output_filename = 'matching_report_enhanced.xlsx'
    generate_enhanced_report(results, bank_statement, output_filename)
    print(f"\n✓ Detailed report saved to: {output_filename}")
    
    # Step 6: Create highlighted copies of original files
    print("\nStep 6: Creating highlighted copies of original files...")
    
    # Extract matched information including unmatched details
    matched_bank_rows, matched_dates_and_types, differences_by_row, differences_by_date_type, unmatched_info = extract_matched_info_from_results(results)
    
    # DEBUG: Print what we're passing to the highlighting function
    print("\n=== DEBUG: Card Summary Matching Info ===")
    print(f"Number of dates with matches: {len(matched_dates_and_types)}")
    if matched_dates_and_types:
        # Show first 3 entries
        for i, (date, card_types) in enumerate(list(matched_dates_and_types.items())[:3]):
            print(f"Date: {date.strftime('%Y-%m-%d')}, Card Types: {card_types}")
    
    # Check card summary columns
    temp_card_summary = preprocess_card_summary(CARD_SUMMARY_PATH)
    print(f"\nCard Summary Columns: {[col for col in temp_card_summary.columns if col != 'Date' and not col.startswith('Unnamed')]}")
    
    # Create highlighted bank statement
    create_highlighted_bank_statement(
        bank_statement_path=BANK_STATEMENT_PATH,
        matched_bank_rows=matched_bank_rows,
        output_path='bank_statement_highlighted.xlsx',
        differences_by_row=differences_by_row
    )
    
    # Create highlighted card summary with unmatched info
    create_highlighted_card_summary(
        card_summary_path=CARD_SUMMARY_PATH,
        matched_dates_and_types=matched_dates_and_types,
        output_path='card_summary_highlighted.xlsx',
        skiprows=[0, 1, 3, 34],  # Same skiprows as used in preprocessing
        differences_info=differences_by_date_type,
        unmatched_info=unmatched_info  # ADD THIS LINE
    )

    # Final summary
    print("\n=== PROCESS COMPLETE ===")
    print("\nGenerated files:")
    print("  1. matching_report_enhanced.xlsx - Detailed matching report")
    print("  2. bank_statement_highlighted.xlsx - Bank statement with matched rows highlighted")
    print("  3. card_summary_highlighted.xlsx - Card summary with matched cells highlighted")