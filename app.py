import streamlit as st
import pandas as pd
import pulp
import plotly.express as px
import time
from datetime import datetime, timedelta
import hashlib
import sqlite3

# --- 1. DATABASE & ENTERPRISE SETUP ---
def init_db():
    conn = sqlite3.connect('prostack_users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT,
            expiry_date TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def add_user(email, password, days=30):
    conn = sqlite3.connect('prostack_users.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        c.execute("INSERT INTO users (email, password, expiry_date, status) VALUES (?, ?, ?, ?)", 
                  (email, hashed_pw, expiry, 'Active'))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def extend_subscription(email, days):
    conn = sqlite3.connect('prostack_users.db')
    c = conn.cursor()
    c.execute("SELECT expiry_date FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    if row:
        current_expiry = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
        base_time = max(datetime.now(), current_expiry)
        new_expiry = (base_time + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute("UPDATE users SET expiry_date = ?, status = 'Active' WHERE email = ?", (new_expiry, email))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_user_status(email):
    conn = sqlite3.connect('prostack_users.db')
    c = conn.cursor()
    c.execute("SELECT expiry_date, status FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row:
        expiry_str, status = row
        if status == 'Blocked':
            return False, "Blocked"
        expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
        if datetime.now() > expiry_date:
            return False, "Expired"
        return True, expiry_date.strftime('%Y-%m-%d')
    return False, "Not Found"

def verify_user(email, password):
    conn = sqlite3.connect('prostack_users.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT expiry_date, status FROM users WHERE email = ? AND password = ?", (email, hashed_pw))
    row = c.fetchone()
    conn.close()
    if row:
        _, status = row
        if status == 'Blocked':
            return False, "Your account has been blocked by Admin."
        return True, "Login Successful"
    return False, "Invalid Email or Password"

# --- 2. EXTREMELY ULTRA PAGE SETUP ---
st.set_page_config(page_title="ProStack AI - GOD MODE", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            [data-testid="stSidebar"] {display: none;}
            
            .stApp p, .stApp label, .stApp div[data-testid="stMarkdownContainer"] p { color: #FFFFFF !important; }
            div[role="radiogroup"] p, div[data-baseweb="radio"] p { color: #FFFFFF !important; font-size: 16px !important; font-weight: bold !important; }
            .stSelectbox label p, .stSlider label p, .stNumberInput label p, .stFileUploader label p { color: #FFFFFF !important; }
            h1, h2, h3, h4, h5, h6 { color: #00FF41 !important; }
            
            div[data-baseweb="select"] span { color: #000000 !important; font-weight: bold !important; }
            div[data-testid="stFileUploaderDropzone"] * { color: #000000 !important; font-weight: bold !important; }
            div[data-testid="stFileUploaderDropzone"] button { border-color: #00FF41 !important; color: #000000 !important; }
            div[data-baseweb="slider"] div { color: #FFFFFF !important; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
st.markdown("""
    <style>
    .stApp {background-color: #0E1117;}
    .god-title {font-size: 38px; color: #00FF41 !important; font-weight: 900; text-transform: uppercase; text-shadow: 0px 0px 10px #00FF41;}
    .sub-text {color: #A0AEC0 !important; font-size: 14px; font-style: italic;}
    .strategy-box {background-color: #1A202C; padding: 15px; border-radius: 8px; border-left: 4px solid #FFD700; margin-bottom: 15px;}
    .recharge-box {background-color: #1A202C; padding: 20px; border-radius: 10px; border: 2px solid #FF3131; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 LOGIN & SIGNUP AUTHENTICATION GATE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = ""

if not st.session_state.logged_in:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>⚡ PROSTACK AI PORTAL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A0AEC0;'>Enter your credentials or create an account to access God-Mode.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        auth_mode = st.radio("Choose Action:", ["Login", "Sign Up (Register)"], horizontal=True)
        
        if auth_mode == "Login":
            l_email = st.text_input("Email Address")
            l_password = st.text_input("Password", type="password")
            if st.button("🔥 LOGIN TO ENGINE", use_container_width=True, type="primary"):
                if l_email == "admin@prostack.ai" and l_password == "ceo2000cr":
                    st.session_state.logged_in = True
                    st.session_state.user_email = "ADMIN"
                    st.rerun()
                else:
                    success, msg = verify_user(l_email, l_password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.user_email = l_email
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        else:
            s_email = st.text_input("Enter Your Email Address")
            s_password = st.text_input("Create Password", type="password")
            if st.button("🚀 CREATE ACCOUNT", use_container_width=True, type="primary"):
                if "@" in s_email and len(s_password) >= 6:
                    if add_user(s_email, s_password, days=30):
                        st.success("✅ Account created successfully! 30 Days Free Trial Granted. Please login.")
                    else:
                        st.error("⚠️ Email already registered!")
                else:
                    st.error("⚠️ Enter valid email and password (min 6 chars).")
    st.stop()

# ==========================================
# 👑 ADMIN PANEL (CEO CONTROL ROOM)
# ==========================================
if st.session_state.user_email == "ADMIN":
    st.markdown("<h1 style='color: #FFD700;'>👑 CEO ADMIN CONTROL ROOM</h1>", unsafe_allow_html=True)
    st.markdown("Yeh aapka master database hai jahan saare 4000+ users ke emails aur expiry dates saved hain:")
    
    conn = sqlite3.connect('prostack_users.db')
    users_df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    
    st.dataframe(users_df, use_container_width=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        target_email = st.selectbox("Select User to Manage", users_df['email'].tolist() if not users_df.empty else ["None"])
    with col_b:
        action = st.selectbox("Action", ["Active", "Blocked"])
        
    if st.button("⚡ Update User Status"):
        if target_email != "None":
            conn = sqlite3.connect('prostack_users.db')
            c = conn.cursor()
            c.execute("UPDATE users SET status = ? WHERE email = ?", (action, target_email))
            conn.commit()
            conn.close()
            st.success(f"User {target_email} status updated to {action}!")
            st.rerun()
            
    if st.button("🚪 Logout Admin"):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()
    st.stop()

# ==========================================
# 🟢 CHECK SUBSCRIPTION STATUS (NON-BLOCKING)
# ==========================================
is_active, exp_info = get_user_status(st.session_state.user_email)

st.markdown(f'<p class="god-title">⚡ ProStack AI</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-text">Welcome, {st.session_state.user_email} | Status: {"🟢 Active (Valid till: " + exp_info + ")" if is_active else "🔴 Expired"}</p>', unsafe_allow_html=True)
st.divider()

# YADI PLAN KHATAM HO GAYA HAI, TOH APP KHULEGA LEKIN RECHARGE WALL DIKHEGI
if not is_active:
    st.markdown("""
    <div class='recharge-box'>
        <h2 style='color: #FF3131 !important;'>⚠️ SUBSCRIPTION EXPIRED</h2>
        <p style='color: white;'>Your 1-month pass has ended. Please choose your recharge plan below to renew your access instantly and unlock the Auto-Pilot Engine.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 💳 Select Your Recharge Plan")
    plan = st.radio("Choose Duration:", [
        "🥇 1 Month Plan ($29 / ₹2,400)", 
        "🥈 3 Months Plan - Popular ($79 / ₹6,500)", 
        "🥉 6 Months Plan - Best Value ($139 / ₹11,500)", 
        "👑 1 Year VIP Pass ($249 / ₹20,000)"
    ])
    
    days_map = {
        "🥇 1 Month Plan ($29 / ₹2,400)": 30,
        "🥈 3 Months Plan - Popular ($79 / ₹6,500)": 90,
        "🥉 6 Months Plan - Best Value ($139 / ₹11,500)": 180,
        "👑 1 Year VIP Pass ($249 / ₹20,000)": 365
    }
    
    st.write("")
    if st.button("🚀 PROCEED TO SECURE PAYMENT & RENEW", type="primary", use_container_width=True):
        selected_days = days_map[plan]
        if extend_subscription(st.session_state.user_email, selected_days):
            st.success("✅ Payment Successful! Subscription Renewed. Refreshing app...")
            time.sleep(2)
            st.rerun()
        else:
            st.error("❌ Recharge failed. Please contact support.")
            
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()
    st.stop()

# ==========================================
# 🚀 ACTIVE USER MAIN DFS ENGINE APP
# ==========================================

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

st.markdown("### 🧭 Step 2: Navigation Menu")
app_mode = st.selectbox(
    "Choose your section:",
    ["🚀 Auto-Pilot Engine", "📊 The Terminal (Player Data)", "📰 Live Match News", "📉 Pro Analytics"],
    label_visibility="collapsed"
)
st.divider()

if app_mode == "🚀 Auto-Pilot Engine":
    st.markdown("### 🧠 Engine Settings")
    st.markdown("""
    <div class='strategy-box'>
        <b style='color:#FFD700; font-size:16px;'>Step 3: Choose Your Strategy</b><br>
        <span style='color:white;'>Let the AI handle the heavy lifting based on your contest type.</span>
    </div>
    """, unsafe_allow_html=True)
    
    strategy = st.radio("Target Contest Type:", ["🛡️ Head-to-Head (Safe & Consistent)", "💣 Mega Grand League (High Risk/Reward)"])
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
            
            csv = df_out.to_csv().encode('utf-8')
            st.download_button("💾 DOWNLOAD MASTER CSV", csv, "ProStack_Lineups.csv", "text/csv", use_container_width=True)
        else:
            st.error("Engine Overload: Salary cap constraint failed.")

elif app_mode == "📊 The Terminal (Player Data)":
    st.subheader("Deep-Dive Player Matrix")
    st.markdown("<span style='color:#A0AEC0; font-size:12px;'>*(Swipe left/right on the table to see full data)*</span>", unsafe_allow_html=True)
    
    full_df = df.copy()
    if 'Proj_Pts' in full_df.columns: full_df['Proj_Pts'] = full_df['Proj_Pts'].round(1)
    if 'Ownership_%' in full_df.columns: full_df['Ownership_%'] = full_df['Ownership_%'].round(1)
    
    st.dataframe(full_df.style.background_gradient(subset=['Proj_Pts'], cmap='Greens')
                 .background_gradient(subset=['Ownership_%'], cmap='Reds'), 
                 use_container_width=True, hide_index=True)

elif app_mode == "📰 Live Match News":
    st.subheader("🚨 Live Match & Injury Updates")
    st.markdown("""
    <div class='news-box-red' style='background-color: #1A202C; padding: 15px; border-radius: 8px; border-left: 4px solid #FF3131; margin-bottom: 15px;'>
        <b style='color:#FF3131; font-size:16px;'>⚠️ INJURY REPORT</b><br>
        <span style='color:white;'>• <b>C. Kupp (WR)</b> - Questionable<br>
        • <b>A. Ekeler (RB)</b> - OUT (Hamstring)</span><br>
    </div>
    """, unsafe_allow_html=True)

elif app_mode == "📉 Pro Analytics":
    st.subheader("Pro Leverage & Risk")
    fig1 = px.scatter(df, x="Salary", y="Proj_Pts", color="Pos", hover_name="Player", template="plotly_dark", title="Value Matrix")
    st.plotly_chart(fig1, use_container_width=True)

# LOGOUT BUTTON FOR USERS
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.rerun()
