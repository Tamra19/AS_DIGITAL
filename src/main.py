import logging
import shutil
from pathlib import Path
import pandas as pd

from extract import extract_data
from clean import clean_data
from transform import transform_data
from validate import validate_data
from load import load_bill_history, load_current_connections
from analytics import generate_revenue_report, generate_anomaly_report

# Configure logging for the central orchestrator
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_etl_pipeline():
    """
    The master function that runs the entire ETL process.
    This can be easily hooked up to a frontend button later.
    """
    project_root = Path(__file__).parent.parent
    input_dir = project_root / "data" / "input"
    processed_dir = project_root / "data" / "processed"
    output_dir = project_root / "data" / "output"
    
    # Ensure directories exist
    input_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Look for any CSV files in the input folder
    csv_files = list(input_dir.glob('*.csv'))
    
    if not csv_files:
        logger.info(f"No new CSV files found in {input_dir}. Nothing to process.")
        return False

    logger.info(f"Found {len(csv_files)} file(s) to process.")
    
    # Process each file found
    for file_path in csv_files:
        try:
            logger.info(f"--- Processing: {file_path.name} ---")
            
            # Extract
            raw_data = extract_data(str(file_path))
            
            # Clean
            cleaned_data = clean_data(raw_data)
            
            # Transform
            transformed_data = transform_data(cleaned_data)
            
            # Validate
            validated_data = validate_data(transformed_data)
            
            # Load
            load_bill_history(validated_data, output_dir)
            load_current_connections(validated_data, output_dir)
            
            # Move the file to 'processed' so it doesn't get run again tomorrow
            destination = processed_dir / file_path.name
            
            # If a file with the same name already exists in processed, we replace it
            if destination.exists():
                destination.unlink()
                
            shutil.move(str(file_path), str(destination))
            logger.info(f"Successfully moved {file_path.name} to processed folder.")
            
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}. Error: {e}")
            # If it fails, it stays in the input folder so you can fix it and try again
    
    # Finally, run the analytics report on the newly updated database
    logger.info("--- Generating Analytics Reports ---")
    history_path = output_dir / "bill_history.csv"
    if history_path.exists():
        generate_revenue_report(history_path)
        generate_anomaly_report(history_path)
        
    return True

if __name__ == "__main__":
    # If someone runs this script directly, execute the function
    run_etl_pipeline()
