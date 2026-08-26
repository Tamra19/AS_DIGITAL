import pandas as pd
from pathlib import Path
from extract import extract_data

def profile_data(df: pd.DataFrame):
    """
    Profiles the dataframe to understand its structure and quality.
    """
    print("\n================ DATA PROFILING REPORT ================\n")
    
    print("1. EXACT COLUMN NAMES:")
    print(df.columns.tolist())
    print("\n-------------------------------------------------------")
    
    print("2. DATA TYPES:")
    # We want to see if pandas thinks numeric columns are strings (object)
    print(df.dtypes)
    print("\n-------------------------------------------------------")
    
    print("3. MISSING VALUES:")
    # counts the number of empty/NaN values per column
    missing = df.isnull().sum()
    print(missing[missing > 0]) # only show columns with missing data
    print("\n-------------------------------------------------------")
    
    print("4. SERVICE_NO DUPLICATES:")
    if 'SERVICE_NO' in df.columns:
        total_connections = len(df)
        unique_connections = df['SERVICE_NO'].nunique()
        print(f"Total Rows: {total_connections}")
        print(f"Unique SERVICE_NOs: {unique_connections}")
        if total_connections != unique_connections:
            print(f"[WARNING] There are {total_connections - unique_connections} duplicate SERVICE_NO records.")
    
    print("\n-------------------------------------------------------")
    
    print("5. SAMPLE OF CRITICAL NUMERIC COLUMNS:")
    critical_cols = ['FTTH_FMC', 'OTF', 'REVENUE_SHARE', 'BILL_AMOUNT', 'PAID_AMOUNT']
    existing_cols = [col for col in critical_cols if col in df.columns]
    
    # Show exactly what the raw text looks like in the file
    print(df[existing_cols].head(10))
    
    print("\n=======================================================\n")

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sample_file = project_root / "commission_test_sheet - Sheet1.csv"
    
    raw_data = extract_data(str(sample_file))
    profile_data(raw_data)
