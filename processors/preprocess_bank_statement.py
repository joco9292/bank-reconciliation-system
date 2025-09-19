import pandas as pd
from dict import mapping  # Assuming you have dict.py with your mapping dictionary

def preprocess_bank_statement(filepath='june 2025 bank statement.CSV'):
    """
    Load and preprocess the bank statement CSV file.
    
    Special handling for BPAD transactions:
    - Transactions with 'BPAD' in description are treated as debits (negative amounts)
    - Transactions with 'Backdated=YES' AND debit amounts are also treated as BPAD transactions
    
    Args:
        filepath (str): Path to the bank statement CSV file
        
    Returns:
        pd.DataFrame: Preprocessed bank statement with Date, Description, Amount, and Backdated columns
    """
    # Load the CSV
    bank_df = pd.read_csv(filepath)
    
    # Convert credit and debit amounts to numeric
    bank_df['Credit Amount'] = pd.to_numeric(bank_df['Credit Amount'])
    bank_df['Debit Amount'] = pd.to_numeric(bank_df['Debit Amount'])
    
    # Fill NaN values with 0
    bank_df = bank_df.fillna(value=0)
    
    # Calculate net amount with proper handling for different transaction types
    def calculate_amount(row):
        credit = row['Credit Amount']
        debit = row['Debit Amount']
        description = str(row['Description']).upper()
        backdated = str(row['Backdated']).upper()
        
        # Check if this should be treated as BPAD:
        # 1. Original BPAD logic: 'BPAD' is in description
        # 2. New logic: Backdated=YES AND debit amount > 0
        is_bpad_transaction = (
            ('BPAD' in description and debit > 0) or 
            (backdated == 'YES' and debit > 0)
        )
        
        if is_bpad_transaction:
            # BPAD transactions: credit - debit (usually negative)
            return credit - debit
        elif credit > 0:
            # Regular credit transactions (money going out - for credit card matching)
            return credit
        elif debit > 0:
            # Regular debit transactions (money coming in - for deposit matching)
            return debit
        else:
            # No amount in either column
            return 0
    
    bank_df['Amount'] = bank_df.apply(calculate_amount, axis=1)
    
    # Add transaction type classification
    def classify_transaction_type(row):
        credit = row['Credit Amount']
        debit = row['Debit Amount']
        description = str(row['Description']).upper()
        backdated = str(row['Backdated']).upper()
        
        # Check if this is BPAD
        is_bpad_transaction = (
            ('BPAD' in description and debit > 0) or 
            (backdated == 'YES' and debit > 0)
        )
        
        if is_bpad_transaction:
            return 'BPAD'
        elif credit > 0:
            return 'CREDIT'  # Money going out - for credit card matching
        elif debit > 0:
            return 'DEBIT'   # Money coming in - for deposit matching
        else:
            return 'UNKNOWN'
    
    bank_df['Transaction_Type'] = bank_df.apply(classify_transaction_type, axis=1)
    
    # Keep only necessary columns (including Transaction_Type and Backdated for debugging/reference)
    bank_df = bank_df[['Date', 'Description', 'Amount', 'Transaction_Type', 'Backdated']]
    
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
    
    # Show backdated transactions
    backdated_transactions = df[df['Backdated'].str.upper() == 'YES']
    if not backdated_transactions.empty:
        print(f"\nBackdated Transactions:")
        print(backdated_transactions)
        print("Note: If any backdated transactions had debit amounts, they would be treated as BPAD")