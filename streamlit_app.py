import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="AI Boekhouder Pro", layout="wide")
st.title("⚖️ AI Boekhouder - Business Audit & Prognose")

# Instelling voor BTW-vrijstelling (belangrijk voor Zorg)
with st.sidebar:
    st.header("Bedrijfsinstellingen")
    is_vrijgesteld = st.toggle("Bedrijf is BTW-vrijgesteld (zoals Zorg)", value=True)
    uploaded_file = st.file_uploader("Upload Yuki Transacties", type=['csv'])

if uploaded_file:
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

    # --- DE BOEKHOUDER LOGICA: GROEPEREN VAN GROOTBOEKEN ---
    # Omzet (8xxx)
    df_omzet = df[df['Code_Str'].str.startswith('8') | (df['Code_Str'] == '18400')].copy()
    # Inkoop (6xxx)
    df_inkoop = df[df['Code_Str'].str.startswith('6')].copy()
    # Personeel (40xxx - 42xxx)
    df_personeel = df[df['Code_Str'].str.startswith(('40', '41', '42'))].copy()
    # Algemene Kosten (43xxx - 49xxx)
    df_algemeen = df[df['Code_Str'].str.startswith(('43', '44', '45', '46', '47', '48', '49'))].copy()

    # --- PROGNOSE MODEL ---
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    
    if len(monthly_rev) >= 3:
        # Correctie voor incompleet 2025
        last_date = monthly_rev['Date'].max()
        if last_date.year == 2025 and last_date.month < 12:
            avg_per_month = monthly_rev[monthly_rev['Date'].dt.year == 2025]['Amount_Clean'].mean()
            omzet_2025_est = avg_per_month * 12
        else:
            omzet_2025_est = monthly_rev[monthly_rev['Date'].dt.year == 2025]['Amount_Clean'].sum()

        # Lineaire Regressie voor 2026
        X = np.arange(len(monthly_rev)).reshape(-1, 1)
        y = monthly_rev['Amount_Clean']
        model = LinearRegression().fit(X, y)
        future_dates = pd.date_range(start='2026-01-01', periods=12, freq='ME')
        forecast_2026 = [max(0, model.predict([[len(monthly_rev) + i]])[0]) for i in range(12)]
        totaal_2026 = sum(forecast_2026)
    else:
        totaal_2026, omzet_2025_est = 0, 0

    # --- DASHBOARD KPI's ---
    st.subheader("📋 Tussentijdse Resultaten & 2026 Voorspelling")
    c1, c2, c3 = st.columns(3)
    
    winst_2026 = totaal_2026 - (df_inkoop['Amount_Clean'].sum() + df_personeel['Amount_Clean'].sum() + df_algemeen['Amount_Clean'].sum()) / 2 # Gemiddelde kosten per jaar
    
    c1.metric("Verwachte Omzet 2026", f"€ {totaal_2026:,.2f}")
    c2.metric("Verwacht Netto Resultaat", f"€ {max(0, winst_2026):,.2f}")
    
    groei = ((totaal_2026 - omzet_2025_est) / omzet_2025_est * 100) if omzet_2025_est > 0 else 0
    c3.metric("Groeipotentieel vs 2025", f"{groei:.1f}%")

    # --- GRAFIEK ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly_rev['Date'], y=monthly_rev['Amount_Clean'], name="Historisch", line=dict(color='green')))
    if totaal_2026 > 0:
        fig.add_trace(go.Scatter(x=future_dates, y=forecast_2026, name="Prognose 2026", line=dict(dash='dot', color='blue')))
    st.plotly_chart(fig, use_container_width=True)

    # --- DE BOEKHOUDER TABEL ---
    st.markdown("---")
    st.subheader("📉 Winst- en Verlies Analyse")
    
    data = {
        "Categorie": ["Netto-omzet", "Kostprijs van de omzet", "Personeelskosten", "Overige bedrijfskosten"],
        "Totaal Bedrag": [
            f"€ {df_omzet['Amount_Clean'].sum():,.2f}",
            f"€ {df_inkoop['Amount_Clean'].sum():,.2f}",
            f"€ {df_personeel['Amount_Clean'].sum():,.2f}",
            f"€ {df_algemeen['Amount_Clean'].sum():,.2f}"
        ]
    }
    st.table(pd.DataFrame(data))

    # --- BTW SECTIE ---
    st.markdown("---")
    if is_vrijgesteld:
        st.warning("⚠️ **Bedrijf is BTW-vrijgesteld:** Er wordt geen BTW-teruggave berekend. Alle kosten zijn inclusief BTW geboekt.")
    else:
        btw = (df_algemeen['Amount_Clean'].sum() + df_personeel['Amount_Clean'].sum()) * 0.21
        st.success(f"💰 **Te ontvangen BTW (Voorbelasting):** € {btw:,.2f}")

else:
    st.info("Upload de Yuki CSV voor een volledige boekhoudkundige analyse.")
