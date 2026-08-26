import pandas as pd
from pathlib import Path

def generate_revenue_report(history_file: Path):
    """
    Reads the Bill History and generates monthly revenue analytics.
    """
    print("\n=== MONTHLY REVENUE REPORT ===")
    df = pd.read_csv(history_file)
    
    # Group by the month and sum the MY_REVENUE column
    monthly_revenue = df.groupby('COMM_MONTH')['MY_REVENUE'].sum().reset_index()
    monthly_revenue['MY_REVENUE'] = monthly_revenue['MY_REVENUE'].map('{:,.2f}'.format)
    print(monthly_revenue.to_string(index=False))
    
    print("\n--- REVENUE BY PAYMENT STATUS ---")
    status_revenue = df.groupby(['COMM_MONTH', 'PAYMENT_STATUS'])['MY_REVENUE'].sum().reset_index()
    status_revenue['MY_REVENUE'] = status_revenue['MY_REVENUE'].map('{:,.2f}'.format)
    print(status_revenue.to_string(index=False))
    
    print("==============================\n")
    
def investigate_payment_status(history_file: Path):
    """
    Inspects how payments are recorded.
    """
    pass # we can just pass this now since we solved the payment status question earlier

def generate_anomaly_report(history_file: Path):
    """
    Scans the history file for any records that were flagged as suspicious during transformation.
    """
    print("--- REVENUE SHARE ANOMALY REPORT ---")
    df = pd.read_csv(history_file)
    
    # Filter for rows where the anomaly flag contains 'Yes'
    all_anomalies = df[df['SUSPICIOUS_REVENUE_SHARE'].str.startswith('Yes')]
    
    # Strictly filter for underpayments (where you lost money)
    anomalies = all_anomalies[all_anomalies['REVENUE_SHARE_LOSS'] > 0]
    
    if anomalies.empty:
        print("No underpayment records found! All revenue share matches expectations or was overpaid.")
    else:
        print(f"Found {len(anomalies)} suspicious records:")
        cols_to_show = ['SERVICE_NO', 'COMM_MONTH', 'FTTH_FMC', 'REVENUE_SHARE', 'EXPECTED_REVENUE_SHARE', 'REVENUE_SHARE_LOSS']
        print(anomalies[cols_to_show].to_string(index=False))
        
        # Calculate and print the exact total financial loss
        total_loss = anomalies['REVENUE_SHARE_LOSS'].sum()
        
        # Formatting neatly as currency
        print(f"\n====================================")
        print(f"TOTAL REVENUE SHARE LOST (UNDERPAID): Rs. {total_loss:,.2f}")
        print(f"====================================\n")
    print("------------------------------------\n")

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    history_path = project_root / "data" / "output" / "bill_history.csv"
    
    generate_revenue_report(history_path)
    investigate_payment_status(history_path)
    generate_anomaly_report(history_path)
