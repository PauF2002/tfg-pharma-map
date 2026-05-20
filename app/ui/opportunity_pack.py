from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
import unicodedata
from urllib.request import urlopen

import pandas as pd


@dataclass
class OpportunityPackPayload:
    context: dict[str, str | int]
    kpis: dict[str, float | int]
    executive_summary: str
    therapeutic_description: str
    therapeutic_table: pd.DataFrame
    target_hospitals: pd.DataFrame
    raw_data: pd.DataFrame
    tier_distribution: pd.DataFrame
    top_score_chart: pd.DataFrame


def _norm_text(value: object) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.replace("-", " ").split())


def _canonical_ccaa_norm(value: object) -> str:
    base = _norm_text(value)
    if not base:
        return ""

    # Remove leading numeric code prefixes from INE labels (e.g. "01 Andalucía").
    parts = base.split(" ", 1)
    if parts and parts[0].isdigit() and len(parts) > 1:
        base = parts[1]

    aliases = {
        "asturias principado de": "principado de asturias",
        "balears illes": "illes balears",
        "castilla la mancha": "castilla-la mancha",
        "cataluna": "cataluña",
        "comunitat valenciana": "comunidad valenciana",
        "madrid comunidad de": "comunidad de madrid",
        "murcia region de": "region de murcia",
        "navarra comunidad foral de": "c. foral de navarra",
        "pais vasco": "país vasco",
    }
    return aliases.get(base, base)


def _resolve_ccaa_flag_path(project_root: Path, ccaa: str) -> Path | None:
    flags_dir = project_root / "app" / "assets" / "fotos"
    local_flag_files = {
        "andalucia": "Flag_of_Andalucía.svg.png",
        "aragon": "Flag_of_Aragon.svg",
        "ppdo. de asturias": "Flag_of_Asturias.svg",
        "principado de asturias": "Flag_of_Asturias.svg",
        "illes balears": "Flag_of_the_Balearic_Islands.svg.png",
        "canarias": "CANARIAS.jpg",
        "cantabria": "Flag_of_Cantabria.svg.png",
        "castilla y leon": "Flag_of_Castile_and_León.svg.png",
        "castilla la mancha": "Flag_of_Castile-La_Mancha.svg.png",
        "castilla-la mancha": "Flag_of_Castile-La_Mancha.svg.png",
        "comunidad valenciana": "Flag_of_the_Valencian_Community_(2x3).svg",
        "extremadura": "Flag_of_Extremadura,_Spain_(with_coat_of_arms).svg.png",
        "galicia": "Flag_of_Galicia.svg",
        "madrid": "Flag_of_the_Community_of_Madrid.svg",
        "comunidad de madrid": "Flag_of_the_Community_of_Madrid.svg",
        "region de murcia": "Flag_of_the_Region_of_Murcia.svg.png",
        "c. foral de navarra": "Bandera_de_Navarra.svg.png",
        "comunidad foral de navarra": "Bandera_de_Navarra.svg.png",
        "pais vasco": "Flag_of_the_Basque_Country.svg",
        "la rioja": "Bandera_Republicana_de_La_Rioja.png",
        "ceuta": "Flag_of_Ceuta.svg",
        "melilla": "Flag_of_Melilla.svg.png",
        "cataluna": "Flag_of_Catalonia.svg",
        "cataluña": "Flag_of_Catalonia.svg",
    }

    key = _canonical_ccaa_norm(ccaa)
    filename = local_flag_files.get(key)
    if not filename:
        return None
    path = flags_dir / filename
    return path if path.exists() else None


def _resolve_ccaa_flag_url(ccaa: str) -> str | None:
    # PNG fallbacks for flags that only exist locally as SVG files.
    by_ccaa = {
        "comunidad valenciana": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Flag_of_the_Valencian_Community_%282x3%29.svg/320px-Flag_of_the_Valencian_Community_%282x3%29.svg.png",
        "aragon": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Flag_of_Aragon.svg/320px-Flag_of_Aragon.svg.png",
        "principado de asturias": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Flag_of_Asturias.svg/320px-Flag_of_Asturias.svg.png",
        "galicia": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Flag_of_Galicia.svg/320px-Flag_of_Galicia.svg.png",
        "comunidad de madrid": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Flag_of_the_Community_of_Madrid.svg/320px-Flag_of_the_Community_of_Madrid.svg.png",
        "pais vasco": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2d/Flag_of_the_Basque_Country.svg/320px-Flag_of_the_Basque_Country.svg.png",
        "ceuta": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Flag_of_Ceuta.svg/320px-Flag_of_Ceuta.svg.png",
        "cataluña": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Flag_of_Catalonia.svg/320px-Flag_of_Catalonia.svg.png",
    }
    return by_ccaa.get(_canonical_ccaa_norm(ccaa))


def _resolve_disease_image_path(project_root: Path, disease: str) -> Path | None:
    photos_dir = project_root / "app" / "assets" / "fotos"
    disease_dir = photos_dir / "diseases"
    norm = _norm_text(disease).replace(" ", "_")

    candidate_dirs = [photos_dir, disease_dir]
    candidate_names = [
        f"disease_{norm}",
        f"icon_{norm}",
        f"{norm}_icon",
        norm,
    ]
    extensions = [".png", ".jpg", ".jpeg", ".webp"]

    for folder in candidate_dirs:
        for base_name in candidate_names:
            for ext in extensions:
                path = folder / f"{base_name}{ext}"
                if path.exists():
                    return path
    return None


def _insert_sheet_image(
    sheet,
    cell: str,
    image_path: Path,
    *,
    x_scale: float,
    y_scale: float,
    x_offset: int = 0,
    y_offset: int = 0,
    target_width_px: int | None = None,
    target_height_px: int | None = None,
    keep_aspect: bool = True,
) -> bool:
    if not image_path.exists():
        return False

    suffix = image_path.suffix.lower()
    raster_ext = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}

    if suffix in raster_ext:
        try:
            image_bytes = image_path.read_bytes()
        except OSError:
            return False
    elif suffix == ".svg":
        try:
            import cairosvg  # type: ignore

            image_bytes = cairosvg.svg2png(url=str(image_path))
        except Exception:
            return False
    else:
        return False

    scale_x = x_scale
    scale_y = y_scale
    if target_width_px and target_height_px:
        try:
            import struct

            width_px = 0
            height_px = 0
            if image_bytes[:8] == b"\x89PNG\r\n\x1a\n" and len(image_bytes) >= 24:
                width_px, height_px = struct.unpack(">II", image_bytes[16:24])
            elif image_bytes[:2] == b"\xff\xd8":
                idx = 2
                while idx + 9 < len(image_bytes):
                    if image_bytes[idx] != 0xFF:
                        idx += 1
                        continue
                    marker = image_bytes[idx + 1]
                    if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        seg_len = struct.unpack(">H", image_bytes[idx + 2:idx + 4])[0]
                        if idx + 2 + seg_len <= len(image_bytes):
                            height_px = struct.unpack(">H", image_bytes[idx + 5:idx + 7])[0]
                            width_px = struct.unpack(">H", image_bytes[idx + 7:idx + 9])[0]
                        break
                    if marker in (0xD8, 0xD9):
                        idx += 2
                        continue
                    seg_len = struct.unpack(">H", image_bytes[idx + 2:idx + 4])[0]
                    idx += 2 + seg_len

            if width_px > 0 and height_px > 0:
                target_sx = target_width_px / float(width_px)
                target_sy = target_height_px / float(height_px)
                if keep_aspect:
                    factor = min(target_sx, target_sy)
                    scale_x = factor
                    scale_y = factor
                else:
                    scale_x = target_sx
                    scale_y = target_sy
        except Exception:
            pass

    image_stream = BytesIO(image_bytes)
    try:
        sheet.insert_image(
            cell,
            image_path.name,
            {
                "image_data": image_stream,
                "x_scale": scale_x,
                "y_scale": scale_y,
                "x_offset": x_offset,
                "y_offset": y_offset,
                "object_position": 2,
            },
        )
    except ValueError:
        return False
    return True


