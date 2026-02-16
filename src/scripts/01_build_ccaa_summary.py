import pandas as pd
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]  # raíz del proyecto
HOSP_FILE = BASE / "data" / "raw" / "CNH_2024_geocoded.csv"
POP_FILE  = BASE / "data" / "raw" / "poblacion_provincias.csv"
OUT_FILE  = BASE / "data" / "processed" / "ccaa_hospital_summary.csv"

def norm_txt(x: str) -> str:
    if pd.isna(x):
        return ""
    x = str(x).strip().lower()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = " ".join(x.split())
    return x

def safe_int(s):
    return pd.to_numeric(s, errors="coerce").fillna(0).astype(int)

# 1) Load hospitals
# Lee CSV tolerante: si alguna fila viene con una coma extra, la salta
total_lines = sum(1 for _ in open(HOSP_FILE, "r", encoding="utf-8", errors="ignore")) - 1
hosp = pd.read_csv(HOSP_FILE, sep=",", engine="python", encoding="utf-8", on_bad_lines="skip")
print(f"Hospitales leídos: {len(hosp)} / líneas totales (sin header): {total_lines}  -> saltadas: {total_lines - len(hosp)}")


hosp["CCAA"] = hosp["CCAA"].astype(str).str.strip()
hosp["Provincia"] = hosp["Provincia"].astype(str).str.strip()
hosp["CAMAS"] = safe_int(hosp["CAMAS"])
hosp["prov_key"] = hosp["Provincia"].map(norm_txt)

# province -> CCAA (por moda, debería ser 1:1)
prov_to_ccaa = (
    hosp.groupby("prov_key")["CCAA"]
    .agg(lambda s: s.value_counts().index[0])
    .reset_index()
)

# 2) Load population (Provincia,Poblacion)
pop = pd.read_csv(POP_FILE)
pop["Provincia"] = pop["Provincia"].astype(str).str.strip()
pop["Poblacion"] = safe_int(pop["Poblacion"])
pop["prov_key"] = pop["Provincia"].map(norm_txt)

# Normalizar nombres de provincia (castellano / variantes) a los que usa el CNH
fix = {
    "baleares": "illes balears",
    "la coruna": "a coruna",
    "gerona": "girona",
    "lerida": "lleida",
    "orense": "ourense",
    # País Vasco: a veces CNH usa formas antiguas
    "bizkaia": "vizcaya",
    "gipuzkoa": "guipuzcoa",
}

pop["prov_key"] = pop["prov_key"].replace(fix)


pop2 = pop.merge(prov_to_ccaa, on="prov_key", how="left")

unmatched = pop2[pop2["CCAA"].isna()]["Provincia"].unique().tolist()
if unmatched:
    print("⚠️ Provincias sin CCAA (revisar nombres):")
    for p in unmatched:
        print("  -", p)

pop_ccaa = (
    pop2.dropna(subset=["CCAA"])
        .groupby("CCAA")["Poblacion"]
        .sum()
        .reset_index()
        .rename(columns={"Poblacion": "population"})
)

# 3) Agregar hospitales por CCAA
hosp["is_private"] = hosp["Dependencia Funcional"].astype(str).str.contains("privad", case=False, na=False)
hosp["is_public"]  = ~hosp["is_private"]
hosp["is_general_hospital"] = hosp["Clase de Centro"].astype(str).str.contains("hospitales generales", case=False, na=False)

agg = hosp.groupby("CCAA").agg(
    hospitals_total=("CODCNH", "count"),
    beds_total=("CAMAS", "sum"),
    hospitals_public=("is_public", "sum"),
    hospitals_private=("is_private", "sum"),
    hospitals_general=("is_general_hospital", "sum"),
).reset_index()

# 4) Merge + métricas per cápita
df = agg.merge(pop_ccaa, on="CCAA", how="left")

df["hospitals_per_1M"] = (df["hospitals_total"] / df["population"] * 1_000_000).round(2)
df["beds_per_100k"]    = (df["beds_total"]      / df["population"] * 100_000).round(2)

df = df.sort_values("beds_per_100k", ascending=False)

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT_FILE, index=False)

print(f"✅ Generado: {OUT_FILE}")
print(df.head(10))
