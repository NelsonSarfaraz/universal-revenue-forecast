import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="AI Kwartaal Planner", layout="wide")
st.title("📅 AI Boekhouder - Kwartaal & Seizoensplanning")

with st.sidebar:
    st.header("Instellingen")
    is_vrijgesteld = st.toggle("Bedrijf is BTW-vrijgesteld", value=False)
    uploaded_file = st.file_uploader("Upload Yuki CSV", type=['csv'])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='iso-8859-1')
    df.columns = df.columns.str.strip()

    def clean_val(x):
        if pd.isna(x): return 0.0
        x = str(x).replace('"', '').replace('.', '').replace(',', '.')
        try: return float(x)
        except: return 0.0

    df['Amount_Clean'] = df['Bedrag'].apply(clean_val).abs()
    df['Date'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
    df['Month'] = df['Date'].dt.month
    df['Quarter'] = df['Date'].dt.quarter
    df['Code_Str'] = df['Code'].astype(str).str.strip()

    # --- DATA GROEPERING ---
    df_omzet = df[df['Code_Str'].str.startswith('8') | (df['Code_Str'] == '18400')].copy()
    df_kosten = df[df['Code_Str'].str.startswith(('4', '6'))].copy()

    # --- SEIZOENSPROGNOSE (PIEKEN & DALEN) ---
    # We berekenen het gemiddelde per maand uit het verleden
    seasonal_profile = df_omzet.groupby('Month')['Amount_Clean'].mean()
    # Als een maand ontbreekt, vullen we die met het algemeen gemiddelde
    avg_monthly = df_omzet['Amount_Clean'].mean()
    full_year_profile = [seasonal_profile.get(m, avg_monthly) for m in range(1, 13)]
    
    future_dates = pd.date_range(start='2026-01-01', periods=12, freq='ME')
    
    # --- BTW PER KWARTAAL BEREKENEN ---
    st.subheader("🏦 BTW Reservering per Kwartaal (Prognose 2026)")
    
    q_data = []
    for q in range(1, 5):
        # Maanden in dit kwartaal
        months = [1,2,3] if q==1 else [4,5,6] if q==2 else [7,8,9] if q==3 else [10,11,12]
        q_omzet = sum([full_year_profile[m-1] for m in months])
        # We schatten kosten op basis van historische verhouding
        marge_ratio = (df_omzet['Amount_Clean'].sum() - df_kosten['Amount_Clean'].sum()) / df_omzet['Amount_Clean'].sum() if not df_omzet.empty else 0.5
        q_kosten = q_omzet * (1 - marge_ratio)
        
        afdracht = q_omzet * 0.21 if not is_vrijgesteld else 0
        voorbelasting = q_kosten * 0.21 if not is_vrijgesteld else 0
        saldo = afdracht - voorbelasting
        
        q_data.append({
            "Kwartaal": f"Q{q} 2026",
            "Verwachte Omzet": f"€ {q_omzet:,.2f}",
            "BTW Afdracht": f"€ {afdracht:,.2f}",
            "BTW Terugvraag": f"€ {voorbelasting:,.2f}",
            "TE BETALEN": f"€ {saldo:,.2f}"
        })
    
    st.table(pd.DataFrame(q_data))

    # --- SEIZOENSGRAFIEK ---
    st.markdown("---")
    st.subheader("📈 Maandelijkse Drukte & Omzetstroom (2026 Forecast)")
    st.info("Deze grafiek laat de seizoensinvloeden zien op basis van jouw eerdere jaren.")
    
    fig = go.Figure()
    # Historische data (maandgemiddeldes)
    fig.add_trace(go.Scatter(x=list(range(1,13)), y=full_year_profile, mode='lines+markers', 
                             name="Seizoenspatroon", line=dict(color='blue', width=4, shape='spline')))
    
    fig.update_layout(xaxis=dict(tickmode='array', tickvals=list(range(1,13)), 
                      ticktext=['Jan', 'Feb', 'Mrt', 'Apr', 'Mei', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec']),
                      yaxis_title="Omzet (€)", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # --- PIEKMAAND ANALYSE ---
    piek_index = np.argmax(full_year_profile)
    maanden_namen = ['Januari', 'Februari', 'Maart', 'April', 'Mei', 'Juni', 'Juli', 'Augustus', 'September', 'Oktober', 'November', 'December']
    
    st.success(f"🔥 **Piekmaand Analyse:** Jouw drukste maand is naar verwachting **{maanden_namen[piek_index]}**. Zorg dat je in deze periode extra cashflow-buffer hebt voor de BTW!")

else:
    st.info("Upload je Yuki CSV voor de kwartaalplanning.")
