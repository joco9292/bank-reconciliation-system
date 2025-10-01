# Bank Statement Comments Guide

## Overview

The bank reconciliation system now includes **informative comments** for each matched transaction in the highlighted bank statement files. These comments provide detailed information about why each transaction was matched and what matching criteria were used.

## What Are Comments?

Comments are small text boxes that appear when you hover over or click on cells in Excel. They contain additional information about the transaction without cluttering the main spreadsheet view.

## How to View Comments

### In Excel:
1. **Hover**: Simply hover your mouse over the first cell of any highlighted (green) row
2. **Click**: Click on the first cell of a highlighted row to see the comment
3. **Right-click**: Right-click on a cell and select "Show/Hide Comments" to toggle comment visibility

### In Other Spreadsheet Applications:
- **Google Sheets**: Comments appear as small red triangles in the corner of cells
- **LibreOffice Calc**: Similar to Excel, hover or click to view comments

## What Information Do Comments Contain?

Comments show **what each bank transaction matched FROM** (the source), not the bank transaction details:

### 🟢 Matched Transactions (Green)
- **Source**: "Matched from Card Summary"
- **Date**: The date from the card summary
- **Card Type**: The card type from the card summary (Visa, Amex, Master Card, etc.)
- **Expected Amount**: What was expected from the card summary
- **Actual Amount**: What was actually found in the bank statement
- **Match Type**: How the transaction was matched (exact, sum_by_description, amount_range, etc.)
- **Difference**: If there's a discrepancy between expected and actual amounts
- **Bank Row**: The row number in the bank statement
- **Status**: Matched

### 🔴 Unmatched Transactions (Red)
- **Source**: "Tried to match from Card Summary"
- **Date**: The date from the card summary
- **Card Type**: The card type from the card summary
- **Expected Amount**: What was expected from the card summary
- **Found Amount**: What was actually found in the bank statement
- **Status**: UNMATCHED
- **Reason**: Why the transaction couldn't be matched
- **Filters Tried**: Which matching filters were attempted
- **Bank Row**: The row number in the bank statement

### 🔵 GC Transactions (Blue)
- **Source**: "Matched from Deposit Slip"
- **Date**: The date from the deposit slip
- **Transaction Type**: GC (Cash & Check)
- **Amount**: The amount from the deposit slip
- **Cash Allocation**: Amount allocated to Cash (if applicable)
- **Check Allocation**: Amount allocated to Check (if applicable)
- **Match Type**: How the transaction was matched
- **Deposit Date**: The date of the deposit slip
- **Bank Row**: The row number in the bank statement
- **Status**: Matched

## Example Comments

### Matched Transaction Comment
```
Matched from Card Summary:
  Date: 2025-01-15
  Card Type: Visa
  Expected: $150.00
  Actual: $150.00
Match Type: exact
Bank Row: 2
Status: Matched
```

### Unmatched Transaction Comment
```
Tried to match from Card Summary:
  Date: 2025-01-17
  Card Type: Unknown
  Expected: $200.25
  Found: $200.25
Status: UNMATCHED
Reason: No matching card type found
Filters Tried: exact_match, amount_range
Bank Row: 4
Note: This bank transaction could not be matched to any expected amount
```

### GC Transaction Comment
```
Matched from Deposit Slip:
  Date: 2025-01-18
  Transaction Type: GC (Cash & Check)
  Amount: $500.00
  Cash Allocation: $300.00
  Check Allocation: $200.00
Match Type: gc_1416_deposit
Deposit Date: 2025-01-18
Bank Row: 5
Status: Matched
Note: This bank transaction was matched from the deposit slip
```

## When Are Comments Added?

Comments are automatically added to:
- ✅ **Matched transactions** (green highlighted rows)
- ✅ **Combined matches** (purple highlighted rows - matched by both card and deposit systems)
- ✅ **Unmatched transactions** (red highlighted rows - failed to match)
- ✅ **GC transactions** (blue highlighted rows - Cash & Check deposit transactions)

## File Types with Comments

The following output files include comments:
- `bank_statement_cards_highlighted.xlsx` - Credit card matches only
- `bank_statement_combined_highlighted.xlsx` - Both card and deposit matches
- `bank_statement_highlighted.xlsx` - General highlighted statements

## Benefits of Comments

1. **Transparency**: See exactly why each transaction was matched
2. **Debugging**: Identify issues with matching logic
3. **Audit Trail**: Track the matching process for each transaction
4. **Quality Control**: Verify that matches are correct
5. **Documentation**: Understand the reconciliation process

## Troubleshooting

### Comments Not Showing?
- Make sure you're looking at the first cell (column A) of highlighted rows
- Try hovering longer over the cell
- Check if comments are enabled in your spreadsheet application

### Missing Information in Comments?
- Some fields may be empty if the information wasn't available during matching
- Check the processing logs for any errors during comment generation

### Comments Too Small to Read?
- Most spreadsheet applications allow you to resize comment boxes
- Try copying the comment text to a text editor for easier reading

## Technical Details

### Comment Generation
Comments are generated automatically during the highlighting process using the `extract_transaction_details_for_comments()` function.

### Comment Format
Comments use a structured format with line breaks for readability and include all available transaction metadata.

### Performance
Adding comments has minimal impact on processing time and file size, but provides significant value for understanding the matching process.

## Best Practices

1. **Review Comments**: Always check comments for important transactions
2. **Use for Validation**: Verify that matches make sense based on the comment information
3. **Share with Team**: Comments help team members understand the reconciliation process
4. **Archive with Files**: Keep the highlighted files with comments for audit purposes

## Support

If you encounter issues with comments or need help interpreting the information, refer to the main documentation or contact the development team.

