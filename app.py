"""
Bank Reconciliation Streamlit Application
Properly structured to work with your existing modules
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
            
    def render_header(self):
        """Render the application header"""
        st.title("🏦 Bank Reconciliation System")
        st.markdown("---")
        
        # Show instructions
        with st.expander("📖 How to Use", expanded=False):
            st.markdown("""
            1. **Select Processing Mode** in the sidebar (Cards, Deposits, or Both)
            2. **Upload Required Files**:
               - Bank Statement (CSV) - Always required
               - Card Summary (Excel) - Required for Cards or Both modes
               - Deposit Slip (Excel) - Required for Deposits or Both modes
            3. **Click Process** to run the reconciliation
            4. **Download Results** after processing completes
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
                
            # Processing statistics
            if st.session_state.processing_complete:
                st.markdown("---")
                st.success("✅ Processing Complete!")
                if st.session_state.generated_files:
                    st.metric("Files Generated", len(st.session_state.generated_files))
                    
            return forward_days, verbose
    
    def render_file_upload(self):
        """Render the file upload interface"""
        st.header("📁 File Upload")
        
        # Determine which files are required based on mode
        mode = st.session_state.processing_mode
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Bank Statement *")
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
                except Exception as e:
                    st.error(f"Error reading file: {e}")
                
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
        return bank_file, card_file, deposit_file
    
    def save_uploaded_files(self, bank_file, card_file, deposit_file):
        """Save uploaded files to temporary directory"""
        file_paths = {}
        
        try:
            if bank_file:
                bank_path = os.path.join(st.session_state.temp_dir, bank_file.name)
                with open(bank_path, 'wb') as f:
                    f.write(bank_file.getbuffer())
                file_paths['bank'] = bank_path
                
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
    
    def process_files(self, file_paths, forward_days, verbose):
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
                    status_text.text("Matching credit card transactions...")
                    
                    results, discrepancies, first_matched_date = run_card_matching(
                        card_summary_path=file_paths['card'],
                        bank_statement_path=file_paths['bank'],
                        output_dir=st.session_state.temp_dir,
                        verbose=verbose
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
                        verbose=verbose
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
                        verbose=verbose
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
            # Create columns for download buttons
            num_files = len(st.session_state.generated_files)
            num_cols = min(3, num_files)
            
            if num_files > 0:
                cols = st.columns(num_cols)
                for idx, (filename, filepath) in enumerate(st.session_state.generated_files.items()):
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
                            
                            st.download_button(
                                label=f"📄 {filename}",
                                data=file_data,
                                file_name=filename,
                                mime=mime,
                                key=f"download_{filename}"
                            )
                        except Exception as e:
                            st.error(f"Error reading {filename}: {str(e)}")
        else:
            st.warning("No files were generated. Please check the processing logs.")
    
    def run(self):
        """Main application flow"""
        self.render_header()
        
        # Sidebar configuration
        forward_days, verbose = self.render_sidebar()
        
        # File upload section
        bank_file, card_file, deposit_file = self.render_file_upload()
        
        # Validate file requirements based on mode
        mode = st.session_state.processing_mode
        can_process = False
        missing_files = []
        
        if mode == 'cards':
            if bank_file and card_file:
                can_process = True
            else:
                if not bank_file:
                    missing_files.append("Bank Statement")
                if not card_file:
                    missing_files.append("Card Summary")
                    
        elif mode == 'deposits':
            if bank_file and deposit_file:
                can_process = True
            else:
                if not bank_file:
                    missing_files.append("Bank Statement")
                if not deposit_file:
                    missing_files.append("Deposit Slip")
                    
        else:  # both
            if bank_file and card_file and deposit_file:
                can_process = True
            else:
                if not bank_file:
                    missing_files.append("Bank Statement")
                if not card_file:
                    missing_files.append("Card Summary")
                if not deposit_file:
                    missing_files.append("Deposit Slip")
        
        # Show missing files warning
        if missing_files and (bank_file or card_file or deposit_file):
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
                help="Process the uploaded files" if can_process else f"Please upload: {', '.join(missing_files)}"
            ):
                # Reset previous results
                st.session_state.processing_complete = False
                st.session_state.results = None
                st.session_state.generated_files = {}
                st.session_state.console_output = ""
                
                # Save files and process
                with st.spinner("Saving uploaded files..."):
                    file_paths = self.save_uploaded_files(bank_file, card_file, deposit_file)
                
                if file_paths:
                    success = self.process_files(file_paths, forward_days, verbose)
                    
                    if success:
                        st.success("✅ Processing completed successfully!")
                        st.balloons()
                else:
                    st.error("Failed to save uploaded files")
        
        # Display results
        if st.session_state.processing_complete:
            self.render_results()
        
        # Footer
        st.markdown("---")
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col2:
                st.caption("Bank Reconciliation System v1.0")

# Run the app
if __name__ == "__main__":
    app = BankReconciliationApp()
    app.run()