def _insert_sheet_image_from_url(
    sheet,
    cell: str,
    image_url: str,
    *,
    x_scale: float,
    y_scale: float,
    x_offset: int = 0,
    y_offset: int = 0,
    target_width_px: int | None = None,
    target_height_px: int | None = None,
    keep_aspect: bool = True,
) -> bool:
    try:
        with urlopen(image_url, timeout=6) as response:
            image_bytes = response.read()
    except Exception:
        return False

    if not image_bytes:
        return False

    scale_x = x_scale
    scale_y = y_scale
    if target_width_px and target_height_px:
        try:
            import struct

            width_px = 0
            height_px = 0
            if image_bytes[:8] == b"\x89PNG\r\n\x1a\n" and len(image_bytes) >= 24:
                width_px, height_px = struct.unpack(">II", image_bytes[16:24])
            elif image_bytes[:2] == b"\xff\xd8":
                idx = 2
                while idx + 9 < len(image_bytes):
                    if image_bytes[idx] != 0xFF:
                        idx += 1
                        continue
                    marker = image_bytes[idx + 1]
                    if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        seg_len = struct.unpack(">H", image_bytes[idx + 2:idx + 4])[0]
                        if idx + 2 + seg_len <= len(image_bytes):
                            height_px = struct.unpack(">H", image_bytes[idx + 5:idx + 7])[0]
                            width_px = struct.unpack(">H", image_bytes[idx + 7:idx + 9])[0]
                        break
                    if marker in (0xD8, 0xD9):
                        idx += 2
                        continue
                    seg_len = struct.unpack(">H", image_bytes[idx + 2:idx + 4])[0]
                    idx += 2 + seg_len

            if width_px > 0 and height_px > 0:
                target_sx = target_width_px / float(width_px)
                target_sy = target_height_px / float(height_px)
                if keep_aspect:
                    factor = min(target_sx, target_sy)
                    scale_x = factor
                    scale_y = factor
                else:
                    scale_x = target_sx
                    scale_y = target_sy
        except Exception:
            pass

    try:
        sheet.insert_image(
            cell,
            "remote_flag.png",
            {
                "image_data": BytesIO(image_bytes),
                "x_scale": scale_x,
                "y_scale": scale_y,
                "x_offset": x_offset,
                "y_offset": y_offset,
                "object_position": 2,
            },
        )
    except ValueError:
        return False
    return True


def _load_market_trend_for_ccaa(project_root: Path, ccaa: str, max_points: int = 24) -> pd.DataFrame:
    market_path = project_root / "data" / "processed" / "ccaa_market_monthly.csv"
    market_df = _safe_read_csv(market_path)
    if market_df.empty:
        return pd.DataFrame(columns=["period", "value"])

    market_df["ccaa_norm"] = market_df.get("CCAA", "").map(_canonical_ccaa_norm)
    selected_norm = _canonical_ccaa_norm(ccaa)
    scoped = market_df[market_df["ccaa_norm"] == selected_norm].copy()
    if scoped.empty:
        return pd.DataFrame(columns=["period", "value"])

    scoped["period"] = scoped.get("year_month", "").astype(str)
    scoped["value"] = pd.to_numeric(scoped.get("market_monthly_eur"), errors="coerce")
    if scoped["value"].isna().all():
        scoped["value"] = pd.to_numeric(scoped.get("market_monthly_eur_per_capita"), errors="coerce")
    scoped = scoped.dropna(subset=["value"])
    scoped = scoped[scoped["period"].str.len() > 0]
    scoped = scoped.sort_values("period").tail(max_points)
    return scoped[["period", "value"]].copy()


def _load_disease_trend_for_ccaa(project_root: Path, ccaa: str, disease: str) -> pd.DataFrame:
    disease_norm = _norm_text(disease)
    selected_norm = _canonical_ccaa_norm(ccaa)

    if any(term in disease_norm for term in ("obesity", "obesidad")):
        obesity_path = project_root / "data" / "raw" / "ine_obesity_ccaa.csv"
        obesity_df = _safe_read_csv(obesity_path)
        if obesity_df.empty:
            return pd.DataFrame(columns=["period", "value"])

        # Source file is tab-delimited in a single quoted column; split if needed.
        if obesity_df.shape[1] == 1:
            col = obesity_df.columns[0]
            expanded = obesity_df[col].astype(str).str.split("\t", expand=True)
            expanded.columns = ["Comunidad autónoma", "Masa corporal", "Periodo", "Total"]
            obesity_df = expanded

        ccaa_col = "Comunidad autónoma" if "Comunidad autónoma" in obesity_df.columns else obesity_df.columns[0]
        mass_col = "Masa corporal" if "Masa corporal" in obesity_df.columns else obesity_df.columns[1]
        period_col = "Periodo" if "Periodo" in obesity_df.columns else obesity_df.columns[2]
        total_col = "Total" if "Total" in obesity_df.columns else obesity_df.columns[3]

        scoped = obesity_df.copy()
        scoped["ccaa_norm"] = scoped[ccaa_col].map(_canonical_ccaa_norm)
        scoped["mass_norm"] = scoped[mass_col].map(_norm_text)
        scoped["period"] = pd.to_numeric(scoped[period_col], errors="coerce")
        scoped["value"] = pd.to_numeric(scoped[total_col].astype(str).str.replace(",", ".", regex=False), errors="coerce")

        scoped = scoped[
            (scoped["ccaa_norm"] == selected_norm)
            & (scoped["mass_norm"].str.contains("obesidad", na=False))
        ].copy()

        scoped = scoped.dropna(subset=["period", "value"])
        if scoped.empty:
            return pd.DataFrame(columns=["period", "value"])

        scoped["period"] = scoped["period"].astype(int).astype(str)
        scoped = scoped.sort_values("period")
        return scoped[["period", "value"]].copy()

    if any(term in disease_norm for term in ("smoking", "smoke", "tabaquismo", "tabaco", "fumador", "fumadores")):
        smoking_path = project_root / "data" / "processed" / "ccaa_smoking.csv"
        smoking_df = _safe_read_csv(smoking_path)
        if smoking_df.empty:
            smoking_path = project_root / "data" / "raw" / "ine_smoking_ccaa.csv"
            smoking_df = _safe_read_csv(smoking_path, sep=";")

        if smoking_df.empty:
            return pd.DataFrame(columns=["period", "value"])

        if "smoking_pct" in smoking_df.columns:
            scoped = smoking_df.copy()
            ccaa_col = "CCAA" if "CCAA" in scoped.columns else scoped.columns[0]
            period_col = "period" if "period" in scoped.columns else None
            value_col = "smoking_pct"
            scoped["ccaa_norm"] = scoped[ccaa_col].map(_canonical_ccaa_norm)
            scoped["value"] = pd.to_numeric(scoped[value_col], errors="coerce")
            if period_col:
                scoped["period"] = scoped[period_col].astype(str)
            else:
                scoped["period"] = "latest"
            scoped = scoped[(scoped["ccaa_norm"] == selected_norm)].copy()
            scoped = scoped.dropna(subset=["value"])
            if scoped.empty:
                return pd.DataFrame(columns=["period", "value"])
            return scoped[["period", "value"]].copy()

        if smoking_df.shape[1] == 1:
            col = smoking_df.columns[0]
            expanded = smoking_df[col].astype(str).str.split("\t", expand=True)
            smoking_df = expanded

        ccaa_col = "Comunidades Autónomas" if "Comunidades Autónomas" in smoking_df.columns else smoking_df.columns[0]
        status_col = "Consumo de tabaco" if "Consumo de tabaco" in smoking_df.columns else smoking_df.columns[1]
        value_col = "Total" if "Total" in smoking_df.columns else smoking_df.columns[2]

        scoped = smoking_df.copy()
        scoped["ccaa_norm"] = scoped[ccaa_col].map(_canonical_ccaa_norm)
        scoped["status_norm"] = scoped[status_col].map(_norm_text)
        scoped["value"] = pd.to_numeric(
            scoped[value_col].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
            errors="coerce",
        )

        scoped = scoped[
            (scoped["ccaa_norm"] == selected_norm)
            & (scoped["status_norm"].str.contains("fuma diariamente", na=False))
        ].copy()
        scoped = scoped.dropna(subset=["value"])
        if scoped.empty:
            return pd.DataFrame(columns=["period", "value"])

        scoped["period"] = "latest"
        return scoped[["period", "value"]].copy()

    return pd.DataFrame(columns=["period", "value"])


