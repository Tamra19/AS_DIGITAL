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
        'REVENUE_SHARE', 'BILL_AMOUNT', 'PAID_AMOUNT', 'PAID_DATE', 'COMM_TYPE'
    ]
    
    available_columns = [col for col in required_columns if col in df.columns]
    df_transformed = df[available_columns].copy()
    
    # 2. Safely handle missing FTTH_FMC
    df_transformed['FTTH_FMC'] = df_transformed['FTTH_FMC'].fillna(0.0)
    
    # 3. Calculate MY_REVENUE
    df_transformed['MY_REVENUE'] = (df_transformed['FTTH_FMC'] * 0.96 * 0.5) - df_transformed['OTF']
    df_transformed['MY_REVENUE'] = df_transformed['MY_REVENUE'].round(2)
    
    # 4. Apply Payment Status Rule
    df_transformed['PAYMENT_STATUS'] = df_transformed.apply(get_payment_status, axis=1)
    
    # 5. Anomaly Detection & Financial Impact
    # Find the most common (mode) REVENUE_SHARE for each FTTH_FMC > 0
    valid_fmc = df_transformed[df_transformed['FTTH_FMC'] > 0]
    expected_rev_map = {}
    for fmc, group in valid_fmc.groupby('FTTH_FMC'):
        modes = group['REVENUE_SHARE'].mode()
        if not modes.empty:
            expected_rev_map[fmc] = modes.iloc[0]
            
    def calculate_expected_rev(row):
        fmc = row['FTTH_FMC']
        if fmc == 0.0:
            # If FMC is 0, we can't establish a standard expectation, so we just expect what we got
            return row['REVENUE_SHARE']
        # Return the mode, or the actual revenue if the mode isn't found for some reason
        return expected_rev_map.get(fmc, row['REVENUE_SHARE'])

    # Create the new columns
    df_transformed['EXPECTED_REVENUE_SHARE'] = df_transformed.apply(calculate_expected_rev, axis=1)
    
    # Calculate the exact financial loss (Expected - Actual)
    df_transformed['REVENUE_SHARE_LOSS'] = df_transformed['EXPECTED_REVENUE_SHARE'] - df_transformed['REVENUE_SHARE']
    
    # Let's keep the old text flag too, as it's useful for quick filtering
    def check_anomaly(row):
        if row['FTTH_FMC'] == 0.0:
            return 'No'
        if abs(row['REVENUE_SHARE_LOSS']) > 0.01:
            return 'Yes'
        return 'No'

    df_transformed['SUSPICIOUS_REVENUE_SHARE'] = df_transformed.apply(check_anomaly, axis=1)
    
    print("Dropped unneeded columns.")
    print("Calculated MY_REVENUE successfully.")
    print("Calculated PAYMENT_STATUS successfully.")
    print("Calculated EXPECTED_REVENUE_SHARE and REVENUE_SHARE_LOSS.")
    
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
