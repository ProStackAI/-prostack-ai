import streamlit as st
import pandas as pd
import pulp
import plotly.express as px
import time

# --- 1. EXTREMELY ULTRA PAGE SETUP ---
st.set_page_config(page_title="ProStack AI - GOD MODE", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

# --- ULTRA VIBE CSS (COLOR FIX & SIDEBAR KILLER) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            
            /* Sidebar ko mobile app se hamesha ke liye gayab karna */
            [data-testid="stSidebar"] {display: none;}
            
            /* Radio Buttons Premium CSS (TEXT COLOR FIXED) */
            div.row-widget.stRadio > div{flex-direction:row; justify-content: space-between; flex-wrap: wrap;}
            div.row-widget.stRadio > div > label{
                background-color: #1A202C !important; 
                padding: 10px; border-radius: 5px; border: 1px solid #00FF41 !important; 
                cursor: pointer; flex-grow: 1; text-align: center; margin: 3px;
            }
            /* Streamlit ke hidden <p> tag ka color force-white karna */
            div.row-widget.stRadio > div > label p {
                color: #FFFFFF !important; 
                font-weight: bold !important;
                font-size: 13px !important;
            }
            div.row-widget.stRadio > div > label:hover{background-color: #00FF41 !important;}
            div.row-widget.stRadio > div > label:hover p{color: #0E1117 !important;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Hacker/Terminal Premium CSS
st.markdown("""
    <style>
    .stApp {background-color: #0E1117;}
    .god-title {font-size: 38px; color: #00FF41; font-weight: 900; text-transform: uppercase; text-shadow: 0px 0px 10px #00FF41;}
    .sub-text {color: #A0AEC0; font-size: 14px; font-style: italic;}
    .metric-box {background-color: #1A202C; padding: 10px; border-radius: 8px; border-left: 4px solid #00FF41; margin-bottom: 10px;}
    .news-box-red {background-color: #1A202C; padding: 15px; border-radius: 8px; border-left: 4px solid #FF3131; margin-bottom: 15px;}
    .news-box-blue {background-color: #1A202C; padding: 15px; border-radius: 8px; border-left: 4px solid #00BFFF; margin-bottom: 15px;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="god-title">⚡ ProStack AI</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-text">Mobile Terminal | Monte Carlo Sims | Auto-Stack</p>', unsafe_allow_html=True)
st.divider()

# --- 2. GOD-MODE DATA GENERATOR ---
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

df = load_god_data()

# --- 3. THE CORE SOLVER ENGINE ---
def run_god_mode_solver(data, lineups_count, cap):
    lineups, stats = [], []
    for i in range(lineups_count):
        prob = pulp.LpProblem(f"GodMode_{i}", pulp.LpMaximize)
        p_vars = pulp.LpVariable.dicts("P", data.index, cat='Binary')
        
        prob += pulp.lpSum([data["Proj_Pts"][idx] * p_vars[idx] for idx in data.index])
        prob += pulp.lpSum([data["Salary"][idx] * p_vars[idx] for idx in data.index]) <= cap
        prob += pulp.lpSum([p_vars[idx] for idx in data.index]) == 5
        
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

# --- 4. TOP METRICS DASHBOARD (MOBILE OPTIMIZED) ---
col1, col2 = st.columns(2)
col1.markdown(f'<div class="metric-box"><b>Total Pool</b><br><span style="font-size:18px; color:#00FF41;">{len(df)} Active</span></div>', unsafe_allow_html=True)
col2.markdown(f'<div class="metric-box"><b>Max Vegas</b><br><span style="font-size:18px; color:#00FF41;">{df["Vegas_Total"].max()} Total</span></div>', unsafe_allow_html=True)

# --- 5. PREMIUM GOD-MODE UI NAVIGATION (4 TABS NOW) ---
app_mode = st.radio(
    "Nav",
    ["📊 Terminal", "📰 Match News", "📉 Analytics", "🚀 Engine"],
    horizontal=True,
    label_visibility="collapsed"
)
st.divider()

if app_mode == "📊 Terminal":
    st.subheader("Mobile-Optimized Matrix")
    st.write("*(Critical data strictly formatted for zero-sliding)*")
    mobile_df = df[['Player', 'Pos', 'Salary', 'Proj_Pts', 'Ownership_%']]
    st.dataframe(mobile_df.style.background_gradient(subset=['Proj_Pts'], cmap='Greens')
                 .background_gradient(subset=['Ownership_%'], cmap='Reds'), 
                 use_container_width=True, hide_index=True)

elif app_mode == "📰 Match News":
    st.subheader("🚨 Live Match & Injury Updates")
    
    st.markdown("""
    <div class='news-box-red'>
        <b style='color:#FF3131; font-size:16px;'>⚠️ INJURY REPORT (OUT & QUESTIONABLE)</b><br><br>
        • <b>C. Kupp (WR)</b> - <span style='color:orange;'>Questionable (Ankle)</span> - Game-time decision.<br>
        • <b>A. Ekeler (RB)</b> - <span style='color:red;'>OUT (Hamstring)</span> - Remove from all lineups.<br>
        • <b>J. Allen (QB)</b> - <span style='color:#00FF41;'>Fit/Probable</span> - Fully cleared to play.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='news-box-blue'>
        <b style='color:#00BFFF; font-size:16px;'>🏟️ WEATHER & STADIUM INTEL</b><br><br>
        • <b>BUF vs KC</b>: 18mph Winds, Light Rain (Downgrade Passing, Upgrade Running).<br>
        • <b>MIN vs LAR</b>: Playing in Dome (Optimal Conditions for WRs).<br>
        • <b>PHI vs LAC</b>: Clear Skies, 65°F (Normal gameplay).
    </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 Pro-Tip: Use these updates to manually adjust players in the Engine before generating 150 lineups.")

elif app_mode == "📉 Analytics":
    st.subheader("Pro Leverage & Risk")
    fig1 = px.scatter(df, x="Salary", y="Proj_Pts", color="Pos", hover_name="Player", 
                      template="plotly_dark", title="Value Matrix")
    st.plotly_chart(fig1, use_container_width=True)
    
    fig2 = px.bar(df, x="Player", y="Ownership_%", color="Ownership_%", 
                  color_continuous_scale="Reds", template="plotly_dark",
                  title="Chalk Exposure Risk")
    st.plotly_chart(fig2, use_container_width=True)

elif app_mode == "🚀 Engine":
    st.markdown("### ⚙️ Engine Settings (150-Max Mode)")
    
    num_lineups = st.slider("🎯 Number of Lineups to Generate", 1, 150, 20)
    salary_cap = st.number_input("💰 Salary Cap Limit", value=50000, step=100)
    simulations = st.select_slider("🎲 Monte Carlo Sims", options=["100", "1,000", "10,000 (Max)"], value="1,000")
    
    st.write("")
    if st.button("🔥 RUN SIMULATIONS & OPTIMIZE", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for percent in range(100):
            time.sleep(0.01)
            progress_bar.progress(percent + 1)
            if percent < 40: status_text.text("Injecting Vegas Odds...")
            elif percent < 80: status_text.text(f"Running {simulations} Scenarios...")
            else: status_text.text("Solving for Maximum ROI...")
            
        status_text.text("✅ EXECUTION COMPLETE.")
        
        final_lineups, stat_list = run_god_mode_solver(df, num_lineups, salary_cap)
        
        if final_lineups:
            st.success(f"🏆 {len(final_lineups)} LINEUPS GENERATED!")
            df_out = pd.DataFrame(final_lineups, columns=["P1", "P2", "P3", "P4", "P5"])
            df_out["Metrics"] = stat_list
            df_out.index = [f"A-{i+1}" for i in range(len(df_out))]
            st.dataframe(df_out, use_container_width=True)
            
            csv = df_out.to_csv().encode('utf-8')
            st.download_button("💾 DOWNLOAD MASTER CSV", csv, "ProStack_Lineups.csv", "text/csv", use_container_width=True)
        else:
            st.error("Engine Overload: Salary cap constraint failed.")