def _normalize_hospital_id(value: object) -> str:
    return str(value or "").strip().replace(",", "").removesuffix(".0")


def _safe_read_csv(path: Path, sep: str = ",") -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding, sep=sep, low_memory=False)
        except pd.errors.ParserError:
            try:
                return pd.read_csv(
                    path,
                    encoding=encoding,
                    sep=sep,
                    engine="python",
                    on_bad_lines="skip",
                )
            except Exception:
                continue
        except UnicodeDecodeError:
            continue
        except Exception:
            continue
    return pd.DataFrame()


def _empty_target_table() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "ranking",
            "hospital_id",
            "hospital",
            "ccaa",
            "ccaa_norm",
            "municipio",
            "provincia",
            "beds",
            "score",
            "tier",
            "inclusion_reason",
            "recommended_action",
            "dependency",
            "center_class",
            "market_potential_eur",
        ]
    )


def _load_hospital_catalog(project_root: Path) -> pd.DataFrame:
    hospitals_path = project_root / "data" / "raw" / "CNH_2024_geocoded.csv"
    hospitals_df = _safe_read_csv(hospitals_path)
    if hospitals_df.empty:
        return _empty_target_table()

    # Unify hospital ID source with CCAA detail selection logic (CCN or CODCNH).
    if "CCN" not in hospitals_df.columns and "CODCNH" in hospitals_df.columns:
        hospitals_df["CCN"] = hospitals_df["CODCNH"]
    elif "CCN" in hospitals_df.columns and "CODCNH" in hospitals_df.columns:
        hospitals_df["CCN"] = hospitals_df["CCN"].where(
            hospitals_df["CCN"].notna() & (hospitals_df["CCN"].astype(str).str.strip() != ""),
            hospitals_df["CODCNH"],
        )

    rename_map = {
        "CCN": "hospital_id",
        "Nombre Centro": "hospital",
        "CCAA": "ccaa",
        "CAMAS": "beds",
        "Dependencia Funcional": "dependency",
        "Clase de Centro": "center_class",
        "Municipio": "municipio",
        "Provincia": "provincia",
    }
    for old_name in rename_map:
        if old_name not in hospitals_df.columns:
            hospitals_df[old_name] = ""

    hospitals_df = hospitals_df.rename(columns=rename_map)
    hospitals_df["hospital_id"] = hospitals_df["hospital_id"].map(_normalize_hospital_id)
    hospitals_df["hospital"] = hospitals_df["hospital"].fillna("").astype(str).str.strip()
    hospitals_df["ccaa"] = hospitals_df["ccaa"].fillna("").astype(str).str.strip()
    hospitals_df["municipio"] = hospitals_df["municipio"].fillna("").astype(str).str.strip()
    hospitals_df["provincia"] = hospitals_df["provincia"].fillna("").astype(str).str.strip()
    hospitals_df["dependency"] = hospitals_df["dependency"].fillna("").astype(str).str.strip()
    hospitals_df["center_class"] = hospitals_df["center_class"].fillna("").astype(str).str.strip()
    hospitals_df["beds"] = pd.to_numeric(hospitals_df["beds"], errors="coerce").fillna(0)

    hospitals_df = hospitals_df[hospitals_df["hospital"].str.len() > 0].copy()
    hospitals_df = hospitals_df[hospitals_df["ccaa"].str.len() > 0].copy()
    hospitals_df["ccaa_norm"] = hospitals_df["ccaa"].map(_norm_text)
    hospitals_df["hospital_id"] = hospitals_df["hospital_id"].where(
        hospitals_df["hospital_id"].str.len() > 0,
        hospitals_df.index.astype(str),
    )
    return hospitals_df


def _load_ccaa_metrics(project_root: Path, disease: str) -> pd.DataFrame:
    disease_norm = _norm_text(disease)
    if any(term in disease_norm for term in ("smoking", "smoke", "tabaquismo", "tabaco", "fumador", "fumadores")):
        score_path = project_root / "data" / "processed" / "ccaa_smoking_opportunity_score.csv"
    else:
        score_path = project_root / "data" / "processed" / "ccaa_opportunity_score.csv"
    score_df = _safe_read_csv(score_path)
    if score_df.empty:
        return pd.DataFrame(columns=["CCAA", "ccaa_norm", "opportunity_score", "market_12m_avg_eur_per_capita", "market_12m_sum_eur"])

    for col in ("opportunity_score", "market_12m_avg_eur_per_capita", "market_12m_sum_eur"):
        score_df[col] = pd.to_numeric(score_df.get(col), errors="coerce").fillna(0)
    score_df["ccaa_norm"] = score_df["CCAA"].map(_norm_text)
    return score_df


def classify_hospital_tiers(scores: pd.Series) -> pd.Series:
    def classify(value: float) -> str:
        if value >= 80:
            return "Tier 1"
        if value >= 65:
            return "Tier 2"
        if value >= 50:
            return "Tier 3"
        return "Tier 4"

    return scores.fillna(0).map(classify)


