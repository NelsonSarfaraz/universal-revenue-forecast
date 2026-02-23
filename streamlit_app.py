import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Universal Business Intelligence", layout="wide")
st.title("📈 Smart Business & Tax Intelligence")

uploaded_file = st.sidebar.file_uploader("Upload Yuki CSV", type=['csv'])

if uploaded_file:
    # 1. DATA LADEN
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

    # 2. SLIMME SELECTIE (Pakt 80032 OF andere 8-codes)
    df_omzet = df[df['Code_Str'].str.startswith('8')].copy()
    df_kosten = df[df['Code_Str'].str.startswith(('4', '6', '7'))].copy()

    # 3. PROGNOSE BEREKENING
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    
    # Initialiseer variabelen om NameErrors te voorkomen
    totaal_omzet_2026 = 0.0
    groeifactor = 0.0
    piek_maand = "Niet beschikbaar"
    forecast_2026 = []
    future_dates = []

    if len(monthly_rev) >= 3:
        X = np.arange(len(monthly_rev)).reshape(-1, 1)
        y = monthly_rev['Amount_Clean']
        model = LinearRegression().fit(X, y)
        
        future_dates = pd.date_range(start='2026-01-01', periods=12, freq='ME')
        forecast_2026 = [max(0, model.predict([[len(monthly_rev) + i]])[0]) for i in range(12)]
        
        totaal_omzet_2026 = sum(forecast_2026)
        omzet_2025 = monthly_rev[monthly_rev['Date'].dt.year == 2025]['Amount_Clean'].sum()
        
        # Als we data hebben van 2025 maar het jaar is nog niet om, schatten we het totaal
        if 0 < monthly_rev[monthly_rev['Date'].dt.year == 2025]['Date'].dt.month.max() < 12:
            maanden = monthly_rev[monthly_rev['Date'].dt.year == 2025]['Date'].dt.month.max()
            omzet_2025_full = (omzet_2025 / maanden) * 12
        else:
            omzet_2025_full = omzet_2025

        if omzet_2025_full > 0:
            groeifactor = ((totaal_omzet_2026 - omzet_2025_full) / omzet_2025_full * 100)
        
        piek_maand = future_dates[np.argmax(forecast_2026)].strftime('%B')

    # 4. WINST MARGE BEREKENEN (Dynamisch)
    tot_omzet = df_omzet['Amount_Clean'].sum()
    tot_kosten = df_kosten['Amount_Clean'].sum()
    werkelijke_marge = (tot_omzet - tot_kosten) / tot_omzet if tot_omzet > 0 else 0.15

    # --- UI WEERGAVE ---
    st.subheader("📊 Strategische Prognose 2026")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Verwachte Omzet 2026", f"€ {totaal_omzet_2026:,.2f}")
    m2.metric("Verwachte Winst", f"€ {(totaal_omzet_2026 * werkelijke_marge):,.2f}")
    m3.metric("Groeipotentieel", f"{groeifactor:.1f}%", delta=f"{groeifactor:.1f}%")
    m4.metric("Piekmaand", piek_maand)

    # --- GRAFIEK MET FOUTCORRECTIE ---
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_rev['Date'], y=monthly_rev['Amount_Clean'], name="Historisch", marker_color='navy'))
    if len(forecast_2026) > 0:
        fig.add_trace(go.Bar(x=future_dates, y=forecast_2026, name="Prognose 2026", marker_color='gold'))
    
    fig.update_layout(title="Omzet Trendlijst", barmode='group')
    st.plotly_chart(fig, use_container_width=True)

    # --- BTW & KOSTEN ---
    st.markdown("---")
    st.subheader("💡 Kosten & Belasting")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.write("Top Kostenposten:")
        st.table(df_kosten.groupby('Grootboekrekening')['Amount_Clean'].sum().sort_values(ascending=False).head(5))
    
    with col_b:
        btw_teruggave = df_kosten[df_kosten['Code_Str'].str.startswith('4')]['Amount_Clean'].sum() * 0.21
        st.success(f"Geschatte BTW-voorbelasting op basis van kosten: € {btw_teruggave:,.2f}")
        st.info("Let op: Als dit bedrijf is vrijgesteld van BTW, is dit bedrag niet terugvorderbaar.")

else:
    st.info("Upload een Yuki CSV bestand om de AI analyse te starten.")
