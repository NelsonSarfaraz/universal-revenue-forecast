import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- PAGINA INSTELLINGEN ---
st.set_page_config(page_title="Universal Finance Intelligence", layout="wide")

st.title("📈 Smart Finance & Tax Intelligence")
st.markdown("Geautomatiseerde analyse van winst, kosten en BTW-reserveringen.")

# --- SIDEBAR VOOR UPLOAD ---
with st.sidebar:
    st.header("Data Import")
    uploaded_file = st.file_uploader("Upload Yuki Transacties (CSV)", type=['csv'])
    st.info("Deze tool filtert automatisch de relevante grootboekrekeningen voor omzet en kosten.")

if uploaded_file:
    # 1. DATA INLADEN & OPSCHONEN
    # FIXED: encoding naar 'iso-8859-1' om de UnicodeDecodeError op te lossen
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='iso-8859-1')
    except Exception as e:
        st.error(f"Er ging iets mis bij het inladen: {e}")
        st.stop()
    
    # Kolomnamen opschonen (verwijder onzichtbare spaties)
    df.columns = df.columns.str.strip()

    # Bedrag kolom opschonen (verwijdert ", . en zorgt voor getallen)
    def clean_currency(x):
        if pd.isna(x): return 0.0
        # Haal aanhalingstekens en duizendtallen (punten) weg, vervang komma door punt
        x = str(x).replace('"', '').replace('.', '').replace(',', '.')
        try:
            return float(x)
        except:
            return 0.0

    df['Amount_Clean'] = df['Bedrag'].apply(clean_currency)
    df['Date'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
    df['Code_Str'] = df['Code'].astype(str).str.strip()
    
    # 2. SLIMME CATEGORISERING
    # Omzet begint met 8, Kosten met 4 of 7.
    df_omzet = df[df['Code_Str'].str.startswith('8')].copy()
    df_kosten = df[df['Code_Str'].str.startswith(('4', '7'))].copy()

    # 3. BTW LOGICA OP MAAT
    def calc_btw_logic(row):
        naam = str(row['Grootboekrekening']).lower()
        bedrag = row['Amount_Clean']
        if 'laag' in naam or '9%' in naam:
            return bedrag * 0.09
        elif 'hoog' in naam or '21%' in naam or row['Code_Str'].startswith('8'):
            return bedrag * 0.21
        return 0.0

    df_omzet['VAT_Estimated'] = df_omzet.apply(calc_btw_logic, axis=1)
    df_kosten['VAT_Reclaim'] = df_kosten['Amount_Clean'] * 0.21

    # --- DASHBOARD WEERGAVE ---
    total_rev = df_omzet['Amount_Clean'].sum()
    total_exp = df_kosten['Amount_Clean'].sum()
    net_profit = total_rev - total_exp
    estimated_vat_due = df_omzet['VAT_Estimated'].sum() - df_kosten['VAT_Reclaim'].sum()

    # Top Metrics
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Totale Omzet (Netto)", f"€ {total_rev:,.2f}")
    m2.metric("Operationele Kosten", f"€ {total_exp:,.2f}")
    m3.metric("Netto Resultaat", f"€ {net_profit:,.2f}")

    # BTW Alert Box
    st.markdown("---")
    st.subheader("🚨 Cashflow Management: Belasting")
    if estimated_vat_due > 0:
        st.warning(f"**BTW Reservering:** Op basis van deze data moet er circa **€ {estimated_vat_due:,.2f}** gereserveerd worden voor de afdracht.")
    else:
        st.success(f"**BTW Teruggave:** Je hebt meer kosten met BTW gemaakt dan omzet. Geschatte teruggave: **€ {abs(estimated_vat_due):,.2f}**.")

    # Visualisatie: Inkomsten vs Uitgaven over tijd
    st.subheader("Inkomsten vs Uitgaven Trend")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_omzet['Date'], y=df_omzet['Amount_Clean'], name="Omzet", mode='lines+markers', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=df_kosten['Date'], y=df_kosten['Amount_Clean'], name="Kosten", mode='lines+markers', line=dict(color='red')))
    st.plotly_chart(fig, use_container_width=True)

    # Tabel met de grootste kostenposten
    st.subheader("Top Kostenposten per Grootboek")
    top_costs = df_kosten.groupby('Grootboekrekening')['Amount_Clean'].sum().sort_values(ascending=False).head(10)
    st.table(top_costs)

else:
    st.info("Upload het financiële exportbestand om de AI-analyse te starten.")
