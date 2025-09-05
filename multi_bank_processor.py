import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from openpyxl.styles import PatternFill

# Import existing modules
from preprocess_bank_statement import preprocess_bank_statement
from preprocess_card_summary import preprocess_card_summary_dynamic, create_highlighted_card_summary_dynamic
from matching_helpers import identify_card_type, TransactionMatcher
from highlighting_functions import create_highlighted_bank_statement, extract_matched_info_from_results
from exclusive_discrepancy import calculate_total_discrepancies_by_card_type_exclusive, find_first_matched_date, print_matching_summary_with_exclusive_allocation

class MultiBankStatementProcessor:
    """
    Process multiple bank statement files and map them to specific card types.
    Useful when different card types come from different bank accounts.
    """
    
    def __init__(self):
        self.bank_statements = {}
        self.card_type_mappings = {}
        self.combined_results = {}
        
    def add_bank_statement(self, 
                          filepath: str, 
                          statement_id: str,
                          card_types: Optional[List[str]] = None,
                          card_type_override: Optional[str] = None):
        """
        Add a bank statement file to process.
        
        Args:
            filepath: Path to the bank statement CSV file
            statement_id: Unique identifier for this statement (e.g., 'main', 'discover')
            card_types: List of card types to look for in this statement (if None, process all)
            card_type_override: Force all transactions in this statement to be treated as this card type
        """
        # Load and preprocess the bank statement
        bank_df = preprocess_bank_statement(filepath)
        
        # Add row numbers
        bank_df['Bank_Row_Number'] = range(2, len(bank_df) + 2)
        bank_df['Statement_ID'] = statement_id  # Track which statement this came from
        
        # Handle card type identification
        if card_type_override:
            # Force all transactions to be a specific card type
            bank_df['Card_Type'] = card_type_override
            bank_df['Card_Type_Original'] = bank_df['Description'].apply(identify_card_type)
        else:
            # Normal card type identification
            bank_df['Card_Type'] = bank_df['Description'].apply(identify_card_type)
            bank_df['Card_Type_Original'] = bank_df['Card_Type']
        
        # Store the statement
        self.bank_statements[statement_id] = {
            'data': bank_df,
            'filepath': filepath,
            'card_types': card_types,
            'card_type_override': card_type_override
        }
        
        # Update card type mappings
        if card_types:
            for card_type in card_types:
                if card_type not in self.card_type_mappings:
                    self.card_type_mappings[card_type] = []
                self.card_type_mappings[card_type].append(statement_id)
        
        print(f"✔ Added bank statement '{statement_id}' from {filepath}")
        print(f"  - Transactions: {len(bank_df)}")
        if card_type_override:
            print(f"  - All transactions forced to: {card_type_override}")
        elif card_types:
            print(f"  - Specific card types: {card_types}")
        print(f"  - Card types found: {bank_df['Card_Type'].value_counts().to_dict()}")
        
    def combine_bank_statements(self) -> pd.DataFrame:
        """
        Combine all bank statements into a single DataFrame for processing.
        Maintains the Statement_ID to track source.
        """
        if not self.bank_statements:
            raise ValueError("No bank statements have been added")
        
        combined_dfs = []
        
        for statement_id, statement_info in self.bank_statements.items():
            df = statement_info['data'].copy()
            combined_dfs.append(df)
        
        combined_df = pd.concat(combined_dfs, ignore_index=True)
        
        # Re-number the bank rows to be unique across all statements
        combined_df['Original_Bank_Row'] = combined_df['Bank_Row_Number']
        combined_df['Bank_Row_Number'] = range(2, len(combined_df) + 2)
        
        return combined_df
    
    def get_filtered_bank_statement(self, card_types_to_include: List[str]) -> pd.DataFrame:
        """
        Get a filtered bank statement containing only specific card types.
        """
        combined_df = self.combine_bank_statements()
        
        # Filter to only include specified card types
        filtered_df = combined_df[combined_df['Card_Type'].isin(card_types_to_include)]
        
        return filtered_df
    
    def match_transactions(self, 
                          card_summary: pd.DataFrame,
                          forward_days: int = 3,
                          verbose: bool = False) -> Dict:
        """
        Match transactions from all bank statements against the card summary.
        """
        # Combine all bank statements
        combined_bank = self.combine_bank_statements()
        
        print(f"\n✔ Combined bank statements: {len(combined_bank)} total transactions")
        print(f"  Sources: {combined_bank['Statement_ID'].value_counts().to_dict()}")
        
        # Create matcher and run matching
        matcher = TransactionMatcher()
        
        # Run the matching algorithm
        results = matcher.match_transactions(
            card_summary, 
            combined_bank,
            forward_days=forward_days,
            verbose=verbose
        )
        
        # Add statement source information to results
        self._add_statement_sources_to_results(results, combined_bank)
        
        return results
    
    def _add_statement_sources_to_results(self, results: Dict, combined_bank: pd.DataFrame):
        """
        Add information about which bank statement each matched transaction came from.
        """
        for date, date_results in results.items():
            if isinstance(date, str) and date.startswith('_'):
                continue
                
            for card_type, match_info in date_results.get('matches_by_card_type', {}).items():
                # Add statement source info to each transaction
                for trans in match_info.get('transactions', []):
                    bank_row = trans.get('Bank_Row_Number')
                    if bank_row:
                        statement_info = combined_bank[
                            combined_bank['Bank_Row_Number'] == bank_row
                        ].iloc[0] if len(combined_bank[combined_bank['Bank_Row_Number'] == bank_row]) > 0 else None
                        
                        if statement_info is not None:
                            trans['Statement_ID'] = statement_info['Statement_ID']
                            trans['Original_Bank_Row'] = statement_info['Original_Bank_Row']
    
    def create_highlighted_statements(self, 
                                    results: Dict,
                                    matched_bank_rows: set,
                                    output_dir: str = '.'):
        """
        Create highlighted versions of each bank statement file.
        """
        combined_bank = self.combine_bank_statements()
        
        for statement_id, statement_info in self.bank_statements.items():
            # Get matched rows for this specific statement
            statement_matched_rows = set()
            
            for bank_row in matched_bank_rows:
                row_data = combined_bank[combined_bank['Bank_Row_Number'] == bank_row]
                if not row_data.empty and row_data.iloc[0]['Statement_ID'] == statement_id:
                    # Use the original row number for this statement
                    statement_matched_rows.add(row_data.iloc[0]['Original_Bank_Row'])
            
            # Create highlighted file for this statement
            output_path = f"{output_dir}/bank_statement_{statement_id}_highlighted.xlsx"
            create_highlighted_bank_statement(
                bank_statement_path=statement_info['filepath'],
                matched_bank_rows=statement_matched_rows,
                output_path=output_path
            )
            
            print(f"  - Created: {output_path}")
    
    def generate_multi_source_report(self, 
                                    results: Dict,
                                    output_path: str = 'multi_bank_matching_report.xlsx'):
        """
        Generate a report showing which bank statement each match came from.
        """
        summary_data = []
        source_analysis = []
        
        for date, date_results in results.items():
            if isinstance(date, str) and date.startswith('_'):
                continue
                
            # Process matched transactions
            for card_type, match_info in date_results.get('matches_by_card_type', {}).items():
                # Track statement sources
                statement_sources = []
                for trans in match_info.get('transactions', []):
                    statement_sources.append(trans.get('Statement_ID', 'unknown'))
                
                unique_sources = list(set(statement_sources))
                
                summary_data.append({
                    'Date': date,
                    'Card_Type': card_type,
                    'Expected_Amount': match_info['expected'],
                    'Match_Type': match_info['match_type'],
                    'Status': 'Matched',
                    'Statement_Sources': ', '.join(unique_sources),
                    'Bank_Rows': ', '.join(map(str, match_info['bank_rows'])),
                    'Transaction_Count': len(match_info['transactions'])
                })
                
                # Detailed source analysis
                for trans in match_info.get('transactions', []):
                    source_analysis.append({
                        'Date': date,
                        'Card_Type': card_type,
                        'Statement_ID': trans.get('Statement_ID', 'unknown'),
                        'Original_Row': trans.get('Original_Bank_Row', ''),
                        'Amount': trans['Amount'],
                        'Description': trans['Description']
                    })
            
            # Process unmatched transactions
            for card_type, unmatch_info in date_results.get('unmatched_by_card_type', {}).items():
                summary_data.append({
                    'Date': date,
                    'Card_Type': card_type,
                    'Expected_Amount': unmatch_info['expected'],
                    'Match_Type': 'Unmatched',
                    'Status': 'Unmatched',
                    'Reason': unmatch_info.get('reason', '')
                })
        
        # Write to Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            if summary_data:
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            if source_analysis:
                pd.DataFrame(source_analysis).to_excel(writer, sheet_name='Source_Analysis', index=False)
        
        print(f"\n✔ Multi-source report saved to: {output_path}")


