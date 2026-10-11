import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def generate_revenue_report(df: pd.DataFrame):
    print("\n" + "="*50)
    print("1. REVENUE ANALYTICS (Actual vs Expected)")
    print("="*50)
    rev = df.groupby('COMM_MONTH')[['ACTUAL_REVENUE_SHARE', 'EXPECTED_REVENUE_SHARE']].sum().reset_index()
    rev['ACTUAL_REVENUE_SHARE'] = rev['ACTUAL_REVENUE_SHARE'].map('Rs. {:,.2f}'.format)
    rev['EXPECTED_REVENUE_SHARE'] = rev['EXPECTED_REVENUE_SHARE'].map('Rs. {:,.2f}'.format)
    print(rev.tail(6).to_string(index=False))  # Show last 6 months

def generate_collection_report(df: pd.DataFrame):
    print("\n" + "="*50)
    print("2. COLLECTION ANALYTICS (Customer Payments)")
    print("="*50)
    # Only look at transactions that actually generate bills
    bills = df[df['TRANSACTION_CATEGORY'].isin(['PERIODIC_REVENUE', 'INSTALLMENT'])].copy()
    
    # Safely convert to numeric before summing
    bills['BILL_AMOUNT'] = pd.to_numeric(bills['BILL_AMOUNT'], errors='coerce').fillna(0)
    bills['PAID_AMOUNT'] = pd.to_numeric(bills['PAID_AMOUNT'], errors='coerce').fillna(0)
    
    col = bills.groupby('COMM_MONTH')[['BILL_AMOUNT', 'PAID_AMOUNT', 'OUTSTANDING_AMOUNT']].sum().reset_index()
    col['COLLECTION_RATE'] = (col['PAID_AMOUNT'] / col['BILL_AMOUNT'] * 100).fillna(0).map('{:.1f}%'.format)
    col['BILL_AMOUNT'] = col['BILL_AMOUNT'].map('Rs. {:,.2f}'.format)
    col['PAID_AMOUNT'] = col['PAID_AMOUNT'].map('Rs. {:,.2f}'.format)
    col['OUTSTANDING_AMOUNT'] = col['OUTSTANDING_AMOUNT'].map('Rs. {:,.2f}'.format)
    print(col.tail(6).to_string(index=False))

def generate_reconciliation_report(df: pd.DataFrame):
    print("\n" + "="*50)
    print("3. RECONCILIATION ANALYTICS (BSNL Accuracy)")
    print("="*50)
    status_counts = df['RECONCILIATION_STATUS'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Transaction Count']
    print(status_counts.to_string(index=False))
    
    shortfall = df['POTENTIAL_SHORTFALL'].sum()
    excess = df['POTENTIAL_EXCESS'].sum()
    print("-" * 40)
    print(f"Total Potential Shortfall (BSNL Owes You): Rs. {shortfall:,.2f}")
    print(f"Total Potential Excess (BSNL Overpaid):  Rs. {excess:,.2f}")

def generate_adjustment_report(df: pd.DataFrame):
    print("\n" + "="*50)
    print("4. ADJUSTMENT ANALYTICS (Bonuses & Recoveries)")
    print("="*50)
    adj = df[df['TRANSACTION_CATEGORY'].isin(['BONUS_INCENTIVE', 'RECOVERY'])].copy()
    if adj.empty:
        print("No bonuses or recoveries found.")
    else:
        summary = adj.groupby('TRANSACTION_CATEGORY')['ACTUAL_REVENUE_SHARE'].sum().reset_index()
        summary['ACTUAL_REVENUE_SHARE'] = summary['ACTUAL_REVENUE_SHARE'].map('Rs. {:,.2f}'.format)
        summary.columns = ['Category', 'Total Financial Impact']
        print(summary.to_string(index=False))
    print("\n")

def run_all_reports(history_path: Path):
    if not history_path.exists():
        logger.error(f"Cannot generate reports. File not found: {history_path}")
        return
        
    df = pd.read_csv(history_path)
    generate_revenue_report(df)
    generate_collection_report(df)
    generate_reconciliation_report(df)
    generate_adjustment_report(df)

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    history_path = project_root / "data" / "output" / "bill_history.csv"
    run_all_reports(history_path)
