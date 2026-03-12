#!/usr/bin/env python
"""Quick test to verify all imports and data loading work"""
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

print("Testing imports...")

try:
    import pandas as pd
    print("✓ pandas")
except ImportError as e:
    print(f"✗ pandas: {e}")

try:
    import streamlit as st
    print("✓ streamlit")
except ImportError as e:
    print(f"✗ streamlit: {e}")

try:
    import plotly.express as px
    print("✓ plotly")
except ImportError as e:
    print(f"✗ plotly: {e}")

try:
    import folium
    print("✓ folium")
except ImportError as e:
    print(f"✗ folium: {e}")

try:
    from src.core.scoring import compute_score
    print("✓ src.core.scoring.compute_score")
except ImportError as e:
    print(f"✗ src.core.scoring: {e}")

print("\nTesting data loading...")
DATA_PRO = ROOT / "data" / "processed"

# Test scores
try:
    scores = pd.read_csv(DATA_PRO / "ccaa_opportunity_score.csv", encoding="utf-8-sig")
    print(f"✓ Scores CSV: {len(scores)} rows, columns: {scores.columns.tolist()}")
except Exception as e:
    print(f"✗ Scores CSV: {e}")

# Test profile
try:
    profile = pd.read_csv(DATA_PRO / "ccaa_profile_latest.csv", encoding="utf-8-sig")
    print(f"✓ Profile CSV: {len(profile)} rows")
except Exception as e:
    print(f"✗ Profile CSV: {e}")

# Test market
try:
    market = pd.read_csv(DATA_PRO / "ccaa_market_monthly.csv", encoding="utf-8-sig")
    print(f"✓ Market CSV: {len(market)} rows")
except Exception as e:
    print(f"✗ Market CSV: {e}")

# Test compute_score function
try:
    from src.core.scoring import compute_score
    result = compute_score(scores, w_beds=0.35, w_market=0.45, w_need=0.20)
    print(f"✓ compute_score works: returned {len(result)} rows")
    print(f"  Columns: {result.columns.tolist()}")
except Exception as e:
    print(f"✗ compute_score: {e}")

print("\nAll tests completed!")
