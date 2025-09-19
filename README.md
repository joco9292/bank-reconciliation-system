# 🏦 Bank Reconciliation System

A comprehensive Streamlit-based application for automated bank reconciliation, supporting credit card transactions, deposit matching, and combined analysis with advanced Excel reporting and highlighting features.

## ✨ Features

### 🔄 Multi-Mode Processing
- **Credit Cards Only**: Match credit card transactions with bank statements
- **Deposits Only**: Match deposit slip transactions with bank statements  
- **Combined Analysis**: Full reconciliation with both cards and deposits

### 📊 Advanced Data Input
- **File Upload**: Support for CSV bank statements and Excel files
- **Text Input**: Paste CSV data directly for quick processing
- **Smart Validation**: Automatic data validation and preview

### 🎯 Intelligent Matching
- **Fuzzy Matching**: Advanced algorithms for transaction matching
- **Date Range Flexibility**: Configurable forward/backward matching windows
- **Amount Tolerance**: Smart handling of rounding differences
- **Multiple Card Types**: Support for Visa, Mastercard, and other card types

### 📈 Rich Reporting
- **Excel Export**: Comprehensive reports with highlighting
- **Discrepancy Analysis**: Detailed variance reporting
- **Visual Indicators**: Color-coded matching status
- **Multiple Output Formats**: CSV and Excel support

### 🎨 User Experience
- **Modern UI**: Clean, intuitive Streamlit interface
- **Real-time Processing**: Live progress updates
- **Error Handling**: Comprehensive error reporting and recovery
- **Responsive Design**: Works on desktop and mobile

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/bank-reconciliation-system.git
   cd bank-reconciliation-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run app.py
   ```

4. **Open your browser**
   Navigate to `http://localhost:8501`

## 📁 Project Structure

```
bank-reconciliation-system/
├── app.py                          # Main Streamlit application
├── main_with_deposits.py           # Core processing logic
├── requirements.txt                # Python dependencies
├── processors/                     # Data preprocessing modules
│   ├── preprocess_bank_statement.py
│   ├── preprocess_card_summary.py
│   └── preprocess_deposit_slip.py
├── matchers/                       # Transaction matching algorithms
│   ├── deposit_matching.py
│   ├── enhanced_deposit_matching.py
│   └── matching_helpers.py
├── debug/                          # Debugging utilities
│   ├── debug_check_issues.py
│   ├── debug_mastercard_differences.py
│   └── debug_matching_issues.py
├── data/                          # Sample data (excluded from repo)
└── README.md                      # This file
```

## 🔧 Configuration

### Processing Modes
- **Combined Analysis**: Full reconciliation with both cards and deposits
- **Credit Cards Only**: Focus on credit card transaction matching
- **Deposits Only**: Focus on deposit slip matching

### Advanced Settings
- **Forward Days**: Number of days to look forward when matching (default: 3)
- **Verbose Output**: Enable detailed matching information
- **Amount Tolerance**: Configure matching precision

## 📊 Data Format Requirements

### Bank Statement (CSV)
Required columns:
- `Date`: Transaction date
- `Description`: Transaction description
- `Debit Amount`: Debit amount (if applicable)
- `Credit Amount`: Credit amount (if applicable)

### Card Summary (Excel)
- Transaction details with amounts and dates
- Card type information
- Reference numbers

### Deposit Slip (Excel)
- Deposit amounts and dates
- Reference information
- Deposit type classification

## 🎯 Usage Guide

1. **Select Processing Mode** in the sidebar
2. **Upload Required Files**:
   - Bank Statement (CSV file or paste text)
   - Card Summary (Excel) - for card/combined modes
   - Deposit Slip (Excel) - for deposit/combined modes
3. **Configure Settings** (optional)
4. **Click "Start Processing"**
5. **Download Results** from the generated reports

## 🔍 Features in Detail

### Smart Matching Algorithm
- **Fuzzy String Matching**: Handles variations in transaction descriptions
- **Date Proximity**: Matches transactions within configurable date ranges
- **Amount Validation**: Ensures amounts match within tolerance
- **Multi-pass Processing**: Multiple matching attempts with different strategies

### Excel Reporting
- **Highlighted Matches**: Color-coded transaction status
- **Summary Sheets**: Overview of matching results
- **Detailed Analysis**: Transaction-by-transaction breakdown
- **Discrepancy Reports**: Variance analysis and recommendations

### Error Handling
- **Input Validation**: Comprehensive data validation
- **Error Recovery**: Graceful handling of processing errors
- **Detailed Logging**: Complete processing logs for debugging
- **User Feedback**: Clear error messages and suggestions

## 🛠️ Development

### Setting up Development Environment

1. **Clone and setup**
   ```bash
   git clone https://github.com/yourusername/bank-reconciliation-system.git
   cd bank-reconciliation-system
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run in development mode**
   ```bash
   streamlit run app.py --server.runOnSave true
   ```

### Testing
- Use the sample data in the `data/` directory for testing
- Check the `debug/` directory for debugging utilities
- Enable verbose mode for detailed processing information

## 📝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🐛 Troubleshooting

### Common Issues

**Import Errors**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version compatibility (3.8+)

**File Upload Issues**
- Verify file formats (CSV for bank statements, Excel for others)
- Check file size limits
- Ensure proper column headers

**Matching Issues**
- Enable verbose mode for detailed matching information
- Check date formats in input files
- Verify amount formats (no currency symbols)

**Performance Issues**
- For large datasets, consider processing in smaller batches
- Enable verbose mode only when needed
- Check available system memory

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for the web interface
- Uses [pandas](https://pandas.pydata.org/) for data processing
- Excel handling powered by [openpyxl](https://openpyxl.readthedocs.io/)
- Fuzzy matching with [fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy)

## 📞 Support

For support, please open an issue on GitHub or contact the development team.

---

**Version**: 1.1  
**Last Updated**: January 2025
