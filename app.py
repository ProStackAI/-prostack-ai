import streamlit as st
import pandas as pd
import pulp
import plotly.express as px
import time
from datetime import datetime, timedelta
import hashlib
import sqlite3

# ==========================================
# 💳 STEP 0: CEO PAYMENT GATEWAY LINKS
# (Jab aapka Stripe/Razorpay account ban jaye, apne links yahan paste kar dein)
# ==========================================
PAYMENT_LINKS = {
    "🥇 1 Month Plan ($29 / ₹2,400)": "https://buy.stripe.com/test_1month_link",
    "🥈 3 Months Plan - Popular ($79 / ₹6,500)": "https://buy.stripe.com/test_3months_link",
    "🥉 6 Months Plan - Best Value ($139 / ₹11,500)": "https://buy.stripe.com/test_6months_link",
    "👑 1 Year VIP Pass ($249 / ₹20,000)": "https://buy.stripe.com/test_1year_link"
}

# --- 1. DATABASE & ENTERPRISE SETUP ---
def init_db():
    conn = sqlite3.connect('prostack_users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT,
            expiry_date TEXT,
            status TEXT,
            pending_plan TEXT DEFAULT 'None',
            payment_ref TEXT DEFAULT 'None'
        )
    ''')
    # Agar purani table hai toh naye columns add kar do bina data udaye
    try:
        c.execute("ALTER TABLE users ADD COLUMN pending_plan TEXT DEFAULT 'None'")
    except:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN payment_ref TEXT DEFAULT 'None'")
    except:
        pass
    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        dummy_pw = hashlib.sha256("password123".encode()).hexdigest()
        expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT OR IGNORE INTO users (email, password, expiry_date, status, pending_plan, payment_ref) VALUES (?, ?, ?, ?, ?, ?)", 
                  ("testuser@prostack.ai", dummy_pw, expiry, 'Active', 'None', 'None'))
        conn.commit()
        
    conn.close()

init_db()

def add_user(email, password, days=30):
    conn = sqlite3.connect('prostack_users.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        c.execute("INSERT INTO users (email, password, expiry_date, status, pending_plan, payment_ref) VALUES (?, ?, ?, ?, ?, ?)", 
                  (email, hashed_pw, expiry, 'Active', 'None', 'None'))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def submit_payment_request(email, plan_name, ref_id):
    conn = sqlite3.connect('prostack_users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET pending_plan = ?, payment_ref = ? WHERE email = ?", (plan_name, ref_id, email))
    conn.commit()
    conn.close()

def admin_update_user(email, new_status, add_days=0):
    conn = sqlite3.connect('prostack_users.db')
    c = conn.cursor()
    if add_days > 0:
        c.execute("SELECT expiry_date FROM users WHERE email = ?", (email,))
        row = c.fetchone()
        if row:
            current_expiry = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
            base_time = max(datetime.now(), current_expiry)
            new_expiry = (base_time + timedelta(days=add_days)).strftime('%Y-%m-%d %H:%M:%S')
            c.execute("UPDATE users SET expiry_date = ?, status = ?, pending_plan = 'Approved', payment_ref = 'Verified' WHERE email = ?", 
                      (new_expiry, new_status, email))
    else:
        c.execute("UPDATE users SET status = ? WHERE email = ?", (new_status, email))
    conn.commit()
    conn.close()

def get_user_status(email):
    if email == "ADMIN":
        return True, "Unlimited (VIP Admin)"
        
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
            
            /* Button Visibility Fix */
            .stButton > button { background-color: #1A202C !important; border: 2px solid #00FF41 !important; border-radius: 8px !important; }
            .stButton > button p, .stButton > button span { color: #00FF41 !important; font-weight: bold !important; }
            .stDownloadButton > button { background-color: #00FF41 !important; border: none !important; }
            .stDownloadButton > button p { color: #000000 !important; font-weight: 900 !important; }
            
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
    .admin-box {background-color: #1A202C; padding: 20px; border-radius: 10px; border: 2px solid #FFD700; margin-bottom: 20px;}
    .pay-link-btn {display: block; width: 100%; text-align: center; background-color: #00FF41; color: #000000 !important; font-weight: 900; padding: 14px; border-radius: 8px; text-decoration: none; font-size: 18px; margin-top: 10px; margin-bottom: 15px;}
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
            if st.button("🔥 LOGIN TO ENGINE", use_container_width=True):
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
            if st.button("🚀 CREATE ACCOUNT", use_container_width=True):
                if "@" in s_email and len(s_password) >= 6:
                    if add_user(s_email, s_password, days=30):
                        st.success("✅ Account created successfully! 30 Days Free Trial Granted. Please login.")
                    else:
                        st.error("⚠️ Email already registered!")
                else:
                    st.error("⚠️ Enter valid email and password (min 6 chars).")
    st.stop()

# ==========================================
# 👑 CEO ADMIN CONTROL ROOM (TOP SECTION)
# ==========================================
if st.session_state.user_email == "ADMIN":
    st.markdown("""
    <div class='admin-box'>
        <h2 style='color: #FFD700 !important;'>👑 CEO ADMIN CONTROL ROOM</h2>
        <p style='color: white;'>Yahan se aap users ke Payment Reference check kar sakte hain, unka plan (1M/3M/6M/1Y) badha sakte hain, ya kisi ko bhi Block kar sakte hain:</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = sqlite3.connect('prostack_users.db')
    users_df = pd.read_sql_query("SELECT email, expiry_date, status, pending_plan, payment_ref FROM users", conn)
    conn.close()
    
    total_users = len(users_df)
    active_users = len(users_df[users_df['status'] == 'Active']) if total_users > 0 else 0
    pending_payments = len(users_df[(users_df['pending_plan'] != 'None') & (users_df['pending_plan'] != 'Approved')]) if total_users > 0 else 0
    
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("👥 Total Users", total_users)
    with col_m2:
        st.metric("🟢 Active Users", active_users)
    with col_m3:
        st.metric("💰 Pending Verifications", pending_payments)
        
    st.dataframe(users_df, use_container_width=True)
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        target_email = st.selectbox("1. Select User", users_df['email'].tolist() if not users_df.empty else ["None"])
    with col_b:
        action = st.selectbox("2. Account Status", ["Active", "Blocked"])
    with col_c:
        plan_boost = st.selectbox("3. Add Subscription Days (Optional)", [
            "0 Days (Status Only)",
            "+30 Days (1 Month Plan)",
            "+90 Days (3 Months Plan)",
            "+180 Days (6 Months Plan)",
            "+365 Days (1 Year VIP)"
        ])
        
    boost_map = {
        "0 Days (Status Only)": 0,
        "+30 Days (1 Month Plan)": 30,
        "+90 Days (3 Months Plan)": 90,
        "+180 Days (6 Months Plan)": 180,
        "+365 Days (1 Year VIP)": 365
    }
        
    if st.button("⚡ EXECUTE ADMIN COMMAND (UPDATE USER)", use_container_width=True):
        if target_email and target_email != "None":
            days_to_add = boost_map[plan_boost]
            admin_update_user(target_email, action, days_to_add)
            st.success(f"✅ User {target_email} updated! Status: {action} | Added Days: {days_to_add}")
            time.sleep(1)
            st.rerun()
            
    st.divider()

# ==========================================
# 🟢 CHECK SUBSCRIPTION STATUS & PAYMENT WALL
# ==========================================
is_active, exp_info = get_user_status(st.session_state.user_email)

st.markdown(f'<p class="god-title">⚡ ProStack AI</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-text">Welcome, {st.session_state.user_email} | Status: {"🟢 Active (Valid till: " + exp_info + ")" if is_active else "🔴 Expired"}</p>', unsafe_allow_html=True)
st.divider()

if not is_active:
    st.markdown("""
    <div class='recharge-box'>
        <h2 style='color: #FF3131 !important;'>⚠️ SUBSCRIPTION EXPIRED</h2>
        <p style='color: white;'>Your access pass has ended. Complete your payment below and submit your Transaction ID to unlock God-Mode.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 💳 Step 1: Select Your Recharge Plan")
    plan = st.radio("Choose Duration:", list(PAYMENT_LINKS.keys()))
    
    selected_link = PAYMENT_LINKS[plan]
    st.markdown(f"<a href='{selected_link}' target='_blank' class='pay-link-btn'>💳 CLICK HERE TO PAY FOR {plan.split('(')[0].upper()}</a>", unsafe_allow_html=True)
    
    st.markdown("### 🧾 Step 2: Verify Your Payment")
    ref_id = st.text_input("Enter Payment Transaction ID / UTR / Reference Number:", placeholder="e.g. TXN982374923 or Stripe Email")
    
    if st.button("🚀 SUBMIT PAYMENT FOR ACTIVATION", use_container_width=True):
        if len(ref_id.strip()) >= 4:
            submit_payment_request(st.session_state.user_email, plan, ref_id.strip())
            st.success("✅ Payment Reference Submitted! Admin will verify and activate your account shortly.")
        else:
            st.error("⚠️ Please enter a valid Transaction / Reference ID after making the payment.")
            
    st.write("")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()
    st.stop()

# ==========================================
# 🚀 MAIN DFS ENGINE & PLAYER MATRIX
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
    if st.button("🔥 RUN AUTO-PILOT OPTIMIZER", use_container_width=True):
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

st.divider()
if st.button("🚪 Logout Account", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.rerun()
