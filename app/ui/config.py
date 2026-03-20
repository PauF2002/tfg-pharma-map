DEFAULT_VIEW = "market_state"
VALID_VIEWS = {"main_page", "overview_map", "market_state", "news", "settings", "profile", "logout"}

DEFAULT_TV_TOP_LINE_TRIM_PX = 1
DEFAULT_TV_CHART_HEIGHT_PERCENT = 90
DEFAULT_TV_EMBED_HEIGHT_PX = 515

DEFAULT_PROFILE_NAME = "Pau Femenia"
DEFAULT_SELECTED_COMPANY = "Pharma Mar (PHM)"

# Preferred: put videos in app/assets/videos and use a relative path from project root.
# Example: "app/assets/videos/kpi_map.mp4"
KPI_INTERACTIVE_MAP_VIDEO_URL = "app/assets/videos/MAP.mp4"
KPI_INTERACTIVE_MAP_VIDEO_POSTER = ""

INVENTORY_VIDEO_URL = "app/assets/videos/ALMACEN.mp4"
INVENTORY_VIDEO_POSTER = ""

HOSPITAL_VIDEO_URL = "app/assets/videos/HOSPITAL.mp4"
HOSPITAL_VIDEO_POSTER = ""

STATISTICS_VIDEO_URL = "app/assets/videos/STATISTIC.mp4"
STATISTICS_VIDEO_POSTER = ""

UI_FONT_OPTIONS = {
    "Moderna": "'Segoe UI', 'Helvetica Neue', sans-serif",
    "Tecnica": "'Trebuchet MS', 'Segoe UI', sans-serif",
    "Serif": "Georgia, 'Times New Roman', serif",
    "Mono": "Consolas, 'Courier New', monospace",
}

UI_ACCENT_OPTIONS = {
    "Cyan": "#06b6d4",
    "Lime": "#84cc16",
    "Coral": "#f97316",
    "Blue": "#3b82f6",
}

SPANISH_PHARMA_COMPANIES = {
    "Pharma Mar (PHM)": {"symbol": "BME:PHM", "subtitle": "Pharma Mar (PHM)"},
    "Almirall (ALM)": {"symbol": "BME:ALM", "subtitle": "Almirall (ALM)"},
    "Laboratorios ROVI (ROVI)": {"symbol": "BME:ROVI", "subtitle": "Laboratorios ROVI (ROVI)"},
    "Faes Farma (FAE)": {"symbol": "BME:FAE", "subtitle": "Faes Farma (FAE)"},
    "Grifols (GRF)": {"symbol": "BME:GRF", "subtitle": "Grifols (GRF)"},
    "Reig Jofre (RJF)": {"symbol": "BME:RJF", "subtitle": "Reig Jofre (RJF)"},
}
