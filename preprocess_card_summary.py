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
    
    return card_summary

if __name__ == "__main__":
    # Test the function
    df = preprocess_card_summary()
    print("Card Summary Preview:")
    print(df.head())
    print(f"\nColumns: {df.columns.tolist()}")
    print(f"Shape: {df.shape}")
    print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")