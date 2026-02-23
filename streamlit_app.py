import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="AI Boekhouder Pro", layout="wide")
st.title("🏛️ Master Business Intelligence Dashboard")

with st.sidebar:
    st.header("⚙️ Instellingen")
    is_vrijgesteld = st.toggle("Bedrijf is BTW-vrijgesteld", value=False)
    uploaded_file = st.file_uploader("Upload Yuki CSV", type=['csv'])

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

    # 2. CATEGORIEËN
    df_omzet = df[df['Code_Str'].str.startswith('8') | (df['Code_Str'] == '18400')].copy()
    df_kosten = df[df['Code_Str'].str.startswith(('4', '6'))].copy()
    df_auto = df[df['Code_Str'].str.startswith('42')].copy()
    df_inkoop = df[df['Code_Str'].str.startswith('6')].copy()

    # 3. SLIMME PROGNOSE (Corrigeert de lage € 4.800 fout)
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    
    # Bereken het seizoenspatroon (bijv. mei hoog, juni laag)
    seasonal_profile = df_omzet.groupby(df_omzet['Date'].dt.month)['Amount_Clean'].mean()
    
    # Gebruik de omzet van het laatste volledige jaar (of schat 2025)
    omzet_2025_nu = df_omzet[df_omzet['Date'].dt.year == 2025]['Amount_Clean'].sum()
    laatste_maand = df_omzet[df_omzet['Date'].dt.year == 2025]['Date'].dt.month.max()
    
    if laatste_maand < 12:
        omzet_2025_full = (omzet_2025_nu / laatste_maand) * 12
    else:
        omzet_2025_full = omzet_2025_nu

    # Prognose 2026 gebaseerd op 2025 niveau + seizoensinvloeden
    totaal_2026 = omzet_2025_full 
    forecast_2026_list = [(seasonal_profile.get(m, seasonal_profile.mean()) / seasonal_profile.sum()) * totaal_2026 for m in range(1, 13)]
    future_dates = pd.date_range(start='2026-01-01', periods=12, freq='ME')

    # 4. KPI'S
    st.subheader("📊 Strategisch Dashboard 2026")
    k1, k2, k3 = st.columns(3)
    
    marge_ratio = (df_omzet['Amount_Clean'].sum() - df_kosten['Amount_Clean'].sum()) / df_omzet['Amount_Clean'].sum() if not df_omzet.empty else 0.5
    winst_2026 = totaal_2026 * marge_ratio
    
    k1.metric("Verwachte Omzet 2026", f"€ {totaal_2026:,.2f}")
    k2.metric("Verwachte Winst 2026", f"€ {winst_2026:,.2f}")
    
    omzet_2024 = df_omzet[df_omzet['Date'].dt.year == 2024]['Amount_Clean'].sum()
    groei = ((totaal_2026 - omzet_2024) / omzet_2024 * 100) if omzet_2024 > 0 else 0
    k3.metric("Groeipotentieel (vs 2024)", f"{groei:.1f}%")

    # --- GRAFIEK: BLAUW (HISTORIE) VS ORANJE (PROGNOSE) ---
    st.markdown("---")
    st.subheader("📈 Omzet Trend: Historie vs. Prognose per Maand")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_rev['Date'], y=monthly_rev['Amount_Clean'], name="Historie (Blauw)", marker_color='#1f77b4'))
    fig.add_trace(go.Bar(x=future_dates, y=forecast_2026_list, name="Prognose 2026 (Oranje)", marker_color='#ff7f0e'))
    fig.update_layout(template="plotly_white", barmode='group', height=450)
    st.plotly_chart(fig, use_container_width=True)

    # --- BTW KWARTAAL PLANNER ---
    st.markdown("---")
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("🏦 BTW-Positie per Kwartaal")
        q_rows = []
        for q in range(1, 5):
            m_idx = [0,1,2] if q==1 else [3,4,5] if q==2 else [6,7,8] if q==3 else [9,10,11]
            q_rev = sum([forecast_2026_list[i] for i in m_idx])
            q_cost = q_rev * (1 - marge_ratio)
            afdracht = q_rev * 0.21 if not is_vrijgesteld else 0
            voorbelasting = q_cost * 0.21 if not is_vrijgesteld else 0
            q_rows.append({"Kwartaal": f"Q{q} 2026", "Omzet": f"€ {q_rev:,.0f}", "Netto BTW": f"€ {afdracht-voorbelasting:,.2f}"})
        st.table(pd.DataFrame(q_rows))

    with c_right:
        st.subheader("🍕 Kostenverdeling (Exploitatie)")
        labels = ['Inkoop', 'Auto', 'Overig']
        values = [df_inkoop['Amount_Clean'].sum(), df_auto['Amount_Clean'].sum(), (df_kosten['Amount_Clean'].sum() - df_inkoop['Amount_Clean'].sum() - df_auto['Amount_Clean'].sum())]
        fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- DETAIL TABEL ---
    st.markdown("---")
    st.subheader("📉 Winst- en Verlies Detail (Totaaloverzicht)")
    details = pd.DataFrame({
        "Categorie": ["Netto-omzet", "Kostprijs omzet", "Autokosten", "Andere Bedrijfslasten"],
        "Bedrag": [df_omzet['Amount_Clean'].sum(), df_inkoop['Amount_Clean'].sum(), df_auto['Amount_Clean'].sum(), df_kosten['Amount_Clean'].sum() - df_inkoop['Amount_Clean'].sum() - df_auto['Amount_Clean'].sum()]
    })
    st.table(details.style.format({"Bedrag": "€ {:,.2f}"}))

else:
    st.info("Upload de Yuki CSV om de analyse te starten.")
