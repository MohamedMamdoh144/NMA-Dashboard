
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import textwrap

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="MS DMD Clinical Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a Clean, Journal-Ready Look
st.markdown("""
<style>
    .main { background-color: #ffffff; }
    h1, h2, h3 { font-family: 'Arial', sans-serif; color: #2c3e50; }
    div[data-testid="stExpander"] div[role="button"] p { font-size: 1.1rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. DATA LOADING
# ---------------------------------------------------------
@st.cache_data
def load_rank_data():
    try:
        df_eff = pd.read_excel("Efficacy_ranks.xlsx")
        df_safe = pd.read_excel("Safety_ranks.xlsx")
        df = pd.concat([df_eff, df_safe])
        # Clean naming
        df['Arm'] = df['Arm'].str.replace('Teriﬂunomide', 'Teriflunomide')
        df['Outcome'] = df['Outcome'].str.replace('_', ' ')
        return df
    except Exception as e:
        st.error(f"Error loading Ranking data: {e}")
        return pd.DataFrame()

@st.cache_data
def load_pairwise_data():
    try:
        df_eff = pd.read_excel("Efficacy_ranks.xlsx", sheet_name="effects")
        df_safe = pd.read_excel("Safety_ranks.xlsx", sheet_name="effects")
        df = pd.concat([df_eff, df_safe])
        df['Outcome'] = df['Outcome'].str.replace('_', ' ')
        return df
    except Exception as e:
        st.error(f"Error loading Pairwise data: {e}")
        return pd.DataFrame()


df = load_rank_data()
pair_df = load_pairwise_data()

# ---------------------------------------------------------
# 3. SIDEBAR: CLINICAL PREFERENCES (MCDA)
# ---------------------------------------------------------
st.sidebar.header("🩺 Clinical Focus Settings")
st.sidebar.info("Adjust weights below to calculate the 'Net Clinical Benefit' (MCDA Score).")
# Calculate Metrics

if not df.empty:
    eff_outcomes = sorted(df[df['Type'] == 'Efficacy']['Outcome'].unique())
    saf_outcomes = sorted(df[df['Type'] == 'Safety']['Outcome'].unique())
else:
    eff_outcomes, saf_outcomes = [], []

weights = {}

with st.sidebar.expander("⚖️ Efficacy Weights", expanded=True):
    for out in eff_outcomes:
        def_val = 1.2 if "Disability" in out else 1.0
        weights[out] = st.slider(f"{out}", 0.0, 2.0, def_val, 0.1, key=out)

with st.sidebar.expander("🛡️ Safety Weights", expanded=False):
    for out in saf_outcomes:
        def_val = 1.0 if "disc" in out else 0.8
        weights[out] = st.slider(f"{out}", 0.0, 2.0, def_val, 0.1, key=out)

st.sidebar.markdown("---")
st.sidebar.subheader("Select Drugs to Compare")

if not df.empty:
    all_drugs = sorted(df['Arm'].unique())
    default_selection = ['Alemtuzumab', 'Fingolimod', 'Ocrelizumab', 'Placebo']
    default_selection = [d for d in default_selection if d in all_drugs] # Safety check

    selected_drugs = st.sidebar.multiselect(
        "Choose treatments", all_drugs, default=default_selection
    )
else:
    selected_drugs = []

# ---------------------------------------------------------
# 4. DATA PROCESSING (MCDA SCORES)
# ---------------------------------------------------------
if not df.empty:
    # Apply Weights
    df['Weight'] = df['Outcome'].map(weights).fillna(1.0)
    df['Weighted_Score'] = df['Rank'] * df['Weight']

    # Calculate Aggregate Scores per Drug
    summary_list = []
    for drug in df['Arm'].unique():
        d_data = df[df['Arm'] == drug]

        # Efficacy Component
        eff_part = d_data[d_data['Type'] == 'Efficacy']
        if not eff_part.empty and eff_part['Weight'].sum() > 0:
            eff_val = eff_part['Weighted_Score'].sum() / eff_part['Weight'].sum()
        else:
            eff_val = 0

        # Safety Component
        saf_part = d_data[d_data['Type'] == 'Safety']
        if not saf_part.empty and saf_part['Weight'].sum() > 0:
            saf_val = saf_part['Weighted_Score'].sum() / saf_part['Weight'].sum()
        else:
            saf_val = 0

        # Total Utility Score (MCDA)
        total_score = (eff_val + saf_val) / 2

        summary_list.append({
            'Arm': drug,
            'Efficacy': eff_val,
            'Safety': saf_val,
            'Total_Score': total_score
        })

    summary_df = pd.DataFrame(summary_list)
    summary_df['Color'] = summary_df['Arm'].apply(lambda x: 'Selected' if x in selected_drugs else 'Other')

# ---------------------------------------------------------
# 5. DASHBOARD LAYOUT
# ---------------------------------------------------------
st.title("Multiple Sclerosis DMD Comparison: Clinical NMA Dashboard")
if not df.empty and not pair_df.empty:
    n_drugs = df['Arm'].nunique()
    n_eff = df[df['Type'] == 'Efficacy']['Outcome'].nunique()
    n_safe = df[df['Type'] == 'Safety']['Outcome'].nunique()

    # Count unique edges (A-B comparisons), excluding duplicates (B-A)
    # We create a set of sorted tuples to count unique pairs
    unique_pairs = set(tuple(sorted((r.treat1, r.treat2))) for i, r in pair_df.iterrows())
    n_pairs = len(unique_pairs)
    n_total = len(pair_df)/2

    # Display Banner
    # Using containers to give it a slight separation
    with st.container():
        m1, m2, m3, m4, m5 = st.columns(5)

        m1.metric(
            label="🦠 Active Treatments",
            value=n_drugs,
            help="Number of unique Disease Modifying Therapies (DMDs) included in the network."
        )

        m2.metric(
            label="💪 Efficacy Outcomes",
            value=n_eff,
            help="Total efficacy endpoints analyzed (e.g., Relapse Rate, NEDA, Disability)."
        )

        m3.metric(
            label="🛡️ Safety Outcomes",
            value=n_safe,
            help="Total safety endpoints analyzed (e.g., AEs, Discontinuation)."
        )

        m4.metric(
            label="🔗 Direct Comparisons",
            value=n_pairs,
            help="Number of unique head-to-head drug pairs available for analysis."
        )

        m5.metric(
            label="🔗 Total Comparisons",
            value=int(n_total),
            help="Number of All head-to-head drug pairs available for analysis."
        )

st.markdown("---")
# --- ROW 1: GLOBAL ASSESSMENT (MCDA) ---

st.header("1. Global Benefit-Risk Assessment")

if not df.empty:
    c1, c2 = st.columns([3, 2])

    # A. Scatter Plot (Left)
    with c1:
        st.subheader("Benefit-Risk Biplot")
        st.caption("Top-Right quadrant represents optimal balance.")

        fig_scatter = px.scatter(
            summary_df, x='Safety', y='Efficacy', hover_name='Arm', text='Arm',
            color='Color', color_discrete_map={'Selected': '#EF553B', 'Other': '#636EFA'}, size_max=60
        )
        fig_scatter.update_traces(textposition='top center', marker=dict(size=14, line=dict(width=2, color='White')))

        # Background Quadrants
        fig_scatter.add_shape(type="rect", x0=0.5, y0=0.5, x1=1.05, y1=1.05, line=dict(width=0), fillcolor="green",
                              opacity=0.1, layer="below")
        fig_scatter.add_shape(type="rect", x0=-0.05, y0=-0.05, x1=0.5, y1=0.5, line=dict(width=0), fillcolor="red",
                              opacity=0.1, layer="below")

        # Guidelines (Adaptive Color)
        fig_scatter.add_hline(y=0.5, line_dash="dot", line_color="rgba(128,128,128,0.5)")
        fig_scatter.add_vline(x=0.5, line_dash="dot", line_color="rgba(128,128,128,0.5)")

        fig_scatter.update_layout(
            xaxis_title="Weighted Safety Score (Higher = Safer)",
            yaxis_title="Weighted Efficacy Score (Higher = Better)",
            height=550, showlegend=False,
            xaxis=dict(range=[-0.05, 1.05], showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
            yaxis=dict(range=[-0.05, 1.05], showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
            margin=dict(l=0, r=0, t=20, b=20),
            # TRANSPARENT BACKGROUND
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # B. League Table (Right)
    with c2:
        st.subheader("Net Clinical Benefit Ranking")
        st.caption("Ranked by Total Utility Score (MCDA)")

        rank_df = summary_df.sort_values('Total_Score', ascending=True)
        colors = ['#EF553B' if x in selected_drugs else '#636EFA' for x in rank_df['Arm']]

        fig_lol = go.Figure()

        # 1. Draw Sticks
        for i, row in rank_df.iterrows():
            color = '#EF553B' if row['Arm'] in selected_drugs else 'rgba(128,128,128,0.5)'
            width = 3 if row['Arm'] in selected_drugs else 1

            fig_lol.add_shape(
                type='line',
                x0=0, y0=row['Arm'],
                x1=row['Total_Score'], y1=row['Arm'],
                line=dict(color=color, width=width),
                layer='below'
            )

        # 2. Draw Dots & Labels
        fig_lol.add_trace(go.Scatter(
            x=rank_df['Total_Score'],
            y=rank_df['Arm'],
            mode='markers+text',
            text=rank_df['Total_Score'].apply(lambda x: f"{x:.2f}"),
            textposition='middle right',
            # Removed 'color' here to let it adapt to Dark Mode automatically
            textfont=dict(size=11),
            marker=dict(
                size=12,
                color=colors,
                line=dict(width=2, color='white')
            ),
            hoverinfo='x+name',
            name='Utility Score'
        ))

        fig_lol.update_layout(
            height=550,
            xaxis=dict(
                showgrid=False,
                showticklabels=False,
                range=[0, 1.2]  # Extra padding for labels
            ),
            yaxis=dict(
                showgrid=True,
                # Adaptive Grid Color (Visible on Dark & Light)
                gridcolor='rgba(128,128,128,0.1)',
                gridwidth=1,
                ticksuffix="   ",
                automargin=True
            ),
            # TRANSPARENT BACKGROUND
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=20, b=20),
            showlegend=False
        )

        st.plotly_chart(fig_lol, use_container_width=True)

    st.caption \
        ("Note: Scores are aggregated across outcomes with varying follow-up durations (TTT). Interpret with consideration for trial heterogeneity.")

# --- ROW 2: RADAR PLOTS ---
st.markdown("---")
st.subheader("2. Detailed Profile Comparison")
st.markdown("Raw P-scores (0-1) per outcome.")

if not df.empty:
    def clean_label(label):
        replacements = {"Annualized Relapse": "ARR", "Disability progression": "CDP", "Brain volume": "BV",
                        "Any events leading to disc": "Discontinuation", "Drug related AEs": "Drug-related AEs",
                        "No evidence of disease activity": "NEDA", "months": "m", "change": "\u0394"}
        for old, new in replacements.items():
            label = label.replace(old, new)
        wrapped = "<br>".join(textwrap.wrap(label, width=12))
        return f"<b>{wrapped}</b>"

    def create_radar(outcome_list, title):
        fig = go.Figure()
        display_names = [clean_label(o) for o in outcome_list]

        for drug in selected_drugs:
            subset = df[(df['Arm'] == drug) & (df['Outcome'].isin(outcome_list))]
            drug_vals_map = dict(zip(subset['Outcome'], subset['Rank']))
            r_values = [drug_vals_map.get(o, 0) for o in outcome_list]
            r_values_closed = r_values + [r_values[0]]
            theta_values_closed = display_names + [display_names[0]]

            fig.add_trace(go.Scatterpolar(
                r=r_values_closed, theta=theta_values_closed, fill='toself', name=drug,
                mode='lines+markers', marker=dict(size=6), line=dict(width=2.5),
                hoverinfo='text+name', text=[f"{o}: {v:.2f}" for o, v in zip(outcome_list, r_values_closed)]
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1.25], showticklabels=True, tickfont=dict(size=9), angle=45, dtick=0.2, gridcolor='rgba(128,128,128,0.2)'),
                angularaxis=dict(showticklabels=True, tickfont=dict(size=10), rotation=90, direction="clockwise", gridcolor='rgba(128,128,128,0.2)')
            ),
            title=dict(text=title, x=0.5, y=0.98, font=dict(size=16)),
            margin=dict(l=80, r=80, t=60, b=60), height=550,
            legend=dict(orientation="h", y=-0.15, x=0.5, xanchor='center')
        )
        return fig

    r1, r2 = st.columns(2)
    with r1: st.plotly_chart(create_radar(eff_outcomes, "Efficacy Profile"), use_container_width=True)
    with r2: st.plotly_chart(create_radar(saf_outcomes, "Safety Profile"), use_container_width=True)

# --- ROW 3: HEAD-TO-HEAD MATCHUP ---
st.markdown("---")
st.subheader("3. Head-to-Head Matchup")

if not pair_df.empty:
    # Selectors
    c1, c2 = st.columns([1, 1])
    drug_list = sorted(pair_df['treat1'].unique())
    with c1: drug_a = st.selectbox("Reference Drug (A)", drug_list, index=0)
    with c2: drug_b = st.selectbox("Comparator Drug (B)", drug_list, index=1 if len(drug_list ) >1 else 0)

    # Filter Data
    comp_data = pair_df[(pair_df['treat1'] == drug_a) & (pair_df['treat2'] == drug_b)].copy()

    if comp_data.empty:
        st.warning("No direct comparison data found for this pair.")
    else:
        # --- LOGIC HELPER ---
        def get_winner_details(row, outcome_type, invert_safety=False):
            null_val = 0 if row['sm'] == 'MD' else 1

            if (row['CI_Lower'] <= null_val <= row['CI_Upper']):
                return "Non-Significant", "#B0B0B0", ""

            # Smart Direction
            lower_is_better = True
            if outcome_type == 'Efficacy':
                good_keywords = ['free', 'without', 'neda', 'no']
                if any(k in row['Outcome'].lower() for k in good_keywords):
                    lower_is_better = False
            elif outcome_type == 'Safety':
                lower_is_better = not invert_safety

            # Decision
            if row['Effect_Size'] < null_val:
                if lower_is_better: return f"Favors {drug_a}", "#1f77b4", "(Lower)"
                else: return f"Favors {drug_b}", "#d62728", "(Higher)"
            else:
                if lower_is_better: return f"Favors {drug_b}", "#d62728", "(Higher)"
                else: return f"Favors {drug_a}", "#1f77b4", "(Higher)"

        # Calculate Globally for Table
        global_logic = comp_data.apply(
            lambda row: pd.Series(get_winner_details(row, row['Type'], False)), axis=1
        )
        comp_data[['Significance', 'Color', 'Note']] = global_logic

        # Scorecard
        sig_counts = comp_data['Significance'].value_counts()
        st.info \
            (f"**Matchup:** {sig_counts.get(f'Favors {drug_a}', 0)} outcomes favor **{drug_a}** | {sig_counts.get(f'Favors {drug_b}', 0)} outcomes favor **{drug_b}**")

        # --- FOREST PLOTS ---
        tab_eff, tab_safe = st.tabs(["💪 Efficacy Outcomes", "🛡️ Safety Outcomes"])

        def render_forest(container, data, name):
            with container:
                if data.empty:
                    st.info("No data."); return

                plot_data = data.copy()
                invert = False

                if name == "Safety":
                    col_a, col_b = st.columns([3, 1])
                    with col_a: st.markdown("**Safety Logic:** Standard (Lower is Better).")
                    with col_b:
                        if st.checkbox("🔄 Invert Direction", key=f"inv_{name}"):
                            invert = True
                            plot_data[['Significance', 'Color', 'Note']] = plot_data.apply(
                                lambda row: pd.Series(get_winner_details(row, name, True)), axis=1
                            )

                for sm in plot_data['sm'].unique():
                    sub = plot_data[plot_data['sm'] == sm].drop_duplicates(subset=['Outcome'])
                    is_ratio = sm in ['RR', 'OR']

                    # Robust Range for Log Scale
                    if is_ratio:
                        sub = sub[sub['Effect_Size'] > 0.001]
                        if sub.empty: continue
                        x_min = max(0.1, sub['CI_Lower'].min() * 0.8)
                        x_max = min(10, sub['CI_Upper'].max() * 1.1)
                    else:
                        x_min = sub['CI_Lower'].min() - 0.5
                        x_max = sub['CI_Upper'].max() + 0.5

                    sub = sub.sort_values('Effect_Size', ascending=False)

                    fig = px.scatter(
                        sub, x="Effect_Size", y="Outcome", log_x=is_ratio,
                        error_x_minus=sub['Effect_Size'] - sub['CI_Lower'],
                        error_x=sub['CI_Upper'] - sub['Effect_Size'],
                        color="Significance",
                        color_discrete_map={"Non-Significant": "#B0B0B0", f"Favors {drug_a}": "#1f77b4", f"Favors {drug_b}": "#d62728"},
                        hover_data={'Effect_Size' :':.3f', 'CI_Lower' :':.3f', 'CI_Upper' :':.3f'},
                        title=f"<b>{sm} Analysis</b> ({name})"
                    )

                    fig.update_traces(marker=dict(symbol="square", size=8))
                    # Corrected VLine syntax
                    fig.add_vline(x=1 if is_ratio else 0, line_dash="dot", line_color="black", opacity=0.5)

                    fig.update_layout(
                        height=100 + len(sub ) *35, plot_bgcolor='white',
                        xaxis=dict(range=[np.log10(x_min), np.log10(x_max)] if is_ratio else [x_min, x_max], showgrid=True, gridcolor='#f0f0f0'),
                        yaxis=dict(type='category', ticksuffix="   ", automargin=True, showgrid=True, gridcolor='#f0f0f0'),
                        margin=dict(l=10, r=10, t=50, b=20), legend=dict(orientation="h", y=-0.15, title=None)
                    )

                    # Annotations
                    l_txt = f"<b>← Favors {drug_a if not invert else drug_b}</b>"
                    r_txt = f"<b>Favors {drug_b if not invert else drug_a} →</b>"
                    fig.add_annotation(x=np.log10(x_min) if is_ratio else x_min, y=len(sub ) -0.5, text=l_txt, showarrow=False, xanchor="left", font=dict(color="#1f77b4", size=10))
                    fig.add_annotation(x=np.log10(x_max) if is_ratio else x_max, y=len(sub ) -0.5, text=r_txt, showarrow=False, xanchor="right", font=dict(color="#d62728", size=10))

                    st.plotly_chart(fig, use_container_width=True)

        render_forest(tab_eff, comp_data[comp_data['Type' ]=='Efficacy'], "Efficacy")
        render_forest(tab_safe, comp_data[comp_data['Type' ]=='Safety'], "Safety")

        # --- TABLE ---
        st.subheader("Detailed Statistics")
        if st.checkbox("Show Significant Only"):
            comp_data = comp_data[comp_data['Significance'] != "Non-Significant"]

        st.dataframe(
            comp_data[['Outcome', 'Type', 'sm', 'Effect_Size', 'CI_Lower', 'CI_Upper', 'Significance']].style.format
                ("{:.3f}", subset=['Effect_Size', 'CI_Lower', 'CI_Upper']).applymap(
                lambda v: 'color: #d62728; font-weight: bold' if 'Favors' in str(v) and str(v).endswith(drug_b) else
                ('color: #1f77b4; font-weight: bold' if 'Favors' in str(v) else 'color: gray'),
                subset=['Significance']
            ), use_container_width=True
        )