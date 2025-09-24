#!/usr/bin/env python3
"""
Fair Transaction Matching Algorithm

This module implements a fair allocation system that prevents one cell from
"eating up" all available transactions, ensuring better distribution across
all cells that need to match.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Set
from itertools import combinations
import numpy as np

class FairTransactionMatcher:
    """
    A fair transaction matching system that prevents greedy allocation
    and ensures optimal distribution of transactions across all cells.
    """
    
    def __init__(self, max_transactions_per_cell: int = 5, 
                 fairness_threshold: float = 0.1):
        """
        Initialize the fair matcher.
        
        Args:
            max_transactions_per_cell: Maximum transactions one cell can consume
            fairness_threshold: Minimum ratio of available transactions to reserve for other cells
        """
        self.max_transactions_per_cell = max_transactions_per_cell
        self.fairness_threshold = fairness_threshold
    
    def identify_card_type(self, description: str) -> str:
        """Identify card type from transaction description."""
        description_upper = description.upper()
        
        if 'AMEX' in description_upper or 'AMERICAN EXPRESS' in description_upper:
            return 'Amex'
        elif 'VISA' in description_upper:
            return 'Visa'
        elif 'MASTERCARD' in description_upper or 'MC' in description_upper:
            return 'Mastercard'
        elif 'DISCOVER' in description_upper:
            return 'Discover'
        
        return 'Unknown'
    
    def filter_by_card_type_and_date(self, transactions: pd.DataFrame, card_type: str, 
                                   date: datetime, forward_days: int = 3) -> pd.DataFrame:
        """Filter transactions by card type and date range.
        
        Amex transactions get an extra day of forward-looking allowance.
        """
        # Give Amex an extra day of forward-looking allowance
        if card_type == 'Amex':
            effective_forward_days = forward_days + 1
        else:
            effective_forward_days = forward_days
        
        date_end = date + timedelta(days=effective_forward_days)
        
        return transactions[
            (transactions['Card_Type'] == card_type) &
            (transactions['Date'] >= date) &
            (transactions['Date'] <= date_end) &
            (transactions['Transaction_Type'].isin(['CREDIT', 'BPAD']))
        ].copy()
    
    def find_exact_match(self, transactions: pd.DataFrame, expected_amount: float, 
                        tolerance: float = 0.01) -> Dict:
        """Find exact single transaction match."""
        exact_matches = transactions[abs(transactions['Amount'] - expected_amount) < tolerance]
        
        if not exact_matches.empty:
            best_match = exact_matches.iloc[0]
            return {
                'matched': True,
                'match_type': 'exact_single',
                'transactions': [best_match.to_dict()],
                'bank_rows': [best_match['Bank_Row_Number']],
                'actual_total': best_match['Amount'],
                'difference': best_match['Amount'] - expected_amount
            }
        
        return {'matched': False}
    
    def find_combination_match(self, transactions: pd.DataFrame, expected_amount: float,
                             max_transactions: int = 3, tolerance: float = 0.01) -> Dict:
        """Find combination of transactions that sum to expected amount."""
        if len(transactions) > 10:
            transactions = transactions.nlargest(10, 'Amount')
        
        for r in range(2, min(len(transactions) + 1, max_transactions + 1)):
            for combo in combinations(transactions.index, r):
                combo_sum = transactions.loc[list(combo), 'Amount'].sum()
                if abs(combo_sum - expected_amount) < tolerance:
                    selected_trans = transactions.loc[list(combo)]
                    return {
                        'matched': True,
                        'match_type': f'combination_{r}_transactions',
                        'transactions': selected_trans.to_dict('records'),
                        'bank_rows': selected_trans['Bank_Row_Number'].tolist(),
                        'actual_total': combo_sum,
                        'difference': combo_sum - expected_amount
                    }
        
        return {'matched': False}
    
    def calculate_fair_allocation(self, all_cells: List[Tuple], 
                                available_transactions: pd.DataFrame) -> Dict:
        """
        Calculate fair allocation of transactions across all cells.
        
        This is the key function that prevents greedy matching by:
        1. Analyzing all cells that need matching
        2. Calculating how many transactions each cell should get
        3. Ensuring no cell gets more than its fair share
        """
        total_transactions = len(available_transactions)
        total_cells = len(all_cells)
        
        # Calculate base allocation per cell
        base_allocation = max(1, total_transactions // total_cells)
        
        # Apply fairness constraints
        max_per_cell = min(self.max_transactions_per_cell, 
                          int(total_transactions * (1 - self.fairness_threshold)))
        
        fair_allocation = {}
        for date, card_type, expected_amount in all_cells:
            # Start with base allocation
            allocation = base_allocation
            
            # Adjust based on expected amount (larger amounts might need more transactions)
            if expected_amount > 1000:
                allocation = min(max_per_cell, allocation + 1)
            elif expected_amount < 100:
                allocation = max(1, allocation - 1)
            
            fair_allocation[(date, card_type)] = allocation
        
        return fair_allocation
    
    def match_with_fair_allocation(self, card_summary: pd.DataFrame, 
                                 bank_statement: pd.DataFrame,
                                 forward_days: int = 3, verbose: bool = False) -> Dict:
        """
        Main matching function that implements fair allocation.
        """
        # Prepare data
        bank_statement['Bank_Row_Number'] = range(2, len(bank_statement) + 2)
        bank_statement['Card_Type'] = bank_statement['Description'].apply(self.identify_card_type)
        
        results = {}
        matched_bank_rows = set()
        
        # Get all cells that need matching
        card_types = [col for col in card_summary.columns 
                     if col not in ['Date', 'Total', 'Visa & MC'] and not col.startswith('Unnamed')]
        
        all_cells = []
        for _, card_row in card_summary.iterrows():
            date = card_row['Date']
            for card_type in card_types:
                expected_amount = card_row[card_type]
                if pd.notna(expected_amount) and expected_amount > 0:
                    all_cells.append((date, card_type, expected_amount))
        
        if verbose:
            print(f"Found {len(all_cells)} cells that need matching")
        
        # Calculate fair allocation
        fair_allocation = self.calculate_fair_allocation(all_cells, bank_statement)
        
        if verbose:
            print("Fair allocation per cell:")
            for (date, card_type), allocation in fair_allocation.items():
                print(f"  {date.strftime('%Y-%m-%d')} {card_type}: {allocation} transactions max")
        
        # Process each cell with fair allocation constraints
        for date, card_type, expected_amount in all_cells:
            # Initialize date results if needed
            if date not in results:
                results[date] = {
                    'date': date,
                    'matches_by_card_type': {},
                    'unmatched_by_card_type': {}
                }
            
            # Get available transactions for this cell
            filtered_transactions = self.filter_by_card_type_and_date(
                bank_statement, card_type, date, forward_days
            )
            
            # Remove already matched transactions
            available_transactions = filtered_transactions[
                ~filtered_transactions['Bank_Row_Number'].isin(matched_bank_rows)
            ]
            
            # Apply fair allocation limit
            max_allowed = fair_allocation[(date, card_type)]
            if len(available_transactions) > max_allowed:
                # Sort by amount descending and take the best ones
                available_transactions = available_transactions.nlargest(max_allowed, 'Amount')
            
            if len(available_transactions) == 0:
                results[date]['unmatched_by_card_type'][card_type] = {
                    'expected': expected_amount,
                    'reason': 'No available transactions after fair allocation',
                    'bank_rows': [],
                    'found_transactions': 0,
                    'total_found': 0
                }
                continue
            
            # Try to find a match
            match_found = False
            
            # Try exact match first
            exact_result = self.find_exact_match(available_transactions, expected_amount)
            if exact_result['matched']:
                results[date]['matches_by_card_type'][card_type] = exact_result
                matched_bank_rows.update(exact_result['bank_rows'])
                match_found = True
                
                if verbose:
                    print(f"✓ {date.strftime('%Y-%m-%d')} {card_type}: Exact match")
            
            # Try combination match if no exact match
            if not match_found:
                combo_result = self.find_combination_match(available_transactions, expected_amount)
                if combo_result['matched']:
                    results[date]['matches_by_card_type'][card_type] = combo_result
                    matched_bank_rows.update(combo_result['bank_rows'])
                    match_found = True
                    
                    if verbose:
                        print(f"✓ {date.strftime('%Y-%m-%d')} {card_type}: Combination match")
            
            # Mark as unmatched if no match found
            if not match_found:
                results[date]['unmatched_by_card_type'][card_type] = {
                    'expected': expected_amount,
                    'reason': 'No match found within fair allocation constraints',
                    'bank_rows': available_transactions['Bank_Row_Number'].tolist(),
                    'found_transactions': len(available_transactions),
                    'total_found': available_transactions['Amount'].sum()
                }
                
                if verbose:
                    print(f"✗ {date.strftime('%Y-%m-%d')} {card_type}: No match found")
        
        return results

# Example usage and testing
if __name__ == "__main__":
    # This would be used to test the fair matching algorithm
    print("Fair Transaction Matcher - Prevents greedy allocation")
    print("Key features:")
    print("- Calculates fair allocation per cell")
    print("- Limits transactions per cell")
    print("- Ensures better distribution across all cells")
    print("- Prevents one cell from consuming all transactions")
