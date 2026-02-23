import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Cruising Travel - Yuki Intelligence", layout="wide")
st.title("🚢 Cruising Travel - Officiële Yuki Prognose")

if uploaded_file := st.sidebar.file_uploader("Upload Yuki CSV", type=['csv']):
    df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='iso-8859-1')
    df.columns = df.columns.str.strip()

    def clean_val(x):
        if pd.isna(x): return 0.0
        x = str(x).replace('"', '').replace('.', '').replace(',', '.')
        try: return float(x)
        except: return 0.0

    df['Amount_Clean'] = df['Bedrag'].apply(clean_val).abs()
    df['Date'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
    df['Code_Str'] = df['Code'].astype(str).str.strip()

    # --- MATCHING MET JOUW TABEL ---
    # Omzet: Code 80032
    df_omzet = df[df['Code_Str'] == '80032'].copy()
    # Inkoop: Code 60032 of 60000
    df_inkoop = df[df['Code_Str'].isin(['60032', '60000'])].copy()
    # Kosten: Alles wat met 4 begint
    df_kosten = df[df['Code_Str'].str.startswith('4')].copy()

    # --- BEREKENINGEN ---
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    
    if len(monthly_rev) > 3:
        X = np.arange(len(monthly_rev)).reshape(-1, 1)
        y = monthly_rev['Amount_Clean']
        model = LinearRegression().fit(X, y)
        future_dates = pd.date_range(start='2026-01-01', periods=12, freq='ME')
        forecast_2026 = [max(0, model.predict([[len(monthly_rev) + i]])[0]) for i in range(12)]
        
        totaal_omzet_2026 = sum(forecast_2026)
        omzet_2025 = monthly_rev[monthly_rev['Date'].dt.year == 2025]['Amount_Clean'].sum()
        groeifactor = ((totaal_omzet_2026 - omzet_2025) / omzet_2025 * 100) if omzet_2025 > 0 else 0
    else:
        totaal_omzet_2026, groeifactor = 0, 0

    # --- DASHBOARD ---
    st.subheader("📊 Financiële Prognose (gebaseerd op Yuki-structuur)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Verwachte Netto-omzet 2026", f"€ {totaal_omzet_2026:,.2f}")
    c2.metric("Verwachte Bruto-marge", f"€ {(totaal_omzet_2026 * 0.045):,.2f}", help="Gebaseerd op je huidige marge van ~4.5%")
    c3.metric("Trend vs 2025", f"{groeifactor:.1f}%", delta=f"{groeifactor:.1f}%")

    # --- GRAFIEK ---
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_rev['Date'], y=monthly_rev['Amount_Clean'], name="Historische Netto-omzet", marker_color='navy'))
    fig.add_trace(go.Bar(x=future_dates, y=forecast_2026, name="Prognose 2026", marker_color='gold'))
    st.plotly_chart(fig, use_container_width=True)

    # --- BTW STATUS ---
    st.markdown("---")
    st.subheader("📝 BTW & Resultaat Check")
    # In jouw tabel is bijna alles 'Margeregeling', dus 0 BTW over de hoofdsom
    voorbelasting = df_kosten['Amount_Clean'].sum() * 0.21
    st.info(f"Geschatte BTW teruggave op basis van kantoorkosten: € {voorbelasting:,.2f}")

    # --- KOSTEN TABEL ---
    st.write("### Top Bedrijfslasten (Yuki)")
    st.table(df_kosten.groupby('Grootboekrekening')['Amount_Clean'].sum().sort_values(ascending=False).head(5))

else:
    st.info("Upload je Yuki CSV om de winst- en omzetprognose te starten.")
