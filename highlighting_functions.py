import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
import shutil

def create_highlighted_bank_statement(bank_statement_path: str, matched_bank_rows: set, 
                                    output_path: str = 'bank_statement_highlighted.xlsx',
                                    differences_by_row: dict = None):
    """
    Create a highlighted copy of the bank statement with matched rows highlighted.
    
    Args:
        bank_statement_path (str): Path to original bank statement CSV
        matched_bank_rows (set): Set of row numbers that were matched (1-based Excel rows)
        output_path (str): Output path for highlighted Excel file
        differences_by_row (dict): Optional dict mapping bank rows to difference amounts
    """
    # Read the original CSV file
    original_df = pd.read_csv(bank_statement_path)
    
    # Write to Excel with highlighting
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        original_df.to_excel(writer, sheet_name='Bank Statement', index=False)
        
        # Get the workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Bank Statement']
        
        # Define highlight color (light green)
        green_fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')
        
        # Highlight matched rows
        for excel_row in matched_bank_rows:
            worksheet_row = excel_row
            if 2 <= worksheet_row <= len(original_df) + 1:
                for col in range(1, len(original_df.columns) + 1):
                    cell = worksheet.cell(row=worksheet_row, column=col)
                    cell.fill = green_fill
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"✓ Created highlighted bank statement: {output_path}")
    print(f"  - Total rows: {len(original_df)}")
    print(f"  - Matched rows: {len(matched_bank_rows)}")

def create_highlighted_card_summary(card_summary_path: str, matched_dates_and_types: dict,
                                  output_path: str = 'card_summary_highlighted.xlsx',
                                  skiprows=[0, 1, 3, 34], differences_info: dict = None,
                                  unmatched_info: dict = None, unmatched_bank_by_type: dict = None):
    """
    Create a highlighted copy of the card summary with matched cells highlighted and unmatched cells commented.
    
    Args:
        card_summary_path (str): Path to original card summary Excel
        matched_dates_and_types (dict): Dict with dates as keys and matched card types as values
        output_path (str): Output path for highlighted Excel file
        skiprows (list): Row indices that were skipped in original processing
        differences_info (dict): Optional dict with (date, card_type) tuples as keys and differences as values
        unmatched_info (dict): Dict with information about unmatched cells
        unmatched_bank_by_type (dict): Dict with unmatched bank transactions by card type, now includes date filter info
    """
    from dict import mapping
    
    # Copy the original Excel file
    shutil.copy2(card_summary_path, output_path)
    
    # Load the workbook
    workbook = load_workbook(output_path)
    worksheet = workbook.active
    
    # Define highlight colors
    green_fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')
    red_fill = PatternFill(start_color='FFB6C1', end_color='FFB6C1', fill_type='solid')
    
    # Read the data to understand the structure
    card_summary_df = pd.read_excel(card_summary_path, skiprows=skiprows)
    card_summary_df['Date'] = pd.to_datetime(card_summary_df['Date'])
    
    # Create a mapping of dates to their Excel row numbers
    excel_row_mapping = {}
    data_row_start = 5
    
    for idx, row in card_summary_df.iterrows():
        excel_row = data_row_start + idx
        if excel_row >= 34:
            excel_row += 1
        excel_row_mapping[row['Date']] = excel_row
    
    # Find column indices for card types
    header_row = 3
    column_mapping = {}
    
    for col_idx in range(1, worksheet.max_column + 1):
        cell_value = worksheet.cell(row=header_row, column=col_idx).value
        if cell_value:
            column_mapping[str(cell_value).strip()] = col_idx
    
    # Track statistics
    matched_cells_count = 0
    unmatched_cells_count = 0
    
    # Find the total row first
    total_row = None
    for row in range(worksheet.max_row, 0, -1):
        cell_value = worksheet.cell(row=row, column=1).value
        if cell_value and 'Total' in str(cell_value):
            total_row = row
            break

    # Process all data rows
    for _, row in card_summary_df.iterrows():
        date = row['Date']
        excel_row = excel_row_mapping[date]
        
        # Skip highlighting if this is the total row
        if total_row and excel_row == total_row:
            continue
        
        # Check each card type column
        for card_type in column_mapping.keys():
            if card_type in ['Date', 'Total', 'Visa & MC'] or card_type.startswith('Unnamed'):
                continue
                
            if card_type in column_mapping and card_type in row.index:
                expected_amount = row[card_type]
                if pd.notna(expected_amount) and expected_amount != 0:
                    col_idx = column_mapping[card_type]
                    cell = worksheet.cell(row=excel_row, column=col_idx)
                    
                    # Check if this cell was matched
                    if matched_dates_and_types and date in matched_dates_and_types and card_type in matched_dates_and_types[date]:
                        # Matched cell - color green
                        cell.fill = green_fill
                        matched_cells_count += 1
                    elif unmatched_info and (date, card_type) in unmatched_info:
                        # Unmatched cell - color red and add comment
                        cell.fill = red_fill
                        unmatched_cells_count += 1
                        
                        # Add comment with what was actually found
                        info = unmatched_info[(date, card_type)]
                        found_count = info.get('found_transactions', 0)
                        total_found = info.get('total_found', 0)
                        expected = info.get('expected', expected_amount)
                        difference = total_found - expected
                        
                        comment_lines = []
                        comment_lines.append(f"Expected: ${expected:,.2f}")
                        comment_lines.append(f"Found transactions: ${total_found:,.2f}")
                        comment_lines.append(f"Difference: ${difference:,.2f}")
                        comment_lines.append(f"Unmatched transactions available: {found_count}")
                        if info.get('reason'):
                            comment_lines.append(f"Reason: {info['reason']}")
                        comment_lines.append("\nNote: 'Found' amount excludes transactions already matched elsewhere")
                        
                        comment_text = "\n".join(comment_lines)
                        cell.comment = Comment(comment_text, "Matching System")
    
    # Add unmatched BANK STATEMENT totals to the Total row with date filtering info
    if total_row and unmatched_bank_by_type:
        # Add comments to total row cells
        for card_type, col_idx in column_mapping.items():
            if card_type in unmatched_bank_by_type and card_type not in ['Date', 'Total', 'Visa & MC']:
                cell = worksheet.cell(row=total_row, column=col_idx)
                totals = unmatched_bank_by_type[card_type]
                
                comment_lines = []
                comment_lines.append(f"Unmatched bank transactions:")
                
                # Add date filter information if applicable
                if totals.get('date_filter_applied', False) and totals.get('first_matched_date'):
                    first_date = totals['first_matched_date']
                    comment_lines.append(f"Counting from: {first_date.strftime('%Y-%m-%d')} (first match)")
                elif not totals.get('date_filter_applied', False):
                    comment_lines.append(f"All transactions (no matches found)")
                
                comment_lines.append(f"Total: ${totals['total']:,.2f}")
                comment_lines.append(f"Count: {totals['count']} transactions")
                comment_lines.append(f"\nBank rows: {', '.join(map(str, totals['rows'][:10]))}")
                if totals['count'] > 10:
                    comment_lines.append(f"... and {totals['count'] - 10} more")
                
                comment_text = "\n".join(comment_lines)
                cell.comment = Comment(comment_text, "Bank Statement Summary")
    
    # Save the workbook
    workbook.save(output_path)
    workbook.close()
    
    print(f"✓ Created highlighted card summary: {output_path}")
    print(f"  - Total dates: {len(card_summary_df)}")
    print(f"  - Matched cells (green): {matched_cells_count}")
    print(f"  - Unmatched cells with comments (red): {unmatched_cells_count}")
    if total_row and unmatched_bank_by_type:
        print(f"  - Total row comments added for unmatched bank transactions: {len([k for k in unmatched_bank_by_type.keys() if k in column_mapping])}")

