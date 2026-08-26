import pandas as pd
import logging
from pathlib import Path

# Set up logging for this file
logger = logging.getLogger(__name__)

def extract_data(file_path: str) -> pd.DataFrame:
    """
    Reads the raw data file from the BSNL system.
    Smartly detects if it is a real CSV or a disguised Excel file,
    and skips garbage header rows.
    """
    logger.info(f"Starting extraction from {file_path}")
    
    try:
        # First, try to read it as a normal CSV (like your original test file)
        df = pd.read_csv(file_path, dtype=str)
    except Exception:
        # If it crashes, it's likely BSNL's disguised Excel format
        logger.info("File appears to be an Excel workbook disguised as a CSV. Extracting...")
        # header=2 tells pandas to skip the first two garbage rows (Report Name, Export Time)
        df = pd.read_excel(file_path, engine='openpyxl', header=2, dtype=str)
    
    # Normalizing COMM_MONTH:
    # If Excel parsed '202309' as '2023-09-01 00:00:00', we need to convert it back to '202309'
    # so our Idempotency logic doesn't break.
    if 'COMM_MONTH' in df.columns:
        def fix_date(val):
            val = str(val).strip()
            if len(val) >= 7 and val[4] == '-':
                # Turns '2023-09-01 00:00:00' into '202309'
                return val.replace('-', '')[:6]
            return val
        df['COMM_MONTH'] = df['COMM_MONTH'].apply(fix_date)
        
    # Drop any completely empty blank rows at the bottom of the sheet
    df = df.dropna(how='all')

    logger.info(f"Successfully loaded {len(df):,} rows and {len(df.columns)} columns.")
    return df

# A simple block to test this file directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Using pathlib to build the path safely, assuming we run from the project root
    project_root = Path(__file__).parent.parent
    sample_file = project_root / "commission_test_sheet - Sheet1.csv"
    
    # Test the extraction
    raw_data = extract_data(str(sample_file))
    
    # Print the first 5 rows to prove it worked
    print("\n--- First 5 rows of the extracted data ---")
    print(raw_data.head())
