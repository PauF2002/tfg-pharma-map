import streamlit as st
import pandas as pd

st.set_page_config(page_title="Inventory", layout="wide")

st.title("Inventory")
st.caption("Resumen y gestion de inventario de medicamentos por tipo.")

medicines = [
    {"name": "Metformin 500mg", "type": "Diabetes", "stock": 1200, "price": 2.8, "status": "OK", "sku": "MED-001", "form": "tablet", "presentation": "30 tablets", "atc": "A10BA02"},
    {"name": "Semaglutide 1mg", "type": "Obesity", "stock": 320, "price": 95.0, "status": "OK", "sku": "MED-002", "form": "injection", "presentation": "4 pens", "atc": "A10BJ06"},
    {"name": "Liraglutide 3mg", "type": "Obesity", "stock": 180, "price": 120.0, "status": "LOW", "sku": "MED-003", "form": "injection", "presentation": "5 pens", "atc": "A10BJ02"},
    {"name": "Insulin Glargine", "type": "Diabetes", "stock": 450, "price": 28.5, "status": "OK", "sku": "MED-004", "form": "injection", "presentation": "5 pens", "atc": "A10AE04"},
    {"name": "Dapagliflozin 10mg", "type": "Diabetes", "stock": 760, "price": 32.0, "status": "OK", "sku": "MED-005", "form": "tablet", "presentation": "28 tablets", "atc": "A10BK01"},
    {"name": "Atorvastatin 20mg", "type": "Cardio", "stock": 980, "price": 6.5, "status": "OK", "sku": "MED-006", "form": "tablet", "presentation": "30 tablets", "atc": "C10AA05"},
    {"name": "Bisoprolol 5mg", "type": "Cardio", "stock": 610, "price": 4.1, "status": "OK", "sku": "MED-007", "form": "tablet", "presentation": "30 tablets", "atc": "C07AB07"},
    {"name": "Amlodipine 5mg", "type": "Cardio", "stock": 540, "price": 3.8, "status": "OK", "sku": "MED-008", "form": "tablet", "presentation": "30 tablets", "atc": "C08CA01"},
    {"name": "Salbutamol Inhaler", "type": "Respiratory", "stock": 860, "price": 9.5, "status": "OK", "sku": "MED-009", "form": "inhaler", "presentation": "200 doses", "atc": "R03AC02"},
    {"name": "Budesonide Inhaler", "type": "Respiratory", "stock": 430, "price": 18.0, "status": "OK", "sku": "MED-010", "form": "inhaler", "presentation": "200 doses", "atc": "R03BA02"},
    {"name": "Ibuprofen 600mg", "type": "Pain", "stock": 1500, "price": 2.2, "status": "OK", "sku": "MED-011", "form": "tablet", "presentation": "40 tablets", "atc": "M01AE01"},
    {"name": "Paracetamol 1g", "type": "Pain", "stock": 2100, "price": 1.9, "status": "OK", "sku": "MED-012", "form": "tablet", "presentation": "20 tablets", "atc": "N02BE01"},
    {"name": "Tramadol 50mg", "type": "Pain", "stock": 320, "price": 7.5, "status": "LOW", "sku": "MED-013", "form": "capsule", "presentation": "30 capsules", "atc": "N02AX02"},
    {"name": "Losartan 50mg", "type": "Cardio", "stock": 720, "price": 5.0, "status": "OK", "sku": "MED-014", "form": "tablet", "presentation": "30 tablets", "atc": "C09CA01"},
    {"name": "Empagliflozin 10mg", "type": "Diabetes", "stock": 610, "price": 34.0, "status": "OK", "sku": "MED-015", "form": "tablet", "presentation": "28 tablets", "atc": "A10BK03"},
    {"name": "Orlistat 120mg", "type": "Obesity", "stock": 260, "price": 22.0, "status": "OK", "sku": "MED-016", "form": "capsule", "presentation": "42 capsules", "atc": "A08AB01"},
    {"name": "Montelukast 10mg", "type": "Respiratory", "stock": 520, "price": 12.0, "status": "OK", "sku": "MED-017", "form": "tablet", "presentation": "28 tablets", "atc": "R03DC03"},
    {"name": "Pregabalin 75mg", "type": "Pain", "stock": 260, "price": 8.8, "status": "LOW", "sku": "MED-018", "form": "capsule", "presentation": "56 capsules", "atc": "N03AX16"},
    {"name": "Naproxen 500mg", "type": "Pain", "stock": 610, "price": 4.4, "status": "OK", "sku": "MED-019", "form": "tablet", "presentation": "30 tablets", "atc": "M01AE02"},
    {"name": "Rosuvastatin 10mg", "type": "Cardio", "stock": 430, "price": 7.2, "status": "OK", "sku": "MED-020", "form": "tablet", "presentation": "30 tablets", "atc": "C10AA07"},
    {"name": "Gliclazide MR 30mg", "type": "Diabetes", "stock": 390, "price": 11.5, "status": "OK", "sku": "MED-021", "form": "tablet", "presentation": "30 tablets", "atc": "A10BB09"},
    {"name": "Hydrochlorothiazide 25mg", "type": "Cardio", "stock": 540, "price": 3.1, "status": "OK", "sku": "MED-022", "form": "tablet", "presentation": "30 tablets", "atc": "C03AA03"},
    {"name": "Tiotropium 18mcg", "type": "Respiratory", "stock": 210, "price": 36.0, "status": "LOW", "sku": "MED-023", "form": "inhaler", "presentation": "30 capsules", "atc": "R03BB04"},
    {"name": "Duloxetine 60mg", "type": "Pain", "stock": 190, "price": 15.5, "status": "LOW", "sku": "MED-024", "form": "capsule", "presentation": "28 capsules", "atc": "N06AX21"},
]

