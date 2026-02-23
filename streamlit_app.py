import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Cruising Travel Business Intelligence", layout="wide")
st.title("🚢 Cruising Travel - Business & Tax Intelligence")

with st.sidebar:
    st.header("Data Import")
    uploaded_file = st.file_uploader("Upload Yuki Transacties (CSV)", type=['csv'])
    st.info("Tip: Gebruik data van de laatste 2 jaar voor de meest nauwkeurige voorspelling.")

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
    
    # 2. CATEGORISEREN
    df_omzet = df[df['Code_Str'].str.startswith('8') | (df['Code_Str'] == '18400')].copy()
    df_kosten = df[df['Code_Str'].str.startswith(('4', '7'))].copy()

    # 3. PROGNOSE LOGICA (OMZET & WINST)
    monthly_data = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    monthly_costs = df_kosten.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    
    # Zorg dat we alleen recente data gebruiken voor de trend (laatste 24 maanden)
    recent_omzet = monthly_data.tail(24)
    
    if len(recent_omzet) > 3:
        # Trendlijn Omzet
        X = np.arange(len(recent_omzet)).reshape(-1, 1)
        y = recent_omzet['Amount_Clean']
        model_omzet = LinearRegression().fit(X, y)
        
        future_dates = pd.date_range(start='2026-01-01', periods=12, freq='ME')
        forecast_2026 = [max(0, model_omzet.predict([[len(recent_omzet) + i]])[0]) for i in range(12)]
        
        totaal_omzet_2026 = sum(forecast_2026)
        omzet_2025 = monthly_data[monthly_data['Date'].dt.year == 2025]['Amount_Clean'].sum()
        groeifactor = ((totaal_omzet_2026 - omzet_2025) / omzet_2025 * 100) if omzet_2025 > 0 else 0
    else:
        totaal_omzet_2026, groeifactor = 0, 0

    # --- UI: KEY METRICS ---
    st.subheader("📊 Business Forecast 2026")
    c1, c2, c3 = st.columns(3)
    c1.metric("Verwachte Jaaromzet 2026", f"€ {totaal_omzet_2026:,.2f}")
    c2.metric("Verwachte Winst (Bruto)", f"€ {(totaal_omzet_2026 * 0.15):,.2f}", help="Geschat op 15% marge")
    c3.metric("Groeipotentieel", f"{groeifactor:.1f}%", delta=f"{groeifactor:.1f}%")

    # --- GRAFIEK: OMZET TREND ---
    st.markdown("---")
    st.subheader("📈 Omzet Ontwikkeling & Prognose")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_data['Date'], y=monthly_data['Amount_Clean'], name="Historische Omzet", marker_color='#1f77b4'))
    if totaal_omzet_2026 > 0:
        fig.add_trace(go.Bar(x=future_dates, y=forecast_2026, name="Prognose 2026", marker_color='#ff7f0e'))
    
    fig.update_layout(template="plotly_white", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # --- BTW SECTIE (VERFIJND) ---
    st.markdown("---")
    st.subheader("📅 BTW & Cashflow Overzicht")
    
    def calc_btw_specific(row):
        naam = str(row['Grootboekrekening']).lower()
        if '0%' in naam or row['Code_Str'] == '18400': return 0.0
        return row['Amount_Clean'] * 0.21

    df_omzet['VAT_Due'] = df_omzet.apply(calc_btw_specific, axis=1)
    df_kosten['VAT_Reclaim'] = df_kosten['Amount_Clean'] * 0.21
    
    q_netto_btw = (df_omzet.groupby(df_omzet['Date'].dt.to_period('Q'))['VAT_Due'].sum() - 
                   df_kosten.groupby(df_kosten['Date'].dt.to_period('Q'))['VAT_Reclaim'].sum()).fillna(0)

    col_btw, col_alert = st.columns([2, 1])
    with col_btw:
        st.bar_chart(q_netto_btw)
    with col_alert:
        latest_val = q_netto_btw.iloc[-1] if not q_netto_btw.empty else 0
        if latest_val > 0:
            st.error(f"BTW Afdracht Q4: € {latest_val:,.2f}")
        else:
            st.success(f"BTW Teruggave Q4: € {abs(latest_val):,.2f}")

    # --- KOSTEN ANALYSE ---
    st.subheader("💡 Grootste Kostenposten")
    top_costs = df_kosten.groupby('Grootboekrekening')['Amount_Clean'].sum().sort_values(ascending=False).head(5)
    st.table(top_costs)

else:
    st.info("Upload de transacties van 2024-2025 voor de volledige business analyse.")
