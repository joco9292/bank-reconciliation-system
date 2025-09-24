#!/usr/bin/env python3
"""
Fair Matching Configuration

This module provides configuration options to enable fair matching
in the existing bank reconciliation system.
"""

# Fair matching configuration
FAIR_MATCHING_CONFIG = {
    'enabled': True,  # Set to True to enable fair matching
    'max_transactions_per_cell': 5,  # Maximum transactions one cell can consume
    'fairness_threshold': 0.2,  # Minimum ratio of transactions to reserve for other cells
    'verbose_fair_allocation': False,  # Show fair allocation details
}

def get_fair_matching_config():
    """Get the current fair matching configuration."""
    return FAIR_MATCHING_CONFIG.copy()

def update_fair_matching_config(**kwargs):
    """Update fair matching configuration."""
    global FAIR_MATCHING_CONFIG
    FAIR_MATCHING_CONFIG.update(kwargs)

def is_fair_matching_enabled():
    """Check if fair matching is enabled."""
    return FAIR_MATCHING_CONFIG['enabled']

def get_max_transactions_per_cell():
    """Get the maximum transactions per cell limit."""
    return FAIR_MATCHING_CONFIG['max_transactions_per_cell']

def get_fairness_threshold():
    """Get the fairness threshold."""
    return FAIR_MATCHING_CONFIG['fairness_threshold']

# Example usage
if __name__ == "__main__":
    print("Fair Matching Configuration")
    print(f"Enabled: {is_fair_matching_enabled()}")
    print(f"Max transactions per cell: {get_max_transactions_per_cell()}")
    print(f"Fairness threshold: {get_fairness_threshold()}")
    
    # Example of updating configuration
    update_fair_matching_config(
        max_transactions_per_cell=3,
        fairness_threshold=0.3
    )
    
    print("\nAfter update:")
    print(f"Max transactions per cell: {get_max_transactions_per_cell()}")
    print(f"Fairness threshold: {get_fairness_threshold()}")
