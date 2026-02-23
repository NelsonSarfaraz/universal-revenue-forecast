import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Pro Finance & Tax Intelligence", layout="wide")
st.title("📈 Smart Finance & Tax Intelligence")

with st.sidebar:
    st.header("Data Import")
    uploaded_file = st.file_uploader("Upload Yuki Transacties (CSV)", type=['csv'])

if uploaded_file:
    # 1. DATA LADEN
    df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='iso-8859-1')
    df.columns = df.columns.str.strip()

    # Bedrag opschonen en "ompolen"
    def clean_val(x):
        if pd.isna(x): return 0.0
        x = str(x).replace('"', '').replace('.', '').replace(',', '.')
        try: return float(x)
        except: return 0.0

    df['Amount_Raw'] = df['Bedrag'].apply(clean_val)
    df['Date'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
    df['Code_Str'] = df['Code'].astype(str).str.strip()
    
    # FILTER: Omzet (8xxx) moet POSITIEF zijn voor de weergave, Kosten (4xxx/7xxx) ook.
    # Yuki zet omzet vaak als negatief (credit), dus we gebruiken abs()
    df_omzet = df[df['Code_Str'].str.startswith('8')].copy()
    df_omzet['Amount_Clean'] = df_omzet['Amount_Raw'].abs() 

    df_kosten = df[df['Code_Str'].str.startswith(('4', '7'))].copy()
    df_kosten['Amount_Clean'] = df_kosten['Amount_Raw'].abs()

    # 2. BTW LOGICA PER KWARTAAL
    df_omzet['BTW_Hoog'] = df_omzet['Amount_Clean'] * 0.21
    df_kosten['BTW_Terug'] = df_kosten['Amount_Clean'] * 0.21
    
    df['Kwartaal'] = df['Date'].dt.to_period('Q')
    
    # 3. PROGNOSE 2026 BEREKENING
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    if len(monthly_rev) > 3:
        X = np.arange(len(monthly_rev)).reshape(-1, 1)
        y = monthly_rev['Amount_Clean']
        model = LinearRegression().fit(X, y)
        
        future_dates = pd.date_range(start='2026-01-01', periods=12, freq='ME')
        forecast_2026 = [max(0, model.predict([[len(monthly_rev) + i]])[0]) for i in range(12)]
        
        totaal_2026 = sum(forecast_2026)
        vorig_jaar_omzet = monthly_rev.iloc[-12:]['Amount_Clean'].sum() if len(monthly_rev) >= 12 else monthly_rev['Amount_Clean'].sum()
        groeifactor = ((totaal_2026 - vorig_jaar_omzet) / vorig_jaar_omzet) * 100 if vorig_jaar_omzet > 0 else 0
        piek_maand = future_dates[np.argmax(forecast_2026)].strftime('%B')
    else:
        totaal_2026, groeifactor, piek_maand = 0, 0, "Onvoldoende data"

    # --- UI WEERGAVE ---
    st.subheader("📊 Key Performance Indicators 2026")
    k1, k2, k3 = st.columns(3)
    k1.metric("Prognose Jaaromzet 2026", f"€ {totaal_2026:,.2f}")
    k2.metric("Groeifactor vs Vorig Jaar", f"{groeifactor:.1f}%", delta=f"{groeifactor:.1f}%")
    k3.metric("Verwachte Piekmaand", piek_maand)

    st.markdown("---")
    st.subheader("🏢 Huidige Financiële Status")
    m1, m2, m3 = st.columns(3)
    m1.metric("Totale Omzet (Netto)", f"€ {df_omzet['Amount_Clean'].sum():,.2f}")
    m2.metric("Operationele Kosten", f"€ {df_kosten['Amount_Clean'].sum():,.2f}")
    m3.metric("Netto Winst", f"€ {(df_omzet['Amount_Clean'].sum() - df_kosten['Amount_Clean'].sum()):,.2f}")

    # BTW PER KWARTAAL
    st.markdown("---")
    st.subheader("📅 BTW Reservering per Kwartaal")
    # Berekening per kwartaal
    q_omzet = df_omzet.groupby(df_omzet['Date'].dt.to_period('Q'))['Amount_Clean'].sum() * 0.21
    q_kosten = df_kosten.groupby(df_kosten['Date'].dt.to_period('Q'))['Amount_Clean'].sum() * 0.21
    q_btw = (q_omzet - q_kosten).fillna(0)
    
    st.bar_chart(q_btw)
    
    latest_q = q_btw.index[-1]
    st.warning(f"⚠️ **Actie vereist:** Voor het laatste kwartaal ({latest_q}) moet er circa **€ {q_btw.iloc[-1]:,.2f}** gereserveerd worden.")

    # TOP KOSTEN
    st.subheader("Top Kostenposten")
    st.table(df_kosten.groupby('Grootboekrekening')['Amount_Clean'].sum().sort_values(ascending=False).head(10))

else:
    st.info("Upload de Yuki-transacties om de volledige analyse te zien.")
