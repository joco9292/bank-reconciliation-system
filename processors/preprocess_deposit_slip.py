import pandas as pd
import numpy as np

def detect_deposit_slip_structure(filepath):
    """
    Dynamically detect the structure of a deposit slip file.
    Similar to card summary but adapted for deposit slip format.
    """
    # Read all rows first to analyze structure
    df_raw = pd.read_excel(filepath, header=None)
    
    # Find the header row by looking for 'Date' in first column
    header_row = None
    for idx, row in df_raw.iterrows():
        if pd.notna(row[0]) and 'Date' in str(row[0]):
            header_row = idx
            break
    
    if header_row is None:
        raise ValueError("Could not find header row with 'Date'")
    
    # Find the first data row
    data_start_row = None
    for idx in range(header_row + 1, len(df_raw)):
        try:
            pd.to_datetime(df_raw.iloc[idx, 0])
            data_start_row = idx
            break
        except:
            continue
    
    # Find the total row
    total_row = None
    for idx in range(data_start_row, len(df_raw)):
        if pd.notna(df_raw.iloc[idx, 0]) and 'Total' in str(df_raw.iloc[idx, 0]):
            total_row = idx
            break
    
    # Build skip rows list
    skip_rows = []
    skip_rows.extend(range(header_row))
    for idx in range(header_row + 1, data_start_row):
        skip_rows.append(idx)
    if total_row is not None:
        skip_rows.append(total_row)
    
    print(f"Deposit slip structure detected:")
    print(f"  Header row: {header_row}")
    print(f"  Data starts: {data_start_row}")
    print(f"  Total row: {total_row}")
    print(f"  Skip rows: {skip_rows}")
    
    return skip_rows, header_row, data_start_row, total_row

def preprocess_deposit_slip_dynamic(filepath):
    """
    Dynamically load and preprocess deposit slip Excel file.
    Handles Cash and Check columns specifically.
    """
    # Detect structure
    skip_rows, header_row, data_start_row, total_row = detect_deposit_slip_structure(filepath)
    
    # Load the Excel file
    deposit_slip = pd.read_excel(filepath, skiprows=skip_rows)
    
    # Convert date to datetime
    deposit_slip['Date'] = pd.to_datetime(deposit_slip['Date'])
    
    # Clean column names
    deposit_slip.columns = deposit_slip.columns.str.strip()
    
    # Identify Cash and Check columns (adjust these names based on your actual file)
    deposit_columns = []
    for col in deposit_slip.columns:
        if 'Cash' in col or 'Check' in col:
            deposit_columns.append(col)
    
    # Convert numeric columns
    for col in deposit_columns:
        if col in deposit_slip.columns:
            deposit_slip[col] = pd.to_numeric(deposit_slip[col], errors='coerce').fillna(0)
    
    # Add a Total column if not present
    if 'Total' not in deposit_slip.columns and deposit_columns:
        deposit_slip['Total'] = deposit_slip[deposit_columns].sum(axis=1)
    
    return deposit_slip, {
        'skip_rows': skip_rows,
        'header_row': header_row,
        'data_start_row': data_start_row,
        'total_row': total_row,
        'deposit_columns': deposit_columns
    }

