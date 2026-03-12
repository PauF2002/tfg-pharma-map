#!/usr/bin/env python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

output = []

try:
    import pandas as pd
    output.append("✓ pandas")
except ImportError as e:
    output.append(f"✗ pandas: {e}")

try:
    import plotly.express as px
    output.append("✓ plotly")
except ImportError as e:
    output.append(f"✗ plotly: {e}")

try:
    from src.core.scoring import compute_score
    output.append("✓ src.core.scoring")
except ImportError as e:
    output.append(f"✗ src.core.scoring: {e}")

DATA_PRO = ROOT / "data" / "processed"

try:
    scores = pd.read_csv(DATA_PRO / "ccaa_opportunity_score.csv", encoding="utf-8-sig")
    output.append(f"✓ Scores CSV: {len(scores)} rows")
    result = compute_score(scores, w_beds=0.35, w_market=0.45, w_need=0.20)
    output.append(f"✓ compute_score: {len(result)} rows, cols: {list(result.columns)}")
except Exception as e:
    output.append(f"✗ Error: {e}")

with open("test_output.txt", "w") as f:
    f.write("\n".join(output))

print("\n".join(output))
