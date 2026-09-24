import streamlit as st
import pandas as pd
import pulp
import plotly.express as px
import time

# --- 1. EXTREMELY ULTRA PAGE SETUP ---
st.set_page_config(page_title="ProStack AI - GOD MODE", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

# --- ULTRA VIBE CSS (ABSOLUTE NUCLEAR TEXT COLOR FIX) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            [data-testid="stSidebar"] {display: none;}
            
            /* 🔥 FORCE EVERY SINGLE TEXT ELEMENT TO WHITE 🔥 */
            /* General text, markdown, and labels */
            .stApp p, .stApp label, .stApp span, .stApp div[data-testid="stMarkdownContainer"] p {
                color: #FFFFFF !important;
            }
            
            /* Specific fix for Radio Buttons ("Head-to-Head", "Mega Grand League") */
            div[role="radiogroup"] p, div[data-baseweb="radio"] p {
                color: #FFFFFF !important;
                font-size: 16px !important;
                font-weight: bold !important;
            }
            
            /* Selectbox, Slider, and Number Input text */
            .stSelectbox label p, .stSlider label p, .stNumberInput label p, .stFileUploader label p {
                color: #FFFFFF !important;
            }
            
            /* Values inside sliders and dropdowns */
            div[data-baseweb="select"] span, div[data-baseweb="slider"] div {
                color: #FFFFFF !important;
            }
            
            /* Make headings Neon Green */
            h1, h2, h3, h4, h5, h6 {
                color: #00FF41 !important;
            }
            
            /* Input box text typing color */
            input {
                color: #FFFFFF !important;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.markdown("""
    <style>
    .stApp {background-color: #0E1117;}
    .god-title {font-size: 38px; color: #00FF41 !important; font-weight: 900; text-transform: uppercase; text-shadow: 0px 0px 10px #00FF41;}
    .sub-text {color: #A0AEC0 !important; font-size: 14px; font-style: italic;}
    .metric-box {background-color: #1A202C; padding: 10px; border-radius: 8px; border-left: 4px solid #00FF41; margin-bottom: 10px;}
    .news-box-red {background-color: #1A202C; padding: 15px; border-radius: 8px; border-left: 4px solid #FF3131; margin-bottom: 15px;}
    .news-box-blue {background-color: #1A202C; padding: 15px; border-radius: 8px; border-left: 4px solid #00BFFF; margin-bottom: 15px;}
    .strategy-box {background-color: #1A202C; padding: 15px; border-radius: 8px; border-left: 4px solid #FFD700; margin-bottom: 15px;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="god-title">⚡ ProStack AI</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-text">Auto-Pilot DFS Engine | Mega League & H2H Dominator</p>', unsafe_allow_html=True)
st.divider()

# --- 2. 📥 FILE UPLOADER (TOP LEVEL) ---
st.markdown("### 📥 Step 1: Upload Match Data")
uploaded_file = st.file_uploader("Upload Real DFS CSV Data (Leave blank for default projections)", type=["csv"])

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
        "Vegas_Total": [52.5, 50.0, 44.0, 48.5, 50.5, 47.0, 52.5, 50.0, 46.5, 49.0]
    })

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("✅ Real DFS Data Uploaded Successfully!")
    except Exception as e:
        st.error("⚠️ Error reading CSV! Using default data.")
        df = load_god_data()
else:
    df = load_god_data()

# --- 3. AUTO-PILOT AI SOLVER ENGINE ---
def run_god_mode_solver(data, lineups_count, cap, strategy_mode):
    lineups, stats = [], []
    for i in range(lineups_count):
        prob = pulp.LpProblem(f"GodMode_{i}", pulp.LpMaximize)
        p_vars = pulp.LpVariable.dicts("P", data.index, cat='Binary')
        
        prob += pulp.lpSum([data["Proj_Pts"][idx] * p_vars[idx] for idx in data.index])
        prob += pulp.lpSum([data["Salary"][idx] * p_vars[idx] for idx in data.index]) <= cap
        prob += pulp.lpSum([p_vars[idx] for idx in data.index]) == 5
        
        if strategy_mode == "💣 Mega Grand League (High Risk/Reward)":
            prob += pulp.lpSum([data["Ownership_%"][idx] * p_vars[idx] for idx in data.index]) <= 80
        
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

st.divider()

# --- 4. PREMIUM GOD-MODE UI NAVIGATION (BULLETPROOF DROPDOWN) ---
st.markdown("### 🧭 Step 2: Navigation Menu")
app_mode = st.selectbox(
    "Choose your section:",
    ["📊 The Terminal (Player Data)", "📰 Live Match News", "📉 Pro Analytics", "🚀 Auto-Pilot Engine"],
    label_visibility="collapsed"
)
st.divider()

if app_mode == "📊 The Terminal (Player Data)":
    st.subheader("Mobile-Optimized Matrix")
    
    mobile_df = df[['Player', 'Pos', 'Salary', 'Proj_Pts', 'Ownership_%']].copy()
    if 'Proj_Pts' in mobile_df.columns:
        mobile_df['Proj_Pts'] = mobile_df['Proj_Pts'].round(1)
    if 'Ownership_%' in mobile_df.columns:
        mobile_df['Ownership_%'] = mobile_df['Ownership_%'].round(1)
    
    st.dataframe(mobile_df.style.background_gradient(subset=['Proj_Pts'], cmap='Greens')
                 .background_gradient(subset=['Ownership_%'], cmap='Reds'), 
                 use_container_width=True, hide_index=True)

elif app_mode == "📰 Live Match News":
    st.subheader("🚨 Live Match & Injury Updates")
    st.markdown("""
    <div class='news-box-red'>
        <b style='color:#FF3131; font-size:16px;'>⚠️ INJURY REPORT</b><br>
        <span style='color:white;'>• <b>C. Kupp (WR)</b> - Questionable<br>
        • <b>A. Ekeler (RB)</b> - OUT (Hamstring)</span><br>
    </div>
    """, unsafe_allow_html=True)

elif app_mode == "📉 Pro Analytics":
    st.subheader("Pro Leverage & Risk")
    fig1 = px.scatter(df, x="Salary", y="Proj_Pts", color="Pos", hover_name="Player", template="plotly_dark", title="Value Matrix")
    st.plotly_chart(fig1, use_container_width=True)

elif app_mode == "🚀 Auto-Pilot Engine":
    st.markdown("### 🧠 Engine Settings")
    
    st.markdown("""
    <div class='strategy-box'>
        <b style='color:#FFD700; font-size:16px;'>Step 3: Choose Your Strategy</b><br>
        <span style='color:white;'>Let the AI handle the heavy lifting based on your contest type.</span>
    </div>
    """, unsafe_allow_html=True)
    
    strategy = st.radio("Target Contest Type:", [
        "🛡️ Head-to-Head (Safe & Consistent)", 
        "💣 Mega Grand League (High Risk/Reward)"
    ])
    
    st.write("")
    num_lineups = st.slider("🎯 Number of Lineups", 1, 150, 20)
    salary_cap = st.number_input("💰 Salary Cap", value=50000, step=100)
    
    st.write("")
    if st.button("🔥 RUN AUTO-PILOT OPTIMIZER", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for percent in range(100):
            time.sleep(0.01)
            progress_bar.progress(percent + 1)
            if percent < 50: status_text.text(f"Applying {strategy} Algorithms...")
            else: status_text.text("Building Optimized Core...")
            
        status_text.text("✅ EXECUTION COMPLETE.")
        
        final_lineups, stat_list = run_god_mode_solver(df, num_lineups, salary_cap, strategy)
        
        if final_lineups:
            st.success(f"🏆 {len(final_lineups)} LINEUPS GENERATED!")
            df_out = pd.DataFrame(final_lineups, columns=["P1", "P2", "P3", "P4", "P5"])
            df_out["Metrics"] = stat_list
            df_out.index = [f"A-{i+1}" for i in range(len(df_out))]
            st.dataframe(df_out, use_container_width=True)
        else:
            st.error("Engine Overload: Salary cap constraint failed.")
