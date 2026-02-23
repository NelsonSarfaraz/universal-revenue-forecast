import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Pagina instellingen
st.set_page_config(page_title="AI Boekhouder Pro", layout="wide")
st.title("🏛️ Master Business Intelligence Dashboard")

with st.sidebar:
    st.header("⚙️ Instellingen")
    is_vrijgesteld = st.toggle("Bedrijf is BTW-vrijgesteld", value=False)
    uploaded_file = st.file_uploader("Upload Yuki CSV", type=['csv'])

if uploaded_file:
    # 1. DATA LADEN & OPSCHONEN
    df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='iso-8859-1')
    df.columns = df.columns.str.strip()

    def clean_val(x):
        if pd.isna(x): return 0.0
        x = str(x).replace('"', '').replace('.', '').replace(',', '.')
        try: return float(x)
        except: return 0.0

    df['Amount_Clean'] = df['Bedrag'].apply(clean_val).abs()
    df['Date'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date')
    df['Code_Str'] = df['Code'].astype(str).str.strip()

    # 2. CATEGORIEËN
    df_omzet = df[df['Code_Str'].str.startswith('8') | (df['Code_Str'] == '18400')].copy()
    df_kosten = df[df['Code_Str'].str.startswith(('4', '6'))].copy()
    df_auto = df[df['Code_Str'].str.startswith('42')].copy()
    df_inkoop = df[df['Code_Str'].str.startswith('6')].copy()

    # 3. SLIMME PROGNOSE LOGICA
    last_date = df['Date'].max()
    one_year_ago = last_date - pd.DateOffset(years=1)
    two_years_ago = one_year_ago - pd.DateOffset(years=1)
    
    recent_omzet_data = df_omzet[df_omzet['Date'] > one_year_ago]
    totaal_omzet_laatste_jaar = recent_omzet_data['Amount_Clean'].sum()
    omzet_vorig_jaar = df_omzet[(df_omzet['Date'] > two_years_ago) & (df_omzet['Date'] <= one_year_ago)]['Amount_Clean'].sum()

    if totaal_omzet_laatste_jaar == 0:
        aantal_jaren = max(1, (df['Date'].max() - df['Date'].min()).days / 365)
        totaal_2026 = df_omzet['Amount_Clean'].sum() / aantal_jaren
    else:
        totaal_2026 = totaal_omzet_laatste_jaar

    # Data Guard voor de groei
    if omzet_vorig_jaar < 1000:
        groei = 0.0
    else:
        raw_groei = ((totaal_2026 - omzet_vorig_jaar) / omzet_vorig_jaar * 100)
        groei = min(raw_groei, 15.0) 
    
    marge_ratio = (df_omzet['Amount_Clean'].sum() - df_kosten['Amount_Clean'].sum()) / df_omzet['Amount_Clean'].sum() if not df_omzet.empty else 0.1
    winst_2026 = totaal_2026 * marge_ratio

    # Seizoenspatroon & Grafiek Data
    seasonal_profile = df_omzet.groupby(df_omzet['Date'].dt.month)['Amount_Clean'].mean()
    if seasonal_profile.empty:
        seasonal_profile = pd.Series([1]*12, index=range(1,13))
    
    forecast_2026_list = [(seasonal_profile.get(m, seasonal_profile.mean()) / seasonal_profile.sum()) * totaal_2026 for m in range(1, 13)]
    future_dates = pd.date_range(start=pd.Timestamp(2026, 1, 1), periods=12, freq='ME')
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()

    # --- LAYOUT START ---

    # A. KPI'S (BOVENAAN)
    st.subheader(f"📊 Strategisch Overzicht 2026")
    if winst_2026 < 0:
        st.error(f"🚨 Let op: Verwacht verlies van € {abs(winst_2026):,.2f}. De kostenstructuur is momenteel niet rendabel.")

    k1, k2, k3 = st.columns(3)
    k1.metric("Verwachte Omzet 2026", f"€ {totaal_2026:,.2f}")
    k2.metric("Verwachte Winst 2026", f"€ {winst_2026:,.2f}", delta_color="inverse" if winst_2026 < 0 else "normal")
    k3.metric("Groeipotentieel", f"{groei:.1f}%")

    # B. TREND GRAFIEK (MIDDEN - VOLLE BREEDTE)
    st.markdown("---")
    st.subheader("📈 Omzet Trend: Historie vs. Prognose")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_rev['Date'].tail(24), y=monthly_rev['Amount_Clean'].tail(24), name="Historie (Laatste 24m)", marker_color='#1f77b4'))
    fig.add_trace(go.Bar(x=future_dates, y=forecast_2026_list, name="Prognose 2026", marker_color='#ff7f0e'))
    fig.update_layout(template="plotly_white", barmode='group', height=400, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # C. BTW EN PIE (TWEE KOLOMMEN ONDER DE GRAFIEK)
    st.markdown("---")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🏦 BTW Planner (Per Kwartaal)")
        q_rows = []
        for q in range(1, 5):
            m_idx = [0,1,2] if q==1 else [3,4,5] if q==2 else [6,7,8] if q==3 else [9,10,11]
            q_rev = sum([forecast_2026_list[i] for i in m_idx])
            q_cost = q_rev * (1 - marge_ratio)
            afdracht = q_rev * 0.21 if not is_vrijgesteld else 0
            voorbelasting = q_cost * 0.21 if not is_vrijgesteld else 0
            q_rows.append({"Kwartaal": f"Q{q} 2026", "Omzet": f"€ {q_rev:,.0f}", "Netto BTW": f"€ {afdracht-voorbelasting:,.2f}"})
        st.table(pd.DataFrame(q_rows))

    with c2:
        st.subheader("🍕 Kostenverdeling (Totaalhistorie)")
        andere_kosten = df_kosten['Amount_Clean'].sum() - df_inkoop['Amount_Clean'].sum() - df_auto['Amount_Clean'].sum()
        fig_pie = go.Figure(data=[go.Pie(labels=['Inkoop', 'Auto', 'Overig'], 
                                         values=[df_inkoop['Amount_Clean'].sum(), df_auto['Amount_Clean'].sum(), max(0, andere_kosten)], 
                                         hole=.3)])
        fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    # D. DETAIL TABEL (ONDERAAN)
    st.markdown("---")
    st.subheader("📉 Winst- en Verlies Detail")
    st.table(pd.DataFrame({
        "Categorie": ["Netto-omzet", "Kostprijs omzet (6xxx)", "Autokosten (42xxx)", "Overige Bedrijfskosten"],
        "Bedrag": [df_omzet['Amount_Clean'].sum(), df_inkoop['Amount_Clean'].sum(), df_auto['Amount_Clean'].sum(), max(0, andere_kosten)]
    }).style.format({"Bedrag": "€ {:,.2f}"}))

else:
    st.info("Upload de Yuki CSV om het Master Dashboard te starten.")


# Kleine toevoeging voor de seizoensberekening:
seasonal_profile = df_omzet.groupby(df_omzet['Date'].dt.month)['Amount_Clean'].mean()
# Vul gaten op met het gemiddelde als een maand op 0 staat
seasonal_profile = seasonal_profile.replace(0, seasonal_profile.mean()).fillna(seasonal_profile.mean())
