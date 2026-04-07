from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
import unicodedata

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


def _normalize_hospital_id(value: object) -> str:
    return str(value or "").strip().replace(",", "").removesuffix(".0")


def _safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except pd.errors.ParserError:
            try:
                return pd.read_csv(
                    path,
                    encoding=encoding,
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


def _load_ccaa_metrics(project_root: Path) -> pd.DataFrame:
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
    score_df = _load_ccaa_metrics(project_root)

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

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        fmt_title = workbook.add_format({"bold": True, "font_size": 18, "font_color": "#0f172a"})
        fmt_subtitle = workbook.add_format({"bold": True, "font_size": 11, "font_color": "#334155"})
        fmt_label = workbook.add_format({"bold": True, "font_color": "#334155"})
        fmt_value = workbook.add_format({"font_color": "#0f172a"})
        fmt_currency = workbook.add_format({"num_format": "#,##0", "font_color": "#0f172a"})
        fmt_wrap = workbook.add_format({"text_wrap": True, "valign": "top"})

        cover = workbook.add_worksheet("Cover")
        cover.write("A1", "Target List", fmt_title)
        cover.write("A3", "CCAA", fmt_label)
        cover.write("B3", str(payload.context.get("ccaa", "N/A")), fmt_value)
        cover.write("A4", "Disease", fmt_label)
        cover.write("B4", str(payload.context.get("disease", "N/A")), fmt_value)
        cover.write("A5", "Snapshot date", fmt_label)
        cover.write("B5", str(payload.context.get("snapshot_date", "N/A")), fmt_value)
        cover.write("A6", "Target hospitals", fmt_label)
        cover.write("B6", int(payload.kpis.get("target_hospitals", 0)), fmt_value)
        cover.set_column("A:A", 24)
        cover.set_column("B:B", 44)

        summary = workbook.add_worksheet("Executive Summary")
        summary.write("A1", "Executive Summary", fmt_title)
        summary.write("A3", "Executive text", fmt_subtitle)
        summary.merge_range("A4:F7", payload.executive_summary, fmt_wrap)
        summary.write("A9", "KPI", fmt_label)
        summary.write("B9", "Value", fmt_label)
        summary_rows = [
            ("Target hospitals", payload.kpis.get("target_hospitals", 0)),
            ("Total beds", payload.kpis.get("total_beds", 0)),
            ("Average score", round(float(payload.kpis.get("avg_score", 0)), 2)),
            ("Max score", round(float(payload.kpis.get("max_score", 0)), 2)),
            ("Market potential", float(payload.kpis.get("market_potential", 0))),
            ("Tier 1 hospitals", payload.kpis.get("tier_1_hospitals", 0)),
        ]
        for idx, (name, value) in enumerate(summary_rows, start=10):
            summary.write(f"A{idx}", name, fmt_value)
            if name == "Market potential":
                summary.write_number(f"B{idx}", float(value), fmt_currency)
            else:
                summary.write(f"B{idx}", value, fmt_value)
        summary.set_column("A:A", 28)
        summary.set_column("B:B", 20)
        summary.set_column("C:F", 16)

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
