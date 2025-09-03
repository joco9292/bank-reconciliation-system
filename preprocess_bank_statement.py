import pandas as pd
from dict import mapping  # Assuming you have dict.py with your mapping dictionary

def preprocess_bank_statement(filepath='june 2025 bank statement.CSV'):
    """
    Load and preprocess the bank statement CSV file.
    
    Args:
        filepath (str): Path to the bank statement CSV file
        
    Returns:
        pd.DataFrame: Preprocessed bank statement with Date, Description, and Amount columns
    """
    # Load the CSV
    bank_df = pd.read_csv(filepath)
    
    # Convert credit and debit amounts to numeric
    bank_df['Credit Amount'] = pd.to_numeric(bank_df['Credit Amount'])
    bank_df['Debit Amount'] = pd.to_numeric(bank_df['Debit Amount'])
    
    # Fill NaN values with 0
    bank_df = bank_df.fillna(value=0)
    
    # Calculate net amount with special handling for BPAD transactions
    # Credits are always positive
    # Debits are negative ONLY if 'BPAD' is in the description, otherwise they're positive
    def calculate_amount(row):
        credit = row['Credit Amount']
        debit = row['Debit Amount']
        description = str(row['Description']).upper()
        
        # If BPAD is in description, debit is negative (actual debit/fee)
        if 'BPAD' in description and debit > 0:
            return credit - debit
        else:
            # Otherwise, both credit and debit are positive (they're deposits)
            return credit
    
    bank_df['Amount'] = bank_df.apply(calculate_amount, axis=1)
    
    # Keep only necessary columns
    bank_df = bank_df[['Date', 'Description', 'Amount']]
    
    # Apply description mapping
    def map_description(desc):
        for key, value in mapping.items():
            if key in desc:
                return value
        return desc  # Return original if no match found
    
    bank_df['Description'] = bank_df['Description'].apply(map_description)
    
    # Convert date to datetime
    bank_df['Date'] = pd.to_datetime(bank_df['Date'])
    
    return bank_df

if __name__ == "__main__":
    # Test the function
    df = preprocess_bank_statement()
    print("Bank Statement Preview:")
    print(df.head(20))  # Show more rows to see BPAD transactions
    print(f"\nShape: {df.shape}")
    print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
    
    # Show BPAD transactions specifically
    bpad_transactions = df[df['Description'].str.contains('BPAD', case=False, na=False)]
    if not bpad_transactions.empty:
        print(f"\nBPAD Transactions (should be negative):")
        print(bpad_transactions)