def _size_factor_from_beds(beds: float) -> float:
    value = float(beds or 0)
    if value >= 900:
        return 1.25
    if value >= 600:
        return 1.15
    if value >= 300:
        return 1.05
    if value >= 100:
        return 0.95
    return 0.85


def _center_type_factor(dependency: object, center_class: object) -> float:
    dep = _norm_text(dependency)
    cls = _norm_text(center_class)

    if "privad" in dep:
        base = 0.92
    elif "servicios e institutos de salud" in dep:
        base = 1.10
    elif "otros centros o establecimientos publicos" in dep:
        base = 1.03
    else:
        base = 1.00

    if "hospitales generales" in cls:
        adjust = 0.05
    elif "hospitales especializados" in cls:
        adjust = 0.02
    elif "media y larga estancia" in cls:
        adjust = -0.04
    elif "salud mental" in cls:
        adjust = -0.06
    else:
        adjust = 0.00

    return float(min(1.35, max(0.75, base + adjust)))


def generate_executive_summary(context: dict[str, str | int], kpis: dict[str, float | int]) -> str:
    ccaa = context.get("ccaa", "CCAA no definida")
    disease = context.get("disease", "Disease no definida")
    hospitals = int(kpis.get("target_hospitals", 0) or 0)
    beds = int(kpis.get("total_beds", 0) or 0)
    avg_score = float(kpis.get("avg_score", 0) or 0)
    potential = float(kpis.get("market_potential", 0) or 0)
    tier_1 = int(kpis.get("tier_1_hospitals", 0) or 0)

    return (
        f"Para {ccaa} y el foco terapéutico en {disease}, se priorizan {hospitals} hospitales "
        f"con una capacidad conjunta de {beds:,} camas. La oportunidad media estimada se sitúa en "
        f"{avg_score:.1f}/100, con {tier_1} centros Tier 1. El potencial comercial agregado anualizado "
        f"se estima en {potential:,.0f} EUR, recomendando activar primero cuentas Tier 1 y Tier 2 con "
        "planes de acceso clínico y acuerdos de valor orientados a resultados."
    )


def _build_therapeutic_block(disease: str) -> tuple[str, pd.DataFrame]:
    disease_key = _norm_text(disease)
    definitions: dict[str, tuple[str, list[dict[str, str]]]] = {
        "obesity": (
            "Oportunidad centrada en manejo integral de obesidad con foco en reducción de riesgo cardiometabólico y adherencia.",
            [
                {"molecule": "Semaglutida", "therapy_line": "2L", "potential_medication": "GLP-1 RA", "commercial_note": "Alta tracción en hospitales con endocrino"},
                {"molecule": "Tirzepatida", "therapy_line": "2L/3L", "potential_medication": "GIP/GLP-1", "commercial_note": "Cuenta estratégica para acceso temprano"},
                {"molecule": "Liraglutida", "therapy_line": "1L/2L", "potential_medication": "GLP-1 RA", "commercial_note": "Defensa en centros con protocolos activos"},
            ],
        ),
        "smoking": (
            "Oportunidad centrada en cesación tabáquica y reducción del riesgo cardio-respiratorio en población fumadora activa.",
            [
                {"molecule": "Vareniclina", "therapy_line": "1L", "potential_medication": "Cese tabáquico", "commercial_note": "Primera elección en programas estructurados"},
                {"molecule": "Bupropion", "therapy_line": "1L/2L", "potential_medication": "Cese tabáquico", "commercial_note": "Opción útil en pacientes seleccionados"},
                {"molecule": "Sustitución nicotínica", "therapy_line": "1L", "potential_medication": "NRT", "commercial_note": "Alta utilidad en atención primaria y hospital"},
            ],
        ),
        "diabetes": (
            "Oportunidad de optimización de control glucémico con reducción de eventos macro y microvasculares en población compleja.",
            [
                {"molecule": "Dapagliflozina", "therapy_line": "1L/2L", "potential_medication": "SGLT2", "commercial_note": "Sinergia con cardio-nefro"},
                {"molecule": "Empagliflozina", "therapy_line": "1L/2L", "potential_medication": "SGLT2", "commercial_note": "Tracción en hospitales de alta complejidad"},
                {"molecule": "Semaglutida", "therapy_line": "2L", "potential_medication": "GLP-1 RA", "commercial_note": "Refuerzo en unidades de diabetes"},
            ],
        ),
        "cardiovascular": (
            "Oportunidad para reducir carga de eventos cardiovasculares en hospitales con alto volumen de pacientes crónicos.",
            [
                {"molecule": "Inclisirán", "therapy_line": "2L", "potential_medication": "siRNA LDL-C", "commercial_note": "Atractivo en prevención secundaria"},
                {"molecule": "Sacubitrilo/Valsartán", "therapy_line": "1L/2L", "potential_medication": "ARNI", "commercial_note": "Consolidar en protocolos IC"},
                {"molecule": "Rivaroxabán", "therapy_line": "1L", "potential_medication": "DOAC", "commercial_note": "Mantenimiento y expansión"},
            ],
        ),
    }

    description, rows = definitions.get(
        disease_key,
        (
            "No hay mapeo terapéutico específico para esta disease. Se muestran placeholders para preparar discusión ejecutiva.",
            [
                {"molecule": "Molecule A", "therapy_line": "1L", "potential_medication": "Therapy Class A", "commercial_note": "Placeholder"},
                {"molecule": "Molecule B", "therapy_line": "2L", "potential_medication": "Therapy Class B", "commercial_note": "Placeholder"},
                {"molecule": "Molecule C", "therapy_line": "3L", "potential_medication": "Therapy Class C", "commercial_note": "Placeholder"},
            ],
        ),
    )

    return description, pd.DataFrame(rows)