def extract_matched_info_from_results(results: dict) -> tuple:
    """
    Extract matched bank rows and matched dates/card types from results.
    Also extracts unmatched information for highlighting.
    
    Returns:
        tuple: (set of matched bank rows, dict of matched dates and card types, 
                dict of differences by bank row, dict of differences by date/card_type,
                dict of unmatched info)
    """
    matched_bank_rows = set()
    matched_dates_and_types = {}
    differences_by_row = {}
    differences_by_date_type = {}
    unmatched_info = {}
    
    for date, date_results in results.items():
        # Skip metadata keys that start with underscore
        if isinstance(date, str) and date.startswith('_'):
            continue
        
        # Also skip if date_results is not a dictionary with expected structure
        if not isinstance(date_results, dict) or 'matches_by_card_type' not in date_results:
            continue
            
        matched_types = []
        
        # Process matched transactions
        for card_type, match_info in date_results['matches_by_card_type'].items():
            matched_types.append(card_type)
            matched_bank_rows.update(match_info['bank_rows'])
            
            diff = match_info.get('difference', 0)
            if abs(diff) > 0.01:
                for bank_row in match_info['bank_rows']:
                    differences_by_row[bank_row] = diff
                differences_by_date_type[(date, card_type)] = diff
        
        if matched_types:
            matched_dates_and_types[date] = matched_types
        
        # Process unmatched transactions
        for card_type, unmatch_info in date_results['unmatched_by_card_type'].items():
            unmatched_info[(date, card_type)] = unmatch_info
    
    print(f"\n=== Match Summary ===")
    print(f"Matched cells: {sum(len(types) for types in matched_dates_and_types.values())}")
    print(f"Unmatched cells: {len(unmatched_info)}")
    
    return matched_bank_rows, matched_dates_and_types, differences_by_row, differences_by_date_type, unmatched_info