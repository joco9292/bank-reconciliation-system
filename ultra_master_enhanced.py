"""
ULTRA MASTER RECONCILIATION SCRIPT - ENHANCED VERSION
Handles complex edge cases:
1. Single GC 1416 transaction representing both Cash and Check
2. Multiple transactions aggregating into Cash or Check
3. Discover transactions appearing on earlier dates (configurable)
"""

import os
import sys
import glob
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import argparse

class UltraMasterReconciliationEnhanced:
    """
    Enhanced unified reconciliation system with advanced edge case handling.
    """
    
    def __init__(self, auto_detect: bool = True, verbose: bool = False, 
                 enable_discover_backward: bool = True):
        self.auto_detect = auto_detect
        self.verbose = verbose
        self.enable_discover_backward = enable_discover_backward
        self.detected_files = {}
        self.processing_mode = None
        
        # Configuration for special handling
        self.config = {
            'discover_backward_days': 3,
            'discover_forward_days': 3,
            'discover_backward_enabled': enable_discover_backward,
            'deposit_forward_days': 3,
            'enable_flexible_deposit_matching': True
        }
        
    def detect_files(self, directory: str = '.') -> Dict:
        """
        Automatically detect reconciliation files in the directory.
        """
        print("🔍 Auto-detecting files...")
        
        detected = {
            'bank_statements': [],
            'card_summary': None,
            'deposit_slip': None,
            'discover_statement': None
        }
        
        # Common patterns for each file type
        patterns = {
            'bank_statements': [
                '*bank*statement*.csv', '*bank*statement*.CSV',
                '*statement*.csv', '*statement*.CSV'
            ],
            'card_summary': [
                '*card*summary*.xlsx', '*credit*card*.xlsx',
                '*CreditCard*.xlsx', '*CardSummary*.xlsx'
            ],
            'deposit_slip': [
                '*deposit*.xlsx', '*Deposit*.xlsx',
                '*MonthlyDeposit*.xlsx'
            ],
            'discover_statement': [
                '*discover*.csv', '*discover*.CSV',
                '*Discover*.csv', '*Discover*.CSV'
            ]
        }
        
        # Search for files
        for file_type, file_patterns in patterns.items():
            for pattern in file_patterns:
                matches = glob.glob(os.path.join(directory, pattern))
                
                if file_type == 'bank_statements':
                    for match in matches:
                        if 'discover' not in match.lower():
                            detected['bank_statements'].append(match)
                elif file_type == 'discover_statement':
                    if matches and not detected['discover_statement']:
                        detected['discover_statement'] = matches[0]
                elif file_type == 'card_summary':
                    if matches and not detected['card_summary']:
                        detected['card_summary'] = matches[0]
                elif file_type == 'deposit_slip':
                    if matches and not detected['deposit_slip']:
                        detected['deposit_slip'] = matches[0]
        
        # Clean up bank statements list
        if detected['discover_statement'] in detected['bank_statements']:
            detected['bank_statements'].remove(detected['discover_statement'])
        
        self.detected_files = detected
        return detected
    
    def determine_processing_mode(self) -> str:
        """
        Determine which processing mode to use based on detected files.
        """
        has_main_bank = len(self.detected_files['bank_statements']) > 0
        has_discover = self.detected_files['discover_statement'] is not None
        has_cards = self.detected_files['card_summary'] is not None
        has_deposits = self.detected_files['deposit_slip'] is not None
        
        modes = []
        
        # Determine mode
        if has_main_bank and has_discover and has_cards:
            modes.append('multi_bank_cards')
        elif has_main_bank and has_cards:
            modes.append('single_bank_cards')
        
        if has_main_bank and has_deposits:
            modes.append('deposits')
        
        # Combine modes
        if 'multi_bank_cards' in modes and 'deposits' in modes:
            return 'full_multi_bank_with_deposits'
        elif 'single_bank_cards' in modes and 'deposits' in modes:
            return 'full_single_bank_with_deposits'
        elif 'multi_bank_cards' in modes:
            return 'multi_bank_cards_only'
        elif 'single_bank_cards' in modes:
            return 'single_bank_cards_only'
        elif 'deposits' in modes:
            return 'deposits_only'
        else:
            return 'insufficient_files'
    
    def print_detection_summary(self):
        """
        Print a summary of detected files and processing mode.
        """
        print("\n" + "="*60)
        print("FILE DETECTION SUMMARY")
        print("="*60)
        
        print("\n📁 Detected Files:")
        
        if self.detected_files['bank_statements']:
            print(f"  ✓ Main Bank Statement: {self.detected_files['bank_statements'][0]}")
        else:
            print("  ✗ Main Bank Statement: Not found")
        
        if self.detected_files['discover_statement']:
            print(f"  ✓ Discover Statement: {self.detected_files['discover_statement']}")
        else:
            print("  ✗ Discover Statement: Not found")
        
        if self.detected_files['card_summary']:
            print(f"  ✓ Card Summary: {self.detected_files['card_summary']}")
        else:
            print("  ✗ Card Summary: Not found")
        
        if self.detected_files['deposit_slip']:
            print(f"  ✓ Deposit Slip: {self.detected_files['deposit_slip']}")
        else:
            print("  ✗ Deposit Slip: Not found")
        
        mode = self.determine_processing_mode()
        self.processing_mode = mode
        
        print(f"\n🎯 Processing Mode: {mode.replace('_', ' ').title()}")
        
        # Show special configurations
        print("\n⚙️  Special Configurations:")
        if self.detected_files['discover_statement']:
            if self.config['discover_backward_enabled']:
                print(f"  • Discover backward matching: ENABLED ({self.config['discover_backward_days']} days)")
            else:
                print(f"  • Discover backward matching: DISABLED")
        
        if self.detected_files['deposit_slip']:
            print(f"  • Flexible deposit matching: ENABLED")
            print(f"    - Single GC 1416 → Cash + Check splitting")
            print(f"    - Multi-transaction aggregation")
        
        return mode
    
    def run_reconciliation(self, output_dir: str = '.', force_mode: Optional[str] = None):
        """
        Run the appropriate reconciliation based on detected files or forced mode.
        """
        mode = force_mode or self.processing_mode
        
        if not mode or mode == 'insufficient_files':
            print("\n❌ Cannot proceed - insufficient files detected")
            return None
        
        print("\n" + "="*60)
        print(f"STARTING ENHANCED RECONCILIATION")
        print("="*60)
        
        # Route to appropriate processor
        if mode == 'full_multi_bank_with_deposits':
            return self._run_full_multi_bank_with_deposits_enhanced(output_dir)
        elif mode == 'full_single_bank_with_deposits':
            return self._run_full_single_bank_with_deposits_enhanced(output_dir)
        elif mode == 'multi_bank_cards_only':
            return self._run_multi_bank_cards_enhanced(output_dir)
        elif mode == 'single_bank_cards_only':
            return self._run_single_bank_cards(output_dir)
        elif mode == 'deposits_only':
            return self._run_deposits_only_enhanced(output_dir)
        else:
            print(f"❌ Unknown processing mode: {mode}")
            return None
    
    def _run_full_multi_bank_with_deposits_enhanced(self, output_dir: str):
        """
        Run complete reconciliation with multiple banks and enhanced deposit matching.
        """
        print("\n🏦 Processing Multiple Banks with Enhanced Deposits...")
        
        # First run enhanced multi-bank card matching
        from enhanced_multi_bank import process_with_enhanced_multi_bank
        
        card_results = process_with_enhanced_multi_bank(
            main_bank_statement_path=self.detected_files['bank_statements'][0],
            discover_bank_statement_path=self.detected_files['discover_statement'],
            card_summary_path=self.detected_files['card_summary'],
            output_dir=output_dir,
            enable_discover_backward_matching=self.config['discover_backward_enabled'],
            discover_backward_days=self.config['discover_backward_days'],
            discover_forward_days=self.config['discover_forward_days'],
            verbose=self.verbose
        )
        
        # Then run enhanced deposit matching on main bank
        from enhanced_deposit_matching import process_deposit_slip_enhanced
        
        deposit_results = process_deposit_slip_enhanced(
            deposit_slip_path=self.detected_files['deposit_slip'],
            bank_statement_path=self.detected_files['bank_statements'][0],
            output_dir=output_dir,
            verbose=self.verbose
        )
        
        self._create_enhanced_summary(card_results, deposit_results, output_dir)
        
        return {'cards': card_results, 'deposits': deposit_results}
    
    def _run_full_single_bank_with_deposits_enhanced(self, output_dir: str):
        """
        Run complete reconciliation with single bank and enhanced deposits.
        """
        print("\n🏦 Processing Single Bank with Enhanced Deposits...")
        
        # Run standard card matching
        from main_with_deposits import run_card_matching
        
        card_results = run_card_matching(
            card_summary_path=self.detected_files['card_summary'],
            bank_statement_path=self.detected_files['bank_statements'][0],
            output_dir=output_dir,
            verbose=self.verbose
        )
        
        # Run enhanced deposit matching
        from enhanced_deposit_matching import process_deposit_slip_enhanced
        
        deposit_results = process_deposit_slip_enhanced(
            deposit_slip_path=self.detected_files['deposit_slip'],
            bank_statement_path=self.detected_files['bank_statements'][0],
            output_dir=output_dir,
            verbose=self.verbose
        )
        
        self._create_enhanced_summary(card_results, deposit_results, output_dir)
        
        return {'cards': card_results, 'deposits': deposit_results}
    
    def _run_multi_bank_cards_enhanced(self, output_dir: str):
        """
        Run enhanced multi-bank card reconciliation only.
        """
        from enhanced_multi_bank import process_with_enhanced_multi_bank
        
        return process_with_enhanced_multi_bank(
            main_bank_statement_path=self.detected_files['bank_statements'][0],
            discover_bank_statement_path=self.detected_files['discover_statement'],
            card_summary_path=self.detected_files['card_summary'],
            output_dir=output_dir,
            enable_discover_backward_matching=self.config['discover_backward_enabled'],
            discover_backward_days=self.config['discover_backward_days'],
            discover_forward_days=self.config['discover_forward_days'],
            verbose=self.verbose
        )
    
    def _run_single_bank_cards(self, output_dir: str):
        """
        Run single bank card reconciliation only.
        """
        print("\n💳 Processing Single Bank Card Reconciliation...")
        
        from main_with_deposits import run_card_matching
        
        return run_card_matching(
            card_summary_path=self.detected_files['card_summary'],
            bank_statement_path=self.detected_files['bank_statements'][0],
            output_dir=output_dir,
            verbose=self.verbose
        )
    
    def _run_deposits_only_enhanced(self, output_dir: str):
        """
        Run enhanced deposit reconciliation only.
        """
        print("\n💰 Processing Enhanced Deposit Reconciliation...")
        
        from enhanced_deposit_matching import process_deposit_slip_enhanced
        
        return process_deposit_slip_enhanced(
            deposit_slip_path=self.detected_files['deposit_slip'],
            bank_statement_path=self.detected_files['bank_statements'][0],
            output_dir=output_dir,
            verbose=self.verbose
        )
    
    def _create_enhanced_summary(self, card_results, deposit_results, output_dir: str):
        """
        Create an enhanced combined summary report.
        """
        summary_path = os.path.join(output_dir, 'MASTER_RECONCILIATION_ENHANCED_SUMMARY.txt')
        
        with open(summary_path, 'w') as f:
            f.write("="*70 + "\n")
            f.write("ENHANCED MASTER RECONCILIATION SUMMARY\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*70 + "\n\n")
            
            f.write("SPECIAL FEATURES ENABLED:\n")
            if self.config['discover_backward_enabled']:
                f.write(f"  ✓ Discover backward date matching ({self.config['discover_backward_days']} days)\n")
            if self.config['enable_flexible_deposit_matching']:
                f.write("  ✓ Flexible deposit matching (single GC 1416 splitting)\n")
                f.write("  ✓ Multi-transaction aggregation for deposits\n")
            
            f.write("\nFILES PROCESSED:\n")
            for file_type, file_path in self.detected_files.items():
                if file_path:
                    if isinstance(file_path, list):
                        for fp in file_path:
                            f.write(f"  - {file_type}: {fp}\n")
                    else:
                        f.write(f"  - {file_type}: {file_path}\n")
            
            f.write("\n" + "-"*70 + "\n")
            f.write("PROCESSING MODE: " + self.processing_mode.replace('_', ' ').title() + "\n")
            f.write("-"*70 + "\n\n")
            
            f.write("RESULTS SUMMARY:\n")
            f.write("  ✓ Credit Card Reconciliation: Complete\n")
            if deposit_results:
                f.write("  ✓ Deposit Reconciliation: Complete (Enhanced)\n")
            
            f.write("\nGENERATED OUTPUT FILES:\n")
            f.write("  - All highlighted Excel files with enhanced matching\n")
            f.write("  - Check color coding for special match types\n")
            
        print(f"\n✅ Enhanced master summary created: {summary_path}")

def main():
    """
    Main entry point with command line interface.
    """
    parser = argparse.ArgumentParser(
        description='Ultra Master Reconciliation System - ENHANCED VERSION',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ENHANCED FEATURES:
  • Single GC 1416 transactions can match both Cash and Check
  • Multiple transactions can aggregate into Cash or Check  
  • Discover transactions can match earlier dates (configurable)

Examples:
  # Auto-detect and run with all enhancements
  python ultra_master_enhanced.py
  
  # Disable Discover backward matching
  python ultra_master_enhanced.py --no-discover-backward
  
  # Specify files manually
  python ultra_master_enhanced.py --bank "bank.CSV" --cards "cards.xlsx" --deposits "deposits.xlsx"
  
  # Verbose output for debugging
  python ultra_master_enhanced.py --verbose
        """
    )
    
    parser.add_argument('--auto', action='store_true', default=True,
                       help='Auto-detect files and run (default)')
    parser.add_argument('--bank', help='Main bank statement CSV path')
    parser.add_argument('--discover', help='Discover bank statement CSV path')
    parser.add_argument('--cards', help='Card summary Excel path')
    parser.add_argument('--deposits', help='Deposit slip Excel path')
    parser.add_argument('--output', default='.', help='Output directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--mode', help='Force specific processing mode')
    
    # Enhanced feature toggles
    parser.add_argument('--no-discover-backward', action='store_true',
                       help='Disable Discover backward date matching')
    parser.add_argument('--discover-backward-days', type=int, default=3,
                       help='Days to look backward for Discover (default: 3)')
    parser.add_argument('--discover-forward-days', type=int, default=3,
                       help='Days to look forward for Discover (default: 3)')
    
    args = parser.parse_args()
    
    print("\n" + "🚀"*30)
    print("ULTRA MASTER RECONCILIATION SYSTEM - ENHANCED")
    print("Handling All Edge Cases")
    print("🚀"*30 + "\n")
    
    # Create enhanced reconciliation instance
    reconciler = UltraMasterReconciliationEnhanced(
        auto_detect=True, 
        verbose=args.verbose,
        enable_discover_backward=not args.no_discover_backward
    )
    
    # Configure Discover settings
    if args.discover_backward_days:
        reconciler.config['discover_backward_days'] = args.discover_backward_days
    if args.discover_forward_days:
        reconciler.config['discover_forward_days'] = args.discover_forward_days
    
    # Manual file specification overrides auto-detection
    if args.bank or args.cards or args.deposits or args.discover:
        print("📁 Using manually specified files...")
        reconciler.detected_files = {
            'bank_statements': [args.bank] if args.bank else [],
            'discover_statement': args.discover,
            'card_summary': args.cards,
            'deposit_slip': args.deposits
        }
    else:
        # Auto-detect files
        reconciler.detect_files(args.output)
    
    # Show detection summary
    mode = reconciler.print_detection_summary()
    
    if mode == 'insufficient_files' and not args.mode:
        print("\n❌ Cannot proceed without required files.")
        print("Please ensure you have:")
        print("  1. At least one bank statement CSV")
        print("  2. Either a card summary or deposit slip Excel file")
        return
    
    # Confirm before proceeding
    print("\n" + "="*60)
    response = input("📋 Ready to proceed with ENHANCED matching? (Y/n): ").strip().lower()
    if response and response != 'y':
        print("Reconciliation cancelled.")
        return
    
    # Run reconciliation
    results = reconciler.run_reconciliation(args.output, args.mode)
    
    if results:
        print("\n" + "🎉"*30)
        print("ENHANCED RECONCILIATION COMPLETE!")
        print("🎉"*30)
        print("\n📂 Check the output directory for all generated files:")
        print(f"   {os.path.abspath(args.output)}")
        print("\nSpecial match types are highlighted with comments in Excel files.")
    else:
        print("\n❌ Reconciliation failed. Please check the files and try again.")

if __name__ == "__main__":
    # Check if running without arguments for "one button" mode
    if len(sys.argv) == 1:
        print("\n🎯 ONE-BUTTON ENHANCED MODE ACTIVATED!")
        print("Auto-detecting all files and running with all enhancements...\n")
        
        # Create instance with all enhancements enabled
        reconciler = UltraMasterReconciliationEnhanced(
            auto_detect=True, 
            verbose=False,
            enable_discover_backward=True  # Enable by default
        )
        
        reconciler.detect_files('.')
        mode = reconciler.print_detection_summary()
        
        if mode != 'insufficient_files':
            print("\n" + "="*60)
            print("🚀 Starting ENHANCED automatic reconciliation in 3 seconds...")
            print("   (Press Ctrl+C to cancel)")
            print("="*60)
            
            import time
            time.sleep(3)
            
            results = reconciler.run_reconciliation('.')
            
            if results:
                print("\n" + "✅"*30)
                print("ALL ENHANCED RECONCILIATION COMPLETE!")
                print("✅"*30)
                print("\n📊 Summary:")
                print("  - All matched transactions are highlighted in GREEN")
                print("  - Unmatched items are highlighted in RED")
                print("  - Special match types have detailed comments")
                print("  - Check the generated Excel files for details")
        else:
            print("\n⚠️  Please add the required files to the directory and try again.")
    else:
        # Run with command line arguments
        main()