def prepare_opportunity_pack_data(
    project_root: Path,
    ccaa: str,
    disease: str,
    hospital_ids: list[str],
    hospital_names: list[str] | None,
    snapshot_date: str,
) -> OpportunityPackPayload:
    hospitals_df = _load_hospital_catalog(project_root)
    score_df = _load_ccaa_metrics(project_root, disease)

    if "ccaa_norm" not in hospitals_df.columns:
        if "ccaa" in hospitals_df.columns:
            hospitals_df["ccaa_norm"] = hospitals_df["ccaa"].map(_norm_text)
        else:
            hospitals_df["ccaa_norm"] = ""

    if "ccaa_norm" not in score_df.columns:
        if "CCAA" in score_df.columns:
            score_df["ccaa_norm"] = score_df["CCAA"].map(_norm_text)
        else:
            score_df["ccaa_norm"] = ""

    ccaa_norm = _norm_text(ccaa)
    ccaa_subset = hospitals_df[hospitals_df["ccaa_norm"] == ccaa_norm].copy()
    if ccaa_subset.empty:
        ccaa_subset = hospitals_df.copy()

    selected_ids = [_normalize_hospital_id(item) for item in hospital_ids if _normalize_hospital_id(item)]
    selected_name_norms = [_norm_text(item) for item in (hospital_names or []) if str(item or "").strip()]
    if selected_ids:
        selected_df = ccaa_subset[ccaa_subset["hospital_id"].isin(selected_ids)].copy()
    else:
        selected_df = pd.DataFrame()

    if selected_df.empty and selected_name_norms:
        selected_df = ccaa_subset[ccaa_subset["hospital"].map(_norm_text).isin(selected_name_norms)].copy()

    if selected_df.empty and selected_name_norms:
        # Keep user-selected hospitals visible even when source catalog load/match fails.
        selected_df = pd.DataFrame(
            {
                "hospital_id": [f"name_{idx+1}" for idx, _ in enumerate(selected_name_norms)],
                "hospital": [name for name in (hospital_names or []) if str(name or "").strip()],
                "ccaa": [ccaa] * len(selected_name_norms),
                "municipio": [""] * len(selected_name_norms),
                "provincia": [""] * len(selected_name_norms),
                "beds": [0] * len(selected_name_norms),
                "dependency": [""] * len(selected_name_norms),
                "center_class": [""] * len(selected_name_norms),
                "ccaa_norm": [ccaa_norm] * len(selected_name_norms),
            }
        )

    if selected_df.empty:
        selected_df = ccaa_subset.sort_values("beds", ascending=False).head(15).copy()

    if selected_df.empty:
        selected_df = _empty_target_table()
        selected_df["ccaa"] = ccaa

    # If selection arrived without rich fields (e.g., name fallback), complete beds and metadata from catalog.
    if not selected_df.empty and not hospitals_df.empty:
        catalog_df = hospitals_df.copy()
        if "hospital" not in catalog_df.columns:
            catalog_df["hospital"] = ""
        catalog_df["hospital_norm"] = catalog_df["hospital"].map(_norm_text)
        catalog_df["beds"] = pd.to_numeric(catalog_df.get("beds"), errors="coerce").fillna(0)

        selected_df["hospital"] = selected_df.get("hospital", "").fillna("").astype(str)
        selected_df["hospital_norm"] = selected_df["hospital"].map(_norm_text)

        scoped_catalog = catalog_df[catalog_df["ccaa_norm"] == ccaa_norm].copy()
        if scoped_catalog.empty:
            scoped_catalog = catalog_df

        lookup_df = (
            scoped_catalog.sort_values("beds", ascending=False)
            .drop_duplicates(subset=["hospital_norm"])
            [["hospital_norm", "beds", "municipio", "provincia", "dependency", "center_class"]]
            .rename(
                columns={
                    "beds": "beds_cat",
                    "municipio": "municipio_cat",
                    "provincia": "provincia_cat",
                    "dependency": "dependency_cat",
                    "center_class": "center_class_cat",
                }
            )
        )

        selected_df = selected_df.merge(lookup_df, on="hospital_norm", how="left")

        selected_df["beds"] = pd.to_numeric(selected_df.get("beds"), errors="coerce").fillna(0)
        selected_df["beds_cat"] = pd.to_numeric(selected_df.get("beds_cat"), errors="coerce").fillna(0)
        selected_df["beds"] = selected_df["beds"].where(selected_df["beds"] > 0, selected_df["beds_cat"])

        for base_col in ("municipio", "provincia", "dependency", "center_class"):
            cat_col = f"{base_col}_cat"
            if base_col not in selected_df.columns:
                selected_df[base_col] = ""
            selected_df[base_col] = selected_df[base_col].fillna("").astype(str).str.strip()
            selected_df[cat_col] = selected_df[cat_col].fillna("").astype(str).str.strip()
            selected_df[base_col] = selected_df[base_col].where(selected_df[base_col].str.len() > 0, selected_df[cat_col])

        selected_df = selected_df.drop(
            columns=["hospital_norm", "beds_cat", "municipio_cat", "provincia_cat", "dependency_cat", "center_class_cat"],
            errors="ignore",
        )

    ccaa_metrics = score_df[score_df["ccaa_norm"] == ccaa_norm]
    ccaa_opportunity_score = float(ccaa_metrics["opportunity_score"].iloc[0]) if not ccaa_metrics.empty else 55.0
    ccaa_market_per_cap = float(ccaa_metrics["market_12m_avg_eur_per_capita"].iloc[0]) if not ccaa_metrics.empty else 55.0

    if "beds" not in selected_df.columns:
        selected_df["beds"] = 0
    selected_df["beds"] = pd.to_numeric(selected_df["beds"], errors="coerce").fillna(0)

    selected_df["size_factor"] = selected_df["beds"].map(_size_factor_from_beds)
    selected_df["center_type_factor"] = selected_df.apply(
        lambda row: _center_type_factor(row.get("dependency"), row.get("center_class")),
        axis=1,
    )
    selected_df["score"] = pd.to_numeric(
        ccaa_opportunity_score * selected_df["size_factor"] * selected_df["center_type_factor"],
        errors="coerce",
    ).fillna(0.0)
    selected_df["score"] = selected_df["score"].clip(0, 100).round(2)
    selected_df["tier"] = classify_hospital_tiers(selected_df["score"])

    tier_multiplier = selected_df["tier"].map({"Tier 1": 1.3, "Tier 2": 1.15, "Tier 3": 1.0, "Tier 4": 0.85}).fillna(1.0)
    selected_df["market_potential_eur"] = (selected_df["beds"] * ccaa_market_per_cap * tier_multiplier).round(0)

    selected_df["inclusion_reason"] = selected_df.apply(
        lambda row: (
            "Alta capacidad y score estratégico"
            if row["tier"] == "Tier 1"
            else "Centro con volumen relevante y potencial de crecimiento"
        ),
        axis=1,
    )
    selected_df["recommended_action"] = selected_df["tier"].map(
        {
            "Tier 1": "Reunión ejecutiva + plan de acceso 90 días",
            "Tier 2": "Activación KAM y propuesta de valor",
            "Tier 3": "Seguimiento trimestral y educación clínica",
            "Tier 4": "Monitorización y nurturing",
        }
    )

    selected_df = selected_df.sort_values(["score", "beds"], ascending=[False, False]).reset_index(drop=True)
    selected_df["ranking"] = selected_df.index + 1

    for col in ("hospital", "ccaa", "municipio", "provincia", "dependency", "center_class", "hospital_id"):
        if col not in selected_df.columns:
            selected_df[col] = ""

    target_hospitals = selected_df[
        [
            "ranking",
            "hospital_id",
            "hospital",
            "ccaa",
            "municipio",
            "provincia",
            "beds",
            "score",
            "tier",
            "inclusion_reason",
            "recommended_action",
            "dependency",
            "center_class",
            "size_factor",
            "center_type_factor",
            "market_potential_eur",
        ]
    ].copy()

    kpis: dict[str, float | int] = {
        "target_hospitals": int(len(target_hospitals)),
        "total_beds": int(target_hospitals["beds"].sum()) if not target_hospitals.empty else 0,
        "avg_score": float(target_hospitals["score"].mean()) if not target_hospitals.empty else 0.0,
        "max_score": float(target_hospitals["score"].max()) if not target_hospitals.empty else 0.0,
        "market_potential": float(target_hospitals["market_potential_eur"].sum()) if not target_hospitals.empty else 0.0,
        "tier_1_hospitals": int((target_hospitals["tier"] == "Tier 1").sum()) if not target_hospitals.empty else 0,
    }

    context = {
        "ccaa": ccaa or "N/A",
        "disease": disease or "Obesity",
        "snapshot_date": snapshot_date or str(date.today()),
        "n_hospitals": int(kpis["target_hospitals"]),
    }

    therapeutic_description, therapeutic_table = _build_therapeutic_block(str(context["disease"]))
    executive_summary = generate_executive_summary(context, kpis)

    tier_distribution = (
        target_hospitals.groupby("tier", as_index=False)["hospital_id"]
        .count()
        .rename(columns={"hospital_id": "hospitals"})
        .sort_values("tier")
    )

    top_score_chart = target_hospitals[["hospital", "score", "beds"]].head(10).copy()

    return OpportunityPackPayload(
        context=context,
        kpis=kpis,
        executive_summary=executive_summary,
        therapeutic_description=therapeutic_description,
        therapeutic_table=therapeutic_table,
        target_hospitals=target_hospitals,
        raw_data=selected_df.copy(),
        tier_distribution=tier_distribution,
        top_score_chart=top_score_chart,
    )


