# Amex Extra Day Feature Guide

## 🎯 Overview

The system now gives **Amex transactions an extra day of forward-looking allowance** when matching transactions. This means if the standard forward days setting is 3, Amex transactions will get 4 days to find matches.

## 💳 How It Works

### **Standard Behavior:**
- **Visa**: Gets 3 days forward (if forward_days = 3)
- **Mastercard**: Gets 3 days forward (if forward_days = 3)
- **Discover**: Gets 3 days forward (if forward_days = 3)

### **Amex Special Treatment:**
- **Amex**: Gets 4 days forward (if forward_days = 3)
- **Formula**: `Amex_forward_days = forward_days + 1`

## 🔧 Implementation Details

### **Files Modified:**
1. **`matchers/matching_helpers.py`** - Core matching logic
2. **`matchers/fair_matching.py`** - Fair matching system
3. **`app.py`** - Web app UI indicators

### **Key Function:**
```python
def filter_by_card_type_and_date(transactions, card_type, date, forward_days=3):
    # Give Amex an extra day of forward-looking allowance
    if card_type == 'Amex':
        effective_forward_days = forward_days + 1
    else:
        effective_forward_days = forward_days
    
    date_end = date + timedelta(days=effective_forward_days)
    # ... rest of filtering logic
```

## 📊 Examples

### **Example 1: Forward Days = 3**
```
Card Type    | Standard Days | Amex Gets | Date Range (from Jan 1)
-------------|---------------|-----------|------------------------
Visa         | 3 days        | 3 days    | Jan 1 to Jan 4
Mastercard   | 3 days        | 3 days    | Jan 1 to Jan 4
Discover     | 3 days        | 3 days    | Jan 1 to Jan 4
Amex         | 3 days        | 4 days    | Jan 1 to Jan 5  ← Extra day!
```

### **Example 2: Forward Days = 5**
```
Card Type    | Standard Days | Amex Gets | Date Range (from Jan 1)
-------------|---------------|-----------|------------------------
Visa         | 5 days        | 5 days    | Jan 1 to Jan 6
Mastercard   | 5 days        | 5 days    | Jan 1 to Jan 6
Discover     | 5 days        | 5 days    | Jan 1 to Jan 6
Amex         | 5 days        | 6 days    | Jan 1 to Jan 7  ← Extra day!
```

## 🖥️ Web App Integration

### **Visual Indicators:**
The web app now shows the Amex extra day information:

1. **Sidebar Configuration:**
   ```
   💳 Card Type Settings
   - Forward days: 3 days
   - Amex gets extra day: 4 days total
   ```

2. **Processing Status:**
   ```
   🛡️ Anti-greedy matching credit card transactions 
   (max 3 per cell, Amex gets 4 days)...
   ```

### **Settings:**
- The extra day is **automatic** - no configuration needed
- Works with **all forward_days values**
- Applies to **all matching modes** (cards only, deposits only, combined)

## 🎯 Benefits

### **Why Amex Gets Extra Time:**
1. **Different Processing Times**: Amex may have different settlement patterns
2. **Network Differences**: Amex uses its own network vs. Visa/MC shared networks
3. **Better Matching**: More time to find the correct Amex transactions
4. **Reduced Unmatched**: Fewer Amex transactions left unmatched

### **Real-World Impact:**
- **Before**: Amex transaction on Jan 1 could only match Jan 1-4 transactions
- **After**: Amex transaction on Jan 1 can match Jan 1-5 transactions
- **Result**: Better Amex matching rates and fewer discrepancies

## 🔍 Technical Details

### **Automatic Application:**
- ✅ **Standard matching** - Uses extra day automatically
- ✅ **Anti-greedy matching** - Uses extra day automatically  
- ✅ **Fair matching** - Uses extra day automatically
- ✅ **All card types** - Only Amex gets the extra day

### **Backward Compatibility:**
- ✅ **No breaking changes** - Existing functionality unchanged
- ✅ **Same file outputs** - Reports and Excel files unchanged
- ✅ **Same UI** - Just shows additional information
- ✅ **Configurable** - Can be disabled by modifying code

## 📈 Expected Results

### **Before (Standard 3 Days for All):**
```
Date       | Amex Expected | Amex Found | Status
-----------|---------------|------------|--------
2025-01-01 | $1,000        | $800       | ❌ Unmatched $200
2025-01-02 | $500          | $500       | ✅ Perfect match
2025-01-03 | $750          | $600       | ❌ Unmatched $150
```

### **After (Amex Gets 4 Days):**
```
Date       | Amex Expected | Amex Found | Status
-----------|---------------|------------|--------
2025-01-01 | $1,000        | $1,000     | ✅ Perfect match
2025-01-02 | $500          | $500       | ✅ Perfect match  
2025-01-03 | $750          | $750       | ✅ Perfect match
```

## 🚀 Usage

### **No Action Required:**
The Amex extra day feature is **automatically enabled** and requires no configuration.

### **To Verify It's Working:**
1. **Run the web app**: `streamlit run app.py`
2. **Check the sidebar**: Look for "Amex gets extra day" information
3. **Process your data**: Amex transactions will automatically get the extra day
4. **Review results**: Amex matching should be improved

### **To Disable (if needed):**
Edit `matchers/matching_helpers.py` and remove the Amex extra day logic:
```python
# Change this:
if card_type == 'Amex':
    effective_forward_days = forward_days + 1
else:
    effective_forward_days = forward_days

# To this:
effective_forward_days = forward_days
```

## 🎉 Summary

The Amex extra day feature is now **fully integrated** and **automatically active**:

- ✅ **Amex gets 1 extra day** of forward-looking allowance
- ✅ **Other cards unchanged** - Visa, MC, Discover get standard days
- ✅ **Web app shows info** - Clear indication of the extra day
- ✅ **All systems updated** - Standard, anti-greedy, and fair matching
- ✅ **No configuration needed** - Works automatically
- ✅ **Better Amex matching** - Improved results for Amex transactions

This should significantly improve your Amex transaction matching rates! 🎯
