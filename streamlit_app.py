import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Cruising Travel BI", layout="wide")
st.title("🚢 Cruising Travel - Business & Tax Intelligence")

with st.sidebar:
    st.header("Data Import")
    uploaded_file = st.file_uploader("Upload Yuki Transacties (CSV)", type=['csv'])

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
    
    # 2. CATEGORISEREN (Specifiek voor Reisbureaus)
    # We pakken de 8-serie voor omzet.
    df_omzet = df[df['Code_Str'].str.startswith('8')].copy()
    df_kosten = df[df['Code_Str'].str.startswith(('4', '7'))].copy()

    # 3. PROGNOSE LOGICA 2026
    monthly_data = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    recent_omzet = monthly_data.tail(24)
    
    if len(recent_omzet) > 3:
        X = np.arange(len(recent_omzet)).reshape(-1, 1)
        y = recent_omzet['Amount_Clean']
        model_omzet = LinearRegression().fit(X, y)
        
        future_dates = pd.date_range(start='2026-01-01', periods=12, freq='ME')
        forecast_2026 = [max(0, model_omzet.predict([[len(recent_omzet) + i]])[0]) for i in range(12)]
        
        totaal_omzet_2026 = sum(forecast_2026)
        omzet_2025 = monthly_data[monthly_data['Date'].dt.year == 2025]['Amount_Clean'].sum()
        groeifactor = ((totaal_omzet_2026 - omzet_2025) / omzet_2025 * 100) if omzet_2025 > 0 else 0
        piek_index = np.argmax(forecast_2026)
        piek_maand_naam = future_dates[piek_index].strftime('%B')
    else:
        totaal_omzet_2026, groeifactor, piek_maand_naam = 0, 0, "N/A"

    # 4. BTW LOGICA (STRENG OP 0% VOOR REIZEN)
    def calc_btw_strict(row):
        naam = str(row['Grootboekrekening']).lower()
        # Bij een reisbureau is bijna alles 0% of marge. Alleen rekenen als '21%' of 'hoog' er staat.
        if '21%' in naam or 'hoog' in naam:
            return row['Amount_Clean'] * 0.21
        return 0.0

    df_omzet['VAT_Due'] = df_omzet.apply(calc_btw_strict, axis=1)
    df_kosten['VAT_Reclaim'] = df_kosten['Amount_Clean'] * 0.21 # Voorbelasting op kosten vaak wel 21%

    # --- UI: KEY METRICS ---
    st.subheader("📊 Business Forecast 2026")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Verwachte Omzet 2026", f"€ {totaal_omzet_2026:,.2f}")
    c2.metric("Verwachte Marge (Winst)", f"€ {(totaal_omzet_2026 * 0.12):,.2f}") # 12% is gangbaar voor reisbureaus
    c3.metric("Groeipotentieel", f"{groeifactor:.1f}%", delta=f"{groeifactor:.1f}%")
    c4.metric("Piekmaand 2026", piek_maand_naam)

    # --- GRAFIEK: TREND ---
    st.markdown("---")
    st.subheader("📈 Omzet Ontwikkeling & Prognose")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly_data['Date'], y=monthly_data['Amount_Clean'], name="Historisch", line=dict(color='blue', width=3)))
    if totaal_omzet_2026 > 0:
        fig.add_trace(go.Scatter(x=future_dates, y=forecast_2026, name="Prognose 2026", line=dict(color='orange', dash='dot')))
    st.plotly_chart(fig, use_container_width=True)

    # --- BTW & CASHFLOW ---
    st.markdown("---")
    st.subheader("📅 BTW & Cashflow Overzicht")
    
    q_btw = (df_omzet.groupby(df_omzet['Date'].dt.to_period('Q'))['VAT_Due'].sum() - 
             df_kosten.groupby(df_kosten['Date'].dt.to_period('Q'))['VAT_Reclaim'].sum()).fillna(0)

    col_chart, col_msg = st.columns([2, 1])
    with col_chart:
        st.bar_chart(q_btw)
    with col_msg:
        afdracht = q_btw.iloc[-1] if not q_btw.empty else 0
        if afdracht > 0:
            st.error(f"BTW Afdracht: € {afdracht:,.2f}")
        else:
            st.success(f"BTW Teruggave: € {abs(afdracht):,.2f}")

    # --- KOSTEN ---
    st.subheader("💡 Grootste Kostenposten")
    st.table(df_kosten.groupby('Grootboekrekening')['Amount_Clean'].sum().sort_values(ascending=False).head(5))

else:
    st.info("Upload je Yuki CSV voor de volledige prognose.")
