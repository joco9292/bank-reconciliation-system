#!/usr/bin/env python3
"""
Improved Matching Helpers with Fair Allocation

This module extends the existing matching system to prevent greedy allocation
where one cell consumes all available transactions.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Set, Optional
from itertools import combinations
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

class ImprovedTransactionMatcher:
    """
    Enhanced transaction matcher that prevents greedy allocation
    and ensures fair distribution of transactions across cells.
    """
    
    def __init__(self, max_transactions_per_cell: int = 5, 
                 fairness_threshold: float = 0.2):
        """
        Initialize the improved matcher.
        
        Args:
            max_transactions_per_cell: Maximum transactions one cell can consume
            fairness_threshold: Minimum ratio of available transactions to reserve for other cells
        """
        self.max_transactions_per_cell = max_transactions_per_cell
        self.fairness_threshold = fairness_threshold
        
        # Define the default filter pipeline
        self.default_filters = [
            ('exact_match', filter_exact_match),
            ('sum_by_description', filter_sum_by_description),
        ]
        
        # Define card-type-specific filters
        self.card_specific_filters = {
            'Amex': [
                ('amount_range', filter_by_amount_range),
            ],
        }
        
        # Optional: Define filters to exclude for specific card types
        self.excluded_filters = {}
    
    def add_filter(self, name: str, filter_func, position: int = None, 
                   card_types: Optional[List[str]] = None):
        """Add a new filter to the pipeline."""
        if card_types is None:
            # Add to default pipeline
            if position is None:
                self.default_filters.append((name, filter_func))
            else:
                self.default_filters.insert(position, (name, filter_func))
        else:
            # Add to specific card types
            for card_type in card_types:
                if card_type not in self.card_specific_filters:
                    self.card_specific_filters[card_type] = []
                self.card_specific_filters[card_type].append((name, filter_func))
    
    def get_filters_for_card_type(self, card_type: str) -> List[tuple]:
        """Get the appropriate filters for a specific card type."""
        filters = self.default_filters.copy()
        
        # Add card-specific filters
        if card_type in self.card_specific_filters:
            filters.extend(self.card_specific_filters[card_type])
        
        # Remove excluded filters
        if card_type in self.excluded_filters:
            excluded_names = self.excluded_filters[card_type]
            filters = [(name, func) for name, func in filters if name not in excluded_names]
        
        return filters
    
    def calculate_fair_allocation(self, all_cells: List[Tuple], 
                                total_available_transactions: int) -> Dict:
        """
        Calculate fair allocation of transactions across all cells.
        
        This prevents greedy matching by ensuring each cell gets a fair share
        of available transactions.
        """
        total_cells = len(all_cells)
        
        if total_cells == 0:
            return {}
        
        # Calculate base allocation per cell
        base_allocation = max(1, total_available_transactions // total_cells)
        
        # Apply fairness constraints
        max_per_cell = min(self.max_transactions_per_cell, 
                          int(total_available_transactions * (1 - self.fairness_threshold)))
        
        fair_allocation = {}
        for date, card_type, expected_amount in all_cells:
            # Start with base allocation
            allocation = base_allocation
            
            # Adjust based on expected amount
            if expected_amount > 1000:
                allocation = min(max_per_cell, allocation + 1)
            elif expected_amount < 100:
                allocation = max(1, allocation - 1)
            
            fair_allocation[(date, card_type)] = allocation
        
        return fair_allocation
    
    def apply_fair_allocation_constraint(self, transactions: pd.DataFrame, 
                                       max_allowed: int) -> pd.DataFrame:
        """
        Apply fair allocation constraint to limit transactions per cell.
        """
        if len(transactions) <= max_allowed:
            return transactions
        
        # Sort by amount descending and take the best ones
        return transactions.nlargest(max_allowed, 'Amount')
    
    def match_transactions_with_fair_allocation(self, card_summary: pd.DataFrame, 
                                              bank_statement: pd.DataFrame,
                                              forward_days: int = 3, 
                                              verbose: bool = False) -> Dict:
        """
        Main matching function that implements fair allocation to prevent greedy matching.
        """
        results = {}
        matched_bank_rows = set()
        
        # Track which bank rows are allocated to which cell for discrepancy calculations
        allocated_for_discrepancy = {}
        attempted_bank_rows = set()
        
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
        
        # Calculate total available transactions for fair allocation
        total_available = len(bank_statement)
        fair_allocation = self.calculate_fair_allocation(all_cells, total_available)
        
        if verbose:
            print("Fair allocation per cell:")
            for (date, card_type), allocation in fair_allocation.items():
                print(f"  {date.strftime('%Y-%m-%d')} {card_type}: {allocation} transactions max")
        
        # PASS 1: Do all matching with fair allocation constraints
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
                
                # Filter 1: Get relevant transactions
                filtered_transactions = filter_by_card_type_and_date(
                    bank_statement, card_type, date, forward_days
                )
                
                # Track all candidate bank rows as "attempted"
                if len(filtered_transactions) > 0:
                    candidate_rows = set(filtered_transactions['Bank_Row_Number'].tolist())
                    attempted_bank_rows.update(candidate_rows)
                
                if len(filtered_transactions) == 0:
                    date_results['unmatched_by_card_type'][card_type] = {
                        'expected': expected_amount,
                        'reason': 'No transactions found for card type in date range',
                        'bank_rows': [],
                        'found_transactions': 0,
                        'total_found': 0
                    }
                    continue
                
                # Remove already matched transactions
                available_transactions = filtered_transactions[
                    ~filtered_transactions['Bank_Row_Number'].isin(matched_bank_rows)
                ]
                
                # Apply fair allocation constraint
                available_transactions = self.apply_fair_allocation_constraint(
                    available_transactions, max_allowed
                )
                
                if len(available_transactions) == 0:
                    date_results['unmatched_by_card_type'][card_type] = {
                        'expected': expected_amount,
                        'reason': 'No available transactions after fair allocation',
                        'bank_rows': [],
                        'found_transactions': 0,
                        'total_found': 0
                    }
                    continue
                
                # Get the appropriate filters for this card type
                filters_to_apply = self.get_filters_for_card_type(card_type)
                
                if verbose:
                    filter_names = [name for name, _ in filters_to_apply]
                    print(f"Processing {date.strftime('%Y-%m-%d')} {card_type}: "
                          f"Using filters: {filter_names} (max {max_allowed} transactions)")
                
                # Run through the card-type-specific filter pipeline
                matched = False
                for filter_name, filter_func in filters_to_apply:
                    result = filter_func(available_transactions, expected_amount)
                    
                    if result['matched']:
                        date_results['matches_by_card_type'][card_type] = {
                            'expected': expected_amount,
                            'match_type': result['match_type'],
                            'transactions': result['transactions'],
                            'bank_rows': result['bank_rows'],
                            'actual_total': result.get('actual_total', expected_amount),
                            'difference': result.get('difference', 0),
                            'fair_allocation_limit': max_allowed,
                            **{k: v for k, v in result.items() 
                               if k not in ['matched', 'match_type', 'transactions', 
                                           'bank_rows', 'actual_total', 'difference']}
                        }
                        matched_bank_rows.update(result['bank_rows'])
                        matched = True
                        
                        if verbose:
                            print(f"  ✓ Matched with {filter_name} (used {len(result['bank_rows'])} transactions)")
                        break
                
                if not matched:
                    # Store preliminary unmatched info - will update in Pass 2
                    date_results['unmatched_by_card_type'][card_type] = {
                        'expected': expected_amount,
                        'date': date,
                        'card_type': card_type,
                        'forward_days': forward_days,
                        'filters_tried': [name for name, _ in filters_to_apply],
                        'fair_allocation_limit': max_allowed,
                        'available_after_allocation': len(available_transactions)
                    }
                    
                    if verbose:
                        print(f"  ✗ No match found after trying {len(filters_to_apply)} filters "
                              f"(had {len(available_transactions)} transactions available)")
            
            results[date] = date_results
        
        # PASS 2: Calculate EXCLUSIVE unmatched totals for discrepancy calculations
        if not verbose:
            print("\nPass 2: Calculating exclusive unmatched transaction totals...")
        
        # Sort unmatched cells by expected amount (descending) to prioritize larger discrepancies
        unmatched_cells = []
        for date, date_results in results.items():
            for card_type, unmatch_info in date_results['unmatched_by_card_type'].items():
                if 'date' in unmatch_info:
                    unmatched_cells.append((date, card_type, unmatch_info))
        
        unmatched_cells.sort(key=lambda x: x[2]['expected'], reverse=True)
        
        # Allocate unmatched bank transactions exclusively
        for date, card_type, unmatch_info in unmatched_cells:
            # Get transactions for this card type and date range
            filtered_transactions = filter_by_card_type_and_date(
                bank_statement, 
                unmatch_info['card_type'], 
                unmatch_info['date'], 
                unmatch_info['forward_days']
            )
            
            # Filter out already matched transactions
            unmatched_only = filtered_transactions[
                ~filtered_transactions['Bank_Row_Number'].isin(matched_bank_rows)
            ]
            
            # Apply fair allocation constraint for unmatched transactions too
            max_allowed = unmatch_info.get('fair_allocation_limit', self.max_transactions_per_cell)
            unmatched_only = self.apply_fair_allocation_constraint(unmatched_only, max_allowed)
            
            # Also filter out transactions already allocated to other cells
            available_for_this_cell = []
            for _, trans in unmatched_only.iterrows():
                bank_row = trans['Bank_Row_Number']
                if bank_row not in allocated_for_discrepancy:
                    available_for_this_cell.append(trans)
                    # Mark this transaction as allocated to this cell
                    allocated_for_discrepancy[bank_row] = (date, card_type)
            
            available_df = pd.DataFrame(available_for_this_cell) if available_for_this_cell else pd.DataFrame()
            
            # Update with accurate EXCLUSIVE unmatched totals
            results[date]['unmatched_by_card_type'][card_type] = {
                'expected': unmatch_info['expected'],
                'found_transactions': len(available_df),
                'total_found': available_df['Amount'].sum() if len(available_df) > 0 else 0,
                'reason': f"No match found after trying filters: {unmatch_info.get('filters_tried', [])}",
                'bank_rows': available_df['Bank_Row_Number'].tolist() if len(available_df) > 0 else [],
                'exclusive_allocation': True,
                'fair_allocation_limit': max_allowed
            }
            
            # Debug output for significant unmatched amounts
            if unmatch_info['expected'] > 1000 and not verbose:
                total_found = available_df['Amount'].sum() if len(available_df) > 0 else 0
                print(f"  {unmatch_info['date'].strftime('%Y-%m-%d')} {card_type}: "
                      f"Expected ${unmatch_info['expected']:,.2f}, "
                      f"Found ${total_found:,.2f} "
                      f"in {len(available_df)} EXCLUSIVELY allocated transactions "
                      f"(limit: {max_allowed})")
        
        # Add allocation info to results for reporting
        results['_allocated_for_discrepancy'] = allocated_for_discrepancy
        results['_attempted_bank_rows'] = attempted_bank_rows
        results['_fair_allocation_limits'] = fair_allocation
        
        return results

# Example usage
if __name__ == "__main__":
    print("Improved Transaction Matcher with Fair Allocation")
    print("Key improvements:")
    print("- Prevents greedy matching")
    print("- Ensures fair distribution of transactions")
    print("- Limits transactions per cell")
    print("- Better overall matching results")
