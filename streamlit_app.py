import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Master BI Dashboard", layout="wide")
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

    df['Amount_Clean'] = df['Bedrag'].apply(clean_val)
    df['Date'] = pd.to_datetime(df['Datum'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date')
    df['Code_Str'] = df['Code'].astype(str).str.strip()

    # 2. ALLE OMZET CODES SCANNER (80000, 80002, 80008, etc.)
    # We pakken ALLES wat begint met een 8
    df_omzet = df[df['Code_Str'].str.startswith('8')].copy()
    
    # BTW Analyse: We kijken naar de 18-serie (BTW) om het gemiddelde percentage te bepalen
    df_btw = df[df['Code_Str'].str.startswith('18')].copy()
    tot_omzet_abs = abs(df_omzet['Amount_Clean'].sum())
    tot_btw_abs = abs(df_btw['Amount_Clean'].sum())
    
    # Bereken effectief BTW tarief (meestal rond de 21% of 9% gemiddeld)
    effectief_btw_tarief = (tot_btw_abs / tot_omzet_abs) if tot_omzet_abs > 0 else 0.21
    if effectief_btw_tarief > 0.25: effectief_btw_tarief = 0.21 # Cap voor realisme

    # 3. MAANDELIJKSE DATA (Zonder gaten in juli/aug/sept)
    # We resampelen op maandbasis en nemen de absolute waarde van elke 8xxxx boeking
    monthly_series = df_omzet.set_index('Date')['Amount_Clean'].resample('MS').sum().abs()
    # Vul gaten op met gemiddelde van de buren voor een strakke lijn
    monthly_series = monthly_series.replace(0, np.nan).interpolate(method='linear').fillna(monthly_series.mean())

    # 4. PROGNOSE LOGICA
    last_12m_omzet = monthly_series.tail(12).sum()
    prev_12m_omzet = monthly_series.iloc[-24:-12].sum() if len(monthly_series) >= 24 else last_12m_omzet
    
    totaal_2026 = last_12m_omzet if last_12m_omzet > 0 else (monthly_series.sum() / 2)
    groei_pct = ((last_12m_omzet - prev_12m_omzet) / prev_12m_omzet * 100) if prev_12m_omzet > 0 else 0.0

    # 5. WINST & KOSTEN
    df_kosten = df[df['Code_Str'].str.startswith(('4', '6', '7'))].copy()
    kosten_totaal = abs(df_kosten['Amount_Clean'].sum())
    marge_ratio = (tot_omzet_abs - kosten_totaal) / tot_omzet_abs if tot_omzet_abs > 0 else 0.1
    winst_2026 = totaal_2026 * marge_ratio

    # Seizoen voor 2026
    seasonal_profile = monthly_series.groupby(monthly_series.index.month).mean()
    forecast_2026 = [(seasonal_profile.get(m, seasonal_profile.mean()) / seasonal_profile.sum()) * totaal_2026 for m in range(1, 13)]
    future_dates = pd.date_range(start=pd.Timestamp(2026, 1, 1), periods=12, freq='MS')

    # --- DASHBOARD ---
    st.subheader("📊 Strategisch Dashboard 2026")
    k1, k2, k3 = st.columns(3)
    k1.metric("Verwachte Omzet 2026", f"€ {totaal_2026:,.2f}")
    k2.metric("Verwachte Winst 2026", f"€ {winst_2026:,.2f}")
    k3.metric("Groeipotentieel (%)", f"{groei_pct:.1f}%")

    # GRAFIEK
    st.markdown("---")
    st.subheader("📈 Omzet Trend: Inclusief alle 8000x-groepen")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_series.index[-24:], y=monthly_series.values[-24:], name="Historie (Alle Omzet)", marker_color='#1f77b4'))
    fig.add_trace(go.Bar(x=future_dates, y=forecast_2026, name="Prognose 2026", marker_color='#ff7f0e'))
    fig.update_layout(template="plotly_white", barmode='group', height=450)
    st.plotly_chart(fig, use_container_width=True)

    # BTW PLANNER
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏦 BTW-Afdracht per Kwartaal")
        st.caption(f"Gebaseerd op effectief tarief van {(effectief_btw_tarief*100):.1f}%")
        q_rows = []
        for q in range(1, 5):
            m_idx = [0,1,2] if q==1 else [3,4,5] if q==2 else [6,7,8] if q==3 else [9,10,11]
            q_rev = sum([forecast_2026[i] for i in m_idx])
            # We schatten de BTW afdracht (omzet-btw minus geschatte voorbelasting)
            q_btw = q_rev * effectief_btw_tarief if not is_vrijgesteld else 0
            q_rows.append({"Kwartaal": f"Q{q} 2026", "Verwachte Omzet": f"€ {q_rev:,.0f}", "Te reserveren BTW": f"€ {q_btw:,.2f}"})
        st.table(pd.DataFrame(q_rows))

    with c2:
        st.subheader("🍕 Kostenverdeling")
        labels = ['Bedrijfslasten (4)', 'Inkoop (6)', 'Overig (7)']
        vals = [abs(df[df['Code_Str'].str.startswith('4')]['Amount_Clean'].sum()), 
                abs(df[df['Code_Str'].str.startswith('6')]['Amount_Clean'].sum()), 
                abs(df[df['Code_Str'].str.startswith('7')]['Amount_Clean'].sum())]
        st.plotly_chart(go.Figure(data=[go.Pie(labels=labels, values=vals, hole=.3)]), use_container_width=True)

    # DETAIL TABEL MET SPECIFIEKE CODES
    st.markdown("---")
    st.subheader("📉 Gesegmenteerde Omzet (Top 5 groepen)")
    omzet_groepen = df_omzet.groupby('Code_Str')['Amount_Clean'].sum().abs().sort_values(ascending=False).head(5)
    omzet_df = pd.DataFrame({'Grootboekcode': omzet_groepen.index, 'Totaal Bedrag': omzet_groepen.values})
    st.table(omzet_df.style.format({"Totaal Bedrag": "€ {:,.2f}"}))

else:
    st.info("Upload de Yuki CSV.")
