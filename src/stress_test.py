import pandas as pd
from pathlib import Path

def run_stress_test(file_path):
    print("\n--- STRESS TEST REPORT ---")
    
    # 1. Load Data
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        print(f"[SUCCESS] Successfully loaded {len(df):,} rows and {len(df.columns)} columns.")
    except Exception as e:
        print(f"[ERROR] Failed to load CSV. Error: {e}")
        return

    # 2. Check for unexpected COMM_TYPEs
    if 'COMM_TYPE' in df.columns:
        print("\n--- Unique COMM_TYPEs found ---")
        counts = df['COMM_TYPE'].value_counts(dropna=False)
        print(counts.to_string())
    
    # 3. Check for new missing columns
    required_columns = ['SERVICE_NO', 'BILL_NBR', 'COMM_MONTH', 'FTTH_FMC', 'OTF', 
                        'REVENUE_SHARE', 'BILL_AMOUNT', 'PAID_AMOUNT', 'PAID_DATE', 'COMM_TYPE']
    
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        print(f"\n[DANGER] The new file is missing these required columns: {missing_cols}")
    else:
        print("\n[SUCCESS] All required columns are present in the new file.")

    # 4. Check for currency format issues
    # Just a quick check to see if strings are still formatted with commas
    currency_cols = ['FTTH_FMC', 'BILL_AMOUNT', 'PAID_AMOUNT', 'REVENUE_SHARE']
    print("\n--- Currency Column Types ---")
    for col in currency_cols:
        if col in df.columns:
            # Check the first non-null value to see what it looks like
            sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            print(f"{col}: type={df[col].dtype}, sample='{sample_val}'")

    print("--------------------------\n")

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    large_file = project_root / "data" / "input" / "commission_history.csv"
    run_stress_test(large_file)
