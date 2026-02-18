# TFG Pharma Map

Data pipeline + interactive choropleth map of Spanish Autonomous Communities (CCAA) based on hospital capacity.

## Setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

## Run
python -u src/scripts/01_build_ccaa_summary.py
python -u src/scripts/02_make_ccaa_map.py

Output: outputs/maps/ccaa_map_beds_per_100k.html
