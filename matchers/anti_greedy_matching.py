#!/usr/bin/env python3
"""
Anti-Greedy Matching Solution

This module provides a simple solution to prevent one cell from "eating up"
all available transactions, leaving insufficient transactions for other cells.

The solution works by:
1. Limiting the number of transactions each cell can consume
2. Implementing a fair allocation system
3. Providing configuration options to control the behavior
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sys
import os

# Import existing functions
sys.path.append(os.path.dirname(__file__))
from matching_helpers import (
    identify_card_type, 
    filter_by_card_type_and_date,
    filter_exact_match,
    filter_sum_by_description,
    filter_by_amount_range,
    filter_split_transactions
)

class AntiGreedyMatcher:
    """
    A simple anti-greedy matching system that prevents one cell from
    consuming all available transactions.
    """
    
    def __init__(self, max_transactions_per_cell: int = 3, 
                 enable_fair_allocation: bool = True):
        """
        Initialize the anti-greedy matcher.
        
        Args:
            max_transactions_per_cell: Maximum transactions one cell can consume
            enable_fair_allocation: Whether to enable fair allocation across cells
        """
        self.max_transactions_per_cell = max_transactions_per_cell
        self.enable_fair_allocation = enable_fair_allocation
    
    def limit_transactions_per_cell(self, transactions: pd.DataFrame, 
                                  max_allowed: int) -> pd.DataFrame:
        """
        Limit the number of transactions available to a cell.
        
        This is the key function that prevents greedy matching.
        """
        if len(transactions) <= max_allowed:
            return transactions
        
        # Sort by amount descending and take the best ones
        # This ensures we get the most relevant transactions
        return transactions.nlargest(max_allowed, 'Amount')
    
    def calculate_fair_allocation(self, all_cells: List[Tuple], 
                                total_transactions: int) -> Dict:
        """
        Calculate how many transactions each cell should get.
        
        This ensures fair distribution across all cells.
        """
        if not self.enable_fair_allocation or len(all_cells) == 0:
            # If fair allocation is disabled, use the max limit for all cells
            return {(date, card_type): self.max_transactions_per_cell 
                   for date, card_type, _ in all_cells}
        
        total_cells = len(all_cells)
        
        # Calculate base allocation per cell
        base_allocation = max(1, total_transactions // total_cells)
        
        # Apply the maximum limit
        fair_allocation = {}
        for date, card_type, expected_amount in all_cells:
            # Start with base allocation
            allocation = base_allocation
            
            # Adjust based on expected amount (larger amounts might need more transactions)
            if expected_amount > 1000:
                allocation = min(self.max_transactions_per_cell, allocation + 1)
            elif expected_amount < 100:
                allocation = max(1, allocation - 1)
            
            fair_allocation[(date, card_type)] = allocation
        
        return fair_allocation
    
    def _attempt_cleanup_matching_anti_greedy(self, leftover_transactions: pd.DataFrame, 
                                            results: Dict, forward_days: int, verbose: bool = False) -> Dict:
        """
        Attempt to match leftover transactions to cells that could benefit.
        Only looks forward within 1-2 extra days to avoid matching too far out.
        """
        cleanup_matches = {}
        
        # Group leftover transactions by card type
        leftover_by_card_type = leftover_transactions.groupby('Card_Type')
        
        for card_type, card_transactions in leftover_by_card_type:
            if card_type == 'Unknown':
                continue  # Skip unknown card types
            
            # Try to match these transactions to cells of the same card type
            for date, date_results in results.items():
                if card_type in date_results.get('unmatched_by_card_type', {}):
                    unmatched_info = date_results['unmatched_by_card_type'][card_type]
                    expected_amount = unmatched_info['expected']
                    
                    # Check if any leftover transactions could help this cell
                    # Use extended forward days (1-2 extra days) for cleanup
                    extended_forward_days = forward_days + 2
                    
                    # Filter transactions within extended date range
                    date_end = date + timedelta(days=extended_forward_days)
                    extended_transactions = card_transactions[
                        (card_transactions['Date'] >= date) &
                        (card_transactions['Date'] <= date_end)
                    ]
                    
                    if len(extended_transactions) == 0:
                        continue
                    
                    # Try to find a match using the same filters as anti-greedy matching
                    match_found = False
                    
                    # Try exact match first
                    exact_result = filter_exact_match(extended_transactions, expected_amount)
                    if exact_result['matched']:
                        cleanup_matches[(date, card_type)] = {
                            'expected': expected_amount,
                            'match_type': 'cleanup_exact',
                            'transactions': exact_result['transactions'],
                            'bank_rows': exact_result['bank_rows'],
                            'actual_total': exact_result.get('actual_total', expected_amount),
                            'difference': exact_result.get('difference', 0),
                            'cleanup_extended_days': extended_forward_days
                        }
                        match_found = True
                    
                    # Try sum by description if no exact match
                    if not match_found:
                        sum_result = filter_sum_by_description(extended_transactions, expected_amount)
                        if sum_result['matched']:
                            cleanup_matches[(date, card_type)] = {
                                'expected': expected_amount,
                                'match_type': 'cleanup_sum_by_description',
                                'transactions': sum_result['transactions'],
                                'bank_rows': sum_result['bank_rows'],
                                'actual_total': sum_result.get('actual_total', expected_amount),
                                'difference': sum_result.get('difference', 0),
                                'cleanup_extended_days': extended_forward_days
                            }
                            match_found = True
                    
                    # Try split transactions if no other match
                    if not match_found:
                        split_result = filter_split_transactions(extended_transactions, expected_amount)
                        if split_result['matched']:
                            cleanup_matches[(date, card_type)] = {
                                'expected': expected_amount,
                                'match_type': 'cleanup_split_transactions',
                                'transactions': split_result['transactions'],
                                'bank_rows': split_result['bank_rows'],
                                'actual_total': split_result.get('actual_total', expected_amount),
                                'difference': split_result.get('difference', 0),
                                'cleanup_extended_days': extended_forward_days
                            }
                            match_found = True
                    
                    if match_found:
                        if verbose:
                            print(f"    Found cleanup match for {date.strftime('%Y-%m-%d')} {card_type}: "
                                  f"${cleanup_matches[(date, card_type)]['actual_total']:,.2f} "
                                  f"(extended to {extended_forward_days} days)")
                        
                        # Remove matched transactions from leftover pool
                        leftover_transactions = leftover_transactions[
                            ~leftover_transactions['Bank_Row_Number'].isin(cleanup_matches[(date, card_type)]['bank_rows'])
                        ]
                        break  # Move to next cell
                    
                    # If we found a match for this cell, don't try other cells
                    if (date, card_type) in cleanup_matches:
                        break
        
        return cleanup_matches
    
    def match_with_anti_greedy(self, card_summary: pd.DataFrame, 
                             bank_statement: pd.DataFrame,
                             forward_days: int = 3, verbose: bool = False) -> Dict:
        """
        Main matching function that implements anti-greedy allocation.
        
        This function can be used as a drop-in replacement for the existing
        matching system to prevent greedy allocation.
        """
        # Prepare data
        bank_statement['Bank_Row_Number'] = range(2, len(bank_statement) + 2)
        bank_statement['Card_Type'] = bank_statement['Description'].apply(identify_card_type)
        
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
            print(f"Anti-greedy matching: Found {len(all_cells)} cells that need matching")
        
        # Calculate fair allocation
        total_transactions = len(bank_statement)
        fair_allocation = self.calculate_fair_allocation(all_cells, total_transactions)
        
        if verbose:
            print("Fair allocation per cell:")
            for (date, card_type), allocation in fair_allocation.items():
                print(f"  {date.strftime('%Y-%m-%d')} {card_type}: {allocation} transactions max")
        
        # Process each cell with anti-greedy constraints
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
                
                # Get the fair allocation limit for this cell
                max_allowed = fair_allocation.get((date, card_type), self.max_transactions_per_cell)
                
                # Get available transactions for this cell
                filtered_transactions = filter_by_card_type_and_date(
                    bank_statement, card_type, date, forward_days
                )
                
                # Remove already matched transactions
                available_transactions = filtered_transactions[
                    ~filtered_transactions['Bank_Row_Number'].isin(matched_bank_rows)
                ]
                
                # Apply anti-greedy constraint
                available_transactions = self.limit_transactions_per_cell(
                    available_transactions, max_allowed
                )
                
                if len(available_transactions) == 0:
                    date_results['unmatched_by_card_type'][card_type] = {
                        'expected': expected_amount,
                        'reason': 'No available transactions after anti-greedy allocation',
                        'bank_rows': [],
                        'found_transactions': 0,
                        'total_found': 0
                    }
                    continue
                
                # Try to find a match using existing filters
                match_found = False
                
                # Try exact match first
                exact_result = filter_exact_match(available_transactions, expected_amount)
                if exact_result['matched']:
                    date_results['matches_by_card_type'][card_type] = exact_result
                    matched_bank_rows.update(exact_result['bank_rows'])
                    match_found = True
                    
                    if verbose:
                        print(f"✓ {date.strftime('%Y-%m-%d')} {card_type}: Exact match "
                              f"(used {len(exact_result['bank_rows'])} transactions)")
                
                # Try sum by description if no exact match
                if not match_found:
                    sum_result = filter_sum_by_description(available_transactions, expected_amount)
                    if sum_result['matched']:
                        date_results['matches_by_card_type'][card_type] = sum_result
                        matched_bank_rows.update(sum_result['bank_rows'])
                        match_found = True
                        
                        if verbose:
                            print(f"✓ {date.strftime('%Y-%m-%d')} {card_type}: Sum by description "
                                  f"(used {len(sum_result['bank_rows'])} transactions)")
                
                # Try split transactions if no other match
                if not match_found:
                    split_result = filter_split_transactions(available_transactions, expected_amount)
                    if split_result['matched']:
                        date_results['matches_by_card_type'][card_type] = split_result
                        matched_bank_rows.update(split_result['bank_rows'])
                        match_found = True
                        
                        if verbose:
                            print(f"✓ {date.strftime('%Y-%m-%d')} {card_type}: Split transactions "
                                  f"(used {len(split_result['bank_rows'])} transactions)")
                
                # Mark as unmatched if no match found
                if not match_found:
                    date_results['unmatched_by_card_type'][card_type] = {
                        'expected': expected_amount,
                        'reason': 'No match found within anti-greedy constraints',
                        'bank_rows': available_transactions['Bank_Row_Number'].tolist(),
                        'found_transactions': len(available_transactions),
                        'total_found': available_transactions['Amount'].sum(),
                        'anti_greedy_limit': max_allowed
                    }
                    
                    if verbose:
                        print(f"✗ {date.strftime('%Y-%m-%d')} {card_type}: No match found "
                              f"(had {len(available_transactions)} transactions available)")
            
            results[date] = date_results
        
        # PASS 2: Cleanup pass - try to match leftover transactions to cells that could benefit
        if not verbose:
            print("\nPass 2: Cleanup pass - attempting to match leftover transactions...")
        
        # Find all unmatched bank transactions
        all_bank_rows = set(bank_statement['Bank_Row_Number'].tolist())
        leftover_bank_rows = all_bank_rows - matched_bank_rows
        
        if len(leftover_bank_rows) > 0:
            if verbose:
                print(f"Found {len(leftover_bank_rows)} leftover transactions to attempt cleanup matching")
            
            # Get leftover transactions
            leftover_transactions = bank_statement[
                bank_statement['Bank_Row_Number'].isin(leftover_bank_rows)
            ].copy()
            
            # Try to match leftover transactions to cells that could benefit
            cleanup_matches = self._attempt_cleanup_matching_anti_greedy(
                leftover_transactions, results, forward_days, verbose
            )
            
            # Apply cleanup matches if any found
            if cleanup_matches:
                for (date, card_type), match_info in cleanup_matches.items():
                    if date in results and 'matches_by_card_type' in results[date]:
                        results[date]['matches_by_card_type'][card_type] = match_info
                        matched_bank_rows.update(match_info['bank_rows'])
                        
                        # Remove from unmatched if it was there
                        if card_type in results[date]['unmatched_by_card_type']:
                            del results[date]['unmatched_by_card_type'][card_type]
                        
                        if verbose:
                            print(f"  ✓ Cleanup match: {date.strftime('%Y-%m-%d')} {card_type} "
                                  f"matched ${match_info['actual_total']:,.2f}")
        
        return results

# Configuration and usage examples
def create_anti_greedy_matcher(max_transactions_per_cell: int = 3, 
                              enable_fair_allocation: bool = True) -> AntiGreedyMatcher:
    """
    Create an anti-greedy matcher with specified configuration.
    
    Args:
        max_transactions_per_cell: Maximum transactions one cell can consume
        enable_fair_allocation: Whether to enable fair allocation across cells
    
    Returns:
        AntiGreedyMatcher instance
    """
    return AntiGreedyMatcher(max_transactions_per_cell, enable_fair_allocation)

# Example usage
if __name__ == "__main__":
    print("Anti-Greedy Matching Solution")
    print("=" * 50)
    print("This solution prevents one cell from consuming all available transactions.")
    print("\nKey features:")
    print("- Limits transactions per cell")
    print("- Implements fair allocation")
    print("- Prevents greedy matching")
    print("- Configurable limits")
    
    # Example configuration
    matcher = create_anti_greedy_matcher(
        max_transactions_per_cell=3,
        enable_fair_allocation=True
    )
    
    print(f"\nExample configuration:")
    print(f"- Max transactions per cell: {matcher.max_transactions_per_cell}")
    print(f"- Fair allocation enabled: {matcher.enable_fair_allocation}")
