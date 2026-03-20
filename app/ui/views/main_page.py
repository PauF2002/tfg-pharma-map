import streamlit as st
from base64 import b64encode
from pathlib import Path

from ..config import (
    HOSPITAL_VIDEO_POSTER,
    HOSPITAL_VIDEO_URL,
    INVENTORY_VIDEO_POSTER,
    INVENTORY_VIDEO_URL,
    KPI_INTERACTIVE_MAP_VIDEO_POSTER,
    KPI_INTERACTIVE_MAP_VIDEO_URL,
    STATISTICS_VIDEO_POSTER,
    STATISTICS_VIDEO_URL,
)


@st.cache_data
def load_video_as_base64(path_or_url: str) -> str:
    """Load and cache video as base64. Only done once, then served from cache."""
    if not path_or_url:
        return ""

    lowered = path_or_url.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return path_or_url

    project_root = Path(__file__).resolve().parents[3]
    media_path = (project_root / path_or_url).resolve()
    if not media_path.exists() or not media_path.is_file():
        return ""

    ext = media_path.suffix.lower()
    mime_map = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".ogg": "video/ogg",
        ".mov": "video/quicktime",
        ".m4v": "video/mp4",
    }
    mime = mime_map.get(ext, "video/mp4")
    
    encoded = b64encode(media_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


@st.cache_data
def load_image_as_base64(path_or_url: str) -> str:
    """Load and cache image as base64."""
    if not path_or_url:
        return ""

    lowered = path_or_url.lower()
    if lowered.startswith("http://") or lowered.startswith("https://") or lowered.startswith("data:"):
        return path_or_url

    project_root = Path(__file__).resolve().parents[3]
    media_path = (project_root / path_or_url).resolve()
    if not media_path.exists() or not media_path.is_file():
        return ""

    ext = media_path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    mime = mime_map.get(ext, "image/png")
    
    encoded = b64encode(media_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class MainPageView:


    def render(self) -> None:
        video_src = load_video_as_base64(KPI_INTERACTIVE_MAP_VIDEO_URL)
        poster_src = load_image_as_base64(KPI_INTERACTIVE_MAP_VIDEO_POSTER)
        inventory_video_src = load_video_as_base64(INVENTORY_VIDEO_URL)
        inventory_poster_src = load_image_as_base64(INVENTORY_VIDEO_POSTER)
        hospital_video_src = load_video_as_base64(HOSPITAL_VIDEO_URL)
        hospital_poster_src = load_image_as_base64(HOSPITAL_VIDEO_POSTER)
        statistics_video_src = load_video_as_base64(STATISTICS_VIDEO_URL)
        statistics_poster_src = load_image_as_base64(STATISTICS_VIDEO_POSTER)

        kpi_video_html = (
            '<div class="mainpage-video-wrap">'
            '<video class="mainpage-video" autoplay muted loop playsinline preload="metadata" '
            f'src="{video_src}" '
            + (f'poster="{poster_src}" ' if poster_src else "")
            + '></video>'
            '<div class="mainpage-video-overlay">KPI map preview</div>'
            '</div>'
            if video_src
            else '<div class="mainpage-video-wrap empty"><div class="mainpage-video-overlay">Add your video in app/assets/videos and set KPI_INTERACTIVE_MAP_VIDEO_URL</div></div>'
        )

        inventory_video_html = (
            '<div class="mainpage-video-wrap">'
            '<video class="mainpage-video" autoplay muted loop playsinline preload="metadata" '
            f'src="{inventory_video_src}" '
            + (f'poster="{inventory_poster_src}" ' if inventory_poster_src else "")
            + '></video>'
            '<div class="mainpage-video-overlay">Inventory preview</div>'
            '</div>'
            if inventory_video_src
            else '<div class="mainpage-video-wrap empty"><div class="mainpage-video-overlay">Set INVENTORY_VIDEO_URL</div></div>'
        )

        hospital_video_html = (
            '<div class="mainpage-video-wrap">'
            '<video class="mainpage-video object-top" autoplay muted loop playsinline preload="metadata" '
            f'src="{hospital_video_src}" '
            + (f'poster="{hospital_poster_src}" ' if hospital_poster_src else "")
            + '></video>'
            '<div class="mainpage-video-overlay">Hospital preview</div>'
            '</div>'
            if hospital_video_src
            else '<div class="mainpage-video-wrap empty"><div class="mainpage-video-overlay">Set HOSPITAL_VIDEO_URL</div></div>'
        )

        statistics_video_html = (
            '<div class="mainpage-video-wrap">'
            '<video class="mainpage-video" autoplay muted loop playsinline preload="metadata" '
            f'src="{statistics_video_src}" '
            + (f'poster="{statistics_poster_src}" ' if statistics_poster_src else "")
            + '></video>'
            '<div class="mainpage-video-overlay">Statistics preview</div>'
            '</div>'
            if statistics_video_src
            else '<div class="mainpage-video-wrap empty"><div class="mainpage-video-overlay">Set STATISTICS_VIDEO_URL</div></div>'
        )

        main_page_html = (
            '<div class="main-wrap">'
            '<div class="main-card">'
            '<div class="main-kicker">PharmaTFG Platform</div>'
            '<div class="main-title">Main Page</div>'
            '<div class="main-text">Centro de acceso rapido a mapas, hospitales, inventario y reporting.</div>'
            '<div class="mainpage-grid">'
            '<div class="mainpage-card mainpage-card-kpi">'
            '<div class="mainpage-card-top">'
            '<div>'
            '<div class="mainpage-card-kicker">Mapa</div>'
            '<div class="mainpage-card-title">KPI Interactive Map</div>'
            '</div>'
            '<div class="mainpage-card-icon">🗺️</div>'
            '</div>'
            f'{kpi_video_html}'
            '</div>'
            '<div class="mainpage-card mainpage-card-compact">'
            '<div class="mainpage-card-top">'
            '<div>'
            '<div class="mainpage-card-kicker">Red asistencial</div>'
            '<div class="mainpage-card-title">Hospitals</div>'
            '</div>'
            '<div class="mainpage-card-icon">🏥</div>'
            '</div>'
            f'{hospital_video_html}'
            '</div>'
            '<div class="mainpage-card mainpage-card-compact">'
            '<div class="mainpage-card-top">'
            '<div>'
            '<div class="mainpage-card-kicker">Logistica</div>'
            '<div class="mainpage-card-title">Inventory</div>'
            '</div>'
            '<div class="mainpage-card-icon">📦</div>'
            '</div>'
            f'{inventory_video_html}'
            '</div>'
            '<div class="mainpage-card mainpage-card-compact">'
            '<div class="mainpage-card-top">'
            '<div>'
            '<div class="mainpage-card-kicker">Analitica</div>'
            '<div class="mainpage-card-title">Statistics / Reports</div>'
            '</div>'
            '<div class="mainpage-card-icon">📈</div>'
            '</div>'
            f'{statistics_video_html}'
            '</div>'
            '</div>'
            '</div>'
            '</div>'
        )
        st.markdown(main_page_html, unsafe_allow_html=True)
