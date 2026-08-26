import pandas as pd
from pathlib import Path
import logging
from extract import extract_data
from clean import clean_data
from transform import transform_data
from validate import validate_data
import os

logger = logging.getLogger(__name__)

def load_bill_history(df: pd.DataFrame, output_dir: Path):
    """
    Saves the validated data into our persistent Bill History dataset.
    Uses UPSERT logic (Idempotency) to ensure running the same data twice 
    does not create duplicate bills.
    """
    print("\n--- Starting Loading (Bill History) ---")
    output_dir.mkdir(parents=True, exist_ok=True)
    history_file = output_dir / "bill_history.csv"
    
    combined_df = df.copy()
    
    if history_file.exists():
        old_history_df = pd.read_csv(history_file)
        combined_df = pd.concat([old_history_df, df], ignore_index=True)
        
    # The Idempotency Key: A customer can only have ONE bill per month.
    # So SERVICE_NO + COMM_MONTH is our unique identifier.
    combined_df = combined_df.drop_duplicates(subset=['SERVICE_NO', 'COMM_MONTH'], keep='last')
    
    # Overwrite the history file with the newly deduplicated dataset
    combined_df.to_csv(history_file, index=False)
        
    print(f"[SUCCESS] Saved {len(combined_df)} total records to {history_file.name}")

def load_current_connections(df: pd.DataFrame, output_dir: Path):
    """
    Maintains a 'snapshot' dataset where there is only ONE row per SERVICE_NO,
    representing their absolute latest status.
    """
    print("\n--- Starting Loading (Current Connections) ---")
    current_file = output_dir / "current_connections.csv"
    
    # 1. Start with the incoming new data
    combined_df = df.copy()
    
    # 2. If we already have a current_connections dataset from last month, 
    # we need to load it and mix it with the new data.
    if current_file.exists():
        old_current_df = pd.read_csv(current_file)
        # pd.concat merges the two DataFrames top-to-bottom
        combined_df = pd.concat([old_current_df, df], ignore_index=True)
    
    # 3. The Magic Step: Sort by COMM_MONTH to ensure the newest is at the bottom,
    # then drop duplicates based on SERVICE_NO, keeping only the 'last' (newest) one.
    
    # (Note: For this to work perfectly, COMM_MONTH must be something like 202309, 202310)
    combined_df = combined_df.sort_values(by=['SERVICE_NO', 'COMM_MONTH'])
    
    # keep='last' tells pandas to delete the older months and keep the most recent row
    final_current_df = combined_df.drop_duplicates(subset=['SERVICE_NO'], keep='last')
    
    # 4. Overwrite the file completely with the new snapshot
    final_current_df.to_csv(current_file, index=False)
    
    print(f"[SUCCESS] Updated {current_file.name}. It now contains exactly {len(final_current_df)} unique connections.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    project_root = Path(__file__).parent.parent
    sample_file = project_root / "commission_test_sheet - Sheet1.csv"
    output_directory = project_root / "data" / "output"
    
    # Pipeline Execution
    raw_data = extract_data(str(sample_file))
    cleaned_data = clean_data(raw_data)
    transformed_data = transform_data(cleaned_data)
    validated_data = validate_data(transformed_data)
    
    # Dataset 1: Bill History (Append-only)
    load_bill_history(validated_data, output_directory)
    
    # Dataset 2: Current Connections (Snapshot / Upsert)
    load_current_connections(validated_data, output_directory)
    
    print("\n------------------------------------------\n")
