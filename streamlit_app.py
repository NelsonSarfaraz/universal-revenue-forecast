import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Cruising Travel Intelligence", layout="wide")
st.title("🚢 Cruising Travel - Finance & Tax Intelligence")

with st.sidebar:
    st.header("Data Import")
    uploaded_file = st.file_uploader("Upload Yuki Transacties (CSV)", type=['csv'])

if uploaded_file:
    # 1. DATA LADEN (Encoding fix voor Yuki)
    df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='iso-8859-1')
    df.columns = df.columns.str.strip()

    def clean_val(x):
        if pd.isna(x): return 0.0
        x = str(x).replace('"', '').replace('.', '').replace(',', '.')
        try: return float(x)
        except: return 0.0

    df['Amount_Clean'] = df['Bedrag'].apply(clean_val).abs() # Omzet positief maken
    df['Date'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
    df['Code_Str'] = df['Code'].astype(str).str.strip()
    
    # 2. SLIMME CATEGORISERING OP BASIS VAN JOUW BESTAND
    # Omzet (8-serie) en BTW-rekeningen voor 0%
    df_omzet = df[df['Code_Str'].str.startswith('8') | (df['Code_Str'] == '18400')].copy()
    df_kosten = df[df['Code_Str'].str.startswith(('4', '7'))].copy()

    # 3. BTW LOGICA: REISBUREAU REGELING (0%)
    def calc_btw_specific(row):
        naam = str(row['Grootboekrekening']).lower()
        code = row['Code_Str']
        bedrag = row['Amount_Clean']
        
        # Als het code 18400 is of er staat 0% in de naam -> 0 BTW
        if '0%' in naam or code == '18400' or 'vrijgesteld' in naam:
            return 0.0
        # Alleen BTW rekenen als het echt om belaste omzet gaat (bijv. administratiekosten)
        elif 'hoog' in naam or '21%' in naam:
            return bedrag * 0.21
        return 0.0

    df_omzet['VAT_Due'] = df_omzet.apply(calc_btw_specific, axis=1)
    
    # Kosten: We rekenen 21% BTW over de meeste 4-rekeningen (voorbelasting)
    df_kosten['VAT_Reclaim'] = df_kosten['Amount_Clean'] * 0.21

    # 4. PROGNOSE 2026 (Focus op recente trend)
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    # Filter op de laatste 24 maanden voor een betere trend
    recent_data = monthly_rev.tail(24)
    
    if len(recent_data) > 3:
        X = np.arange(len(recent_data)).reshape(-1, 1)
        y = recent_data['Amount_Clean']
        model = LinearRegression().fit(X, y)
        
        future_dates = pd.date_range(start='2026-01-01', periods=12, freq='ME')
        forecast_2026 = [max(0, model.predict([[len(recent_data) + i]])[0]) for i in range(12)]
        totaal_2026 = sum(forecast_2026)
        
        last_year_total = monthly_rev[monthly_rev['Date'].dt.year == 2025]['Amount_Clean'].sum()
        groeifactor = ((totaal_2026 - last_year_total) / last_year_total * 100) if last_year_total > 0 else 0
        piek_maand = future_dates[np.argmax(forecast_2026)].strftime('%B')
    else:
        totaal_2026, groeifactor, piek_maand = 0, 0, "Niet genoeg data"

    # --- DASHBOARD ---
    st.subheader("📊 Strategische Prognose 2026")
    c1, c2, c3 = st.columns(3)
    c1.metric("Verwachte Omzet 2026", f"€ {totaal_2026:,.2f}")
    c2.metric("Groeifactor", f"{groeifactor:.1f}%")
    c3.metric("Piekmaand 2026", piek_maand)

    st.markdown("---")
    st.subheader("📅 BTW & Cashflow (Kwartaal)")
    
    # BTW per Kwartaal
    df_omzet['Q'] = df_omzet['Date'].dt.to_period('Q')
    df_kosten['Q'] = df_kosten['Date'].dt.to_period('Q')
    
    q_btw_due = df_omzet.groupby('Q')['VAT_Due'].sum()
    q_btw_reclaim = df_kosten.groupby('Q')['VAT_Reclaim'].sum()
    q_netto_btw = (q_btw_due - q_btw_reclaim).fillna(0)

    st.bar_chart(q_netto_btw)

    current_q_val = q_netto_btw.iloc[-1] if not q_netto_btw.empty else 0
    if current_q_val > 0:
        st.error(f"⚠️ **Reserveren voor BTW:** € {current_q_val:,.2f}")
    else:
        st.success(f"✅ **Verwachte BTW Teruggave:** € {abs(current_q_val):,.2f}")

    st.subheader("Top Kostenposten (Inzicht)")
    st.table(df_kosten.groupby('Grootboekrekening')['Amount_Clean'].sum().sort_values(ascending=False).head(5))

else:
    st.info("Upload de Yuki-transacties voor de Reisbureau-specifieke analyse.")
