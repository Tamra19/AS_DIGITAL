import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Ensure Python can find our src modules
sys.path.insert(0, './src')
from main import run_etl_pipeline

st.set_page_config(page_title="BSNL Financial Analytics", layout="wide", page_icon="📡")

st.title("📡 BSNL Revenue & Reconciliation Dashboard")

# ----------------------------------------
# SIDEBAR: ETL Trigger & Filters
# ----------------------------------------
with st.sidebar:
    st.header("1. Upload Monthly Data")
    uploaded_file = st.file_uploader("Upload BSNL Commission Report (.csv or .xlsx)", type=["csv", "xlsx"])

    if uploaded_file is not None:
        input_dir = Path("data/input")
        input_dir.mkdir(parents=True, exist_ok=True)
        file_path = input_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success("File saved to input folder.")
        
        if st.button("Run ETL Pipeline", type="primary"):
            with st.spinner("Executing Rule Engine..."):
                success = run_etl_pipeline()
                if success:
                    st.success("✅ Pipeline executed successfully!")
                else:
                    st.error("❌ Pipeline failed to process.")

# ----------------------------------------
# MAIN AREA: Load Data
# ----------------------------------------
output_file = Path("data/output/bill_history.csv")

if not output_file.exists():
    st.info("No historical data found. Please upload your BSNL file in the sidebar and run the pipeline.")
    st.stop()

df = pd.read_csv(output_file)

# Ensure sorting
df['COMM_MONTH'] = df['COMM_MONTH'].astype(str)
df = df.sort_values('COMM_MONTH')

# Global Filters
st.sidebar.header("2. Dashboard Filters")
all_months = df['COMM_MONTH'].unique().tolist()
selected_months = st.sidebar.multiselect("Filter by Month", all_months, default=all_months[-3:] if len(all_months)>=3 else all_months)

if selected_months:
    df = df[df['COMM_MONTH'].isin(selected_months)]

# ----------------------------------------
# 1. FINANCIAL OVERVIEW
# ----------------------------------------
st.header("Financial Overview")
col1, col2, col3, col4 = st.columns(4)

total_actual = df['ACTUAL_REVENUE_SHARE'].sum()
total_expected = df['EXPECTED_REVENUE_SHARE'].sum()
total_shortfall = df['POTENTIAL_SHORTFALL'].sum()
total_excess = df['POTENTIAL_EXCESS'].sum()
total_outstanding = df['OUTSTANDING_AMOUNT'].sum()

col1.metric("Actual Revenue Share", f"₹{total_actual:,.2f}")
col2.metric("Expected Revenue", f"₹{total_expected:,.2f}")
col3.metric("Potential Shortfall (BSNL Owes)", f"₹{total_shortfall:,.2f}", delta="- Loss", delta_color="inverse")
col4.metric("Potential Excess (Overpaid)", f"₹{total_excess:,.2f}", delta="+ Gain", delta_color="normal")

st.divider()

# ----------------------------------------
# 2. REVENUE TREND & COMPOSITION
# ----------------------------------------
col_trend, col_comp = st.columns([2, 1])

with col_trend:
    st.subheader("Revenue Trend (Actual vs Expected)")
    trend_df = df.groupby('COMM_MONTH')[['ACTUAL_REVENUE_SHARE', 'EXPECTED_REVENUE_SHARE']].sum().reset_index()
    st.line_chart(trend_df.set_index('COMM_MONTH'), use_container_width=True)

with col_comp:
    st.subheader("Revenue Composition")
    comp_df = df.groupby('TRANSACTION_CATEGORY')['ACTUAL_REVENUE_SHARE'].sum().reset_index()
    st.dataframe(comp_df.style.format({'ACTUAL_REVENUE_SHARE': '₹{:,.2f}'}), use_container_width=True, hide_index=True)

st.divider()

# ----------------------------------------
# 3. COLLECTION ANALYTICS
# ----------------------------------------
st.subheader("Collection Analytics (Customer Payments)")
billing_df = df[df['TRANSACTION_CATEGORY'].isin(['PERIODIC_REVENUE', 'INSTALLMENT'])].copy()

# Ensure numeric for collection math
billing_df['BILL_AMOUNT'] = pd.to_numeric(billing_df['BILL_AMOUNT'], errors='coerce').fillna(0)
billing_df['PAID_AMOUNT'] = pd.to_numeric(billing_df['PAID_AMOUNT'], errors='coerce').fillna(0)

col_collect = billing_df.groupby('COMM_MONTH')[['BILL_AMOUNT', 'PAID_AMOUNT', 'OUTSTANDING_AMOUNT']].sum().reset_index()
col_collect['COLLECTION_RATE'] = (col_collect['PAID_AMOUNT'] / col_collect['BILL_AMOUNT'] * 100).fillna(0)

st.dataframe(
    col_collect.style.format({
        'BILL_AMOUNT': '₹{:,.2f}',
        'PAID_AMOUNT': '₹{:,.2f}',
        'OUTSTANDING_AMOUNT': '₹{:,.2f}',
        'COLLECTION_RATE': '{:.1f}%'
    }), 
    use_container_width=True, 
    hide_index=True
)

st.divider()

# ----------------------------------------
# 4. RECONCILIATION & ANOMALIES
# ----------------------------------------
st.header("Reconciliation (BSNL Audit)")

recon_counts = df['RECONCILIATION_STATUS'].value_counts().reset_index()
recon_counts.columns = ['Status', 'Transaction Count']

st.markdown("### High Confidence Shortfalls (Action Required)")
shortfalls = df[df['RECONCILIATION_STATUS'] == 'POTENTIAL_SHORTFALL'].copy()
if shortfalls.empty:
    st.success("No High-Confidence Shortfalls detected in the selected period!")
else:
    cols_to_show = ['SERVICE_NO', 'COMM_MONTH', 'TRANSACTION_CATEGORY', 'FTTH_FMC', 'REVENUE_SHARE_PERCENT', 'ACTUAL_REVENUE_SHARE', 'EXPECTED_REVENUE_SHARE', 'POTENTIAL_SHORTFALL', 'RULE_APPLIED']
    shortfalls_sorted = shortfalls[cols_to_show].sort_values(by='POTENTIAL_SHORTFALL', ascending=False)
    st.dataframe(shortfalls_sorted.style.format({
        'ACTUAL_REVENUE_SHARE': '₹{:,.2f}', 
        'EXPECTED_REVENUE_SHARE': '₹{:,.2f}', 
        'POTENTIAL_SHORTFALL': '₹{:,.2f}'
    }), use_container_width=True, hide_index=True)

st.markdown("### Data Quality & Review Required")
review_needed = df[df['RECONCILIATION_STATUS'].isin(['REVIEW_REQUIRED', 'UNKNOWN_RULE'])].copy()
if review_needed.empty:
    st.success("No records require manual review.")
else:
    st.warning(f"{len(review_needed)} records were flagged for manual review because the Rule Engine confidence was LOW or UNKNOWN.")
    st.dataframe(review_needed[['SERVICE_NO', 'COMM_MONTH', 'COMM_TYPE', 'RECONCILIATION_STATUS', 'RULE_CONFIDENCE', 'ACTUAL_REVENUE_SHARE']].head(50), use_container_width=True, hide_index=True)
