import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

# --- CONFIGURATIE & STYLING ---
st.set_page_config(page_title="Universal Finance Analytics", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { background-color: #004b91; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 Smart Revenue Forecasting Tool")
st.subheader("Data-driven inzichten en seizoensgebonden prognoses")

# --- ZIJB BALK (SIDEBAR) ---
with st.sidebar:
    st.header("Instellingen")
    st.info("Upload uw financiële export (.csv) om de analyse te starten.")
    uploaded_file = st.file_uploader("Kies bestand", type=['csv'])

# --- DATA VERWERKING ---
def clean_finance_data(file):
    # Automatische detectie van scheidingsteken
    df = pd.read_csv(file, sep=None, engine='python', encoding='iso-8859-1')
    df.columns = df.columns.str.strip()
    
    # Valuta opschonen (universele logica)
    def to_float(v):
        if pd.isna(v): return 0.0
        s = str(v).replace('.', '').replace(',', '.')
        try: return abs(float(s))
        except: return 0.0

    # Zoek naar kolomnamen die lijken op Bedrag en Datum
    col_bedrag = next((c for c in df.columns if 'bedrag' in c.lower()), None)
    col_datum = next((c for c in df.columns if 'datum' in c.lower() or 'date' in c.lower()), None)
    
    if col_bedrag and col_datum:
        df['Amount'] = df[col_bedrag].apply(to_float)
        df['Date'] = pd.to_datetime(df[col_datum], dayfirst=True, errors='coerce')
        # Filter op omzetrekeningen (meestal beginnend met 8)
        if 'Grootboekrekening Code' in df.columns:
            df = df[df['Grootboekrekening Code'].astype(str).str.startswith('8')]
        return df.dropna(subset=['Date'])
    return None

# --- DASHBOARD LOGICA ---
if uploaded_file:
    df = clean_finance_data(uploaded_file)
    
    if df is not None:
        # Groeperen per maand
        monthly = df.resample('ME', on='Date')['Amount'].sum().reset_index()
        
        # Seizoensinvloeden berekenen
        monthly['month'] = monthly['Date'].dt.month
        seasonal_factors = monthly.groupby('month')['Amount'].mean()
        avg_revenue = monthly['Amount'].mean()
        
        # Trendlijn (Linear Regression)
        X = np.arange(len(monthly)).reshape(-1, 1)
        y = monthly['Amount']
        model = LinearRegression().fit(X, y)
        
        # Prognose 2026
        future_dates = pd.date_range(start='2026-01-01', periods=12, freq='ME')
        forecast = []
        for i, date in enumerate(future_dates):
            base_trend = model.predict([[len(monthly) + i]])[0]
            factor = seasonal_factors.get(date.month, avg_revenue) / avg_revenue if avg_revenue > 0 else 1
            forecast.append(max(0, base_trend * factor))
        
        forecast_df = pd.DataFrame({'Date': future_dates, 'Amount': forecast})

        # --- VISUALISATIE ---
        fig = go.Figure()
        fig.add_trace(go.Bar(x=monthly['Date'], y=monthly['Amount'], name='Historische Omzet', marker_color='#1f77b4'))
        fig.add_trace(go.Bar(x=forecast_df['Date'], y=forecast_df['Amount'], name='Prognose 2026', marker_color='#ff7f0e'))
        
        fig.update_layout(
            title="Omzet Analyse & Predictive Forecast",
            xaxis_title="Periode",
            yaxis_title="Omzet (€)",
            hovermode="x unified",
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Statistieken
        col1, col2 = st.columns(2)
        col1.metric("Verwachte Jaaromzet 2026", f"€ {sum(forecast):,.2f}")
        col2.metric("Gemiddelde Maandomzet", f"€ {avg_revenue:,.2f}")
        
    else:
        st.error("Kon de kolommen 'Datum' en 'Bedrag' niet vinden in het bestand.")
else:
    st.info("👋 Welkom! Upload een financiële export aan de linkerkant om de analyse te genereren.")