def build_opportunity_pack_excel(payload: OpportunityPackPayload) -> bytes:
    output = BytesIO()
    project_root = Path(__file__).resolve().parents[2]

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        fmt_title = workbook.add_format({"bold": True, "font_size": 20, "font_color": "#0f172a"})
        fmt_subtitle = workbook.add_format({"bold": True, "font_size": 11, "font_color": "#334155"})
        fmt_label = workbook.add_format({"bold": True, "font_color": "#334155"})
        fmt_value = workbook.add_format({"font_color": "#0f172a"})
        fmt_currency = workbook.add_format({"num_format": "#,##0", "font_color": "#0f172a"})
        fmt_wrap = workbook.add_format({"text_wrap": True, "valign": "top"})

        fmt_header_bar = workbook.add_format(
            {
                "bold": True,
                "font_size": 18,
                "font_color": "#0b1f36",
                "bg_color": "#eaf2fb",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "border_color": "#d8e5f5",
            }
        )
        fmt_context = workbook.add_format(
            {
                "font_size": 10,
                "font_color": "#334155",
                "bg_color": "#f8fbff",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "border_color": "#e2e8f0",
            }
        )
        fmt_card_label = workbook.add_format(
            {
                "bold": True,
                "font_size": 10,
                "font_color": "#475569",
                "bg_color": "#f8fafc",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "border_color": "#dbe4ef",
            }
        )
        fmt_card_value = workbook.add_format(
            {
                "bold": True,
                "font_size": 18,
                "font_color": "#0f172a",
                "bg_color": "#f8fafc",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "border_color": "#dbe4ef",
            }
        )
        fmt_card_value_currency = workbook.add_format(
            {
                "bold": True,
                "font_size": 16,
                "num_format": "#,##0",
                "font_color": "#0f172a",
                "bg_color": "#f8fafc",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "border_color": "#dbe4ef",
            }
        )
        fmt_section = workbook.add_format(
            {
                "bold": True,
                "font_size": 11,
                "font_color": "#0f172a",
                "bg_color": "#eef4fb",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "border_color": "#d8e5f5",
            }
        )
        fmt_cover_title = workbook.add_format(
            {
                "bold": True,
                "font_size": 26,
                "font_color": "#0b1f36",
                "align": "left",
                "valign": "vcenter",
            }
        )
        fmt_cover_subtitle = workbook.add_format(
            {
                "font_size": 11,
                "font_color": "#334155",
                "align": "left",
                "valign": "vcenter",
            }
        )
        fmt_cover_kpi_label = workbook.add_format(
            {
                "bold": True,
                "font_size": 10,
                "font_color": "#475569",
                "bg_color": "#f8fafc",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "border_color": "#dbe4ef",
            }
        )
        fmt_cover_kpi_value = workbook.add_format(
            {
                "bold": True,
                "font_size": 20,
                "font_color": "#0f172a",
                "bg_color": "#f8fafc",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "border_color": "#dbe4ef",
            }
        )
        fmt_cover_kpi_currency = workbook.add_format(
            {
                "bold": True,
                "font_size": 16,
                "num_format": "#,##0",
                "font_color": "#0f172a",
                "bg_color": "#f8fafc",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "border_color": "#dbe4ef",
            }
        )
        fmt_cover_highlight = workbook.add_format(
            {
                "bold": True,
                "font_size": 11,
                "font_color": "#0f172a",
                "bg_color": "#edf6ff",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "border_color": "#cfe0f5",
            }
        )
        fmt_cover_story = workbook.add_format(
            {
                "font_size": 10,
                "font_color": "#334155",
                "bg_color": "#f8fbff",
                "text_wrap": True,
                "valign": "top",
                "border": 1,
                "border_color": "#d8e5f5",
            }
        )

        cover = workbook.add_worksheet("Cover")
        cover.hide_gridlines(2)
        cover.set_zoom(94)
        cover.set_column("A:A", 4)
        cover.set_column("B:B", 20)
        cover.set_column("C:C", 16)
        cover.set_column("D:D", 18)
        cover.set_column("E:E", 18)
        cover.set_column("F:F", 18)
        cover.set_column("G:G", 15.67)
        cover.set_column("H:H", 0)
        cover.set_column("I:I", 18)
        cover.set_column("J:Z", 14, None, {"hidden": True})
        cover.set_column("BW:BZ", 40, None, {"hidden": False})
        cover.set_row(1, 36)
        cover.set_row(2, 24)
        cover.set_row(4, 20)
        cover.set_row(6, 20)
        cover.set_row(7, 24)
        cover.set_row(8, 28)
        cover.set_row(10, 20)
        cover.set_row(11, 24)
        cover.set_row(12, 60)

        cover.merge_range("B2:F2", "Target Opportunity Pack", fmt_cover_title)
        cover.merge_range(
            "B3:F3",
            "Investor Snapshot: impacto comercial y foco de ejecución en una sola vista.",
            fmt_cover_subtitle,
        )

        context_line = (
            f"CCAA: {payload.context.get('ccaa', 'N/A')} | "
            f"Disease: {payload.context.get('disease', 'N/A')} | "
            f"Snapshot date: {payload.context.get('snapshot_date', 'N/A')}"
        )
        cover.merge_range("B5:F5", context_line, fmt_context)

        selected_ccaa = str(payload.context.get("ccaa", ""))
        selected_disease = str(payload.context.get("disease", ""))
        ccaa_flag_path = _resolve_ccaa_flag_path(project_root, selected_ccaa)
        ccaa_flag_url = _resolve_ccaa_flag_url(selected_ccaa)
        disease_image_path = _resolve_disease_image_path(project_root, selected_disease)

        cover.merge_range("G2:H2", "CCAA flag", fmt_section)
        cover.write("I2", "Disease", fmt_section)

        flag_x_scale = 0.13
        flag_y_scale = 0.13
        flag_x_offset = 0
        flag_y_offset = 0
        flag_target_width_px = 115
        flag_target_height_px = 78

        inserted_flag = False
        if ccaa_flag_path is not None:
            inserted_flag = _insert_sheet_image(
                cover,
                "G3",
                ccaa_flag_path,
                x_scale=flag_x_scale,
                y_scale=flag_y_scale,
                x_offset=flag_x_offset,
                y_offset=flag_y_offset,
                target_width_px=flag_target_width_px,
                target_height_px=flag_target_height_px,
                keep_aspect=False,
            )
        if (not inserted_flag) and ccaa_flag_url:
            inserted_flag = _insert_sheet_image_from_url(
                cover,
                "G3",
                ccaa_flag_url,
                x_scale=flag_x_scale,
                y_scale=flag_y_scale,
                x_offset=flag_x_offset,
                y_offset=flag_y_offset,
                target_width_px=flag_target_width_px,
                target_height_px=flag_target_height_px,
                keep_aspect=False,
            )
        if not inserted_flag:
            cover.merge_range("G3:H4", f"Flag: {selected_ccaa}", fmt_cover_highlight)

        inserted_disease = False
        if disease_image_path is not None:
            inserted_disease = _insert_sheet_image(
                cover,
                "I3",
                disease_image_path,
                x_scale=0.34,
                y_scale=0.34,
                x_offset=4,
                y_offset=2,
            )
        if not inserted_disease:
            cover.merge_range("I3:I4", f"{selected_disease}", fmt_cover_highlight)

        cover.merge_range("B7:C7", "Target hospitals", fmt_cover_kpi_label)
        cover.merge_range("D7:E7", "Total beds", fmt_cover_kpi_label)
        cover.merge_range("F7:G7", "Average score", fmt_cover_kpi_label)
        cover.merge_range("H7:I7", "Market potential (EUR)", fmt_cover_kpi_label)

        cover.merge_range("B8:C9", int(payload.kpis.get("target_hospitals", 0)), fmt_cover_kpi_value)
        cover.merge_range("D8:E9", int(payload.kpis.get("total_beds", 0)), fmt_cover_kpi_value)
        cover.merge_range("F8:G9", round(float(payload.kpis.get("avg_score", 0)), 1), fmt_cover_kpi_value)
        cover.merge_range("H8:I9", float(payload.kpis.get("market_potential", 0)), fmt_cover_kpi_currency)

        top_hospital = "N/A"
        if not payload.target_hospitals.empty:
            top_hospital = str(
                payload.target_hospitals.sort_values("score", ascending=False).iloc[0].get("hospital", "N/A")
            )

        cover.merge_range("B11:E11", "Top account recommendation", fmt_section)
        cover.merge_range("B12:E13", f"Prioritize executive engagement with {top_hospital}.", fmt_cover_highlight)
        cover.merge_range("F11:I11", "Investment narrative", fmt_section)
        cover.merge_range("F12:I13", payload.executive_summary, fmt_cover_story)

        market_trend_df = _load_market_trend_for_ccaa(project_root, selected_ccaa, max_points=24)

        # Hidden helper data for a dedicated pharma spend trend chart on Cover.
        pharma_spend_df = market_trend_df.copy()
        if not pharma_spend_df.empty:
            pharma_spend_df["rolling_3m"] = (
                pd.to_numeric(pharma_spend_df["value"], errors="coerce")
                .rolling(window=3, min_periods=1)
                .mean()
            )
        else:
            pharma_spend_df = pd.DataFrame(columns=["period", "value", "rolling_3m"])

        pharma_mean = float(pd.to_numeric(pharma_spend_df.get("value"), errors="coerce").mean()) if not pharma_spend_df.empty else 0.0

        cover.write("BW2", "Period")
        cover.write("BX2", "Pharma spend EUR")
        cover.write("BY2", "3M moving avg")
        cover.write("BZ2", "Mean EUR")
        for row_idx, row in enumerate(pharma_spend_df.itertuples(index=False), start=3):
            cover.write(f"BW{row_idx}", str(getattr(row, "period", "")))
            cover.write_number(f"BX{row_idx}", float(getattr(row, "value", 0.0)))
            cover.write_number(f"BY{row_idx}", float(getattr(row, "rolling_3m", 0.0)))
            cover.write_number(f"BZ{row_idx}", pharma_mean)

        if not pharma_spend_df.empty:
            pharma_end = 2 + len(pharma_spend_df)
            chart_pharma_spend = workbook.add_chart({"type": "column"})
            chart_pharma_spend.add_series(
                {
                    "name": "Pharma spend EUR",
                    "categories": f"='Cover'!$BW$3:$BW${pharma_end}",
                    "values": f"='Cover'!$BX$3:$BX${pharma_end}",
                    "fill": {"color": "#0ea5e9"},
                    "border": {"color": "#0369a1"},
                    "data_labels": {"value": True},
                }
            )

            chart_pharma_mean = workbook.add_chart({"type": "line"})
            chart_pharma_mean.add_series(
                {
                    "name": "Media",
                    "categories": f"='Cover'!$BW$3:$BW${pharma_end}",
                    "values": f"='Cover'!$BZ$3:$BZ${pharma_end}",
                    "line": {"color": "#FBD1AE", "width": 1.75},
                    "marker": {"type": "none"},
                }
            )
            chart_pharma_spend.combine(chart_pharma_mean)

            chart_pharma_spend.set_title({"name": f"Gasto farmaceutico ({selected_ccaa})"})
            chart_pharma_spend.set_y_axis({"name": "EUR", "major_gridlines": {"visible": False}})
            chart_pharma_spend.set_x_axis({"name": "Year-Month", "num_font": {"rotation": -45, "size": 8}})
            chart_pharma_spend.set_legend({"position": "bottom"})
            chart_pharma_spend.set_chartarea({"border": {"none": True}})
            chart_pharma_spend.set_plotarea({"border": {"none": True}})
            cover.insert_chart("B15", chart_pharma_spend, {"x_scale": 2.94, "y_scale": 1.05})
        else:
            cover.merge_range("B15:I18", "No hay datos de gasto farmaceutico para la CCAA seleccionada.", fmt_cover_highlight)

        summary = workbook.add_worksheet("Executive Summary")
        summary.hide_gridlines(2)
        summary.set_zoom(80)
        summary.set_column("A:A", 4)
        summary.set_column("B:B", 24)
        summary.set_column("C:C", 18)
        summary.set_column("D:D", 20)
        summary.set_column("E:E", 18)
        summary.set_column("F:F", 20)
        summary.set_column("G:G", 35)
        summary.set_column("H:H", 20)
        summary.set_column("I:I", 18)
        summary.set_column("J:O", 14)

        summary.merge_range("B2:I3", "Executive Dashboard - Opportunity Pack", fmt_header_bar)
        context_text = (
            f"CCAA: {payload.context.get('ccaa', 'N/A')} | "
            f"Disease: {payload.context.get('disease', 'N/A')} | "
            f"Snapshot: {payload.context.get('snapshot_date', 'N/A')}"
        )
        summary.merge_range("B4:I4", context_text, fmt_context)

        # KPI cards
        summary.merge_range("B6:C6", "Target hospitals", fmt_card_label)
        summary.merge_range("D6:E6", "Total beds", fmt_card_label)
        summary.merge_range("F6:G6", "Average score", fmt_card_label)
        summary.merge_range("H6:I6", "Market potential (EUR)", fmt_card_label)

        summary.merge_range("B7:C8", int(payload.kpis.get("target_hospitals", 0)), fmt_card_value)
        summary.merge_range("D7:E8", int(payload.kpis.get("total_beds", 0)), fmt_card_value)
        summary.merge_range("F7:G8", round(float(payload.kpis.get("avg_score", 0)), 1), fmt_card_value)
        summary.merge_range("H7:I8", float(payload.kpis.get("market_potential", 0)), fmt_card_value_currency)

        summary.merge_range("B10:C10", "Tier 1 hospitals", fmt_card_label)
        summary.merge_range("D10:E10", "Max score", fmt_card_label)
        summary.merge_range("F10:I10", "Executive summary", fmt_section)

        summary.merge_range("B11:C12", int(payload.kpis.get("tier_1_hospitals", 0)), fmt_card_value)
        summary.merge_range("D11:E12", round(float(payload.kpis.get("max_score", 0)), 1), fmt_card_value)
        summary.merge_range("F11:I12", payload.executive_summary, fmt_wrap)

        # Build chart datasets on hidden helper columns.
        target_df = payload.target_hospitals.copy()
        target_df["dependency"] = target_df.get("dependency", "").fillna("").astype(str)

        def _bucket_hospital_type(value: str) -> str:
            lower = value.lower()
            if "privad" in lower:
                return "Private"
            if (
                "public" in lower
                or "públic" in lower
                or "servicios e institutos de salud" in lower
                or "seguridad social" in lower
                or "autonomica" in lower
                or "autonómica" in lower
            ):
                return "Public"
            return "Other"

        type_split = (
            target_df["dependency"].map(_bucket_hospital_type).value_counts().reindex(["Public", "Private", "Other"], fill_value=0)
        )

        summary.write("U2", "Type")
        summary.write("V2", "Hospitals")
        for row_idx, (label, value) in enumerate(type_split.items(), start=3):
            summary.write(f"U{row_idx}", label)
            summary.write_number(f"V{row_idx}", int(value))

        top_chart_df = payload.top_score_chart.copy().head(8)
        summary.write("U8", "Hospital")
        summary.write("V8", "Score")
        for row_idx, row in enumerate(top_chart_df.itertuples(index=False), start=9):
            summary.write(f"U{row_idx}", str(getattr(row, "hospital", "")))
            summary.write_number(f"V{row_idx}", float(getattr(row, "score", 0.0)))

        tier_df = payload.tier_distribution.copy()
        if tier_df.empty:
            tier_df = pd.DataFrame({"tier": ["Tier 1", "Tier 2", "Tier 3", "Tier 4"], "hospitals": [0, 0, 0, 0]})
        summary.write("W2", "Tier")
        summary.write("X2", "Hospitals")
        for row_idx, row in enumerate(tier_df.itertuples(index=False), start=3):
            summary.write(f"W{row_idx}", str(getattr(row, "tier", "")))
            summary.write_number(f"X{row_idx}", int(getattr(row, "hospitals", 0)))

        # Public / private split chart
        chart_split = workbook.add_chart({"type": "doughnut"})
        chart_split.add_series(
            {
                "name": "Hospital type split",
                "categories": "='Executive Summary'!$U$3:$U$5",
                "values": "='Executive Summary'!$V$3:$V$5",
                "data_labels": {"percentage": True, "leader_lines": True},
                "points": [
                    {"fill": {"color": "#4f78ad"}},
                    {"fill": {"color": "#b25666"}},
                    {"fill": {"color": "#94a3b8"}},
                ],
            }
        )
        chart_split.set_title({"name": "Public vs Private hospitals"})
        chart_split.set_legend({"position": "bottom"})
        chart_split.set_chartarea({"border": {"none": True}})
        summary.insert_chart("B14", chart_split, {"x_scale": 1.05, "y_scale": 1.1})

        # Top hospitals by score chart
        top_end = max(9, 8 + len(top_chart_df))
        chart_top = workbook.add_chart({"type": "column"})
        chart_top.add_series(
            {
                "name": "Opportunity score",
                "categories": f"='Executive Summary'!$U$9:$U${top_end}",
                "values": f"='Executive Summary'!$V$9:$V${top_end}",
                "fill": {"color": "#5ea388"},
                "border": {"color": "#4d8b73"},
                "data_labels": {"value": True},
            }
        )
        chart_top.set_title({"name": "Top hospitals by opportunity score"})
        chart_top.set_y_axis({"name": "Score", "max": 100, "major_gridlines": {"visible": False}})
        chart_top.set_x_axis({"label_position": "low"})
        chart_top.set_legend({"none": True})
        chart_top.set_chartarea({"border": {"none": True}})
        chart_top.set_plotarea({"border": {"none": True}})
        summary.insert_chart("E14", chart_top, {"x_scale": 1.22, "y_scale": 1.1})

        # Tier distribution chart
        tier_end = max(3, 2 + len(tier_df))
        chart_tier = workbook.add_chart({"type": "bar"})
        chart_tier.add_series(
            {
                "name": "Hospitals",
                "categories": f"='Executive Summary'!$W$3:$W${tier_end}",
                "values": f"='Executive Summary'!$X$3:$X${tier_end}",
                "fill": {"color": "#4f8b9f"},
                "border": {"none": True},
                "data_labels": {"value": True},
            }
        )
        chart_tier.set_title({"name": "Hospital priority tier distribution"})
        chart_tier.set_x_axis({"name": "Hospitals", "major_gridlines": {"visible": False}})
        chart_tier.set_legend({"none": True})
        chart_tier.set_chartarea({"border": {"none": True}})
        chart_tier.set_plotarea({"border": {"none": True}})
        summary.insert_chart("H14", chart_tier, {"x_scale": 1.05, "y_scale": 1.1, "x_offset": 24})

        summary.set_row(1, 24)
        summary.set_row(5, 20)
        summary.set_row(6, 22)
        summary.set_row(7, 24)
        summary.set_row(10, 20)
        summary.set_row(11, 48)

        payload.therapeutic_table.to_excel(writer, sheet_name="Therapeutic Opportunity", index=False, startrow=2)
        therapeutic_sheet = writer.sheets["Therapeutic Opportunity"]
        therapeutic_sheet.write("A1", "Therapeutic Opportunity", fmt_title)
        therapeutic_sheet.write("A2", payload.therapeutic_description)
        therapeutic_sheet.set_column("A:D", 30)

        payload.target_hospitals.to_excel(writer, sheet_name="Hospital Target List", index=False)
        target_sheet = writer.sheets["Hospital Target List"]
        target_sheet.set_column("A:A", 10)
        target_sheet.set_column("B:B", 16)
        target_sheet.set_column("C:C", 34)
        target_sheet.set_column("D:F", 16)
        target_sheet.set_column("G:H", 12)
        target_sheet.set_column("I:I", 10)
        target_sheet.set_column("J:K", 42)
        target_sheet.set_column("L:M", 20)
        target_sheet.set_column("N:N", 18)

        payload.raw_data.to_excel(writer, sheet_name="Raw Data", index=False)
        raw_sheet = writer.sheets["Raw Data"]
        raw_sheet.set_column("A:Z", 18)

    output.seek(0)
    return output.getvalue()
