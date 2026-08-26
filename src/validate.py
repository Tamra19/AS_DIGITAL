import pandas as pd
from pathlib import Path
import logging
from extract import extract_data
from clean import clean_data
from transform import transform_data

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception raised when data fails business rules."""
    pass

def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Acts as a checkpoint. If the data violates any business rules,
    it raises an error and stops the pipeline before bad data is saved.
    """
    print("\n--- Starting Data Validation ---")
    
    # 1. Check for missing SERVICE_NO
    # If a row has no SERVICE_NO, we have no idea who the customer is.
    missing_service = df['SERVICE_NO'].isnull().sum()
    if missing_service > 0:
        raise ValidationError(f"Data contains {missing_service} rows with a blank SERVICE_NO.")
    
    # 2. Check for NaN in MY_REVENUE
    # If our calculation broke, we want to know now, not later.
    missing_revenue = df['MY_REVENUE'].isnull().sum()
    if missing_revenue > 0:
        raise ValidationError(f"Calculation Error: {missing_revenue} rows have NaN for MY_REVENUE.")
    
    # 3. Check for massive negative revenue (Logic Check)
    # If MY_REVENUE is extremely negative, something might be wrong with OTF
    negative_revenue = df[df['MY_REVENUE'] < -5000]
    if not negative_revenue.empty:
        logger.warning(f"Warning: {len(negative_revenue)} rows have MY_REVENUE below -5000. Check OTF deductions.")

    print("[SUCCESS] Validation Passed: SERVICE_NO is populated for all rows.")
    print("[SUCCESS] Validation Passed: MY_REVENUE calculated without NaN errors.")
    
    return df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    project_root = Path(__file__).parent.parent
    sample_file = project_root / "commission_test_sheet - Sheet1.csv"
    
    # Run the pipeline up to Step 7
    raw_data = extract_data(str(sample_file))
    cleaned_data = clean_data(raw_data)
    transformed_data = transform_data(cleaned_data)
    
    # Validate
    validated_data = validate_data(transformed_data)
    
    print("\n------------------------------------------\n")
