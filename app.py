import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Ensure Python can find our src modules
sys.path.insert(0, './src')
from main import run_etl_pipeline

# Configure the Streamlit page
st.set_page_config(page_title="BSNL Revenue Manager", layout="wide", page_icon="📡")

st.title("📡 BSNL Franchise Revenue Manager")
st.markdown("Automated ETL Pipeline & Financial Analytics Dashboard")

# ----------------------------------------
# SIDEBAR: File Upload & Pipeline Trigger
# ----------------------------------------
st.sidebar.header("1. Upload Monthly Data")
uploaded_file = st.sidebar.file_uploader("Upload BSNL Commission Report (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded_file is not None:
    # Save the uploaded file to data/input
    input_dir = Path("data/input")
    input_dir.mkdir(parents=True, exist_ok=True)
    file_path = input_dir / uploaded_file.name
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.sidebar.success(f"File saved to input folder.")
    
    # Run Pipeline Button
    st.sidebar.header("2. Process Data")
    if st.sidebar.button("Run ETL Pipeline", type="primary"):
        with st.spinner("Cleaning, Transforming, and Loading data..."):
            success = run_etl_pipeline()
            if success:
                st.sidebar.success("✅ Pipeline executed successfully!")
            else:
                st.sidebar.error("❌ Pipeline failed to process the file.")

# ----------------------------------------
# MAIN AREA: Analytics Dashboards
# ----------------------------------------
st.header("📊 Business Analytics")

output_file = Path("data/output/bill_history.csv")

if output_file.exists():
    df = pd.read_csv(output_file)
    
    # 1. Monthly Revenue KPIs
    st.subheader("Monthly Generated Revenue")
    monthly_rev = df.groupby('COMM_MONTH')['MY_REVENUE'].sum().reset_index()
    
    # Display metrics side by side dynamically based on how many months are found
    cols = st.columns(len(monthly_rev))
    for i, row in monthly_rev.iterrows():
        cols[i].metric(label=f"Month: {row['COMM_MONTH']}", value=f"₹{row['MY_REVENUE']:,.2f}")
        
    st.divider()
    
    # 2. Payment Status Breakdown
    st.subheader("Revenue by Payment Status")
    status_rev = df.groupby(['COMM_MONTH', 'PAYMENT_STATUS'])['MY_REVENUE'].sum().reset_index()
    
    # Pivot the table to make it look nicer in the UI
    status_pivot = status_rev.pivot(index='COMM_MONTH', columns='PAYMENT_STATUS', values='MY_REVENUE').fillna(0)
    
    # Formatting for display
    st.dataframe(status_pivot.style.format("₹{:,.2f}"), use_container_width=True)
    
    st.divider()
    
    # 3. Anomaly Report (Underpayments Only)
    st.subheader("🚨 Revenue Share Anomaly Report (Underpaid Only)")
    st.markdown("Customers whose Revenue Share payout was **less** than the expected standard for their FTTH_FMC plan.")
    
    all_anomalies = df[df['SUSPICIOUS_REVENUE_SHARE'].str.startswith('Yes')].copy()
    
    # Strictly filter for underpayments (where you lost money)
    anomalies = all_anomalies[all_anomalies['REVENUE_SHARE_LOSS'] > 0]
    
    if anomalies.empty:
        st.success("No underpayment anomalies found! All revenue share matches expectations or was overpaid.")
    else:
        total_loss = anomalies['REVENUE_SHARE_LOSS'].sum()
        
        # Display loss metric in a big prominent box
        st.metric(
            label="Total Revenue Share Lost (Underpaid)", 
            value=f"₹{total_loss:,.2f}", 
            delta="Financial Loss", 
            delta_color="inverse"
        )
        
        cols_to_show = ['SERVICE_NO', 'COMM_MONTH', 'FTTH_FMC', 'REVENUE_SHARE', 'EXPECTED_REVENUE_SHARE', 'REVENUE_SHARE_LOSS']
        
        # Sort anomalies so the biggest losses are at the top
        anomalies_sorted = anomalies[cols_to_show].sort_values(by='REVENUE_SHARE_LOSS', ascending=False)
        st.dataframe(anomalies_sorted, use_container_width=True)
        
else:
    st.info("No historical data found. Please upload your BSNL file in the sidebar and run the pipeline to generate your dashboard.")
