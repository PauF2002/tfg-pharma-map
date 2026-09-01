Pharma Decision Platform - TFG


Data analytics platform for decision support in the pharmaceutical sector.

This project was developed as a Final Degree Project in Computer Engineering. Its main goal is to design and implement an interactive data analysis platform capable of integrating hospital, demographic, healthcare, market and geographic data to support decision-making in the pharmaceutical sector.

The platform transforms heterogeneous public datasets into interactive maps, rankings, KPIs, hospital target lists, opportunity packs and executive Excel reports.

⸻

Project Overview

<img width="567" height="259" alt="image" src="https://github.com/user-attachments/assets/e287f356-afb9-4bb1-b205-0f3f79d8c580" />



The pharmaceutical sector works with multiple sources of information, such as hospitals, population, health indicators, market data and territorial data. However, these sources are often dispersed, use different formats and are not directly prepared for analysis.

This platform addresses that problem by integrating and processing different datasets in order to provide a territorial and hospital-level view of opportunity.

The solution allows users to:

* Compare Spanish autonomous communities using an opportunity score.
* Analyze different health indicators such as obesity, smoking, Alzheimer, epilepsy and diabetes.
* Explore regional details by autonomous community.
* Visualize hospitals on an interactive map.
* Filter, sort and select hospitals.
* Generate hospital target lists.
* Build an Opportunity Pack.
* Export the results to an executive Excel report.

⸻

Main Features

Interactive Opportunity Map

<img width="514" height="230" alt="image" src="https://github.com/user-attachments/assets/797fb231-d3ff-43a1-8213-8b3f2e0a09bf" />




The platform includes an interactive map where each autonomous community is colored according to its opportunity score. The score combines market data, health indicators and hospital capacity.

Multi-indicator Analysis

The user can switch between different health indicators. When the selected indicator changes, the platform updates the map, legend and ranking dynamically.

Regional Detail View

<img width="514" height="236" alt="image" src="https://github.com/user-attachments/assets/4dd0c6b2-48da-48ca-92e5-7e0430b7e844" />




After selecting an autonomous community, the platform shows a detailed view with regional KPIs, market evolution, hospitals and comparison with the national average.

Hospital Explorer

The hospital table allows users to search, filter and sort hospitals by different criteria such as name, municipality, dependency type or number of beds.

Opportunity Pack

<img width="505" height="228" alt="image" src="https://github.com/user-attachments/assets/c4144558-2fe4-4528-b26c-fbe224c85828" />





Selected hospitals are grouped into an Opportunity Pack. This module summarizes the selected hospitals, calculates average and maximum scores, estimates market potential and classifies hospitals by priority tiers.

Excel Export


<img width="581" height="285" alt="image" src="https://github.com/user-attachments/assets/85990ade-6ce6-43dd-b6e1-4f56a2abe07d" />








<img width="586" height="241" alt="image" src="https://github.com/user-attachments/assets/9dc9bca0-63dd-4287-8058-d4db89ce7a84" />




The platform can export the analysis into an executive Excel report, including a cover page, executive summary, therapeutic opportunity, hospital target list and raw data.

⸻

Opportunity Score

The opportunity score is an exploratory indicator used to prioritize territories. It is not intended to predict sales.

The score combines three normalized dimensions:

Opportunity Score = 100 × (0.45 × market_n + 0.35 × health_indicator_n + 0.20 × beds_n)

Where:

* market_n represents the normalized market component.
* health_indicator_n represents the selected health indicator.
* beds_n represents hospital capacity through beds per 100,000 inhabitants.

The result is a score between 0 and 100 that allows regions to be compared.

⸻

Market Indicator

The market values are expressed as euros per capita. They represent a territorial average, not the direct spending of a specific person.

The value is calculated by dividing the monthly pharmaceutical or healthcare expenditure of an autonomous community by its population.

EUR/cap = monthly pharmaceutical expenditure / population

This allows communities with different population sizes to be compared.

⸻

Data Sources

The project uses public data sources, including:

* Spanish National Hospital Catalogue.
* INE population data.
* INE health indicators.
* Ministry of Finance pharmaceutical and healthcare expenditure data.
* GeoJSON geographic boundaries.
* CARTO / OpenStreetMap map layers.

⸻

Technology Stack

* Python
* Streamlit
* Pandas
* Folium
* Plotly
* GeoJSON
* Excel export libraries
* OpenStreetMap / CARTO base maps

⸻

Repository Structure

app/
  Streamlit application and UI components
src/scripts/
  Data processing scripts
data/raw/
  Original datasets
data/processed/
  Cleaned and processed datasets
docs/assets/
  Images and figures for documentation
README.md
  Project documentation

⸻

Screenshots

Interactive Opportunity Map

Regional Detail View

Opportunity Pack

Excel Export

⸻

Limitations

The platform should be interpreted as an exploratory decision-support tool. It has several limitations:

* The analysis is mainly aggregated at autonomous community level.
* The opportunity score is exploratory and not predictive.
* Market values are used as a proxy.
* Hospital beds are used as an approximation of hospital capacity.
* The platform does not include private internal sales data.
* Real-time automatic data updates are not implemented yet.

⸻

Future Work

Possible future improvements include:

* Adding more health indicators and diseases.
* Increasing territorial granularity.
* Integrating real sales or commercial activity data.
* Automating data updates.
* Validating the score weights with domain experts.
* Adding authentication and user roles.
* Expanding the platform to other sectors.

⸻

Author

Pau Femenia Mahiques
Final Degree Project - Computer Engineering
University of Castilla-La Mancha

⸻

Disclaimer

This platform is not a medical decision-making system and does not provide clinical recommendations. It is an exploratory data analysis tool designed to support strategic and territorial decision-making.
