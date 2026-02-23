import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Pro AI Dashboard", layout="wide")
st.title("🚀 Full Business Intelligence Dashboard")

with st.sidebar:
    st.header("⚙️ Instellingen")
    is_vrijgesteld = st.toggle("Bedrijf is BTW-vrijgesteld", value=False)
    uploaded_file = st.file_uploader("Upload Yuki CSV", type=['csv'])

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

    # 2. CATEGORISERING
    df_omzet = df[df['Code_Str'].str.startswith('8') | (df['Code_Str'] == '18400')].copy()
    df_inkoop = df[df['Code_Str'].str.startswith('6')].copy()
    df_auto = df[df['Code_Str'].str.startswith('42')].copy()
    df_huisvesting = df[df['Code_Str'].str.startswith('43')].copy()
    df_overig = df[df['Code_Str'].str.startswith(('40', '41', '44', '45', '46', '47', '48', '49'))].copy()
    df_totaal_kosten = df[df['Code_Str'].str.startswith(('4', '6'))].copy()

    # 3. PROGNOSE & SEIZOEN LOGICA
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    seasonal_profile = df_omzet.groupby(df_omzet['Date'].dt.month)['Amount_Clean'].mean()
    avg_m = df_omzet['Amount_Clean'].mean()
    full_year_profile = [seasonal_profile.get(m, avg_m) for m in range(1, 13)]
    
    totaal_2026 = sum(full_year_profile)
    marge_ratio = (df_omzet['Amount_Clean'].sum() - df_totaal_kosten['Amount_Clean'].sum()) / df_omzet['Amount_Clean'].sum() if not df_omzet.empty else 0.5
    winst_2026 = totaal_2026 * marge_ratio

    # --- UI: HOOFD KPI'S (HET OVERZICHT VAN VROEGER) ---
    st.subheader("📋 Financieel Overzicht 2026")
    k1, k2, k3 = st.columns(3)
    k1.metric("Verwachte Omzet 2026", f"€ {totaal_2026:,.2f}")
    k2.metric("Verwachte Winst 2026", f"€ {winst_2026:,.2f}")
    
    # Groei berekening
    omzet_2025 = df_omzet[df_omzet['Date'].dt.year == 2025]['Amount_Clean'].sum()
    groei = ((totaal_2026 - omzet_2025) / omzet_2025 * 100) if omzet_2025 > 0 else 0
    k3.metric("Groeipotentieel", f"{groei:.1f}%")

    # --- UI: GRAFIEK (MAANDELIJKSE TREND) ---
    st.markdown("---")
    st.subheader("📈 Seizoenspatroon & Drukte")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=['Jan','Feb','Mrt','Apr','Mei','Jun','Jul','Aug','Sep','Okt','Nov','Dec'], 
                             y=full_year_profile, mode='lines+markers', name="Omzet Flow",
                             line=dict(color='#1f77b4', width=4, shape='spline')))
    fig.update_layout(template="plotly_white", height=400)
    st.plotly_chart(fig, use_container_width=True)

    # --- UI: BTW & KOSTEN (TAARTDIAGRAM) ---
    st.markdown("---")
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("🍕 Kostenverdeling")
        labels = ['Inkoop', 'Auto', 'Huisvesting', 'Overig']
        values = [df_inkoop['Amount_Clean'].sum(), df_auto['Amount_Clean'].sum(), 
                  df_huisvesting['Amount_Clean'].sum(), df_overig['Amount_Clean'].sum()]
        fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        st.plotly_chart(fig_pie, use_container_width=True)

    with c_right:
        st.subheader("🏦 BTW Planner (Kwartaal)")
        q_rows = []
        for q in range(1, 5):
            months = [1,2,3] if q==1 else [4,5,6] if q==2 else [7,8,9] if q==3 else [10,11,12]
            q_rev = sum([full_year_profile[m-1] for m in months])
            q_cost = q_rev * (1 - marge_ratio)
            afdracht = q_rev * 0.21 if not is_vrijgesteld else 0
            voorbelasting = q_cost * 0.21 if not is_vrijgesteld else 0
            q_rows.append({"Kwartaal": f"Q{q}", "Omzet": f"€ {q_rev:,.0f}", "TE BETALEN": f"€ {afdracht-voorbelasting:,.2f}"})
        st.table(pd.DataFrame(q_rows))

    # --- UI: DE DETAIL TABEL (ZOALS VROEGER) ---
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
    st.info("Upload de Yuki CSV voor het volledige overzicht.")