def process_with_multiple_bank_statements(
    main_bank_statement_path: str,
    discover_bank_statement_path: str,
    card_summary_path: str,
    output_dir: str = '.',
    verbose: bool = False):
    """
    Process card matching with multiple bank statement files.
    
    Args:
        main_bank_statement_path: Path to main bank statement (all cards except Discover)
        discover_bank_statement_path: Path to Discover-specific bank statement
        card_summary_path: Path to card summary Excel file
        output_dir: Directory for output files
        verbose: Whether to show detailed matching info
    """
    print("=== MULTI-BANK STATEMENT TRANSACTION MATCHING ===\n")
    
    # Step 1: Create processor and add bank statements
    processor = MultiBankStatementProcessor()
    
    # Add main bank statement (all card types EXCEPT Discover)
    processor.add_bank_statement(
        filepath=main_bank_statement_path,
        statement_id='main',
        card_types=['Visa', 'Master Card', 'Amex', 'Debit Visa', 
                   'Debit Master', 'Other Cards', 'Cash', 'Check']
    )
    
    # Add Discover-specific bank statement
    # Option 1: Force all transactions to be Discover
    processor.add_bank_statement(
        filepath=discover_bank_statement_path,
        statement_id='discover',
        card_type_override='Discover'  # Force all to be Discover
    )
    
    # Option 2: Only process Discover transactions from this file
    # processor.add_bank_statement(
    #     filepath=discover_bank_statement_path,
    #     statement_id='discover',
    #     card_types=['Discover']
    # )
    
    # Step 2: Load card summary
    print("\nLoading card summary...")
    card_summary, structure_info = preprocess_card_summary_dynamic(card_summary_path)
    print(f"✔ Loaded card summary: {len(card_summary)} days")
    
    # Step 3: Run matching
    print("\nRunning transaction matching...")
    results = processor.match_transactions(
        card_summary=card_summary,
        forward_days=3,
        verbose=verbose
    )
    
    # Step 4: Extract matched information
    matched_bank_rows, matched_dates_and_types, differences_by_row, \
    differences_by_date_type, unmatched_info = extract_matched_info_from_results(results)
    
    # Step 5: Calculate discrepancies
    combined_bank = processor.combine_bank_statements()
    discrepancies_by_type, first_matched_date = calculate_total_discrepancies_by_card_type_exclusive(
        results, combined_bank, matched_bank_rows
    )
    
    # Step 6: Generate reports
    print("\nGenerating reports...")
    
    # Generate multi-source report
    processor.generate_multi_source_report(
        results=results,
        output_path=f"{output_dir}/multi_bank_matching_report.xlsx"
    )
    
    # Create highlighted bank statements (one for each source)
    print("\nCreating highlighted bank statements...")
    processor.create_highlighted_statements(
        results=results,
        matched_bank_rows=matched_bank_rows,
        output_dir=output_dir
    )
    
    # Create highlighted card summary
    create_highlighted_card_summary_dynamic(
        card_summary_path=card_summary_path,
        matched_dates_and_types=matched_dates_and_types,
        output_path=f"{output_dir}/card_summary_highlighted.xlsx",
        differences_info=differences_by_date_type,
        unmatched_info=unmatched_info,
        differences_by_card_type=discrepancies_by_type
    )
    
    # Print summary
    print_matching_summary_with_exclusive_allocation(
        results, discrepancies_by_type, first_matched_date
    )
    
    print("\n=== PROCESS COMPLETE ===")
    print("\nGenerated files:")
    print(f"  1. {output_dir}/multi_bank_matching_report.xlsx")
    print(f"  2. {output_dir}/bank_statement_main_highlighted.xlsx")
    print(f"  3. {output_dir}/bank_statement_discover_highlighted.xlsx")
    print(f"  4. {output_dir}/card_summary_highlighted.xlsx")
    
    return results


# Example usage in your main.py
if __name__ == "__main__":
    # Process with separate Discover bank statement
    results = process_with_multiple_bank_statements(
        main_bank_statement_path='july 2025 bank statement.CSV',
        discover_bank_statement_path='discover_july_2025_statement.CSV',  # Your Discover statement
        card_summary_path='XYZ Storage Laird - CreditCardSummary - 07-01-2025 - 07-31-2025 (3) (1).xlsx',
        output_dir='.',
        verbose=False
    )