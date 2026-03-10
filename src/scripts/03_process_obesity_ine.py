import pandas as pd
from pathlib import Path
import unicodedata
import re
#LOS DATOS OBTENIDOS DEL INE VIENEN EN UN FORMATO UN POCO RARO, ASI QUE HAY QUE HACER VARIAS TRANSFORMACIONES PARA LIMPIARLOS Y DEJARLOS EN UN FORMATO HOMOGÉNEO PARA PODER USARLOS EN EL PIPELINE DE HOSPITALES/GEODATOS
#ADEMAS ESTOS DATOS DE OBESIDAD SE TRATAN DE UNA FORMA ESPECIFIA NOSOTROS OBTENEMOS EL ULTIMO DATO DEL INE QUE ES DEL 2023. COMO SEGUIREMOS TRATANDO OTRAS PATOLOGÍAS ESTO PUEDE IR AJUSTANDOSE PARA OBTENER LOS DATOS DE LOS ULTIMOS AÑOS DE CADA PATOLOGÍA, PERO EN ESTE CASO SOLO QUEREMOS EL DATO DE OBESIDAD DEL 2023 PORQUE ES EL MAS RECIENTE Y EL QUE QUEREMOS USAR PARA CRUZAR CON LOS DATOS DE HOSPITALES/GEODATOS
BASE = Path(__file__).resolve().parents[2]
INP = BASE / "data" / "raw" / "ine_obesity_ccaa.csv"
OUT = BASE / "data" / "processed" / "ccaa_obesity.csv"

def norm_txt(x: str) -> str:
    x = str(x).strip().lower()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return " ".join(x.split())

#NOTAS PAU: leemos el csv sin ponerle cabecera
raw = pd.read_csv(INP, encoding="utf-8-sig", engine="python", header=None)
#agarro el array entero,por que esta en una linea y esta en [0], lo hago str y con funcion tipo str.strip() le quito espacios 
df = raw[0].astype(str).str.strip()

# quitar comillas externas
#NOTAS: (^") comilla al inicio, ("$) comilla al final, se remplaza por " "(nada, espacio vacio)
df = df.str.replace(r'^"|"$', "", regex=True)

# separar por tab real
df = df.str.split("\t", expand=True)

# primera fila es cabecera, con el iloc hacemos que la primera fila[0] sea df.columns
df.columns = df.iloc[0].tolist()
#la primera fila del df se ha quedado con los nombres de las columnas asi que aqui lo hemos arregaldo quitandola
df = df.iloc[1:].reset_index(drop=True)


print("✅ INE columns:", df.columns.tolist(), "| rows:", len(df))

# 2) Renombrar columnas esperadas (por si vienen con mayúsculas/acentos)
# Esperado: Comunidad autónoma, Masa corporal, Periodo, Total
col_ccaa = next(c for c in df.columns if "comunidad" in c.lower())
col_masa = next(c for c in df.columns if "masa" in c.lower())
col_periodo = next(c for c in df.columns if "period" in c.lower())
col_total = next(c for c in df.columns if c.lower().strip() == "total" or "total" in c.lower())

# 3) Filtrar SOLO obesidad (IMC >= 30)
mask_ob = df[col_masa].astype(str).str.contains("Obesidad", case=False, na=False)
df = df[mask_ob].copy()

# 4) Parsear valores
#Pasamos valores como periodo o Total de string a numero praa evitar errores
df["period"] = pd.to_numeric(df[col_periodo], errors="coerce")
df["obesity_pct"] = (
    df[col_total].astype(str)
      .str.replace(",", ".", regex=False)   # coma decimal -> punto
)
df["obesity_pct"] = pd.to_numeric(df["obesity_pct"], errors="coerce")

# 5) Limpiar CCAA (quitar prefijo "01 ", "02 ", etc.)
#primero lo convertimos a tipo string, para aplicarle funciones como replace
#^donde debe empezar a buscar | s* que tipo de carateres (space) | que tipo de caracteres (digits) \ s* que tipo de carateres (space) lo que hace es buscar un numero al principio de la cadena, seguido de espacios, y lo reemplaza por una cadena vacía, dejando solo el nombre de la comunidad autónoma.
df["CCAA_raw"] = df[col_ccaa].astype(str).str.replace(r"^\s*\d+\s*", "", regex=True).str.strip()

# quitar Total Nacional
df = df[~df["CCAA_raw"].str.lower().str.contains("total nacional", na=False)]

df = df.dropna(subset=["period", "obesity_pct"])

# 6) Quedarnos con el último año por CCAA
df = df.sort_values(["CCAA_raw", "period"]).groupby("CCAA_raw", as_index=False).tail(1)

# 7) Homogeneizar nombres para casar con tu pipeline (hospital/geojson)
fix = {
    norm_txt("Asturias, Principado de"): "Ppdo. de Asturias",
    norm_txt("Balears, Illes"): "Illes Balears",
    norm_txt("Murcia, Región de"): "Región de Murcia",
    norm_txt("Navarra, Comunidad Foral de"): "C. Foral de Navarra",
    norm_txt("Rioja, La"): "La Rioja",
    norm_txt("Comunitat Valenciana"): "Comunidad Valenciana",
    norm_txt("Castilla - La Mancha"): "Castilla-La Mancha",
}
df["CCAA"] = df["CCAA_raw"].apply(lambda x: fix.get(norm_txt(x), x))

out = df[["CCAA", "period", "obesity_pct"]].copy()
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False, encoding="utf-8-sig")


print(f"✅ Generado: {OUT}")
print(out.head(10).to_string(index=False))
print("✅ CCAA count:", out["CCAA"].nunique(), "| latest years:", sorted(out["period"].unique())[-5:])