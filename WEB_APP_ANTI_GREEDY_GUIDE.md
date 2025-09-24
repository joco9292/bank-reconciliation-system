# Web App Anti-Greedy Matching Configuration Guide

## 🎉 New Features Added

The web app now includes **configurable anti-greedy matching** to prevent one cell from consuming all available transactions. This solves the problem where early cells would "eat up" all the good matches, leaving later cells with nothing to match against.

## 🛡️ How to Use Anti-Greedy Matching

### 1. **Access the Configuration**
1. Open the web app: `streamlit run app.py`
2. Look for the **"Advanced Settings"** section in the sidebar
3. Scroll down to find the **"🛡️ Anti-Greedy Matching"** section

### 2. **Enable Anti-Greedy Matching**
- ✅ **Check "Enable Anti-Greedy Matching"** (enabled by default)
- This prevents greedy allocation and ensures fair distribution

### 3. **Configure Settings**

#### **Max Transactions per Cell**
- **Range**: 1-20 transactions
- **Default**: 3 transactions
- **Purpose**: Limits how many transactions one cell can consume
- **Recommendation**: Start with 3, adjust based on your data

#### **Enable Fair Allocation**
- **Default**: Enabled
- **Purpose**: Distributes transactions fairly across all cells
- **Effect**: Ensures better overall matching results

#### **Fairness Threshold**
- **Range**: 10-50%
- **Default**: 20%
- **Purpose**: Minimum percentage of transactions to reserve for other cells
- **Effect**: Prevents one cell from taking too many transactions

### 4. **Visual Feedback**

The sidebar shows your current configuration:
- 🛡️ **Anti-greedy matching enabled** - Shows your settings
- ⚠️ **Warning** - If enabled but no limit set
- ℹ️ **Info** - If using standard matching

During processing, you'll see:
- **🛡️ Anti-greedy matching credit card transactions (max X per cell)...**

## 📊 Configuration Examples

### **Conservative (Recommended for Most Cases)**
```
✅ Enable Anti-Greedy Matching
Max Transactions per Cell: 3
✅ Enable Fair Allocation
Fairness Threshold: 20%
```

### **Aggressive (For Large Datasets)**
```
✅ Enable Anti-Greedy Matching
Max Transactions per Cell: 5
✅ Enable Fair Allocation
Fairness Threshold: 15%
```

### **Very Restrictive (For Problematic Data)**
```
✅ Enable Anti-Greedy Matching
Max Transactions per Cell: 2
✅ Enable Fair Allocation
Fairness Threshold: 30%
```

### **Standard Matching (Original Behavior)**
```
❌ Enable Anti-Greedy Matching
```

## 🎯 Expected Results

### **Before (Greedy Matching)**
```
Cell 1 (2025-01-01 Amex): Matched 8 transactions ($1,200) ✅
Cell 2 (2025-01-01 Visa): No transactions left to match ❌
Cell 3 (2025-01-02 Mastercard): No transactions left to match ❌
```

### **After (Anti-Greedy Matching)**
```
Cell 1 (2025-01-01 Amex): Matched 3 transactions ($1,200) ✅
Cell 2 (2025-01-01 Visa): Matched 3 transactions ($800) ✅
Cell 3 (2025-01-02 Mastercard): Matched 2 transactions ($600) ✅
```

## ⚙️ Troubleshooting

### **Too Few Matches**
- **Increase** "Max Transactions per Cell" (try 4-5)
- **Decrease** "Fairness Threshold" (try 15%)

### **Too Many Unmatched Cells**
- **Decrease** "Max Transactions per Cell" (try 2)
- **Increase** "Fairness Threshold" (try 30%)

### **Performance Issues**
- **Disable** "Enable Fair Allocation"
- **Use smaller** "Max Transactions per Cell" values

### **Still Getting Greedy Behavior**
- **Enable** anti-greedy matching
- **Set** "Max Transactions per Cell" to 2-3
- **Enable** "Enable Fair Allocation"

## 🔧 Technical Details

### **How It Works**
1. **Analyzes** all cells that need matching
2. **Calculates** fair allocation per cell
3. **Limits** transactions each cell can consume
4. **Distributes** remaining transactions fairly

### **Integration**
- **Seamless** integration with existing workflow
- **Backward compatible** - can be disabled
- **No changes** to file formats or outputs
- **Same reports** and Excel exports

### **Performance**
- **Minimal overhead** - only affects matching logic
- **Configurable** - can be tuned for your data size
- **Efficient** - uses same underlying algorithms

## 📈 Benefits

1. **Better Distribution**: All cells get a fair chance to match
2. **More Successful Matches**: Overall better matching results
3. **Configurable**: Adjust settings based on your data
4. **Easy to Use**: Simple checkboxes and sliders
5. **Visual Feedback**: See your configuration at a glance
6. **No Breaking Changes**: Can be enabled/disabled anytime

## 🚀 Getting Started

1. **Run the web app**: `streamlit run app.py`
2. **Go to Advanced Settings** in the sidebar
3. **Enable Anti-Greedy Matching** (already enabled by default)
4. **Adjust settings** based on your data
5. **Process your files** as usual
6. **Compare results** with and without anti-greedy matching

The anti-greedy matching is now fully integrated into your web app and ready to use! 🎉
