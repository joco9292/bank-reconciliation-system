"""
Enhanced Multi-Bank Processor
Handles complex multi-bank scenarios including:
1. Discover transactions appearing on earlier dates
2. Configurable date matching per card type
3. Backward and forward date searching
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from openpyxl.styles import PatternFill

# Import existing modules
from preprocess_bank_statement import preprocess_bank_statement
from preprocess_card_summary import preprocess_card_summary_dynamic, create_highlighted_card_summary_dynamic
from matching_helpers import identify_card_type, TransactionMatcher, filter_by_amount_range
from highlighting_functions import create_highlighted_bank_statement, extract_matched_info_from_results
from exclusive_discrepancy import calculate_total_discrepancies_by_card_type_exclusive, print_matching_summary_with_exclusive_allocation

class EnhancedMultiBankProcessor:
    """
    Enhanced processor with card-type-specific date matching configurations.
    """
    
    def __init__(self):
        self.bank_statements = {}
        self.card_type_mappings = {}
        self.combined_results = {}
        
        # Card-specific date matching configurations
        self.date_configs = {
            'Discover': {
                'backward_days': 3,  # Look backward for Discover
                'forward_days': 3,   # Also look forward
                'enabled': True      # Easy toggle for this feature
            },
            'default': {
                'backward_days': 0,  # Standard cards don't look backward
                'forward_days': 3
            }
        }
    
    def set_discover_date_matching(self, enabled: bool = True, 
                                  backward_days: int = 3, 
                                  forward_days: int = 3):
        """
        Configure Discover-specific date matching.
        Makes it easy to enable/disable looking backward for Discover.
        """
        self.date_configs['Discover']['enabled'] = enabled
        self.date_configs['Discover']['backward_days'] = backward_days
        self.date_configs['Discover']['forward_days'] = forward_days
        
        print(f"Discover date matching configured:")
        print(f"  - Enabled: {enabled}")
        if enabled:
            print(f"  - Look backward: {backward_days} days")
            print(f"  - Look forward: {forward_days} days")
    
    def add_bank_statement(self, filepath: str, statement_id: str,
                          card_types: Optional[List[str]] = None,
                          card_type_override: Optional[str] = None):
        """Add a bank statement file to process."""
        bank_df = preprocess_bank_statement(filepath)
        bank_df['Bank_Row_Number'] = range(2, len(bank_df) + 2)
        bank_df['Statement_ID'] = statement_id
        
        if card_type_override:
            bank_df['Card_Type'] = card_type_override
            bank_df['Card_Type_Original'] = bank_df['Description'].apply(identify_card_type)
        else:
            bank_df['Card_Type'] = bank_df['Description'].apply(identify_card_type)
            bank_df['Card_Type_Original'] = bank_df['Card_Type']
        
        self.bank_statements[statement_id] = {
            'data': bank_df,
            'filepath': filepath,
            'card_types': card_types,
            'card_type_override': card_type_override
        }
        
        print(f"✓ Added bank statement '{statement_id}' from {filepath}")
        print(f"  - Transactions: {len(bank_df)}")
        if card_type_override:
            print(f"  - All transactions forced to: {card_type_override}")
        print(f"  - Card types found: {bank_df['Card_Type'].value_counts().to_dict()}")
    
    def filter_by_card_type_and_date_flexible(self, transactions: pd.DataFrame, 
                                             card_type: str, date: datetime) -> pd.DataFrame:
        """
        Filter transactions with card-type-specific date ranges.
        Handles backward date searching for specific card types like Discover.
        """
        # Get date configuration for this card type
        if card_type in self.date_configs and self.date_configs[card_type].get('enabled', True):
            config = self.date_configs[card_type]
        else:
            config = self.date_configs['default']
        
        # Calculate date range
        date_start = date - timedelta(days=config.get('backward_days', 0))
        date_end = date + timedelta(days=config.get('forward_days', 3))
        
        # Filter transactions
        filtered = transactions[
            (transactions['Card_Type'] == card_type) &
            (transactions['Date'] >= date_start) &
            (transactions['Date'] <= date_end)
        ].copy()
        
        return filtered
    
    def combine_bank_statements(self) -> pd.DataFrame:
        """Combine all bank statements into a single DataFrame."""
        if not self.bank_statements:
            raise ValueError("No bank statements have been added")
        
        combined_dfs = []
        for statement_id, statement_info in self.bank_statements.items():
            df = statement_info['data'].copy()
            combined_dfs.append(df)
        
        combined_df = pd.concat(combined_dfs, ignore_index=True)
        combined_df['Original_Bank_Row'] = combined_df['Bank_Row_Number']
        combined_df['Bank_Row_Number'] = range(2, len(combined_df) + 2)
        
        return combined_df
    
    def match_transactions_with_flexible_dates(self, card_summary: pd.DataFrame,
                                              verbose: bool = False) -> Dict:
        """
        Match transactions with card-type-specific date ranges.
        """
        combined_bank = self.combine_bank_statements()
        results = {}
        matched_bank_rows = set()
        
        print(f"\n✓ Combined bank statements: {len(combined_bank)} total transactions")
        
        # Card types to process
        card_types = [col for col in card_summary.columns 
                     if col not in ['Date', 'Total', 'Visa & MC'] 
                     and not col.startswith('Unnamed')]
        
        # Process each date in card summary
        for _, card_row in card_summary.iterrows():
            date = card_row['Date']
            date_results = {
                'date': date,
                'matches_by_card_type': {},
                'unmatched_by_card_type': {}
            }
            
            for card_type in card_types:
                expected_amount = card_row[card_type]
                
                if pd.isna(expected_amount) or expected_amount == 0:
                    continue
                
                # Get filtered transactions with flexible date range
                filtered_transactions = self.filter_by_card_type_and_date_flexible(
                    combined_bank, card_type, date
                )
                
                # Show date range being used if verbose
                if verbose and card_type == 'Discover' and self.date_configs['Discover']['enabled']:
                    backward = self.date_configs['Discover']['backward_days']
                    forward = self.date_configs['Discover']['forward_days']
                    print(f"  Discover on {date.strftime('%Y-%m-%d')}: Searching {backward} days back to {forward} days forward")
                
                if len(filtered_transactions) == 0:
                    date_results['unmatched_by_card_type'][card_type] = {
                        'expected': expected_amount,
                        'reason': 'No transactions found in extended date range',
                        'date_range_used': self._get_date_range_description(card_type)
                    }
                    continue
                
                # Try to match with exact amount first
                exact_matches = filtered_transactions[
                    abs(filtered_transactions['Amount'] - expected_amount) < 0.01
                ]
                
                if len(exact_matches) > 0:
                    # Take the closest date match
                    exact_matches = exact_matches.copy()
                    exact_matches['Date_Diff'] = abs((exact_matches['Date'] - date).dt.days)
                    best_match = exact_matches.nsmallest(1, 'Date_Diff')
                    
                    date_results['matches_by_card_type'][card_type] = {
                        'expected': expected_amount,
                        'match_type': 'exact',
                        'transactions': best_match.to_dict('records'),
                        'bank_rows': best_match['Bank_Row_Number'].tolist(),
                        'actual_total': best_match['Amount'].sum(),
                        'difference': 0,
                        'date_offset': best_match.iloc[0]['Date_Diff']
                    }
                    matched_bank_rows.update(best_match['Bank_Row_Number'].tolist())
                    
                    if verbose and best_match.iloc[0]['Date_Diff'] > 0:
                        offset_dir = "earlier" if best_match.iloc[0]['Date'] < date else "later"
                        print(f"  ✓ {card_type} matched {best_match.iloc[0]['Date_Diff']} days {offset_dir}")
                    
                    continue
                
                # If no exact match, record as unmatched
                date_results['unmatched_by_card_type'][card_type] = {
                    'expected': expected_amount,
                    'found_transactions': len(filtered_transactions),
                    'total_found': filtered_transactions['Amount'].sum(),
                    'reason': 'No exact match found in date range',
                    'date_range_used': self._get_date_range_description(card_type)
                }
            
            results[date] = date_results
        
        # Add metadata
        results['_matched_bank_rows'] = matched_bank_rows
        results['_date_configs_used'] = self.date_configs
        
        return results
    
    def _get_date_range_description(self, card_type: str) -> str:
        """Get description of date range used for a card type."""
        if card_type in self.date_configs and self.date_configs[card_type].get('enabled', True):
            config = self.date_configs[card_type]
            backward = config.get('backward_days', 0)
            forward = config.get('forward_days', 3)
            return f"-{backward} to +{forward} days"
        else:
            forward = self.date_configs['default']['forward_days']
            return f"0 to +{forward} days"
    
    def create_highlighted_statements(self, results: Dict, matched_bank_rows: set, output_dir: str = '.'):
        """Create highlighted versions of each bank statement file."""
        combined_bank = self.combine_bank_statements()
        
        for statement_id, statement_info in self.bank_statements.items():
            statement_matched_rows = set()
            
            for bank_row in matched_bank_rows:
                row_data = combined_bank[combined_bank['Bank_Row_Number'] == bank_row]
                if not row_data.empty and row_data.iloc[0]['Statement_ID'] == statement_id:
                    statement_matched_rows.add(row_data.iloc[0]['Original_Bank_Row'])
            
            output_path = f"{output_dir}/bank_statement_{statement_id}_highlighted.xlsx"
            create_highlighted_bank_statement(
                bank_statement_path=statement_info['filepath'],
                matched_bank_rows=statement_matched_rows,
                output_path=output_path
            )
            
            print(f"  - Created: {output_path}")


def process_with_enhanced_multi_bank(
    main_bank_statement_path: str,
    discover_bank_statement_path: str,
    card_summary_path: str,
    output_dir: str = '.',
    enable_discover_backward_matching: bool = True,  # Easy toggle
    discover_backward_days: int = 3,
    discover_forward_days: int = 3,
    verbose: bool = False):
    """
    Enhanced multi-bank processing with configurable Discover date matching.
    
    Args:
        enable_discover_backward_matching: Set to False to disable backward date matching for Discover
        discover_backward_days: How many days backward to look for Discover transactions
        discover_forward_days: How many days forward to look for Discover transactions
    """
    print("=== ENHANCED MULTI-BANK TRANSACTION MATCHING ===\n")
    
    # Create processor
    processor = EnhancedMultiBankProcessor()
    
    # Configure Discover date matching (easy to disable)
    processor.set_discover_date_matching(
        enabled=enable_discover_backward_matching,
        backward_days=discover_backward_days,
        forward_days=discover_forward_days
    )
    
    # Add main bank statement
    processor.add_bank_statement(
        filepath=main_bank_statement_path,
        statement_id='main',
        card_types=['Visa', 'Master Card', 'Amex', 'Debit Visa', 
                   'Debit Master', 'Other Cards', 'Cash', 'Check']
    )
    
    # Add Discover bank statement
    processor.add_bank_statement(
        filepath=discover_bank_statement_path,
        statement_id='discover',
        card_type_override='Discover'
    )
    
    # Load card summary
    print("\nLoading card summary...")
    card_summary, structure_info = preprocess_card_summary_dynamic(card_summary_path)
    print(f"✓ Loaded card summary: {len(card_summary)} days")
    
    # Run matching with flexible dates
    print("\nRunning enhanced transaction matching...")
    results = processor.match_transactions_with_flexible_dates(
        card_summary=card_summary,
        verbose=verbose
    )
    
    # Extract matched information
    matched_bank_rows = results.get('_matched_bank_rows', set())
    matched_dates_and_types = {}
    unmatched_info = {}
    
    for date, date_results in results.items():
        if isinstance(date, str) and date.startswith('_'):
            continue
        
        if date_results.get('matches_by_card_type'):
            matched_dates_and_types[date] = list(date_results['matches_by_card_type'].keys())
        
        for card_type, unmatch in date_results.get('unmatched_by_card_type', {}).items():
            unmatched_info[(date, card_type)] = unmatch
    
    # Generate reports
    print("\nGenerating reports...")
    
    # Create highlighted bank statements
    processor.create_highlighted_statements(
        results=results,
        matched_bank_rows=matched_bank_rows,
        output_dir=output_dir
    )
    
    # Create highlighted card summary
    create_highlighted_card_summary_dynamic(
        card_summary_path=card_summary_path,
        matched_dates_and_types=matched_dates_and_types,
        output_path=f"{output_dir}/card_summary_enhanced_highlighted.xlsx",
        unmatched_info=unmatched_info
    )
    
    # Print summary
    print("\n=== MATCHING SUMMARY ===")
    total_matched = sum(len(dr.get('matches_by_card_type', {})) 
                       for dr in results.values() 
                       if isinstance(dr, dict))
    total_unmatched = sum(len(dr.get('unmatched_by_card_type', {})) 
                         for dr in results.values() 
                         if isinstance(dr, dict))
    
    print(f"Total matched: {total_matched}")
    print(f"Total unmatched: {total_unmatched}")
    
    # Show any Discover matches with date offsets
    discover_offsets = []
    for date, date_results in results.items():
        if isinstance(date, str) and date.startswith('_'):
            continue
        for card_type, match in date_results.get('matches_by_card_type', {}).items():
            if card_type == 'Discover' and match.get('date_offset', 0) > 0:
                discover_offsets.append({
                    'date': date,
                    'offset': match['date_offset'],
                    'amount': match['expected']
                })
    
    if discover_offsets:
        print(f"\nDiscover matches with date offsets:")
        for offset_info in discover_offsets:
            print(f"  - {offset_info['date'].strftime('%Y-%m-%d')}: "
                  f"Found {offset_info['offset']} days off, ${offset_info['amount']:.2f}")
    
    print("\n=== PROCESS COMPLETE ===")
    
    return results