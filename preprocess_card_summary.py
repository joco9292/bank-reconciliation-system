import pandas as pd

def preprocess_card_summary(filepath='card summary june.xlsx', skiprows=[0, 1, 3, 34]):
    """
    Load and preprocess the card summary Excel file.
    
    Args:
        filepath (str): Path to the card summary Excel file
        skiprows (list): List of row indices to skip when reading the file
        
    Returns:
        pd.DataFrame: Preprocessed card summary with date and card type columns
    """
    # Load the Excel file with specified rows to skip
    card_summary = pd.read_excel(filepath, skiprows=skiprows)
    
    # Convert date to datetime
    card_summary['Date'] = pd.to_datetime(card_summary['Date'])
    
    # Clean column names (remove any leading/trailing spaces)
    card_summary.columns = card_summary.columns.str.strip()
    
    # Convert all card type columns to numeric (except Date and any text columns)
    # Get list of columns that should be numeric
    numeric_columns = [col for col in card_summary.columns 
                      if col not in ['Date'] and not col.startswith('Unnamed')]
    
    # Convert to numeric, replacing any non-numeric values with 0
    for col in numeric_columns:
        card_summary[col] = pd.to_numeric(card_summary[col], errors='coerce').fillna(0)
    
    return card_summary

if __name__ == "__main__":
    # Test the function
    df = preprocess_card_summary()
    print("Card Summary Preview:")
    print(df.head())
    print(f"\nColumns: {df.columns.tolist()}")
    print(f"Shape: {df.shape}")
    print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"\nData types:")
    print(df.dtypes)