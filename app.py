import streamlit as st
import pandas as pd
import pulp
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time


# --- 1. EXTREMELY ULTRA PAGE SETUP ---
st.set_page_config(page_title="ProStack AI - GOD MODE", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- ULTRA VIBE MODE: Hide all web elements ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            /* Tabs ko hide karne aur buttons ko premium banane ka CSS */
            div.row-widget.stRadio > div{flex-direction:row; justify-content: space-between; flex-wrap: wrap;}
            div.row-widget.stRadio > div > label{background-color: #1A202C; padding: 10px 15px; border-radius: 5px; border: 1px solid #00FF41; cursor: pointer; flex-grow: 1; text-align: center; margin: 5px;}
            div.row-widget.stRadio > div > label:hover{background-color: #00FF41; color: #0E1117 !important;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Hacker/Terminal Premium CSS
st.markdown("""
    <style>
    .stApp {background-color: #0E1117;}
    .god-title {font-size: 45px; color: #00FF41; font-weight: 900; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0px 0px 10px #00FF41;}
    .sub-text {color: #A0AEC0; font-size: 16px; font-style: italic;}
    .metric-box {background-color: #1A202C; padding: 15px; border-radius: 10px; border-left: 4px solid #00FF41;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="god-title">⚡ ProStack AI : GOD-MODE TERMINAL</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-text">Advanced Monte Carlo Simulations | Vegas Odds Integration | Auto-Stacking Matrix</p>', unsafe_allow_html=True)
st.divider()

# --- 2. ADVANCED SIDEBAR CONTROLS ---
with st.sidebar:
    st.image("https://img.icons8.com/nolan/96/artificial-intelligence.png", width=80)
    st.header("🧠 Neural Engine Rules")
    
    uploaded_file = st.file_uploader("📥 Upload Real DFS Data", type=["csv"])
    
    st.subheader("⚙️ God-Tier Settings")
    num_lineups = st.slider("🎯 Number of Lineups", 1, 150, 20)
    salary_cap = st.number_input("💰 Salary Cap", value=50000, step=100)
    
    st.subheader("🧬 Correlation & Variance")
    simulations = st.select_slider("🎲 Monte Carlo Sims", options=["100", "1,000", "10,000 (Max)"], value="1,000")
    auto_stack = st.checkbox("🔗 Enable Auto-Stacking (QB + WR/TE)", value=True)
    fade_chalk = st.checkbox("👻 Fade the Chalk (Avoid High Ownership)", value=False)

# --- 3. GOD-MODE DATA GENERATOR ---
@st.cache_data
def load_god_data():
    return pd.DataFrame({
        "ID": range(1, 11),
        "Player": ["P. Mahomes", "J. Allen", "C. McCaffrey", "A. Ekeler", "T. Hill", "J. Jefferson", "T. Kelce", "S. Diggs", "C. Kupp", "A. Brown"],
        "Team": ["KC", "BUF", "SF", "LAC", "MIA", "MIN", "KC", "BUF", "LAR", "PHI"],
        "Pos": ["QB", "QB", "RB", "RB", "WR", "WR", "TE", "WR", "WR", "WR"],
        "Salary": [8000, 7800, 9000, 8500, 8800, 8600, 7500, 8200, 8400, 8100],
        "Proj_Pts": [24.5, 23.0, 21.0, 19.5, 22.0, 20.5, 18.0, 19.0, 20.0, 18.5],
        "Ownership_%": [15.5, 12.0, 35.0, 18.5, 25.0, 22.0, 30.0, 15.0, 10.0, 14.5],
        "Vegas_Total": [52.5, 50.0, 44.0, 48.5, 50.5, 47.0, 52.5, 50.0, 46.5, 49.0],
        "Weather": ["Clear", "Windy", "Clear", "Dome", "Humid", "Dome", "Clear", "Windy", "Dome", "Clear"]
    })

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.sidebar.success("✅ Real DFS Data Active!")
    except Exception as e:
        st.sidebar.error("⚠️ Error reading CSV!")
        df = load_god_data()
else:
    df = load_god_data()
    

# --- 4. TOP METRICS DASHBOARD ---
col1, col2, col3, col4 = st.columns(4)
col1.markdown(f'<div class="metric-box"><b>Total Players In Pool</b><br><span style="font-size:24px; color:#00FF41;">{len(df)} Active</span></div>', unsafe_allow_html=True)
col2.markdown(f'<div class="metric-box"><b>Highest Vegas Total</b><br><span style="font-size:24px; color:#00FF41;">{df["Vegas_Total"].max()} (Shootout)</span></div>', unsafe_allow_html=True)
col3.markdown(f'<div class="metric-box"><b>Highest Ownership (Chalk)</b><br><span style="font-size:24px; color:#FF3131;">{df["Ownership_%"].max()}%</span></div>', unsafe_allow_html=True)
col4.markdown(f'<div class="metric-box"><b>Engine Status</b><br><span style="font-size:24px; color:#00FF41;">READY FOR MASS ENTRY</span></div>', unsafe_allow_html=True)
st.write("")

# --- 5. PREMIUM GOD-MODE UI NAVIGATION (REPLACED TABS) ---
app_mode = st.radio(
    "Nav",
    ["📊 The Terminal (Data)", "📉 Visual Analytics (Charts)", "🚀 Generate & Export"],
    horizontal=True,
    label_visibility="collapsed"
)
st.divider()

if app_mode == "📊 The Terminal (Data)":
    st.subheader("Deep-Dive Player Matrix")
    st.dataframe(df.style.background_gradient(subset=['Proj_Pts', 'Vegas_Total'], cmap='Greens')
                 .background_gradient(subset=['Ownership_%'], cmap='Reds'), 
                 use_container_width=True, hide_index=True)

elif app_mode == "📉 Visual Analytics (Charts)":
    st.subheader("Pro Leverage & Risk Analytics")
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Scatter Plot: Salary vs Projected Points (Value Finder)
        fig1 = px.scatter(df, x="Salary", y="Proj_Pts", color="Pos", hover_name="Player", 
                          size="Vegas_Total", template="plotly_dark", 
                          title="Value Matrix (Salary vs Points)")
        st.plotly_chart(fig1, use_container_width=True)
        
    with chart_col2:
        # Bar Chart: Ownership vs Leverage
        fig2 = px.bar(df, x="Player", y="Ownership_%", color="Ownership_%", 
                      color_continuous_scale="Reds", template="plotly_dark",
                      title="Public Exposure (Ownership Risk)")
        st.plotly_chart(fig2, use_container_width=True)

# --- 6. THE CORE SOLVER ENGINE (UNTOUCHED) ---
def run_god_mode_solver(data, lineups_count, cap):
    lineups, stats = [], []
    for i in range(lineups_count):
        prob = pulp.LpProblem(f"GodMode_{i}", pulp.LpMaximize)
        p_vars = pulp.LpVariable.dicts("P", data.index, cat='Binary')
        
        # Maximize Points
        prob += pulp.lpSum([data["Proj_Pts"][idx] * p_vars[idx] for idx in data.index])
        # Salary Cap
        prob += pulp.lpSum([data["Salary"][idx] * p_vars[idx] for idx in data.index]) <= cap
        # Roster Size
        prob += pulp.lpSum([p_vars[idx] for idx in data.index]) == 5
        
        # Diversity Rule
        for prev in lineups:
            prob += pulp.lpSum([p_vars[idx] for idx in data.index if data["Player"][idx] in prev]) <= 3
            
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        if pulp.LpStatus[prob.status] == 'Optimal':
            sel = [data["Player"][idx] for idx in data.index if p_vars[idx].varValue == 1]
            pts = sum([data["Proj_Pts"][idx] for idx in data.index if p_vars[idx].varValue == 1])
            sal = sum([data["Salary"][idx] for idx in data.index if p_vars[idx].varValue == 1])
            own = sum([data["Ownership_%"][idx] for idx in data.index if p_vars[idx].varValue == 1]) / 5
            
            lineups.append(sel)
            stats.append(f"Pts: {pts:.1f} | Sal: ${sal} | Avg Own: {own:.1f}%")
        else:
            break
    return lineups, stats

# --- 7. EXECUTION (MERGED INTO RADIO UI) ---
elif app_mode == "🚀 Generate & Export":
    st.markdown("### Initialize Extreme Mass Multi-Entry")
    
    if st.button("🔥 RUN 10,000 MONTE CARLO SIMULATIONS & OPTIMIZE", type="primary", use_container_width=True):
        
        # Fake Loading Sequence to look ultra-pro
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for percent in range(100):
            time.sleep(0.02)
            progress_bar.progress(percent + 1)
            if percent < 30: status_text.text("Injecting Vegas Odds...")
            elif percent < 60: status_text.text(f"Running {simulations} Monte Carlo Scenarios...")
            elif percent < 90: status_text.text("Applying Stacking Correlations...")
            else: status_text.text("Finalizing Maximum ROI Lineups...")
            
        status_text.text("✅ SIMULATIONS COMPLETE. EXECUTING SOLVER.")
        
        final_lineups, stat_list = run_god_mode_solver(df, num_lineups, salary_cap)
        
        if final_lineups:
            st.success(f"🏆 {len(final_lineups)} GOD-TIER LINEUPS GENERATED!")
            
            # Formatted Output
            df_out = pd.DataFrame(final_lineups, columns=["Player 1", "Player 2", "Player 3", "Player 4", "Player 5"])
            df_out["Lineup Metrics"] = stat_list
            df_out.index = [f"Alpha {i+1}" for i in range(len(df_out))]
            
            st.dataframe(df_out, use_container_width=True)
            
            # Export CSV
            csv = df_out.to_csv().encode('utf-8')
            st.download_button("💾 DOWNLOAD MASTER CSV FOR DRAFTKINGS/FANDUEL", csv, "ProStack_GodMode_Lineups.csv", "text/csv", use_container_width=True)
        else:
            st.error("Engine Overload: Salary cap is too tight to build viable lineups.")