df = pd.DataFrame(medicines)
df["value_eur"] = df["stock"] * df["price"]

summary_tab, meds_tab, detail_tab = st.tabs(["Resumen", "Medicamentos", "Detalle"])

with summary_tab:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Medicamentos", f"{len(df)}")
    col2.metric("Tipos", f"{df['type'].nunique()}")
    col3.metric("Stock total", f"{int(df['stock'].sum()):,}")
    col4.metric("Stock bajo", f"{int((df['status'] == 'LOW').sum())}")

    st.markdown("---")

    left, right = st.columns([1.2, 0.8])
    with left:
        by_type = df.groupby("type").size().sort_values(ascending=False)
        st.subheader("Medicamentos por tipo")
        st.bar_chart(by_type)

    with right:
        st.subheader("Top valor inventario")
        top_value = df.sort_values("value_eur", ascending=False).head(8)
        st.dataframe(
            top_value[["name", "type", "stock", "price", "value_eur"]],
            use_container_width=True,
        )

with meds_tab:
    st.subheader("Listado de medicamentos")
    all_types = sorted(df["type"].unique().tolist())
    selected_types = st.multiselect("Filtrar por tipo", all_types, default=all_types)

    filtered = df[df["type"].isin(selected_types)].copy()
    st.caption(f"Resultados: {len(filtered)} medicamentos")

    st.dataframe(
        filtered[["name", "type", "stock", "price", "status"]].sort_values(["type", "name"]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.subheader("Listas por tipo")
    for t in all_types:
        subset = filtered[filtered["type"] == t]
        if len(subset) == 0:
            continue
        with st.expander(f"{t} ({len(subset)})", expanded=False):
            st.dataframe(
                subset[["name", "stock", "price", "status"]].sort_values("name"),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("---")
    st.subheader("Ver detalle de medicamento")
    selected_name = st.selectbox("Selecciona un medicamento", filtered["name"].tolist())
    if st.button("Ver detalles"):
        st.session_state["selected_medicine"] = selected_name
        st.success("Seleccion guardada. Abre la pestaña 'Detalle'.")

with detail_tab:
    selected_name = st.session_state.get("selected_medicine")
    if not selected_name:
        st.info("Selecciona un medicamento en la pestana 'Medicamentos'.")
    else:
        row = df[df["name"] == selected_name].iloc[0]
        st.subheader(row["name"])
        st.caption(f"Tipo: {row['type']}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Stock", f"{int(row['stock'])}")
        col2.metric("Precio", f"{row['price']:.2f} EUR")
        col3.metric("Valor", f"{row['value_eur']:.2f} EUR")
        col4.metric("Estado", row["status"])

        st.markdown("---")
        st.markdown(
            f"""
            **SKU:** {row['sku']}  
            **Forma:** {row['form']}  
            **Presentacion:** {row['presentation']}  
            **ATC:** {row['atc']}  
            """
        )
