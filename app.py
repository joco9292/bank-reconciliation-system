"""
Bank Reconciliation Streamlit Application
Enhanced with CSV text input support
"""

import streamlit as st
import pandas as pd
import sys
import os
import tempfile
import traceback
from pathlib import Path
from io import StringIO
import contextlib

# Add your existing modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'processors'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'matchers'))

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="Bank Reconciliation System",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import your existing functions AFTER setting up paths
from main_with_deposits import (
    run_card_matching,
    run_deposit_matching,
    run_combined_analysis
)

# Import anti-greedy matching solution
try:
    from matchers.anti_greedy_matching import create_anti_greedy_matcher
    ANTI_GREEDY_AVAILABLE = True
except ImportError:
    ANTI_GREEDY_AVAILABLE = False
    print("Note: Anti-greedy matching not available")

class BankReconciliationApp:
    def __init__(self):
        self.init_session_state()
        
    def init_session_state(self):
        """Initialize session state variables"""
        if 'processing_complete' not in st.session_state:
            st.session_state.processing_complete = False
        if 'results' not in st.session_state:
            st.session_state.results = None
        if 'generated_files' not in st.session_state:
            st.session_state.generated_files = {}
        if 'processing_mode' not in st.session_state:
            st.session_state.processing_mode = 'both'
        if 'temp_dir' not in st.session_state:
            # Create a persistent temp directory for this session
            st.session_state.temp_dir = tempfile.mkdtemp(prefix="bank_recon_")
        if 'console_output' not in st.session_state:
            st.session_state.console_output = ""
        if 'bank_input_method' not in st.session_state:
            st.session_state.bank_input_method = 'file'
            
    def render_header(self):
        """Render the application header"""
        st.title("🏦 Bank Reconciliation System")
        st.markdown("---")
        
        # Show instructions
        with st.expander("📖 How to Use", expanded=False):
            st.markdown("""
            1. **Select Processing Mode** in the sidebar (Cards, Deposits, or Both)
            2. **Provide Required Data**:
               - **Bank Statement**: Choose between file upload or paste CSV text
               - **Card Summary** (Excel) - Required for Cards or Both modes
               - **Deposit Slip** (Excel) - Required for Deposits or Both modes
            3. **Click Process** to run the reconciliation
            4. **Download Results** after processing completes
            
            **Bank Statement Input Options:**
            - **File Upload**: Upload a CSV file directly
            - **Text Input**: Copy and paste CSV text from your bank statement
            """)
            
    def render_sidebar(self):
        """Render the sidebar with configuration options"""
        with st.sidebar:
            st.header("⚙️ Configuration")
            
            # Processing mode selection
            st.session_state.processing_mode = st.selectbox(
                "Processing Mode",
                options=['both', 'cards', 'deposits'],
                format_func=lambda x: {
                    'both': '🔄 Combined Analysis',
                    'cards': '💳 Credit Cards Only',
                    'deposits': '💵 Deposits Only'
                }[x],
                help="Choose what type of reconciliation to perform"
            )
            
            # Advanced settings
            with st.expander("Advanced Settings"):
                forward_days = st.number_input(
                    "Forward Days for Matching",
                    min_value=1,
                    max_value=30,
                    value=3,
                    help="Number of days to look forward when matching transactions"
                )
                
                verbose = st.checkbox(
                    "Verbose Output",
                    value=False,
                    help="Show detailed matching information"
                )
                
                # Anti-Greedy Matching Settings
                st.markdown("**🛡️ Anti-Greedy Matching**")
                st.markdown("*Prevent one cell from consuming all available transactions*")
                
                enable_anti_greedy = st.checkbox(
                    "Enable Anti-Greedy Matching",
                    value=True,
                    help="Prevents one cell from 'eating up' all transactions, ensuring fair distribution"
                )
                
                if enable_anti_greedy:
                    max_transactions_per_cell = st.number_input(
                        "Max Transactions per Cell",
                        min_value=1,
                        max_value=20,
                        value=3,
                        help="Maximum number of transactions one cell can consume (prevents greedy matching)"
                    )
                    
                    enable_fair_allocation = st.checkbox(
                        "Enable Fair Allocation",
                        value=True,
                        help="Distribute transactions fairly across all cells"
                    )
                    
                    if enable_fair_allocation:
                        fairness_threshold = st.slider(
                            "Fairness Threshold (%)",
                            min_value=10,
                            max_value=50,
                            value=20,
                            help="Minimum percentage of transactions to reserve for other cells"
                        ) / 100.0
                    else:
                        fairness_threshold = 0.2
                else:
                    max_transactions_per_cell = None
                    enable_fair_allocation = False
                    fairness_threshold = 0.2
                
                # Cleanup Pass Settings
                st.markdown("**🧹 Cleanup Pass**")
                st.markdown("*Match leftover transactions to cells that could benefit*")
                
                enable_cleanup_pass = st.checkbox(
                    "Enable Cleanup Pass",
                    value=True,
                    help="Attempt to match leftover transactions to unmatched cells (extends forward days by 1-2 days)"
                )
                
                if enable_cleanup_pass:
                    cleanup_extra_days = st.slider(
                        "Extra Days for Cleanup",
                        min_value=1,
                        max_value=3,
                        value=2,
                        help="Additional days to look forward when attempting cleanup matches"
                    )
                else:
                    cleanup_extra_days = 0
                
                # Show current anti-greedy configuration
                if enable_anti_greedy and max_transactions_per_cell is not None:
                    st.info(f"🛡️ **Anti-greedy matching enabled**\n"
                           f"- Max transactions per cell: {max_transactions_per_cell}\n"
                           f"- Fair allocation: {'Yes' if enable_fair_allocation else 'No'}\n"
                           f"- Fairness threshold: {int(fairness_threshold * 100)}%")
                elif enable_anti_greedy:
                    st.warning("⚠️ Anti-greedy matching enabled but no limit set")
                else:
                    st.info("ℹ️ Using standard matching (no anti-greedy protection)")
                
                # Show Amex extra day information
                st.info(f"💳 **Card Type Settings**\n"
                       f"- Forward days: {forward_days} days\n"
                       f"- Amex gets extra day: {forward_days + 1} days total")
                
                # Show cleanup pass information
                if enable_cleanup_pass:
                    st.info(f"🧹 **Cleanup Pass Enabled**\n"
                           f"- Extra days for cleanup: {cleanup_extra_days}\n"
                           f"- Total cleanup window: {forward_days + cleanup_extra_days} days")
                else:
                    st.info("🧹 **Cleanup Pass Disabled**")
                
            # Processing statistics
            if st.session_state.processing_complete:
                st.markdown("---")
                st.success("✅ Processing Complete!")
                if st.session_state.generated_files:
                    st.metric("Files Generated", len(st.session_state.generated_files))
                    
            return forward_days, verbose, enable_anti_greedy, max_transactions_per_cell, enable_fair_allocation, fairness_threshold, enable_cleanup_pass, cleanup_extra_days
    
    def validate_csv_text(self, csv_text):
        """Validate CSV text input"""
        try:
            # Try to parse the CSV text
            df = pd.read_csv(StringIO(csv_text))
            
            # Check if it has required columns (adjust based on your requirements)
            required_cols = ['Date', 'Description']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                return False, f"Missing required columns: {', '.join(missing_cols)}", None
            
            # Check if there's actual data
            if len(df) == 0:
                return False, "CSV contains no data rows", None
                
            return True, "Valid CSV format", df
            
        except Exception as e:
            return False, f"Invalid CSV format: {str(e)}", None
    
    def render_file_upload(self):
        """Render the file upload interface with text input option"""
        st.header("📁 Data Input")
        
        # Determine which files are required based on mode
        mode = st.session_state.processing_mode
        
        # Bank Statement Section with tabs for input method
        st.subheader("Bank Statement *")
        
        # Input method selection
        bank_input_tabs = st.tabs(["📄 File Upload", "📝 Text Input"])
        
        bank_file = None
        bank_csv_text = None
        bank_df = None
        
        with bank_input_tabs[0]:
            bank_file = st.file_uploader(
                "Upload Bank Statement CSV",
                type=['csv'],
                key='bank_upload',
                help="Upload your bank statement in CSV format"
            )
            if bank_file:
                st.success(f"✅ {bank_file.name}")
                # Show preview
                try:
                    df = pd.read_csv(bank_file)
                    with st.expander("Preview (first 5 rows)"):
                        st.dataframe(df.head(), use_container_width=True)
                    bank_file.seek(0)  # Reset file pointer
                    st.session_state.bank_input_method = 'file'
                except Exception as e:
                    st.error(f"Error reading file: {e}")
        
        with bank_input_tabs[1]:
            st.markdown("**Paste your bank statement CSV text below:**")
            bank_csv_text = st.text_area(
                "CSV Text Input",
                height=300,
                placeholder="Account Number,Currency,Date,Description,Debit Amount,Credit Amount\n015760404641,CAD,2025/08/01,GC 1509-DEPOSIT,,766.14\n...",
                key='bank_csv_input',
                help="Copy and paste your bank statement data in CSV format"
            )
            
            if bank_csv_text and bank_csv_text.strip():
                # Validate CSV text
                is_valid, message, df = self.validate_csv_text(bank_csv_text)
                
                if is_valid:
                    st.success(f"✅ {message}")
                    bank_df = df
                    st.session_state.bank_input_method = 'text'
                    
                    # Show preview
                    with st.expander("Preview (first 5 rows)"):
                        st.dataframe(df.head(), use_container_width=True)
                    
                    # Show data statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Rows", len(df))
                    with col2:
                        st.metric("Columns", len(df.columns))
                    with col3:
                        if 'Date' in df.columns:
                            try:
                                dates = pd.to_datetime(df['Date'], errors='coerce')
                                date_range = f"{dates.min().strftime('%Y-%m-%d')} to {dates.max().strftime('%Y-%m-%d')}"
                                st.metric("Date Range", date_range)
                            except:
                                pass
                else:
                    st.error(f"❌ {message}")
        
        st.markdown("---")
        
        # Other file uploads (Card Summary and Deposit Slip)
        col2, col3 = st.columns(2)
        
        with col2:
            required_for_cards = mode in ['cards', 'both']
            st.subheader(f"Card Summary {'*' if required_for_cards else ''}")
            card_file = st.file_uploader(
                "Upload Card Summary Excel",
                type=['xlsx', 'xls'],
                key='card_upload',
                help="Upload your credit card summary Excel file",
                disabled=mode == 'deposits'
            )
            if card_file and mode != 'deposits':
                st.success(f"✅ {card_file.name}")
                # Show preview
                try:
                    df = pd.read_excel(card_file)
                    with st.expander("Preview (first 5 rows)"):
                        st.dataframe(df.head(), use_container_width=True)
                    card_file.seek(0)  # Reset file pointer
                except Exception as e:
                    st.error(f"Error reading file: {e}")
                
        with col3:
            required_for_deposits = mode in ['deposits', 'both']
            st.subheader(f"Deposit Slip {'*' if required_for_deposits else ''}")
            deposit_file = st.file_uploader(
                "Upload Deposit Slip Excel",
                type=['xlsx', 'xls'],
                key='deposit_upload',
                help="Upload your deposit slip Excel file",
                disabled=mode == 'cards'
            )
            if deposit_file and mode != 'cards':
                st.success(f"✅ {deposit_file.name}")
                # Show preview
                try:
                    df = pd.read_excel(deposit_file)
                    with st.expander("Preview (first 5 rows)"):
                        st.dataframe(df.head(), use_container_width=True)
                    deposit_file.seek(0)  # Reset file pointer
                except Exception as e:
                    st.error(f"Error reading file: {e}")
        
        st.caption("* Required for selected mode")
        return bank_file, bank_csv_text, bank_df, card_file, deposit_file
    
    def save_uploaded_files(self, bank_file, bank_csv_text, bank_df, card_file, deposit_file):
        """Save uploaded files and text input to temporary directory"""
        file_paths = {}
        
        try:
            # Handle bank statement - either file or text
            if bank_file:
                # Save uploaded file
                bank_path = os.path.join(st.session_state.temp_dir, bank_file.name)
                with open(bank_path, 'wb') as f:
                    f.write(bank_file.getbuffer())
                file_paths['bank'] = bank_path
                
            elif bank_csv_text and bank_df is not None:
                # Save text input as CSV file
                bank_path = os.path.join(st.session_state.temp_dir, "bank_statement_input.csv")
                bank_df.to_csv(bank_path, index=False)
                file_paths['bank'] = bank_path
                st.info(f"💾 Bank statement text saved as: bank_statement_input.csv")
                
            # Handle other files
            if card_file:
                card_path = os.path.join(st.session_state.temp_dir, card_file.name)
                with open(card_path, 'wb') as f:
                    f.write(card_file.getbuffer())
                file_paths['card'] = card_path
                
            if deposit_file:
                deposit_path = os.path.join(st.session_state.temp_dir, deposit_file.name)
                with open(deposit_path, 'wb') as f:
                    f.write(deposit_file.getbuffer())
                file_paths['deposit'] = deposit_path
                
            return file_paths
        except Exception as e:
            st.error(f"Error saving files: {str(e)}")
            return None
    
    def run_card_matching_with_config(self, card_summary_path, bank_statement_path, output_dir, verbose, forward_days, enable_anti_greedy, max_transactions_per_cell, enable_fair_allocation, fairness_threshold, enable_cleanup_pass, cleanup_extra_days):
        """Run card matching with anti-greedy configuration if enabled"""
        if enable_anti_greedy and ANTI_GREEDY_AVAILABLE and max_transactions_per_cell is not None:
            # Use anti-greedy matching
            from matchers.anti_greedy_matching import create_anti_greedy_matcher
            import pandas as pd
            from processors.preprocess_bank_statement import preprocess_bank_statement
            from processors.preprocess_card_summary import preprocess_card_summary_dynamic
            from highlighting_functions import create_highlighted_bank_statement, extract_matched_info_from_results
            from exclusive_discrepancy import calculate_total_discrepancies_by_card_type_exclusive
            
            print("=== Using Anti-Greedy Card Matching ===\n")
            
            # Load data
            bank_statement = preprocess_bank_statement(bank_statement_path)
            card_summary, structure_info = preprocess_card_summary_dynamic(card_summary_path)
            
            # Create anti-greedy matcher
            matcher = create_anti_greedy_matcher(
                max_transactions_per_cell=max_transactions_per_cell,
                enable_fair_allocation=enable_fair_allocation
            )
            
            # Run anti-greedy matching
            results = matcher.match_with_anti_greedy(
                card_summary, bank_statement, 
                forward_days=forward_days, verbose=verbose
            )
            
            # Extract info and generate reports (same as original)
            matched_bank_rows, matched_dates_and_types, differences_by_row, differences_by_date_type, unmatched_info = extract_matched_info_from_results(results)
            
            # Calculate discrepancies by card type
            discrepancies_by_type, first_matched_date = calculate_total_discrepancies_by_card_type_exclusive(
                results, bank_statement, matched_bank_rows
            )
            
            # Print discrepancy summary (optional)
            if verbose:
                print("\n=== CARD TYPE DISCREPANCIES ===")
                if first_matched_date:
                    print(f"(Calculated from {first_matched_date.strftime('%Y-%m-%d')} onwards)")
                for card_type, disc in sorted(discrepancies_by_type.items()):
                    if abs(disc) > 0.01:
                        if disc > 0:
                            print(f"{card_type}: +${disc:,.2f} (bank has more)")
                        else:
                            print(f"{card_type}: -${abs(disc):,.2f} (bank has less)")
            
            # Generate highlighted reports (same as original)
            create_highlighted_bank_statement(
                bank_statement, results, output_dir, 
                matched_bank_rows, differences_by_row
            )
            
            print(f"✓ Anti-greedy card matching complete. Files saved to {output_dir}/")
            
            return results, discrepancies_by_type, first_matched_date
        else:
            # Use regular matching
            return run_card_matching(
                card_summary_path=card_summary_path,
                bank_statement_path=bank_statement_path,
                output_dir=output_dir,
                verbose=verbose,
                forward_days=forward_days
            )

    def process_files(self, file_paths, forward_days, verbose, enable_anti_greedy, max_transactions_per_cell, enable_fair_allocation, fairness_threshold, enable_cleanup_pass, cleanup_extra_days):
        """Process the uploaded files"""
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
            console_output = st.empty()
            
            # Capture console output
            output_buffer = StringIO()
            
            with contextlib.redirect_stdout(output_buffer):
                if st.session_state.processing_mode == 'cards':
                    progress_bar.progress(10)
                    status_text.text("Loading files...")
                    
                    progress_bar.progress(50)
                    if enable_anti_greedy and max_transactions_per_cell is not None:
                        status_text.text(f"🛡️ Anti-greedy matching credit card transactions (max {max_transactions_per_cell} per cell, Amex gets {forward_days + 1} days)...")
                    else:
                        status_text.text(f"Matching credit card transactions (Amex gets {forward_days + 1} days)...")
                    
                    results, discrepancies, first_matched_date = self.run_card_matching_with_config(
                        card_summary_path=file_paths['card'],
                        bank_statement_path=file_paths['bank'],
                        output_dir=st.session_state.temp_dir,
                        verbose=verbose,
                        forward_days=forward_days,
                        enable_anti_greedy=enable_anti_greedy,
                        max_transactions_per_cell=max_transactions_per_cell,
                        enable_fair_allocation=enable_fair_allocation,
                        fairness_threshold=fairness_threshold,
                        enable_cleanup_pass=enable_cleanup_pass,
                        cleanup_extra_days=cleanup_extra_days
                    )
                    
                    st.session_state.results = {
                        'card_results': results,
                        'discrepancies': discrepancies,
                        'first_matched_date': first_matched_date,
                        'mode': 'cards'
                    }
                    
                elif st.session_state.processing_mode == 'deposits':
                    progress_bar.progress(10)
                    status_text.text("Loading files...")
                    
                    progress_bar.progress(50)
                    status_text.text("Matching deposit transactions...")
                    
                    results = run_deposit_matching(
                        deposit_slip_path=file_paths['deposit'],
                        bank_statement_path=file_paths['bank'],
                        output_dir=st.session_state.temp_dir,
                        verbose=verbose,
                        forward_days=forward_days
                    )
                    
                    st.session_state.results = {
                        'deposit_results': results,
                        'mode': 'deposits'
                    }
                    
                else:  # both
                    progress_bar.progress(10)
                    status_text.text("Loading bank statement...")
                    
                    progress_bar.progress(33)
                    status_text.text("Running combined analysis...")
                    
                    run_combined_analysis(
                        card_summary_path=file_paths['card'],
                        deposit_slip_path=file_paths['deposit'],
                        bank_statement_path=file_paths['bank'],
                        output_dir=st.session_state.temp_dir,
                        verbose=verbose,
                        forward_days=forward_days
                    )
                    
                    st.session_state.results = {
                        'mode': 'combined'
                    }
                
                progress_bar.progress(100)
                status_text.text("Processing complete!")
            
            # Store console output
            st.session_state.console_output = output_buffer.getvalue()
            
            # Store results in session state
            st.session_state.processing_complete = True
            
            # Find generated files
            self.find_generated_files()
            
            return True
                
        except Exception as e:
            st.error(f"❌ Error during processing: {str(e)}")
            with st.expander("Show detailed error"):
                st.text(traceback.format_exc())
            return False
    
    def find_generated_files(self):
        """Find all generated Excel files"""
        temp_dir = Path(st.session_state.temp_dir)
        generated_files = {}
        
        # Look for all Excel files in temp directory
        for file_path in temp_dir.glob("*.xlsx"):
            generated_files[file_path.name] = str(file_path)
        
        # Also look for any CSV files that might have been generated
        for file_path in temp_dir.glob("*.csv"):
            # Don't include the input bank statement file if it was from text
            if file_path.name != "bank_statement_input.csv":
                generated_files[file_path.name] = str(file_path)
                
        st.session_state.generated_files = generated_files
    
    def render_results(self):
        """Render the processing results"""
        if not st.session_state.processing_complete:
            return
            
        st.header("📊 Results")
        
        # Display console output
        if st.session_state.console_output:
            with st.expander("📝 Processing Log", expanded=True):
                st.text(st.session_state.console_output)
        
        # Display any specific results based on mode
        if st.session_state.results and 'discrepancies' in st.session_state.results:
            with st.expander("💰 Discrepancy Analysis"):
                discrepancies = st.session_state.results['discrepancies']
                if discrepancies:
                    for card_type, amount in discrepancies.items():
                        if abs(amount) > 0.01:
                            if amount > 0:
                                st.warning(f"{card_type}: +${amount:,.2f} (bank has more)")
                            else:
                                st.error(f"{card_type}: -${abs(amount):,.2f} (bank has less)")
        
        # Download section
        st.subheader("📥 Download Generated Files")
        
        if st.session_state.generated_files:
            # Define primary files to showcase
            primary_files = [
                'card_summary_highlighted.xlsx',
                'bank_statement_combined_highlighted.xlsx',
                'deposit_slip_highlighted.xlsx'
            ]
            
            # Separate files into primary and additional
            primary_downloads = {}
            additional_downloads = {}
            
            for filename, filepath in st.session_state.generated_files.items():
                if filename in primary_files:
                    primary_downloads[filename] = filepath
                else:
                    additional_downloads[filename] = filepath
            
            # Display primary files prominently
            if primary_downloads:
                st.markdown("**📌 Primary Reports**")
                cols = st.columns(3)
                
                # Ensure consistent ordering
                for idx, primary_file in enumerate(primary_files):
                    if primary_file in primary_downloads:
                        with cols[idx % 3]:
                            filepath = primary_downloads[primary_file]
                            try:
                                with open(filepath, 'rb') as f:
                                    file_data = f.read()
                                
                                # Create a more descriptive label
                                if 'card_summary' in primary_file:
                                    label = "💳 Card Summary Report"
                                elif 'bank_statement_combined' in primary_file:
                                    label = "🏦 Combined Bank Statement"
                                elif 'deposit_slip' in primary_file:
                                    label = "💵 Deposit Slip Report"
                                else:
                                    label = f"📄 {primary_file}"
                                
                                st.download_button(
                                    label=label,
                                    data=file_data,
                                    file_name=primary_file,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key=f"download_primary_{primary_file}",
                                    type="primary"  # Make primary files stand out
                                )
                            except Exception as e:
                                st.error(f"Error reading {primary_file}: {str(e)}")
            
            # Display additional files under expander
            if additional_downloads:
                st.markdown("---")
                with st.expander(f"📂 Additional Files ({len(additional_downloads)} files)", expanded=False):
                    # Calculate columns needed
                    num_files = len(additional_downloads)
                    num_cols = min(3, num_files)
                    
                    if num_files > 0:
                        cols = st.columns(num_cols)
                        for idx, (filename, filepath) in enumerate(additional_downloads.items()):
                            col_idx = idx % num_cols
                            with cols[col_idx]:
                                try:
                                    with open(filepath, 'rb') as f:
                                        file_data = f.read()
                                    
                                    # Determine MIME type
                                    if filename.endswith('.xlsx'):
                                        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    elif filename.endswith('.csv'):
                                        mime = "text/csv"
                                    else:
                                        mime = "application/octet-stream"
                                    
                                    # Shorten label if needed
                                    if len(filename) > 30:
                                        display_name = filename[:27] + "..."
                                    else:
                                        display_name = filename
                                    
                                    st.download_button(
                                        label=f"📄 {display_name}",
                                        data=file_data,
                                        file_name=filename,
                                        mime=mime,
                                        key=f"download_additional_{filename}"
                                    )
                                except Exception as e:
                                    st.error(f"Error reading {filename}: {str(e)}")
        else:
            st.warning("No files were generated. Please check the processing logs.")
    
    def run(self):
        """Main application flow"""
        self.render_header()
        
        # Sidebar configuration
        forward_days, verbose, enable_anti_greedy, max_transactions_per_cell, enable_fair_allocation, fairness_threshold, enable_cleanup_pass, cleanup_extra_days = self.render_sidebar()
        
        # File upload section with text input option
        bank_file, bank_csv_text, bank_df, card_file, deposit_file = self.render_file_upload()
        
        # Validate file requirements based on mode
        mode = st.session_state.processing_mode
        can_process = False
        missing_files = []
        
        # Check if we have bank statement (either file or text)
        has_bank = bank_file or (bank_csv_text and bank_df is not None)
        
        if mode == 'cards':
            if has_bank and card_file:
                can_process = True
            else:
                if not has_bank:
                    missing_files.append("Bank Statement")
                if not card_file:
                    missing_files.append("Card Summary")
                    
        elif mode == 'deposits':
            if has_bank and deposit_file:
                can_process = True
            else:
                if not has_bank:
                    missing_files.append("Bank Statement")
                if not deposit_file:
                    missing_files.append("Deposit Slip")
                    
        else:  # both
            if has_bank and card_file and deposit_file:
                can_process = True
            else:
                if not has_bank:
                    missing_files.append("Bank Statement")
                if not card_file:
                    missing_files.append("Card Summary")
                if not deposit_file:
                    missing_files.append("Deposit Slip")
        
        # Show missing files warning
        if missing_files and (has_bank or card_file or deposit_file):
            st.warning(f"⚠️ Missing required files: {', '.join(missing_files)}")
        
        # Process button
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "🚀 Start Processing",
                type="primary",
                use_container_width=True,
                disabled=not can_process,
                help="Process the uploaded files" if can_process else f"Please provide: {', '.join(missing_files)}"
            ):
                # Reset previous results
                st.session_state.processing_complete = False
                st.session_state.results = None
                st.session_state.generated_files = {}
                st.session_state.console_output = ""
                
                # Save files and process
                with st.spinner("Saving input data..."):
                    file_paths = self.save_uploaded_files(
                        bank_file, bank_csv_text, bank_df, card_file, deposit_file
                    )
                
                if file_paths:
                    success = self.process_files(file_paths, forward_days, verbose, enable_anti_greedy, max_transactions_per_cell, enable_fair_allocation, fairness_threshold, enable_cleanup_pass, cleanup_extra_days)
                    
                    if success:
                        st.success("✅ Processing completed successfully!")
                        st.balloons()
                else:
                    st.error("Failed to save input data")
        
        # Display results
        if st.session_state.processing_complete:
            self.render_results()
        
        # Footer
        st.markdown("---")
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col2:
                st.caption("Bank Reconciliation System v1.1")

# Run the app
if __name__ == "__main__":
    app = BankReconciliationApp()
    app.run()