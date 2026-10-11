import pandas as pd
from pathlib import Path
from extract import extract_data
from clean import clean_data

def get_payment_status(row):
    """Business rule for determining if a bill is paid."""
    if row['PAID_AMOUNT'] == 0:
        return 'UNPAID'
    elif row['PAID_AMOUNT'] >= (row['BILL_AMOUNT'] - 2.0):
        # Allowing a 2 Rupee rounding difference
        return 'PAID'
    else:
        return 'PARTIALLY_PAID'

def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Selects required columns and adds calculated fields like MY_REVENUE.
    """
    print("\n--- Starting Transformation ---")
    
    # 1. Select only the columns we actually need
    required_columns = [
        'SERVICE_NO', 'BILL_NBR', 'COMM_MONTH', 'FTTH_FMC', 'OTF', 
        'REVENUE_SHARE', 'BILL_AMOUNT', 'PAID_AMOUNT', 'PAID_DATE', 'COMM_TYPE',
        'REVENUE_SHARE_PERCENT'
    ]
    
    available_columns = [col for col in required_columns if col in df.columns]
    df_transformed = df[available_columns].copy()
    
    # 2. Safely handle missing FTTH_FMC
    df_transformed['FTTH_FMC'] = df_transformed['FTTH_FMC'].fillna(0.0)
    
    # 2b. Transaction Classification (Phase 2)
    def classify_transaction(comm_type):
        comm = str(comm_type).strip().upper()
        if comm in ['MONTHLY', 'ANNUALLY', 'QUARTERLY', 'HALF-YEARLY', 'ANNUALLY-202309']:
            return 'PERIODIC_REVENUE'
        elif 'INSTALLMENT' in comm:
            return 'INSTALLMENT'
        elif 'PARTIAL' in comm:
            return 'PARTIAL_PAYMENT'
        elif 'BONUS' in comm or 'INCENTIVE' in comm or 'MP_SA_COMM' in comm or 'STATELED' in comm:
            return 'BONUS_INCENTIVE'
        elif 'RECOVERY' in comm:
            return 'RECOVERY'
        elif 'LEGACY' in comm:
            return 'LEGACY'
        else:
            return 'UNKNOWN'
            
    df_transformed['TRANSACTION_CATEGORY'] = df_transformed['COMM_TYPE'].apply(classify_transaction)
    
    # Ensure numeric columns are ready for math
    df_transformed['REVENUE_SHARE_PERCENT_NUM'] = pd.to_numeric(df_transformed['REVENUE_SHARE_PERCENT'], errors='coerce')
    df_transformed['ACTUAL_REVENUE_SHARE'] = pd.to_numeric(df_transformed['REVENUE_SHARE'], errors='coerce').fillna(0.0)
    
    # 4. Apply Payment Status Rule (Kept from original, but moved up)
    df_transformed['PAYMENT_STATUS'] = df_transformed.apply(get_payment_status, axis=1)
    
    # 5. Phase 3: Revenue Rule Engine
    # Pre-compute historical modes for the Fallback Rule
    valid_fmc = df_transformed[(df_transformed['FTTH_FMC'] > 0) & (df_transformed['TRANSACTION_CATEGORY'] == 'PERIODIC_REVENUE')]
    historical_modes = {}
    for (fmc, share_pct), group in valid_fmc.groupby(['FTTH_FMC', 'REVENUE_SHARE_PERCENT_NUM']):
        modes = group['ACTUAL_REVENUE_SHARE'].mode()
        if not modes.empty:
            historical_modes[(fmc, share_pct)] = modes.iloc[0]

    def revenue_rule_engine(row):
        category = row['TRANSACTION_CATEGORY']
        fmc = row['FTTH_FMC']
        share_pct = row['REVENUE_SHARE_PERCENT_NUM']
        actual = row['ACTUAL_REVENUE_SHARE']
        
        # Rule 1: Special Transactions (Bonuses, Recoveries, Legacy) cannot be mathematically predicted
        if category in ['BONUS_INCENTIVE', 'RECOVERY', 'LEGACY']:
            return pd.Series([None, 'Special Transaction - No Rule', 'UNKNOWN'])
            
        # Rule 2: Billing Transactions
        if category in ['PERIODIC_REVENUE', 'INSTALLMENT', 'PARTIAL_PAYMENT']:
            if pd.isna(share_pct) or fmc == 0.0:
                return pd.Series([None, 'Missing FMC or Share %', 'LOW'])
                
            # Theoretical Math Formula (8% LF Deduction -> 0.92 Adjustment Factor)
            ADJUSTMENT_FACTOR = 0.92
            math_expected = round(fmc * (share_pct / 100) * ADJUSTMENT_FACTOR, 2)
            
            # Check if actual aligns with standard math
            if pd.notna(actual) and abs(actual - math_expected) <= 0.05:
                return pd.Series([math_expected, 'Standard Telecom Formula (0.92)', 'HIGH'])
                
            # Rule 2b: Historical Fallback (For plans like 999 that deduct OTT first)
            fallback_expected = historical_modes.get((fmc, share_pct))
            if fallback_expected is not None:
                return pd.Series([fallback_expected, 'Historical Statistical Mode', 'MEDIUM'])
                
            # Rule 2c: If all else fails, default to theoretical math but flag as LOW confidence
            return pd.Series([math_expected, 'Standard Formula (Unverified)', 'LOW'])

        return pd.Series([None, 'UNKNOWN', 'UNKNOWN'])

    # Apply Rule Engine (returns EXPECTED_REVENUE_SHARE, RULE_APPLIED, RULE_CONFIDENCE)
    rule_cols = ['EXPECTED_REVENUE_SHARE', 'RULE_APPLIED', 'RULE_CONFIDENCE']
    df_transformed[rule_cols] = df_transformed.apply(revenue_rule_engine, axis=1)

    # 6. Phase 4: Reconciliation Analytics
    VARIANCE_TOLERANCE = 5.00
    
    def calculate_reconciliation(row):
        actual = row.get('ACTUAL_REVENUE_SHARE')
        expected = row.get('EXPECTED_REVENUE_SHARE')
        confidence = row.get('RULE_CONFIDENCE')
        category = row.get('TRANSACTION_CATEGORY')
        
        # Default empty states
        variance = 0.0
        shortfall = 0.0
        excess = 0.0
        status = 'UNKNOWN'
        
        if pd.notna(actual) and pd.notna(expected):
            variance = round(actual - expected, 2)
            
            if abs(variance) <= VARIANCE_TOLERANCE:
                status = 'NORMAL'
            elif variance < -VARIANCE_TOLERANCE:
                # Actual is less than Expected -> Shortfall
                if confidence in ['HIGH', 'MEDIUM']:
                    shortfall = abs(variance)
                    status = 'POTENTIAL_SHORTFALL'
                else:
                    status = 'REVIEW_REQUIRED'
            elif variance > VARIANCE_TOLERANCE:
                # Actual is more than Expected -> Excess
                excess = variance
                if confidence in ['HIGH', 'MEDIUM']:
                    status = 'POTENTIAL_EXCESS'
                else:
                    status = 'REVIEW_REQUIRED'
        else:
            if category in ['BONUS_INCENTIVE', 'RECOVERY', 'LEGACY']:
                status = 'SPECIAL_TRANSACTION'
            else:
                status = 'UNKNOWN_RULE'
                
        return pd.Series([variance, shortfall, excess, status])

    recon_cols = ['REVENUE_SHARE_VARIANCE', 'POTENTIAL_SHORTFALL', 'POTENTIAL_EXCESS', 'RECONCILIATION_STATUS']
    df_transformed[recon_cols] = df_transformed.apply(calculate_reconciliation, axis=1)

    # Calculate OUTSTANDING_AMOUNT only for relevant bill transactions
    def calc_outstanding(row):
        if row['TRANSACTION_CATEGORY'] in ['PERIODIC_REVENUE', 'INSTALLMENT', 'PARTIAL_PAYMENT']:
            bill = pd.to_numeric(row['BILL_AMOUNT'], errors='coerce')
            paid = pd.to_numeric(row['PAID_AMOUNT'], errors='coerce')
            if pd.notna(bill) and pd.notna(paid):
                return max(bill - paid, 0.0)
        return None

    df_transformed['OUTSTANDING_AMOUNT'] = df_transformed.apply(calc_outstanding, axis=1)

    # 6. Generate deterministic TRANSACTION_ID
    import hashlib
    def generate_tx_id(row):
        parts = [
            str(row.get('SERVICE_NO', '')),
            str(row.get('COMM_MONTH', '')),
            str(row.get('COMM_TYPE', '')),
            str(row.get('BILL_NBR', '')),
            str(row.get('REVENUE_SHARE', '')),
            str(row.get('BILL_AMOUNT', ''))
        ]
        raw_str = "|".join(parts)
        return hashlib.md5(raw_str.encode('utf-8')).hexdigest()
        
    df_transformed['TRANSACTION_ID'] = df_transformed.apply(generate_tx_id, axis=1)
    
    # Reorder so TRANSACTION_ID is the first column
    cols = df_transformed.columns.tolist()
    cols = ['TRANSACTION_ID'] + [c for c in cols if c != 'TRANSACTION_ID']
    df_transformed = df_transformed[cols]

    print("Dropped unneeded columns.")
    print("Classified Transactions.")
    print("Executed Phase 3 Revenue Rule Engine.")
    print("Generated unique TRANSACTION_ID.")
    
    return df_transformed

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sample_file = project_root / "commission_test_sheet - Sheet1.csv"
    
    raw_data = extract_data(str(sample_file))
    cleaned_data = clean_data(raw_data)
    transformed_data = transform_data(cleaned_data)
    
    # Print a sample of the calculation to verify it visually
    print("\n--- Testing the MY_REVENUE Calculation ---")
    
    # Let's look at 5 rows where FTTH_FMC is greater than 0 so we can check the math
    sample_test = transformed_data[transformed_data['FTTH_FMC'] > 0].head(5)
    
    cols_to_verify = ['FTTH_FMC', 'OTF', 'MY_REVENUE', 'REVENUE_SHARE']
    print(sample_test[cols_to_verify])
    
    print("\n------------------------------------------\n")
