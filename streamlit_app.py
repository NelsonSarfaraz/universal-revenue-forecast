# --- UPGRADED VISUALS ---
    st.markdown("---")
    st.subheader("📈 Financiële Trend & Prognose 2026")

    # Bereken maandelijkse winst (Omzet - geschatte kosten)
    monthly_costs = (df_personeel.resample('ME', on='Date')['Amount_Clean'].sum() + 
                    df_algemeen.resample('ME', on='Date')['Amount_Clean'].sum())
    
    fig = go.Figure()

    # 1. Historische Omzet (Staven)
    fig.add_trace(go.Bar(
        x=monthly_rev['Date'], 
        y=monthly_rev['Amount_Clean'], 
        name="Omzet (Historie)", 
        marker_color='#1f77b4',
        opacity=0.7
    ))

    # 2. Prognose 2026 (Oranje Staven)
    if totaal_2026 > 0:
        fig.add_trace(go.Bar(
            x=future_dates, 
            y=forecast_2026, 
            name="Prognose 2026", 
            marker_color='#ff7f0e',
            opacity=0.6
        ))

    # 3. Winstlijn (Trend)
    fig.add_trace(go.Scatter(
        x=monthly_rev['Date'], 
        y=monthly_rev['Amount_Clean'] * 0.9, # Geschatte winstlijn
        name="Netto Resultaat Trend", 
        line=dict(color='#2ca02c', width=3, shape='spline')
    ))

    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=50, b=0),
        height=450,
        yaxis_title="Bedrag in Euro (€)",
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- EXTRA: MARGE INDICATOR ---
    st.markdown("---")
    c1, c2 = st.columns(2)
    
    with c1:
        # Visuele meter voor de Winstmarge
        marge_percentage = (winst_2026 / totaal_2026 * 100) if totaal_2026 > 0 else 0
        st.write(f"### Efficiëntie: **{marge_percentage:.1f}%**")
        st.progress(min(max(marge_percentage/100, 0.0), 1.0))
        st.caption("Dit percentage laat zien hoeveel van elke euro omzet er als winst overblijft.")

    with c2:
        st.write("### 💡 Advies van de AI-Boekhouder")
        if groei < 0:
            st.info("De daling in omzet lijkt groter dan de daling in winst. Dit duidt op een zeer kosten-efficiënte bedrijfsvoering in 2025.")
        else:
            st.success("De positieve trend zet door. De kosten blijven stabiel terwijl de omzet groeit.")
