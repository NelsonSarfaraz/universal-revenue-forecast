import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Pagina instellingen
st.set_page_config(page_title="AI Boekhouder Pro (Full Scan)", layout="wide")
st.title("🏛️ Master Business Intelligence Dashboard")

with st.sidebar:
    st.header("⚙️ Instellingen")
    is_vrijgesteld = st.toggle("Bedrijf is BTW-vrijgesteld", value=False)
    uploaded_file = st.file_uploader("Upload Yuki CSV", type=['csv'])

if uploaded_file:
    # 1. DATA LADEN & SCHOONMAKEN
    df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='iso-8859-1')
    df.columns = df.columns.str.strip()

    def clean_val(x):
        if pd.isna(x): return 0.0
        # Haal tekens weg, behandel punt als duizend-separator en komma als decimaal
        x = str(x).replace('"', '').replace('.', '').replace(',', '.')
        try: return float(x)
        except: return 0.0

    # We houden rekening met positieve/negatieve getallen voor Winst & Verlies
    df['Amount_Clean'] = df['Bedrag'].apply(clean_val)
    df['Date'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date')
    df['Code_Str'] = df['Code'].astype(str).str.strip()
    df['Hoofdcode'] = df['Code_Str'].str[0] # Pak het eerste cijfer (0-9)

    # 2. CATEGORIEËN VERDELING (0 t/m 9)
    # Voor de winst kijken we naar de Resultatenrekening (4 t/m 9)
    # Omzet is meestal 8xxx
    df_omzet = df[df['Code_Str'].str.startswith('8')].copy()
    
    # Kosten zijn 4, 6, 7 en soms 9 (als last)
    # We berekenen de winst door alle W&V posten te salderen
    df_wv = df[df['Hoofdcode'].isin(['4', '6', '7', '8', '9'])].copy()
    werkelijke_winst_totaal = df_wv['Amount_Clean'].sum() * -1 # Yuki credits zijn vaak negatief

    # 3. PROGNOSE LOGICA
    last_date = df['Date'].max()
    one_year_ago = last_date - pd.DateOffset(years=1)
    
    recent_omzet = df_omzet[df_omzet['Date'] > one_year_ago]['Amount_Clean'].sum()
    totaal_2026 = abs(recent_omzet) if recent_omzet != 0 else (abs(df_omzet['Amount_Clean'].sum()) / 2)

    # Marge bepalen op basis van de hele historie (4,6,7,8,9)
    tot_omzet_hist = abs(df_omzet['Amount_Clean'].sum())
    if tot_omzet_hist > 0:
        marge_ratio = (tot_omzet_hist - abs(df[df['Hoofdcode'].isin(['4', '6', '7'])]['Amount_Clean'].sum())) / tot_omzet_hist
    else:
        marge_ratio = 0.2

    winst_2026 = totaal_2026 * marge_ratio

    # Seizoenspatroon (Anti-Gat juli fix)
    seasonal_profile = df_omzet.groupby(df_omzet['Date'].dt.month)['Amount_Clean'].mean().abs()
    overall_mean = seasonal_profile.mean() if not seasonal_profile.empty else 1.0
    seasonal_profile = seasonal_profile.reindex(range(1, 13)).fillna(overall_mean).replace(0, overall_mean)
    
    forecast_2026_list = [(seasonal_profile.get(m) / seasonal_profile.sum()) * totaal_2026 for m in range(1, 13)]
    future_dates = pd.date_range(start=pd.Timestamp(2026, 1, 1), periods=12, freq='ME')

    # --- LAYOUT ---
    st.subheader(f"📊 Strategisch Overzicht 2026 (Full Scan 0-9)")
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Geprojecteerde Omzet", f"€ {totaal_2026:,.2f}")
    k2.metric("Geprojecteerde Winst", f"€ {winst_2026:,.2f}")
    k3.metric("Scan Status", "Volledig (0-9)")

    # GRAFIEK
    st.markdown("---")
    st.subheader("📈 Omzet Trend: Historie vs. Prognose")
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().abs().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_rev['Date'].tail(24), y=monthly_rev['Amount_Clean'].tail(24), name="Historie", marker_color='#1f77b4'))
    fig.add_trace(go.Bar(x=future_dates, y=forecast_2026_list, name="Prognose 2026", marker_color='#ff7f0e'))
    fig.update_layout(template="plotly_white", barmode='group', height=400)
    st.plotly_chart(fig, use_container_width=True)

    # BTW EN KOSTEN
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏦 BTW-Positie (Inclusief Balans)")
        q_rows = []
        for q in range(1, 5):
            m_idx = [0,1,2] if q==1 else [3,4,5] if q==2 else [6,7,8] if q==3 else [9,10,11]
            q_rev = sum([forecast_2026_list[i] for i in m_idx])
            q_tax = q_rev * 0.21 if not is_vrijgesteld else 0
            q_rows.append({"Kwartaal": f"Q{q} 2026", "Omzet": f"€ {q_rev:,.0f}", "Te reserveren": f"€ {q_tax:,.2f}"})
        st.table(pd.DataFrame(q_rows))

    with c2:
        st.subheader("🍕 Kostenverdeling (Codes 4, 6, 7)")
        kosten_labels = ['Bedrijfskosten (4)', 'Inkoop (6)', 'Overig (7/9)']
        kosten_values = [
            abs(df[df['Hoofdcode'] == '4']['Amount_Clean'].sum()),
            abs(df[df['Hoofdcode'] == '6']['Amount_Clean'].sum()),
            abs(df[df['Hoofdcode'].isin(['7', '9'])]['Amount_Clean'].sum())
        ]
        fig_pie = go.Figure(data=[go.Pie(labels=kosten_labels, values=kosten_values, hole=.3)])
        st.plotly_chart(fig_pie, use_container_width=True)

    # DE COMPLETE TABEL 0-9
    st.markdown("---")
    st.subheader("📉 Volledige Grootboek Analyse (Totaaloverzicht)")
    full_table = []
    namen = {
        '0': 'Vaste Activa (Inventaris/Auto)',
        '1': 'Vlottende Activa (Bank/Debiteuren)',
        '2': 'Kortlopende Schulden (BTW/Crediteuren)',
        '3': 'Eigen Vermogen',
        '4': 'Bedrijfslasten (Huur/Personeel)',
        '5': 'Niet in gebruik (Tussenrekeningen)',
        '6': 'Kostprijs van de Omzet (Inkoop)',
        '7': 'Financiële Baten/Lasten (Rente)',
        '8': 'Netto-omzet',
        '9': 'Resultaatbestemming/Privé'
    }
    for code in sorted(df['Hoofdcode'].unique()):
        totaal = df[df['Hoofdcode'] == code]['Amount_Clean'].sum()
        full_table.append({"Serie": code, "Omschrijving": namen.get(code, "Overig"), "Totaal Saldo": totaal})
    
    st.table(pd.DataFrame(full_table).style.format({"Totaal Saldo": "€ {:,.2f}"}))

else:
    st.info("Upload de Yuki CSV voor een volledige 0-9 scan.")
