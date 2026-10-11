import pytest
import pandas as pd
import sys
from pathlib import Path

# Ensure src can be imported
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from transform import transform_data

@pytest.fixture
def sample_data():
    """Provides a sample dataframe mirroring BSNL raw data."""
    data = {
        'SERVICE_NO': ['0761-2931200', '0761-2931200', '1111-2222', '3333-4444', '5555-6666', '5555-6667', '0761-2931201'],
        'COMM_MONTH': ['202309', '202309', '202310', '202310', '202311', '202311', '202309'],
        'COMM_TYPE': ['MONTHLY', 'Q4_BU_RETENTION_BONUS', 'MONTHLY', 'CREDIT_NOTE_RECOVERY', 'MONTHLY', 'MONTHLY', 'MONTHLY'],
        'BILL_NBR': ['B1', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6'],
        'FTTH_FMC': [799.0, 0.0, 599.0, 0.0, 999.0, 999.0, 799.0],
        'REVENUE_SHARE_PERCENT': ['50', '50', '30', '-', '50', '50', '50'],
        'REVENUE_SHARE': [367.54, 500.00, 165.32, -100.00, 459.54, 459.54, 367.54],
        'BILL_AMOUNT': [942.82, 0.0, 706.82, 0.0, 1178.82, 1178.82, 942.82],
        'PAID_AMOUNT': [942.82, 0.0, 500.00, 0.0, 1178.82, 1178.82, 942.82],
        'OTF': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        'PAID_DATE': ['2023-10-01', '2023-10-01', '2023-11-01', '2023-11-01', '2023-12-01', '2023-12-01', '2023-10-01']
    }
    return pd.DataFrame(data)

def test_transaction_classification(sample_data):
    df = transform_data(sample_data)
    
    # Row 0: MONTHLY -> PERIODIC_REVENUE
    assert df.loc[0, 'TRANSACTION_CATEGORY'] == 'PERIODIC_REVENUE'
    # Row 1: BONUS -> BONUS_INCENTIVE
    assert df.loc[1, 'TRANSACTION_CATEGORY'] == 'BONUS_INCENTIVE'
    # Row 3: RECOVERY -> RECOVERY
    assert df.loc[3, 'TRANSACTION_CATEGORY'] == 'RECOVERY'

def test_transaction_identity(sample_data):
    df = transform_data(sample_data)
    
    # Rows 0 and 1 have the exact same SERVICE_NO and COMM_MONTH
    # But because one is MONTHLY and one is a BONUS, they should have DIFFERENT TRANSACTION_IDs
    assert df.loc[0, 'TRANSACTION_ID'] != df.loc[1, 'TRANSACTION_ID']
    # This proves the Idempotency bug from Phase 1 is officially fixed.

def test_revenue_rule_engine_standard(sample_data):
    df = transform_data(sample_data)
    
    # Row 0: FMC 799 @ 50%. Math = 799 * 0.50 * 0.92 = 367.54
    assert df.loc[0, 'EXPECTED_REVENUE_SHARE'] == 367.54
    assert df.loc[0, 'RULE_APPLIED'] == 'Standard Telecom Formula (0.92)'
    assert df.loc[0, 'RULE_CONFIDENCE'] == 'HIGH'
    
    # Row 2: FMC 599 @ 30%. Math = 599 * 0.30 * 0.92 = 165.32
    assert df.loc[2, 'EXPECTED_REVENUE_SHARE'] == 165.32

def test_revenue_rule_engine_specials(sample_data):
    df = transform_data(sample_data)
    
    # Row 1 is a Bonus. Expectation should be bypassed.
    assert pd.isna(df.loc[1, 'EXPECTED_REVENUE_SHARE'])
    assert df.loc[1, 'RULE_CONFIDENCE'] == 'UNKNOWN'
    
    # Row 3 is a Recovery. Expectation should be bypassed.
    assert pd.isna(df.loc[3, 'EXPECTED_REVENUE_SHARE'])

def test_reconciliation_analytics(sample_data):
    # Let's create a scenario where BSNL underpays on row 5, but we use FMC 799 (mode established by row 0 as 367.54)
    sample_data.loc[5, 'FTTH_FMC'] = 799.0
    sample_data.loc[5, 'REVENUE_SHARE_PERCENT'] = '50'
    sample_data.loc[5, 'REVENUE_SHARE'] = 300.00  # Expected is 367.54
    df = transform_data(sample_data)
    
    # Variance should be -67.54
    assert df.loc[5, 'REVENUE_SHARE_VARIANCE'] == pytest.approx(-67.54)
    # Shortfall should be 67.54
    assert df.loc[5, 'POTENTIAL_SHORTFALL'] == pytest.approx(67.54)
    # Status should be POTENTIAL_SHORTFALL
    assert df.loc[5, 'RECONCILIATION_STATUS'] == 'POTENTIAL_SHORTFALL'
    
def test_outstanding_amount(sample_data):
    df = transform_data(sample_data)
    
    # Row 2 has Bill 706.82, but Paid 500.00. Outstanding should be 206.82
    assert df.loc[2, 'OUTSTANDING_AMOUNT'] == pytest.approx(206.82)
    
    # Row 1 is a Bonus. Bill 0, Paid 0. Outstanding should be NaN/None for non-billing categories.
    assert pd.isna(df.loc[1, 'OUTSTANDING_AMOUNT'])
