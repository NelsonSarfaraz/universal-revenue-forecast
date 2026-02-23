import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Master AI Boekhouder", layout="wide")
st.title("🏛️ Master AI Boekhouder - Full Financial Intelligence")

with st.sidebar:
    st.header("Instellingen")
    is_vrijgesteld = st.toggle("Bedrijf is BTW-vrijgesteld (Zorg/Onderwijs)", value=False)
    uploaded_file = st.file_uploader("Upload Yuki Transacties (CSV)", type=['csv'])

if uploaded_file:
    # 1. DATA PARSING
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

    # 2. CATEGORISERING (BOEKHOUDKUNDIG)
    df_omzet = df[df['Code_Str'].str.startswith('8') | (df['Code_Str'] == '18400')].copy()
    df_inkoop = df[df['Code_Str'].str.startswith('6')].copy()
    df_auto = df[df['Code_Str'].str.startswith('42')].copy()
    df_huisvesting = df[df['Code_Str'].str.startswith('43')].copy()
    df_overig = df[df['Code_Str'].str.startswith(('40', '41', '44', '45', '46', '47', '48', '49'))].copy()
    df_totaal_kosten = df[df['Code_Str'].str.startswith(('4', '6'))].copy()

    # 3. PROGNOSE MODEL (MET EXTRAPOLATIE 2025)
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    
    if len(monthly_rev) >= 3:
        last_date = monthly_rev['Date'].max()
        omzet_2025_nu = monthly_rev[monthly_rev['Date'].dt.year == 2025]['Amount_Clean'].sum()
        
        # Schatting 2025 als het jaar nog bezig is
        if last_date.year == 2025 and last_date.month < 12:
            omzet_2025_est = (omzet_2025_nu / last_date.month) * 12
        else:
            omzet_2025_est = omzet_2025_nu

        X = np.arange(len(monthly_rev)).reshape(-1, 1)
        y = monthly_rev['Amount_Clean']
        model = LinearRegression().fit(X, y)
        future_dates = pd.date_range(start='2026-01-01', periods=12, freq='ME')
        forecast_2026 = [max(0, model.predict([[len(monthly_rev) + i]])[0]) for i in range(12)]
        totaal_2026 = sum(forecast_2026)
        groei = ((totaal_2026 - omzet_2025_est) / omzet_2025_est * 100) if omzet_2025_est > 0 else 0
    else:
        totaal_2026, groei, forecast_2026, future_dates = 0, 0, [], []

    # 4. BTW ANALYSE
    btw_afdracht = 0 if is_vrijgesteld else (df_omzet['Amount_Clean'].sum() * 0.21)
    btw_voorbelasting = 0 if is_vrijgesteld else (df_totaal_kosten['Amount_Clean'].sum() * 0.21)
    btw_saldo = btw_afdracht - btw_voorbelasting

    # --- UI: KPI TILES ---
    st.subheader("📊 Strategisch Overzicht 2026")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Verwachte Omzet 2026", f"€ {totaal_2026:,.2f}")
    
    marge_ratio = (df_omzet['Amount_Clean'].sum() - df_totaal_kosten['Amount_Clean'].sum()) / df_omzet['Amount_Clean'].sum() if not df_omzet.empty else 0
    winst_2026 = totaal_2026 * marge_ratio
    kpi2.metric("Verwachte Winst 2026", f"€ {winst_2026:,.2f}")
    kpi3.metric("Groeipotentieel vs 2025", f"{groei:.1f}%", delta=f"{groei:.1f}%")

    # --- UI: TREND GRAFIEK ---
    st.markdown("---")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_rev['Date'], y=monthly_rev['Amount_Clean'], name="Omzet Historie", marker_color='#1f77b4'))
    if len(forecast_2026) > 0:
        fig.add_trace(go.Bar(x=future_dates, y=forecast_2026, name="Prognose 2026", marker_color='#ff7f0e'))
    fig.update_layout(title="Omzetontwikkeling & Forecast", template="plotly_white", barmode='group')
    st.plotly_chart(fig, use_container_width=True)

    # --- UI: BTW & KOSTEN PIE ---
    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🏦 BTW-Positie (Totaaloverzicht)")
        if is_vrijgesteld:
            st.warning("Dit bedrijf is BTW-vrijgesteld. Geen afdracht of teruggave.")
        else:
            st.write(f"**Te betalen (Omzet):** € {btw_afdracht:,.2f}")
            st.write(f"**Te ontvangen (Kosten):** € {btw_voorbelasting:,.2f}")
            if btw_saldo > 0:
                st.error(f"**Netto betalen aan Belastingdienst:** € {btw_saldo:,.2f}")
            else:
                st.success(f"**Netto te ontvangen:** € {abs(btw_saldo):,.2f}")

    with col_right:
        st.subheader("🍕 Kostenverdeling")
        labels = ['Inkoop', 'Auto', 'Huisvesting', 'Overige Bedrijfskosten']
        values = [df_inkoop['Amount_Clean'].sum(), df_auto['Amount_Clean'].sum(), 
                  df_huisvesting['Amount_Clean'].sum(), df_overig['Amount_Clean'].sum()]
        fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- UI: DETAIL TABEL ---
    st.markdown("---")
    st.subheader("📉 Winst- en Verlies Detail")
    details = pd.DataFrame({
        "Categorie": ["Omzet", "Inkoop", "Autokosten", "Huisvesting", "Overig"],
        "Bedrag": [df_omzet['Amount_Clean'].sum(), df_inkoop['Amount_Clean'].sum(), 
                   df_auto['Amount_Clean'].sum(), df_huisvesting['Amount_Clean'].sum(), 
                   df_overig['Amount_Clean'].sum()]
    })
    st.table(details.style.format({"Bedrag": "€ {:,.2f}"}))

else:
    st.info("Upload een Yuki CSV om de volledige analyse te starten.")
