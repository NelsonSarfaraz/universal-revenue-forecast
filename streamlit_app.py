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
    # 1. DATA LADEN & OPSCHONEN
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
    df['Hoofdcode'] = df['Code_Str'].str[0]

    # 2. OMZET & KOSTEN DEFINITIES
    df_omzet = df[df['Hoofdcode'] == '8'].copy()
    
    # 3. HISTORISCHE DATA REPAREREN (De "Juli Fix")
    # Maak een tijdreeks van alle maanden
    full_range = pd.date_range(start=df_omzet['Date'].min(), end=df_omzet['Date'].max(), freq='ME')
    monthly_rev = df_omzet.resample('ME', on='Date')['Amount_Clean'].sum().abs().reindex(full_range).fillna(0)
    
    # Als een maand 0 is, vul deze voor de grafiek in met het gemiddelde van de buren
    monthly_rev_filled = monthly_rev.replace(0, np.nan).interpolate(method='linear').fillna(monthly_rev.mean())

    # 4. PROGNOSE & GROEI
    last_date = df['Date'].max()
    one_year_ago = last_date - pd.DateOffset(years=1)
    two_years_ago = one_year_ago - pd.DateOffset(years=1)
    
    omzet_laatste_12m = abs(df_omzet[df_omzet['Date'] > one_year_ago]['Amount_Clean'].sum())
    omzet_jaar_ervoor = abs(df_omzet[(df_omzet['Date'] > two_years_ago) & (df_omzet['Date'] <= one_year_ago)]['Amount_Clean'].sum())
    
    totaal_2026 = omzet_laatste_12m if omzet_laatste_12m > 0 else (abs(df_omzet['Amount_Clean'].sum()) / 2)
    groei_pct = ((omzet_laatste_12m - omzet_jaar_ervoor) / omzet_jaar_ervoor * 100) if omzet_jaar_ervoor > 0 else 0.0

    kosten_totaal = abs(df[df['Hoofdcode'].isin(['4', '6', '7'])]['Amount_Clean'].sum())
    marge_ratio = (abs(df_omzet['Amount_Clean'].sum()) - kosten_totaal) / abs(df_omzet['Amount_Clean'].sum()) if abs(df_omzet['Amount_Clean'].sum()) > 0 else 0.1
    winst_2026 = totaal_2026 * marge_ratio

    # Seizoenspatroon voor de toekomst
    seasonal_profile = monthly_rev_filled.groupby(monthly_rev_filled.index.month).mean()
    forecast_2026_list = [(seasonal_profile.get(m) / seasonal_profile.sum()) * totaal_2026 for m in range(1, 13)]
    future_dates = pd.date_range(start=pd.Timestamp(2026, 1, 1), periods=12, freq='ME')

    # --- DASHBOARD LAYOUT ---
    st.subheader(f"📊 Strategisch Dashboard 2026")
    k1, k2, k3 = st.columns(3)
    k1.metric("Verwachte Omzet 2026", f"€ {totaal_2026:,.2f}")
    k2.metric("Verwachte Winst 2026", f"€ {winst_2026:,.2f}")
    k3.metric("Groeipotentieel", f"{groei_pct:.1f}%")

    # GRAFIEK MET GEREPAREERDE JULI
    st.markdown("---")
    st.subheader("📈 Omzet Trend: Historie vs. Prognose")
    fig = go.Figure()
    # Blauwe balken (nu zonder gaten)
    fig.add_trace(go.Bar(x=monthly_rev_filled.index[-24:], y=monthly_rev_filled.values[-24:], name="Historie (Gecorrigeerd)", marker_color='#1f77b4'))
    # Oranje balken
    fig.add_trace(go.Bar(x=future_dates, y=forecast_2026_list, name="Prognose 2026", marker_color='#ff7f0e'))
    fig.update_layout(template="plotly_white", barmode='group', height=400)
    st.plotly_chart(fig, use_container_width=True)

    # BTW & PIE
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏦 BTW-Positie per Kwartaal")
        q_rows = []
        for q in range(1, 5):
            m_idx = [0,1,2] if q==1 else [3,4,5] if q==2 else [6,7,8] if q==3 else [9,10,11]
            q_rev = sum([forecast_2026_list[i] for i in m_idx])
            afdracht = q_rev * 0.21 if not is_vrijgesteld else 0
            q_rows.append({"Kwartaal": f"Q{q} 2026", "Omzet": f"€ {q_rev:,.0f}", "Netto BTW": f"€ {afdracht:,.2f}"})
        st.table(pd.DataFrame(q_rows))

    with c2:
        st.subheader("🍕 Kostenverdeling (Exploitatie)")
        labels = ['Bedrijfslasten (4)', 'Inkoop (6)', 'Rente/Overig (7)']
        values = [abs(df[df['Hoofdcode'] == '4']['Amount_Clean'].sum()), 
                  abs(df[df['Hoofdcode'] == '6']['Amount_Clean'].sum()), 
                  abs(df[df['Hoofdcode'] == '7']['Amount_Clean'].sum())]
        fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        st.plotly_chart(fig_pie, use_container_width=True)

    # TABEL
    st.markdown("---")
    st.subheader("📉 Winst- en Verlies Detail")
    namen = {'4': 'Bedrijfslasten', '6': 'Kostprijs Omzet', '7': 'Financieel resultaat', '8': 'Netto-omzet'}
    detail_data = [{"Categorie": namen[c], "Bedrag": abs(df[df['Hoofdcode'] == c]['Amount_Clean'].sum())} for c in ['8', '6', '4', '7']]
    st.table(pd.DataFrame(detail_data).style.format({"Bedrag": "€ {:,.2f}"}))

else:
    st.info("Upload de Yuki CSV om te starten.")
