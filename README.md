# BSNL WiFi Franchise Revenue Management - User Manual

## Overview
This Python-based ETL (Extract, Transform, Load) pipeline automates the processing of your monthly BSNL WiFi/FTTH franchise billing data. It reads raw commission sheets (even messy ones), cleans the data, calculates your actual generated revenue, flags financial anomalies, and safely stores the data in a historical database without duplicating bills.

## Project Architecture
This project uses a fully automated "Drop Folder" ETL architecture:

1. **Extract (`src/extract.py`)**: Reads the raw file. It includes smart detection—if BSNL provides an Excel file disguised as a CSV with garbage report titles at the top, it seamlessly switches engines and skips the garbage rows.
2. **Clean (`src/clean.py`)**: Fixes formatting issues (e.g., removing commas from numbers) and coerces bad data or empty spaces in currency columns into clean `0.0`s.
3. **Transform (`src/transform.py`)**: Calculates `MY_REVENUE`, determines `PAYMENT_STATUS`, and executes the **Anomaly Detection** logic (comparing actual payouts to the expected mode for that FMC).
4. **Validate (`src/validate.py`)**: Acts as a bouncer, crashing the script purposefully if the data is fundamentally corrupted (e.g., missing `SERVICE_NO`).
5. **Load (`src/load.py`)**: Uses intelligent "Upsert" logic (Idempotency) to save data to `bill_history.csv` without duplicating existing records.
6. **Analytics (`src/analytics.py`)**: Generates high-level business reports and the financial anomaly breakdown.
7. **Orchestrator (`src/main.py`)**: The master script that runs everything in order and manages your folders.

## Folder Structure
```text
REVENUE_MANAGEMENT_SYSTEM/
│
├── data/
│   ├── input/                     # DROP YOUR RAW BSNL FILES HERE
│   ├── processed/                 # Files are moved here after success
│   └── output/
│       ├── bill_history.csv       # Persistent historical database
│       └── current_connections.csv# Latest snapshot of each customer
│
├── src/                           # All python logic scripts
├── requirements.txt               # Python dependencies
└── README.md                      # This manual
```

## How to Run the Pipeline Locally

### 1. Activate the Environment
Open your terminal in the `REVENUE_MANAGEMENT_SYSTEM` folder and run:
**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Drop the File
Take your latest monthly report from BSNL (e.g., `commission_history.csv`) and drop it directly into the `data/input/` folder.

### 3. Run the Orchestrator
Execute the master pipeline:
```powershell
python src/main.py
```
**What happens next?**
1. The script will find the file in the `input/` folder and process it.
2. It will update your databases in `data/output/`.
3. It will automatically move the raw file into `data/processed/` so it isn't processed twice.
4. It will print your Monthly Revenue Report, Payment Status breakdown, and Total Revenue Share Lost to anomalies.

## Business Rules Implemented
* **Revenue Calculation**: `MY_REVENUE = (FTTH_FMC * 0.96 * 0.5) - OTF`
* **Payment Status**: 
  * `UNPAID` if Paid Amount is 0.
  * `PAID` if Paid Amount is equal to (or within 2 Rupees of) the Bill Amount.
  * `PARTIALLY_PAID` if Paid Amount is strictly less than the Bill Amount minus 2 Rupees.
* **Anomaly Detection**: 
  * Calculates `EXPECTED_REVENUE_SHARE` based on the most common payout for a given `FTTH_FMC`.
  * Calculates `REVENUE_SHARE_LOSS` by subtracting Actual from Expected.
* **Idempotency**: A customer (`SERVICE_NO`) can only have one bill per month (`COMM_MONTH`). The newest record processed will overwrite any older copies.
