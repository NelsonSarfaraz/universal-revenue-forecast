import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Pagina instellingen
st.set_page_config(page_title="Master AI Dashboard", layout="wide")
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
        x = str(x).replace('"', '').replace('.', '').replace(',', '.')
        try: return float(x)
        except: return 0.0

    df['Amount_Clean'] = df['Bedrag'].apply(clean_val).abs()
    df['Date'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date') # Belangrijk voor 5-jaar data
    df['Code_Str'] = df['Code'].astype(str).str.strip()

    # 2. CATEGORIEËN
    df_omzet = df[df['Code_Str'].str.startswith('8') | (df['Code_Str'] == '18400')].copy()
    df_kosten = df[df['Code_Str'].str.startswith(('4', '6'))].copy()
    df_auto = df[df['Code_Str'].str.startswith('42')].copy()
    df_inkoop = df[df['Code_Str'].str.startswith('6')].copy()

    # 3. ROBUUSTE PROGNOSE (Corrigeert de € 0 fout)
    # Pak de laatste 12 maanden uit het bestand als basis voor 2026
    last_date = df['Date'].max()
    one_year_ago = last_date - pd.DateOffset(years=1)
    
    recent_omzet_data = df_omzet[df_omzet['Date'] > one_year_ago]
    totaal_omzet_laatste_jaar = recent_omzet_data['Amount_Clean'].sum()

    # Als het laatste jaar leeg is (foutje in data), pak dan het gemiddelde van alle jaren
    if totaal_omzet_laatste_jaar == 0:
        aantal_jaren = max(1, (df['Date'].max() - df['Date'].min()).days / 365)
        totaal_2026 = df_omzet['Amount_Clean'].sum() / aantal_jaren
    else:
        totaal_2026 = totaal_omzet_laatste_jaar

    # Seizoenspatroon berekenen op basis van alle data (5 jaar gemiddelde per maand)
    seasonal_profile = df_omzet.groupby(df_omzet['Date'].dt.month)['Amount_Clean'].mean()
    if seasonal_profile.empty: # Fallback
        seasonal_profile = pd.Series([1]*12, index=range(1,13))
    
    forecast_2026_list = [(seasonal_profile.get(m, seasonal_profile.mean()) / seasonal_profile.sum()) * totaal_2026 for m in range(1, 13)]
    future_dates = pd.date_range(start=pd.Timestamp(last_date.year + 1, 1, 1), periods=12, freq='ME')

    # 4. KPI'S BEREKENEN
    marge_ratio = (df_omzet['Amount_Clean'].sum() - df_kosten['Amount_Clean'].sum()) / df_omzet['Amount_Clean'].sum() if not df_omzet.empty else 0.1
    winst_2026 = totaal_2026 * marge_ratio

    st.subheader(f"📊 Strategisch Dashboard (Basis: {last_date.year})")
    k1, k2, k3 = st.columns(3)
    k1.metric("Verwachte Omzet 2026", f"€ {totaal_2026:,.2f}")
    k2.metric("Verwachte Winst 2026", f"€ {winst_2026:,.2f}")
    
    # Groei vergelijking met het jaar daarvóór
    twee_jaar_geleden = one_year_ago - pd.DateOffset(years=1)
    omzet_vorig_jaar = df_omzet[(df_omzet['Date'] > twee_jaar_geleden) & (df_omzet['Date'] <= one_year_ago)]['Amount_Clean'].sum()
    groei = ((totaal_2026 - omzet_vorig_jaar) / omzet_vorig_jaar * 100) if omzet_vorig_jaar > 0 else 0
    k3.metric("Groeipotentieel", f"{groei:.1f}%")

    # 5. VISUALISATIE: TREND
    st.markdown("---")
    st.subheader("📈 Omzet Trend: Historie vs. Prognose")
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_rev['Date'].tail(24), y=monthly_rev['Amount_Clean'].tail(24), name="Historie (Laatste 24m)", marker_color='#1f77b4'))
    fig.add_trace(go.Bar(x=future_dates, y=forecast_2026_list, name="Prognose 2026", marker_color='#ff7f0e'))
    fig.update_layout(template="plotly_white", barmode='group', height=400)
    st.plotly_chart(fig, use_container_width=True)

    # 6. BTW & KOSTEN
    st.markdown("---")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("🏦 BTW Planner (Per Kwartaal)")
        q_rows = []
        for q in range(1, 5):
            m_idx = [0,1,2] if q==1 else [3,4,5] if q==2 else [6,7,8] if q==3 else [9,10,11]
            q_rev = sum([forecast_2026_list[i] for i in m_idx])
            q_cost = q_rev * (1 - marge_ratio)
            afdracht = q_rev * 0.21 if not is_vrijgesteld else 0
            voorbelasting = q_cost * 0.21 if not is_vrijgesteld else 0
            q_rows.append({"Kwartaal": f"Q{q} Proj.", "Omzet": f"€ {q_rev:,.0f}", "Netto BTW": f"€ {afdracht-voorbelasting:,.2f}"})
        st.table(pd.DataFrame(q_rows))

    with col_b:
        st.subheader("🍕 Kostenverdeling (Totaalhistorie)")
        andere_kosten = df_kosten['Amount_Clean'].sum() - df_inkoop['Amount_Clean'].sum() - df_auto['Amount_Clean'].sum()
        fig_pie = go.Figure(data=[go.Pie(labels=['Inkoop', 'Auto', 'Overig'], 
                                         values=[df_inkoop['Amount_Clean'].sum(), df_auto['Amount_Clean'].sum(), max(0, andere_kosten)], 
                                         hole=.3)])
        st.plotly_chart(fig_pie, use_container_width=True)

    # 7. DETAIL TABEL
    st.markdown("---")
    st.subheader("📉 Winst- en Verlies Detail")
    details = pd.DataFrame({
        "Categorie": ["Netto-omzet", "Kostprijs omzet (6xxx)", "Autokosten (42xxx)", "Overige Bedrijfslasten"],
        "Bedrag": [df_omzet['Amount_Clean'].sum(), df_inkoop['Amount_Clean'].sum(), df_auto['Amount_Clean'].sum(), max(0, andere_kosten)]
    })
    st.table(details.style.format({"Bedrag": "€ {:,.2f}"}))

else:
    st.info("Upload de Yuki CSV (bijv. 5 jaar data van Peter Bouw) om te beginnen.")