def create_highlighted_deposit_slip(deposit_slip_path: str, 
                                  matched_dates_and_types: dict,
                                  output_path: str = 'deposit_slip_highlighted.xlsx',
                                  unmatched_info: dict = None,
                                  gc_1416_allocation: dict = None):
    """
    Create highlighted deposit slip with special handling for GC 1416 allocations.
    
    Args:
        deposit_slip_path: Path to original deposit slip
        matched_dates_and_types: Dict of matched dates and deposit types
        output_path: Output path for highlighted file
        unmatched_info: Information about unmatched entries
        gc_1416_allocation: Dict showing how GC 1416 transactions were allocated between Cash/Check
    """
    import shutil
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill
    from openpyxl.comments import Comment
    
    # Get the structure info
    deposit_slip_df, structure_info = preprocess_deposit_slip_dynamic(deposit_slip_path)
    
    # Copy the original Excel file
    shutil.copy2(deposit_slip_path, output_path)
    
    # Load the workbook
    workbook = load_workbook(output_path)
    worksheet = workbook.active
    
    # Define highlight colors
    green_fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')
    red_fill = PatternFill(start_color='FFB6C1', end_color='FFB6C1', fill_type='solid')
    yellow_fill = PatternFill(start_color='FFFF99', end_color='FFFF99', fill_type='solid')  # Add this
    # Create mapping of dates to Excel rows
    excel_row_mapping = {}
    excel_row = structure_info['data_start_row'] + 1
    
    for idx, row in deposit_slip_df.iterrows():
        while (excel_row - 1) in structure_info['skip_rows']:
            excel_row += 1
        excel_row_mapping[row['Date']] = excel_row
        excel_row += 1
    
    # Find column indices for deposit types
    header_row = structure_info['header_row'] + 1
    column_mapping = {}
    
    for col_idx in range(1, worksheet.max_column + 1):
        cell_value = worksheet.cell(row=header_row, column=col_idx).value
        if cell_value:
            column_mapping[str(cell_value).strip()] = col_idx
    
    # Process all data rows
    matched_cells_count = 0
    unmatched_cells_count = 0
    gc_1416_cells_count = 0
    
    for _, row in deposit_slip_df.iterrows():
        date = row['Date']
        excel_row = excel_row_mapping[date]
        
        # Process Cash and Check columns
        for deposit_type in structure_info['deposit_columns']:
            if deposit_type in column_mapping and deposit_type in row.index:
                expected_amount = row[deposit_type]
                if pd.notna(expected_amount) and expected_amount != 0:
                    col_idx = column_mapping[deposit_type]
                    cell = worksheet.cell(row=excel_row, column=col_idx)
                    
                    # Check if matched
                    if matched_dates_and_types and date in matched_dates_and_types:
                        if deposit_type in matched_dates_and_types[date]:
                            cell.fill = green_fill
                            matched_cells_count += 1
                            
                            # Add comment if this was from GC 1416 allocation
                            if gc_1416_allocation and (date, deposit_type) in gc_1416_allocation:
                                alloc_info = gc_1416_allocation[(date, deposit_type)]
                                comment_text = f"Matched from GC 1416 transactions:\n"
                                comment_text += f"Allocated ${alloc_info['amount']:,.2f} to {deposit_type}\n"
                                comment_text += f"Bank rows: {', '.join(map(str, alloc_info['bank_rows'][:5]))}"
                                if len(alloc_info['bank_rows']) > 5:
                                    comment_text += f"... and {len(alloc_info['bank_rows'])-5} more"
                                cell.comment = Comment(comment_text, "GC 1416 Allocation")
                                gc_1416_cells_count += 1
                        else:
                            # Check if partially matched (e.g., Cash matched but Check didn't)
                            if any(dt in matched_dates_and_types[date] for dt in structure_info['deposit_columns']):
                                cell.fill = yellow_fill  # Partial match for the date

                    # NEW: Check for best match (yellow highlighting)
                    elif unmatched_info and (date, deposit_type) in unmatched_info:
                        info = unmatched_info[(date, deposit_type)]
                        
                        # Check if this has a best_match stored
                        if 'best_match' in info and info['best_match'] and info['best_match']['total'] > 0:
                            # Yellow for approximate matches
                            cell.fill = yellow_fill
                            best_match = info['best_match']
                            
                            # Add detailed comment
                            comment_text = f"Expected: ${expected_amount:,.2f}\n"
                            comment_text += f"Best match found: ${best_match['total']:.2f}\n"
                            comment_text += f"Difference: ${best_match['difference']:.2f}\n"
                            comment_text += f"Using {best_match['combo_size']} GC 1416 transaction(s)\n"
                            comment_text += f"Bank rows: {', '.join(map(str, best_match['bank_rows'][:5]))}"
                            if len(best_match['bank_rows']) > 5:
                                comment_text += f"... and {len(best_match['bank_rows'])-5} more"
                            
                            cell.comment = Comment(comment_text, "Best Match (Not Exact)")
                        else:
                            # Red for no matches at all
                            cell.fill = red_fill
                            unmatched_cells_count += 1
                            
                            comment_text = f"Expected: ${expected_amount:,.2f}\n"
                            comment_text += f"No GC 1416 transactions found\n"
                            comment_text += info.get('reason', 'No matches in date range')
                            
                            cell.comment = Comment(comment_text, "Unmatched")
                    
                    elif unmatched_info and (date, deposit_type) in unmatched_info:
                        # Unmatched cell
                        cell.fill = red_fill
                        unmatched_cells_count += 1
                        
                        info = unmatched_info[(date, deposit_type)]
                        comment_text = f"Expected: ${expected_amount:,.2f}\n"
                        comment_text += f"Found GC 1416: ${info.get('gc_1416_found', 0):,.2f}\n"
                        comment_text += f"Difference: ${info.get('gc_1416_found', 0) - expected_amount:,.2f}\n"
                        comment_text += "\nNote: GC 1416 transactions can be either Cash or Check"
                        
                        cell.comment = Comment(comment_text, "Matching System")
    
    # Save
    workbook.save(output_path)
    workbook.close()
    
    print(f"✓ Created highlighted deposit slip: {output_path}")
    print(f"  - Detected {len(deposit_slip_df)} data rows")
    print(f"  - Matched cells (green): {matched_cells_count}")
    print(f"  - GC 1416 allocations: {gc_1416_cells_count}")
    print(f"  - Unmatched cells (red): {unmatched_cells_count}")

if __name__ == "__main__":
    # Test the preprocessor
    test_file = 'XYZ Storage Laird - MonthlyDepositSlip - 06-01-2025 - 06-30-2025.xlsx'
    
    try:
        print(f"Testing {test_file}:")
        df, info = preprocess_deposit_slip_dynamic(test_file)
        print(f"Successfully loaded {len(df)} days")
        print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
        print(f"Deposit columns found: {info['deposit_columns']}")
        print("\nFirst few rows:")
        print(df.head())
    except Exception as e:
        print(f"Error: {e}")