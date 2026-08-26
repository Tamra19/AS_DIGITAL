import pandas as pd
from pathlib import Path
from extract import extract_data

def clean_currency_column(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Removes commas and converts a column to a numeric float type.
    """
    if column_name in df.columns:
        # 1. Convert to string (in case some are already numbers or missing)
        # 2. Replace commas with nothing
        # 3. Convert the result to a float (decimal number)
        cleaned_strings = df[column_name].astype(str).str.replace(',', '').str.strip()
        df[column_name] = pd.to_numeric(cleaned_strings, errors='coerce')
    return df

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies data cleaning rules discovered during profiling.
    """
    print("\n--- Starting Data Cleaning ---")
    df_cleaned = df.copy() # Good practice: don't modify the original raw DataFrame
    
    # RULE 1: Fix numeric columns containing commas
    currency_columns = ['FTTH_FMC', 'BILL_AMOUNT', 'PAID_AMOUNT', 'REVENUE_SHARE', 'OTF']
    for col in currency_columns:
        df_cleaned = clean_currency_column(df_cleaned, col)
        
    # RULE 2: Handle missing OTF
    if 'OTF' in df_cleaned.columns:
        # Replace missing (NaN) values with 0.0
        df_cleaned['OTF'] = df_cleaned['OTF'].fillna(0.0)
        
    print(f"Cleaned {len(currency_columns)} currency columns.")
    print("Filled missing OTF values with 0.0.")
    
    return df_cleaned

def investigate_duplicates(df: pd.DataFrame):
    """
    Helper function to look at why SERVICE_NO is duplicated.
    """
    print("\n--- Investigating SERVICE_NO Duplicates ---")
    # Find rows where SERVICE_NO is duplicated (keep=False marks all copies as True)
    duplicates = df[df.duplicated(subset=['SERVICE_NO'], keep=False)]
    
    # Sort by SERVICE_NO so the duplicates are next to each other
    duplicates = duplicates.sort_values('SERVICE_NO')
    
    # We will just print the first 4 rows of duplicates to see what's happening
    cols_to_show = ['SERVICE_NO', 'BILL_NBR', 'COMM_MONTH', 'COMM_TYPE', 'REMARKS']
    print(duplicates[cols_to_show].head(4))
    print("-------------------------------------------\n")

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sample_file = project_root / "commission_test_sheet - Sheet1.csv"
    
    # 1. Extract
    raw_data = extract_data(str(sample_file))
    
    # 2. Investigate duplicates BEFORE cleaning
    investigate_duplicates(raw_data)
    
    # 3. Clean
    cleaned_data = clean_data(raw_data)
    
    # 4. Prove the data types are fixed
    print("\n--- Data Types After Cleaning ---")
    cols_to_check = ['FTTH_FMC', 'OTF', 'BILL_AMOUNT', 'PAID_AMOUNT']
    print(cleaned_data[cols_to_check].dtypes)
    print("\n--- Missing OTF check after cleaning ---")
    print(f"Missing OTF values: {cleaned_data['OTF'].isnull().sum()}")
