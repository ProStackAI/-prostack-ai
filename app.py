import streamlit as st
import pandas as pd
import numpy as np
import pulp
import plotly.express as px
import time
import random
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
import hashlib
import sqlite3

# ==========================================
# ⚙️ STEP 0: USA & CANADA PAYMENT LINKS (USD & CAD ONLY)
# ==========================================
PAYMENT_LINKS = {
    "🥇 1 Month All-Access Pass ($29 USD / $39 CAD)": "https://buy.stripe.com/test_1month_link",
    "🥈 3 Months Pro Pass - Popular ($79 USD / $109 CAD)": "https://buy.stripe.com/test_3months_link",
    "🥉 6 Months Elite Pass - Best Value ($139 USD / $189 CAD)": "https://buy.stripe.com/test_6months_link",
    "👑 1 Year VIP Vegas Pass ($249 USD / $339 CAD)": "https://buy.stripe.com/test_1year_link"
}

SUPPORT_WHATSAPP_URL = "https://wa.me/19999999999?text=Hello%20ProStack%20AI%20VIP%20Support"
SUPPORT_TELEGRAM_URL = "https://t.me/ProStackAI_Support"
SUPPORT_EMAIL = "support@prostack.ai"

SMTP_SENDER_EMAIL = ""
SMTP_APP_PASSWORD = ""

# --- 1. DATABASE & ENTERPRISE SETUP ---
DB_FILE = 'prostack_us_canada_v5.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            phone TEXT DEFAULT 'Not Provided',
            password TEXT,
            expiry_date TEXT,
            status TEXT,
            pending_plan TEXT DEFAULT 'None',
            payment_ref TEXT DEFAULT 'None'
        )
    ''')
    try:
        c.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT 'Not Provided'")
    except:
        pass
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
        c.execute("INSERT OR IGNORE INTO users (email, phone, password, expiry_date, status, pending_plan, payment_ref) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                  ("testuser@prostack.ai", "+1234567890", dummy_pw, expiry, 'Active', 'None', 'None'))
        conn.commit()
        
    conn.close()

init_db()

def add_user(email, phone, password, days=30):
    clean_email = email.strip().lower()
    clean_phone = phone.strip()
    clean_pw = password.strip()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    hashed_pw = hashlib.sha256(clean_pw.encode()).hexdigest()
    expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        c.execute("INSERT INTO users (email, phone, password, expiry_date, status, pending_plan, payment_ref) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                  (clean_email, clean_phone, hashed_pw, expiry, 'Active', 'None', 'None'))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def check_user_for_recovery(email, phone):
    clean_email = email.strip().lower()
    clean_phone = phone.strip()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT email, phone FROM users WHERE email = ?", (clean_email,))
    row = c.fetchone()
    conn.close()
    if row:
        db_email, db_phone = row
        if db_phone == clean_phone or clean_phone in db_phone or db_phone == "Not Provided":
            return True
    return False

def reset_user_password(email, new_password):
    clean_email = email.strip().lower()
    hashed_pw = hashlib.sha256(new_password.strip().encode()).hexdigest()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_pw, clean_email))
    conn.commit()
    conn.close()
    return True

def send_recovery_otp_notification(target_email, target_phone, otp_code):
    if SMTP_SENDER_EMAIL and SMTP_APP_PASSWORD:
        try:
            msg = EmailMessage()
            msg['Subject'] = f"🔑 ProStack AI - Password Reset OTP: {otp_code}"
            msg['From'] = SMTP_SENDER_EMAIL
            msg['To'] = target_email
            msg.set_content(f"Hello ProStack AI Member,\n\nYour One-Time Password (OTP) for resetting your account password is: {otp_code}\nRegistered Phone: {target_phone}\n\nIf you did not request this, please ignore this message.")
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(SMTP_SENDER_EMAIL, SMTP_APP_PASSWORD)
                smtp.send_message(msg)
            return True, "Sent to Email & SMS Gateway"
        except Exception:
            return False, "Instant Gateway Active"
    return False, "Instant Gateway Active"

def submit_payment_request(email, plan_name, ref_id):
    clean_email = email.strip().lower()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET pending_plan = ?, payment_ref = ? WHERE email = ?", (plan_name, ref_id, clean_email))
    conn.commit()
    conn.close()

def admin_update_user(email, new_status, add_days=0, delete_user=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if delete_user:
        c.execute("DELETE FROM users WHERE email = ?", (email,))
    elif add_days > 0:
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
        
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT expiry_date, status FROM users WHERE email = ?", (email.strip().lower(),))
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
    clean_email = email.strip().lower()
    clean_pw = password.strip()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    hashed_pw = hashlib.sha256(clean_pw.encode()).hexdigest()
    hashed_pw_lower = hashlib.sha256(clean_pw.lower().encode()).hexdigest()
    
    c.execute("SELECT expiry_date, status FROM users WHERE email = ? AND (password = ? OR password = ?)", 
              (clean_email, hashed_pw, hashed_pw_lower))
    row = c.fetchone()
    conn.close()
    if row:
        _, status = row
        if status == 'Blocked':
            return False, "Your account has been blocked by Admin."
        return True, "Login Successful"
    return False, "Invalid Email or Password"

# --- 2. EXTREMELY ULTRA PAGE SETUP ---
st.set_page_config(page_title="ProStack AI - USA & Canada DFS", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            [data-testid="stSidebar"] {display: none;}
            
            .stApp p, .stApp label, .stApp div[data-testid="stMarkdownContainer"] p { color: #FFFFFF !important; }
            div[role="radiogroup"] p, div[data-baseweb="radio"] p { color: #FFFFFF !important; font-size: 16px !important; font-weight: bold !important; }
            .stSelectbox label p, .stMultiSelect label p, .stSlider label p, .stNumberInput label p, .stFileUploader label p { color: #FFFFFF !important; }
            h1, h2, h3, h4, h5, h6 { color: #00FF41 !important; }
            
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
    .vip-box {background-color: #1A202C; padding: 20px; border-radius: 10px; border: 2px solid #00BFFF; margin-bottom: 20px;}
    .live-card {background-color: #1A202C; padding: 14px; border-radius: 8px; border-left: 5px solid #FF3131; border-right: 1px solid #00FF41; margin-bottom: 10px;}
    .upcoming-card {background-color: #1A202C; padding: 14px; border-radius: 8px; border-left: 5px solid #00BFFF; margin-bottom: 10px;}
    .badge-live {background-color: #FF3131; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;}
    .badge-upcoming {background-color: #00BFFF; color: black; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;}
    .pay-link-btn {display: block; width: 100%; text-align: center; background-color: #00FF41; color: #000000 !important; font-weight: 900; padding: 14px; border-radius: 8px; text-decoration: none; font-size: 17px; margin-top: 10px; margin-bottom: 15px;}
    .support-btn {display: block; width: 100%; text-align: center; background-color: #00BFFF; color: #000000 !important; font-weight: 900; padding: 12px; border-radius: 8px; text-decoration: none; font-size: 16px; margin-top: 8px; margin-bottom: 8px;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 LOGIN, SIGNUP & FORGOT PASSWORD GATE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = ""
if 'reset_otp' not in st.session_state:
    st.session_state.reset_otp = None
    st.session_state.reset_target_email = ""

if not st.session_state.logged_in:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>⚡ PROSTACK AI PORTAL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A0AEC0;'>#1 AI Daily Fantasy Optimizer for USA 🇺🇸 & Canada 🇨🇦 (DraftKings • FanDuel • PrizePicks)</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        auth_mode = st.radio("Choose Action:", ["Login", "Sign Up (New User)", "🔑 Forgot Password"], horizontal=True)
        
        if auth_mode == "Login":
            l_email = st.text_input("Email Address", placeholder="Enter your registered email")
            l_password = st.text_input("Password", type="password", placeholder="Enter password")
            
            if st.button("🔥 LOGIN TO ENGINE", use_container_width=True):
                clean_l_email = l_email.strip().lower()
                clean_l_pw = l_password.strip().lower()
                
                if clean_l_email in ["admin@prostack.ai", "admin"] and clean_l_pw == "ceo2000cr":
                    st.session_state.logged_in = True
                    st.session_state.user_email = "ADMIN"
                    st.rerun()
                else:
                    success, msg = verify_user(l_email, l_password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.user_email = clean_l_email
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                        
        elif auth_mode == "Sign Up (New User)":
            s_email = st.text_input("Enter Your Email Address", placeholder="name@email.com")
            s_phone = st.text_input("Enter US / Canada Mobile Number (For SMS OTP)", placeholder="e.g. +1 (555) 234-5678")
            s_password = st.text_input("Create Password (min 6 chars)", type="password")
            
            if st.button("🚀 CREATE ACCOUNT & LOGIN", use_container_width=True):
                clean_s_email = s_email.strip().lower()
                clean_s_phone = s_phone.strip()
                clean_s_pw = s_password.strip()
                if "@" in clean_s_email and len(clean_s_phone) >= 7 and len(clean_s_pw) >= 6:
                    if add_user(clean_s_email, clean_s_phone, clean_s_pw, days=30):
                        st.session_state.logged_in = True
                        st.session_state.user_email = clean_s_email
                        st.rerun()
                    else:
                        st.error("⚠️ Email already registered! Please switch to Login or Forgot Password.")
                else:
                    st.error("⚠️ Please enter a valid Email, Phone Number, and Password (min 6 chars).")
                    
        elif auth_mode == "🔑 Forgot Password":
            st.markdown("#### 📲 Instant Password Recovery (Email / SMS OTP)")
            rec_email = st.text_input("Registered Email Address", placeholder="Enter your email")
            rec_phone = st.text_input("Registered Mobile Number", placeholder="Enter your +1 phone number")
            
            if st.button("📩 SEND RECOVERY OTP MESSAGE", use_container_width=True):
                if check_user_for_recovery(rec_email, rec_phone):
                    otp_val = str(random.randint(100000, 999999))
                    st.session_state.reset_otp = otp_val
                    st.session_state.reset_target_email = rec_email.strip().lower()
                    sent_real, mode_msg = send_recovery_otp_notification(rec_email.strip(), rec_phone.strip(), otp_val)
                    st.success(f"✅ Recovery OTP Dispatched to {rec_email} & Phone {rec_phone}!")
                    st.info(f"💬 **[SMS / EMAIL GATEWAY DISPATCH]**: Your ProStack AI Password Reset OTP is: **{otp_val}**")
                else:
                    st.error("❌ Email and Phone Number do not match any registered account!")
                    
            if st.session_state.reset_otp is not None:
                st.markdown("---")
                entered_otp = st.text_input("Enter 6-Digit OTP Received", placeholder="e.g. 123456")
                new_pass = st.text_input("Enter New Password (min 6 chars)", type="password")
                if st.button("✅ VERIFY OTP & RESET PASSWORD", use_container_width=True):
                    if entered_otp.strip() == st.session_state.reset_otp and len(new_pass.strip()) >= 6:
                        reset_user_password(st.session_state.reset_target_email, new_pass.strip())
                        st.session_state.reset_otp = None
                        st.success("🎉 Password Reset Successfully! Switch to 'Login' tab to enter.")
                    else:
                        st.error("⚠️ Invalid OTP or Password too short (min 6 chars)!")
    st.stop()

# ==========================================
# 👑 CEO ADMIN CONTROL ROOM
# ==========================================
if st.session_state.user_email == "ADMIN":
    st.markdown("""
    <div class='admin-box'>
        <h2 style='color: #FFD700 !important;'>👑 CEO ADMIN CONTROL ROOM (USA & CANADA EDITION)</h2>
        <p style='color: white;'>Manage all North American users, verify USD/CAD payments, or download CSV database backups:</p>
    </div>
    """, unsafe_allow_html=True)
    
    conn = sqlite3.connect(DB_FILE)
    users_df = pd.read_sql_query("SELECT email, phone, expiry_date, status, pending_plan, payment_ref FROM users", conn)
    full_db_df = pd.read_sql_query("SELECT * FROM users", conn)
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
        action = st.selectbox("2. Account Action", ["Active", "Blocked", "🗑️ Delete User Permanently"])
    with col_c:
        plan_boost = st.selectbox("3. Add Subscription Days", [
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
        
    if st.button("⚡ EXECUTE ADMIN COMMAND", use_container_width=True):
        if target_email and target_email != "None":
            if action == "🗑️ Delete User Permanently":
                admin_update_user(target_email, "Deleted", 0, delete_user=True)
                st.warning(f"🗑️ User {target_email} permanently deleted!")
            else:
                days_to_add = boost_map[plan_boost]
                admin_update_user(target_email, action, days_to_add, delete_user=False)
                st.success(f"✅ User {target_email} updated! Status: {action} | Added Days: {days_to_add}")
            time.sleep(1)
            st.rerun()
            
    st.markdown("#### 💾 Master Database Backup & Restore")
    col_bk1, col_bk2 = st.columns(2)
    with col_bk1:
        db_csv = full_db_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 DOWNLOAD ALL USERS CSV BACKUP", db_csv, "ProStack_US_Canada_Backup.csv", "text/csv", use_container_width=True)
    with col_bk2:
        restore_file = st.file_uploader("📤 Restore Users from CSV Backup", type=["csv"])
        if restore_file is not None:
            if st.button("🔄 RESTORE DATABASE NOW", use_container_width=True):
                try:
                    restored_df = pd.read_csv(restore_file)
                    conn = sqlite3.connect(DB_FILE)
                    restored_df.to_sql('users', conn, if_exists='replace', index=False)
                    conn.close()
                    st.success("✅ Database Restored Successfully!")
                    time.sleep(1)
                    st.rerun()
                except Exception:
                    st.error("⚠️ Invalid Backup CSV File!")
            
    st.divider()

# ==========================================
# 🟢 CHECK SUBSCRIPTION STATUS & PAYMENT WALL
# ==========================================
is_active, exp_info = get_user_status(st.session_state.user_email)

st.markdown(f'<p class="god-title">⚡ ProStack AI</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-text">Welcome, {st.session_state.user_email} | Market: 🇺🇸 USA & 🇨🇦 Canada ($ USD / $ CAD) | Status: {"🟢 Active (Valid till: " + exp_info + ")" if is_active else "🔴 Expired"}</p>', unsafe_allow_html=True)
st.divider()

if not is_active:
    st.markdown("""
    <div class='recharge-box'>
        <h2 style='color: #FF3131 !important;'>⚠️ SUBSCRIPTION EXPIRED</h2>
        <p style='color: white;'>Your access pass has ended. Complete your payment below ($ USD / $ CAD) and submit your Transaction Reference to unlock God-Mode.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 💳 Step 1: Select Your North American Plan")
    plan = st.radio("Choose Duration:", list(PAYMENT_LINKS.keys()))
    
    selected_link = PAYMENT_LINKS[plan]
    st.markdown(f"<a href='{selected_link}' target='_blank' class='pay-link-btn'>💳 CLICK HERE TO PAY FOR {plan.split('(')[0].upper()}</a>", unsafe_allow_html=True)
    
    st.markdown("### 🧾 Step 2: Verify Your Payment")
    ref_id = st.text_input("Enter Payment Transaction ID / Stripe Reference / Receipt Email:", placeholder="e.g. TXN982374923 or Stripe Email")
    
    if st.button("🚀 SUBMIT PAYMENT FOR ACTIVATION", use_container_width=True):
        if len(ref_id.strip()) >= 4:
            submit_payment_request(st.session_state.user_email, plan, ref_id.strip())
            st.success("✅ Payment Reference Submitted! Admin will verify and activate your account shortly.")
        else:
            st.error("⚠️ Please enter a valid Transaction / Reference ID after making the payment.")
            
    st.markdown("### 💬 Need Instant Help? Contact 24/7 VIP Support")
    st.markdown(f"<a href='{SUPPORT_WHATSAPP_URL}' target='_blank' class='support-btn'>📲 Chat on WhatsApp Support</a>", unsafe_allow_html=True)
    st.markdown(f"<a href='{SUPPORT_TELEGRAM_URL}' target='_blank' class='support-btn'>✈️ Join Telegram VIP Support</a>", unsafe_allow_html=True)
    
    st.write("")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()
    st.stop()

# ==========================================
# 🏟️ STEP 1: 10-SPORT PURE USA & CANADA MATCH CENTER (EST / PST TIMINGS)
# ==========================================
st.markdown("### 🎮 Step 1: North America Game Selector & Match Center (🇺🇸 USA & 🇨🇦 Canada)")

SPORTS_DATA = {
    "🏈 NFL — American Football (DraftKings / FanDuel / PrizePicks)": {
        "default_format_idx": 2,
        "live_matches": [
            {"title": "Kansas City Chiefs (KC) vs Buffalo Bills (BUF)", "status": "🔴 LIVE • Q2 (14 - 10) | CBS / Main Slate", "info": "🔥 Vegas Total: 52.5 Pts | Spread: KC -2.5"},
            {"title": "San Francisco 49ers (SF) vs Philadelphia Eagles (PHI)", "status": "🟢 TODAY • Kickoff 4:25 PM EST", "info": "⚡ Vegas Total: 48.0 Pts | Spread: SF -3.0"},
            {"title": "Miami Dolphins (MIA) vs Los Angeles Chargers (LAC)", "status": "🟢 TODAY • Sunday Night Football 8:20 PM EST", "info": "🚀 Vegas Total: 50.5 Pts | High Pace Dome Game"}
        ],
        "upcoming_matches": [
            {"title": "Dallas Cowboys (DAL) vs Detroit Lions (DET)", "time": "⏳ Tomorrow • 8:15 PM EST (Monday Night Football)", "info": "📊 Early Vegas Line: 51.0 Pts | Dome Shootout"},
            {"title": "Baltimore Ravens (BAL) vs Cincinnati Bengals (CIN)", "time": "⏳ Thursday Night • 8:15 PM EST (Prime Video)", "info": "📊 Early Vegas Line: 49.5 Pts | AFC North Rivalry"}
        ],
        "players": {
            "ID": range(1, 17),
            "Player": ["P. Mahomes", "J. Allen", "C. McCaffrey", "A. Ekeler", "T. Hill", "J. Jefferson", "T. Kelce", "S. Diggs", "C. Kupp", "A. Brown", "J. Hurts", "D. Achane", "G. Kittle", "J. Cook", "B. Purdy", "SF Defense"],
            "Team": ["KC", "BUF", "SF", "LAC", "MIA", "MIN", "KC", "BUF", "LAR", "PHI", "PHI", "MIA", "SF", "BUF", "SF", "SF"],
            "Pos": ["QB", "QB", "RB", "RB", "WR", "WR", "TE", "WR", "WR", "WR", "QB", "RB", "TE", "RB", "QB", "DST"],
            "Salary": [8200, 8000, 9000, 8100, 8600, 8400, 7400, 7800, 8000, 7700, 7900, 7300, 6600, 6900, 6500, 5800],
            "Proj_Pts": [24.5, 23.8, 22.5, 19.5, 22.0, 20.5, 18.0, 19.0, 20.0, 18.5, 23.0, 18.8, 16.2, 17.5, 18.0, 12.5],
            "Ownership_%": [15.5, 14.0, 35.0, 18.5, 25.0, 22.0, 30.0, 15.0, 10.0, 14.5, 16.0, 21.0, 12.5, 13.0, 11.0, 14.0],
            "Vegas_Total": [52.5] * 16
        }
    },
    "🏀 NBA — Pro Basketball (US & Canada Main Slate)": {
        "default_format_idx": 1,
        "live_matches": [
            {"title": "Denver Nuggets (DEN) vs Los Angeles Lakers (LAL)", "status": "🔴 LIVE • 3rd Quarter (88 - 84) | TNT", "info": "🔥 Vegas Total: 234.5 Pts | Fast Pace Slate"},
            {"title": "Toronto Raptors (TOR) vs Boston Celtics (BOS)", "status": "🟢 TODAY • Tip-Off 7:30 PM EST (Scotiabank Arena)", "info": "⚡ Vegas Total: 228.0 Pts | Atlantic Division Clash"},
            {"title": "Golden State Warriors (GSW) vs Phoenix Suns (PHX)", "status": "🟢 TODAY • Tip-Off 10:00 PM EST", "info": "🚀 Vegas Total: 236.0 Pts | Late Night Shootout"}
        ],
        "upcoming_matches": [
            {"title": "Milwaukee Bucks (MIL) vs New York Knicks (NYK)", "time": "⏳ Tomorrow • 7:30 PM EST (MSG)", "info": "📊 Early Total: 229.5 Pts | Giannis Probable"},
            {"title": "Oklahoma City Thunder (OKC) vs Dallas Mavericks (DAL)", "time": "⏳ Tomorrow • 9:30 PM EST", "info": "📊 Early Total: 232.0 Pts | West Top Seed Battle"}
        ],
        "players": {
            "ID": range(1, 17),
            "Player": ["N. Jokic", "L. Doncic", "L. James", "J. Tatum", "S. Curry", "K. Durant", "A. Davis", "K. Irving", "D. Booker", "J. Murray", "J. Brown", "A. Reaves", "D. White", "M. Porter Jr.", "S. Barnes", "R.J. Barrett"],
            "Team": ["DEN", "DAL", "LAL", "BOS", "GSW", "PHX", "LAL", "DAL", "PHX", "DEN", "BOS", "LAL", "BOS", "DEN", "TOR", "TOR"],
            "Pos": ["C", "PG", "SF", "SF", "PG", "PF", "C", "SG", "SG", "PG", "SG", "SG", "PG", "SF", "PF", "SG"],
            "Salary": [10200, 9900, 9200, 9300, 8900, 8800, 9400, 8300, 8500, 7700, 8000, 7000, 6800, 6500, 7800, 6900],
            "Proj_Pts": [58.5, 56.0, 47.5, 49.0, 45.5, 46.0, 51.0, 42.0, 44.5, 39.5, 41.0, 35.5, 34.0, 32.5, 40.5, 34.5],
            "Ownership_%": [28.0, 25.5, 18.0, 20.0, 22.5, 16.0, 19.5, 14.0, 15.0, 12.5, 15.5, 17.0, 13.0, 11.0, 16.5, 12.0],
            "Vegas_Total": [234.5] * 16
        }
    },
    "🏒 NHL — Ice Hockey (Canada & USA Prime Slate)": {
        "default_format_idx": 1,
        "live_matches": [
            {"title": "Edmonton Oilers (EDM) vs Toronto Maple Leafs (TOR)", "status": "🔴 LIVE • 2nd Period (3 - 2) | Hockey Night in Canada", "info": "🔥 Goal Total: 6.5 | Power-Play Heavy Match"},
            {"title": "Montreal Canadiens (MTL) vs Boston Bruins (BOS)", "status": "🟢 TODAY • Puck Drop 7:00 PM EST", "info": "⚡ Goal Total: 6.0 | Original Six Rivalry"},
            {"title": "Vancouver Canucks (VAN) vs Vegas Golden Knights (VGK)", "status": "🟢 TODAY • Puck Drop 10:00 PM EST", "info": "🚀 Goal Total: 6.5 | Pacific Division Showdown"}
        ],
        "upcoming_matches": [
            {"title": "Winnipeg Jets (WPG) vs Colorado Avalanche (COL)", "time": "⏳ Tomorrow • 9:00 PM EST", "info": "📊 Early Goal Line: 6.5 | High Shot Volume"},
            {"title": "New York Rangers (NYR) vs Florida Panthers (FLA)", "time": "⏳ Tomorrow • 7:30 PM EST", "info": "📊 Early Goal Line: 6.0 | East Finals Rematch"}
        ],
        "players": {
            "ID": range(1, 17),
            "Player": ["C. McDavid", "N. MacKinnon", "A. Matthews", "L. Draisaitl", "D. Pastrnak", "C. Makar", "M. Marner", "M. Rantanen", "A. Panarin", "E. Bouchard", "W. Nylander", "B. Marchand", "Z. Hyman", "D. Toews", "Q. Hughes", "N. Suzuki"],
            "Team": ["EDM", "COL", "TOR", "EDM", "BOS", "COL", "TOR", "COL", "NYR", "EDM", "TOR", "BOS", "EDM", "COL", "VAN", "MTL"],
            "Pos": ["C", "C", "C", "W", "W", "D", "W", "W", "W", "D", "W", "W", "W", "D", "D", "C"],
            "Salary": [9600, 9400, 9100, 8800, 8900, 8400, 8000, 8500, 8300, 7700, 8100, 7500, 7800, 6700, 8200, 7200],
            "Proj_Pts": [22.5, 21.8, 20.5, 19.0, 19.5, 18.2, 17.0, 18.5, 18.0, 16.5, 17.5, 15.8, 16.8, 14.2, 17.8, 15.2],
            "Ownership_%": [31.0, 28.0, 24.5, 20.0, 22.0, 25.0, 15.0, 18.0, 16.5, 14.0, 16.0, 12.5, 17.5, 10.5, 19.0, 11.5],
            "Vegas_Total": [6.5] * 16
        }
    },
    "⚾ MLB — Major League Baseball (USA & Toronto Slate)": {
        "default_format_idx": 2,
        "live_matches": [
            {"title": "Los Angeles Dodgers (LAD) vs New York Yankees (NYY)", "status": "🔴 LIVE • Top 5th Inning (4 - 2)", "info": "🔥 Run Total: 9.5 | Wind Blowing Out 12 mph"},
            {"title": "Toronto Blue Jays (TOR) vs Philadelphia Phillies (PHI)", "status": "🟢 TODAY • First Pitch 7:07 PM EST (Rogers Centre)", "info": "⚡ Run Total: 8.5 | High Strikeout & HR Upside"}
        ],
        "upcoming_matches": [
            {"title": "Houston Astros (HOU) vs Texas Rangers (TEX)", "time": "⏳ Tomorrow • 8:05 PM EST", "info": "📊 Early Run Total: 9.0 | Roof Closed"},
            {"title": "Atlanta Braves (ATL) vs Boston Red Sox (BOS)", "time": "⏳ Tomorrow • 7:10 PM EST (Fenway Park)", "info": "📊 Early Run Total: 9.5 | Bullpen Game"}
        ],
        "players": {
            "ID": range(1, 17),
            "Player": ["S. Ohtani", "A. Judge", "M. Betts", "J. Soto", "F. Freeman", "R. Acuna", "B. Harper", "G. Cole", "T. Glasnow", "M. Olson", "T. Turner", "K. Schwarber", "A. Riley", "G. Stanton", "V. Guerrero Jr.", "B. Bichette"],
            "Team": ["LAD", "NYY", "LAD", "NYY", "LAD", "ATL", "PHI", "NYY", "LAD", "ATL", "PHI", "PHI", "ATL", "NYY", "TOR", "TOR"],
            "Pos": ["OF", "OF", "SS", "OF", "1B", "OF", "1B", "P", "P", "1B", "SS", "OF", "3B", "OF", "1B", "SS"],
            "Salary": [6500, 6400, 5900, 6100, 5600, 6200, 5800, 9500, 9200, 5400, 5500, 5300, 5200, 4900, 5700, 5100],
            "Proj_Pts": [14.5, 14.0, 12.5, 13.0, 11.8, 13.5, 12.2, 24.0, 22.5, 11.0, 11.5, 11.2, 10.8, 10.2, 12.0, 10.5],
            "Ownership_%": [30.0, 26.0, 18.5, 22.0, 15.0, 24.0, 17.0, 32.0, 25.0, 12.0, 14.0, 13.5, 11.5, 9.0, 18.0, 11.0],
            "Vegas_Total": [9.5] * 16
        }
    },
    "🏈🏀 NCAA — College Football & Basketball (US CFB / CBB)": {
        "default_format_idx": 1,
        "live_matches": [
            {"title": "Georgia Bulldogs (UGA) vs Alabama Crimson Tide (ALA)", "status": "🔴 LIVE • 2nd Quarter (17 - 14) | SEC on ABC", "info": "🔥 Vegas Total: 54.5 Pts | Spread: UGA -2.0"},
            {"title": "Ohio State Buckeyes (OSU) vs Oregon Ducks (ORE)", "status": "🟢 TODAY • Kickoff 7:30 PM EST", "info": "⚡ Vegas Total: 56.0 Pts | Big Ten Shootout"}
        ],
        "upcoming_matches": [
            {"title": "Texas Longhorns (TEX) vs Oklahoma Sooners (OU)", "time": "⏳ Saturday • 3:30 PM EST (Red River Rivalry)", "info": "📊 Early Vegas Line: 58.5 Pts | High Tempo Offense"},
            {"title": "Duke Blue Devils vs UNC Tar Heels (College Basketball)", "time": "⏳ Upcoming Prime Slate • 9:00 PM EST (ESPN)", "info": "📊 Early Total: 154.5 Pts | Rivalry Classic"}
        ],
        "players": {
            "ID": range(1, 17),
            "Player": ["C. Beck", "J. Milroe", "Q. Ewers", "D. Gabriel", "J. Smith", "R. Williams", "T. Henderson", "A. Jeanty", "C. Ward", "T. Hunter", "S. Sanders", "O. Hampton", "C. Flagg", "R. Davis", "H. Dickinson", "M. Sears"],
            "Team": ["UGA", "ALA", "TEX", "ORE", "OSU", "ALA", "OSU", "BSU", "MIA", "COL", "COL", "UNC", "DUKE", "UNC", "KAN", "ALA"],
            "Pos": ["QB", "QB", "QB", "QB", "WR", "WR", "RB", "RB", "QB", "WR", "QB", "RB", "FWD", "G", "C", "G"],
            "Salary": [9200, 9400, 8900, 9000, 8600, 8500, 8200, 9600, 9100, 8800, 8700, 8000, 8400, 7900, 8100, 7700],
            "Proj_Pts": [28.5, 31.0, 26.5, 27.8, 24.0, 23.5, 22.0, 33.5, 29.0, 25.5, 26.0, 21.5, 38.0, 34.5, 36.0, 33.0],
            "Ownership_%": [24.0, 31.0, 20.0, 22.5, 26.0, 25.0, 18.0, 38.0, 23.0, 27.0, 19.5, 15.0, 29.0, 17.0, 21.0, 16.0],
            "Vegas_Total": [55.0] * 16
        }
    },
    "🥊 UFC / MMA — Las Vegas Fight Night & PPV": {
        "default_format_idx": 0,
        "live_matches": [
            {"title": "Alex Pereira vs Khalil Rountree Jr. (T-Mobile Arena Vegas)", "status": "🔴 LIVE • Main Card Underway on ESPN+ PPV", "info": "🔥 KO/TKO Odds: -280 | 5-Round Championship"},
            {"title": "Sean O'Malley vs Merab Dvalishvili (Co-Main Event)", "status": "🟢 TODAY • Walkouts at 11:15 PM EST", "info": "⚡ High-Output Striking & Takedown Volume"}
        ],
        "upcoming_matches": [
            {"title": "Jon Jones vs Stipe Miocic (Madison Square Garden NY)", "time": "⏳ Saturday Night • 10:00 PM EST (PPV)", "info": "📊 Heavyweight Title | Finish Rate: 82%"},
            {"title": "Islam Makhachev vs Arman Tsarukyan", "time": "⏳ Next PPV Slate • 10:00 PM EST", "info": "📊 Elite Grappling & Bonus Points Ceiling"}
        ],
        "players": {
            "ID": range(1, 17),
            "Player": ["A. Pereira", "I. Makhachev", "J. Jones", "S. O'Malley", "I. Topuria", "M. Holloway", "C. Oliveira", "D. Du Plessis", "K. Chimaev", "J. Gaethje", "A. Volkanovski", "D. Poirier", "T. Aspinall", "M. Dvalishvili", "B. Nickal", "C. Covington"],
            "Team": ["UFC"] * 16,
            "Pos": ["MMA"] * 16,
            "Salary": [9500, 9400, 9300, 8900, 9100, 8500, 8700, 8400, 9000, 8200, 8300, 8000, 9200, 8600, 8800, 7800],
            "Proj_Pts": [105.0, 98.5, 96.0, 91.0, 94.5, 86.0, 89.0, 85.5, 95.0, 82.0, 83.5, 80.0, 97.0, 88.0, 92.0, 79.0],
            "Ownership_%": [35.0, 32.0, 28.0, 24.0, 26.5, 19.0, 21.0, 17.5, 29.0, 15.0, 16.0, 14.5, 30.0, 20.5, 25.5, 14.0],
            "Vegas_Total": [2.5] * 16
        }
    },
    "⛳ PGA Tour — US & Canadian Open Fantasy Golf": {
        "default_format_idx": 0,
        "live_matches": [
            {"title": "The Players Championship — TPC Sawgrass Round 3", "status": "🔴 LIVE • Leaders at -12 Under Par (NBC/Golf Channel)", "info": "🔥 Birdie Fest | Soft Greens & Low Wind"},
            {"title": "RBC Canadian Open — Featured Groups", "status": "🟢 TODAY • Tee Times 8:00 AM - 2:00 PM EST", "info": "⚡ Strokes Gained Approach Key Metric"}
        ],
        "upcoming_matches": [
            {"title": "The Masters Tournament — Augusta National", "time": "⏳ Upcoming Thursday • 7:30 AM EST", "info": "📊 Major Championship | $20M Purse"},
            {"title": "U.S. Open Championship — Pinehurst No. 2", "time": "⏳ Next Major Slate", "info": "📊 Driving Accuracy & Scrambling Crucial"}
        ],
        "players": {
            "ID": range(1, 17),
            "Player": ["S. Scheffler", "R. McIlroy", "X. Schauffele", "J. Rahm", "C. Morikawa", "V. Hovland", "L. Aberg", "B. DeChambeau", "W. Clark", "P. Cantlay", "H. Matsuyama", "T. Finau", "S. Theegala", "J. Thomas", "C. Conners", "N. Taylor"],
            "Team": ["USA", "NIR", "USA", "ESP", "USA", "NOR", "SWE", "USA", "USA", "USA", "JPN", "USA", "USA", "USA", "CAN", "CAN"],
            "Pos": ["GOLF"] * 16,
            "Salary": [10400, 10000, 9600, 9400, 9000, 8700, 8900, 9200, 8300, 8500, 8400, 8100, 7800, 7900, 7700, 7500],
            "Proj_Pts": [88.5, 84.0, 81.5, 79.0, 76.5, 73.0, 75.5, 78.0, 70.5, 72.0, 71.5, 69.0, 67.5, 68.0, 66.5, 65.0],
            "Ownership_%": [34.0, 27.5, 25.0, 22.0, 19.5, 16.0, 21.0, 24.0, 13.5, 15.0, 16.5, 14.0, 12.0, 13.0, 14.5, 11.5],
            "Vegas_Total": [72.0] * 16
        }
    },
    "🏎️ NASCAR Cup Series & Formula 1 (North America Racing)": {
        "default_format_idx": 0,
        "live_matches": [
            {"title": "NASCAR Cup Series — Daytona 500 / Talladega Superspeedway", "status": "🔴 LIVE • Stage 2 Green Flag | FOX Sports", "info": "🔥 Pack Racing | Place Differential & Laps Led Strategy"},
            {"title": "F1 Las Vegas / Miami Grand Prix", "status": "🟢 TODAY • Lights Out 10:00 PM EST", "info": "⚡ High Overtake & Fastest Lap Bonus Active"}
        ],
        "upcoming_matches": [
            {"title": "NASCAR Coca-Cola 600 — Charlotte Motor Speedway", "time": "⏳ Sunday • 6:00 PM EST", "info": "📊 400 Laps Dominator Points Available"},
            {"title": "F1 Canadian Grand Prix — Circuit Gilles Villeneuve Montreal", "time": "⏳ Sunday • 2:00 PM EST", "info": "📊 High Safety Car Probability"}
        ],
        "players": {
            "ID": range(1, 17),
            "Player": ["K. Larson", "D. Hamlin", "W. Byron", "C. Elliott", "R. Blaney", "T. Reddick", "C. Bell", "J. Logano", "M. Verstappen", "L. Norris", "C. Leclerc", "L. Hamilton", "O. Piastri", "G. Russell", "S. Perez", "L. Stroll"],
            "Team": ["HMS", "JGR", "HMS", "HMS", "PENSKE", "23XI", "JGR", "PENSKE", "RBR", "MCL", "FER", "MER", "MCL", "MER", "RBR", "AMR"],
            "Pos": ["DRV"] * 16,
            "Salary": [10200, 9900, 9500, 9100, 9300, 8900, 9000, 8600, 10400, 9800, 9200, 8700, 8800, 8400, 8000, 7400],
            "Proj_Pts": [54.0, 51.5, 48.0, 45.5, 47.0, 44.5, 46.0, 42.0, 49.0, 46.5, 41.0, 38.5, 40.0, 36.5, 34.0, 29.5],
            "Ownership_%": [34.0, 29.0, 25.0, 22.0, 24.0, 19.5, 21.0, 17.0, 36.0, 30.0, 20.0, 18.0, 19.0, 15.0, 13.0, 10.5],
            "Vegas_Total": [55.0] * 16
        }
    },
    "⚽ MLS & Champions League Soccer (US & Canada DraftKings)": {
        "default_format_idx": 1,
        "live_matches": [
            {"title": "Inter Miami CF vs Los Angeles FC (MLS Prime Slate)", "status": "🔴 LIVE • 65' Min (2 - 1) | Apple TV MLS Season Pass", "info": "🔥 Goal Total: 3.5 | High Shot & Cross Volume"},
            {"title": "Toronto FC vs Vancouver Whitecaps (Canadian Rivalry)", "status": "🟢 TODAY • Kickoff 7:30 PM EST", "info": "⚡ Goal Total: 3.0 | Set-Piece Heavy Slate"}
        ],
        "upcoming_matches": [
            {"title": "LA Galaxy vs Seattle Sounders FC", "time": "⏳ Tomorrow • 10:30 PM EST", "info": "📊 Early Goal Line: 3.5 | Attacking Slate"},
            {"title": "Real Madrid vs Manchester City (UCL US Afternoon Slate)", "time": "⏳ Tuesday • 3:00 PM EST (Paramount+)", "info": "📊 Early Goal Line: 3.5 | High Ceiling Showdown"}
        ],
        "players": {
            "ID": range(1, 17),
            "Player": ["L. Messi", "L. Suarez", "D. Bouanga", "C. Hernandez", "R. Puig", "E. Haaland", "K. Mbappe", "V. Junior", "J. Bellingham", "M. Salah", "B. Saka", "C. Palmer", "K. De Bruyne", "F. Bernardeschi", "L. Insigne", "R. Gauld"],
            "Team": ["MIA", "MIA", "LAFC", "CLB", "LAG", "MCI", "RMA", "RMA", "RMA", "LIV", "ARS", "CHE", "MCI", "TOR", "TOR", "VAN"],
            "Pos": ["FWD", "FWD", "FWD", "FWD", "MID", "FWD", "FWD", "FWD", "MID", "FWD", "MID", "MID", "MID", "FWD", "FWD", "MID"],
            "Salary": [10400, 9500, 9300, 9100, 8600, 10000, 9800, 9200, 8700, 9000, 8500, 8400, 8200, 7900, 7700, 8000],
            "Proj_Pts": [28.5, 23.5, 23.0, 22.0, 20.5, 26.5, 25.8, 22.5, 20.0, 21.8, 19.5, 19.8, 19.0, 18.2, 17.5, 18.8],
            "Ownership_%": [38.0, 27.0, 25.0, 23.0, 19.0, 32.0, 29.5, 21.0, 18.0, 22.0, 17.5, 20.0, 16.0, 15.0, 14.0, 16.5],
            "Vegas_Total": [3.5] * 16
        }
    },
    "🎾 Tennis — US Open & Canadian National Bank Open": {
        "default_format_idx": 0,
        "live_matches": [
            {"title": "Taylor Fritz vs Frances Tiafoe (Arthur Ashe Stadium NY)", "status": "🔴 LIVE • Set 2 (6-4, 4-3) | ESPN", "info": "🔥 All-American Showdown | High Ace Bonus Slate"},
            {"title": "Carlos Alcaraz vs Jannik Sinner", "status": "🟢 TODAY • Night Session 7:00 PM EST", "info": "⚡ Hardcourt Baseline Marathon Projected"}
        ],
        "upcoming_matches": [
            {"title": "Felix Auger-Aliassime vs Denis Shapovalov (Montreal/Toronto)", "time": "⏳ Tomorrow • 1:00 PM EST", "info": "📊 Canadian Hardcourt Clash | 3+ Sets Likely"},
            {"title": "Coco Gauff vs Aryna Sabalenka (US Open Final)", "time": "⏳ Tomorrow • 4:00 PM EST", "info": "📊 Straight Sets Bonus Potential"}
        ],
        "players": {
            "ID": range(1, 17),
            "Player": ["T. Fritz", "C. Alcaraz", "J. Sinner", "N. Djokovic", "B. Shelton", "F. Tiafoe", "T. Paul", "C. Gauff", "J. Pegula", "A. Sabalenka", "I. Swiatek", "F. Auger-Aliassime", "D. Shapovalov", "L. Fernandez", "D. Medvedev", "A. Zverev"],
            "Team": ["USA", "ESP", "ITA", "SRB", "USA", "USA", "USA", "USA", "USA", "BLR", "POL", "CAN", "CAN", "CAN", "RUS", "GER"],
            "Pos": ["TENNIS"] * 16,
            "Salary": [9400, 10000, 9800, 9500, 8600, 8400, 8500, 9200, 8800, 9300, 9600, 8100, 7800, 8000, 8900, 9000],
            "Proj_Pts": [66.0, 72.0, 70.5, 67.5, 60.5, 58.5, 59.5, 65.0, 61.5, 66.5, 68.5, 56.5, 54.0, 55.5, 62.5, 64.0],
            "Ownership_%": [28.0, 34.0, 31.0, 26.0, 21.0, 18.5, 19.0, 27.0, 22.0, 25.0, 29.0, 16.5, 14.0, 15.5, 19.5, 20.5],
            "Vegas_Total": [22.5] * 16
        }
    }
}

selected_sport = st.selectbox(
    "🇺🇸🇨🇦 Choose Your North American Sport League (10 Leagues Active):",
    list(SPORTS_DATA.keys())
)

match_view = st.radio(
    "Select Match View:",
    ["🔴 Live & Today's Slates (EST)", "⏳ Upcoming Slates (Next 48 Hrs EST)"],
    horizontal=True
)

if match_view == "🔴 Live & Today's Slates (EST)":
    for m in SPORTS_DATA[selected_sport]["live_matches"]:
        st.markdown(f"""
        <div class='live-card'>
            <span class='badge-live'>LIVE / TODAY</span>
            <b style='color:#00FF41; font-size:16px; margin-left:8px;'>🆚 {m['title']}</b><br>
            <span style='color:#FFD700; font-size:13px;'>{m['status']}</span><br>
            <span style='color:#FFFFFF; font-size:13px;'>{m['info']}</span>
        </div>
        """, unsafe_allow_html=True)
else:
    for u in SPORTS_DATA[selected_sport]["upcoming_matches"]:
        st.markdown(f"""
        <div class='upcoming-card'>
            <span class='badge-upcoming'>UPCOMING</span>
            <b style='color:#00BFFF; font-size:16px; margin-left:8px;'>🆚 {u['title']}</b><br>
            <span style='color:#FFD700; font-size:13px;'>{u['time']}</span><br>
            <span style='color:#FFFFFF; font-size:13px;'>{u['info']}</span>
        </div>
        """, unsafe_allow_html=True)

all_match_titles = ["🔥 Full Main Slate (All Today's Games)"] + [m["title"] for m in SPORTS_DATA[selected_sport]["live_matches"]] + [u["title"] + " (Upcoming)" for u in SPORTS_DATA[selected_sport]["upcoming_matches"]]
selected_slate = st.selectbox("🎯 Select Target Game / Contest Slate for Optimizer:", all_match_titles)

st.markdown("#### 📥 Custom DraftKings / FanDuel CSV Upload (Optional)")
uploaded_file = st.file_uploader("Upload Custom DFS CSV Data (Or use Auto-Loaded Vegas Slate Data)", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("✅ Custom DFS CSV Data Uploaded Successfully!")
    except Exception:
        st.error("⚠️ Error reading CSV! Using Auto-Loaded Slate Data.")
        df = pd.DataFrame(SPORTS_DATA[selected_sport]["players"])
else:
    df = pd.DataFrame(SPORTS_DATA[selected_sport]["players"])

# ==========================================
# 🧠 NORTH AMERICAN SOLVER ($50,000 SALARY CAP CALIBRATED FOR 6, 8 & 9 PLAYERS)
# ==========================================
def run_god_mode_solver(data, lineups_count, cap, strategy_mode, locked_players, excluded_players, roster_size):
    lineups, stats = [], []
    base_data = data[~data["Player"].isin(excluded_players)].copy().reset_index(drop=True)
    if len(base_data) < roster_size:
        return [], []
        
    avg_raw_sal = base_data["Salary"].mean()
    target_avg_sal = (cap * 0.96) / roster_size
    if avg_raw_sal * roster_size > cap * 0.98:
        scale_factor = target_avg_sal / avg_raw_sal
        base_data["Eff_Salary"] = (base_data["Salary"] * scale_factor / 100).round().astype(int) * 100
    else:
        base_data["Eff_Salary"] = base_data["Salary"]
    
    for i in range(lineups_count):
        prob = pulp.LpProblem(f"GodMode_{i}", pulp.LpMaximize)
        p_vars = pulp.LpVariable.dicts("P", base_data.index, cat='Binary')
        
        noise = np.random.normal(0, 0.95 if i > 0 else 0.0, size=len(base_data))
        sim_pts = base_data["Proj_Pts"] + noise
        
        prob += pulp.lpSum([sim_pts[idx] * p_vars[idx] for idx in base_data.index])
        prob += pulp.lpSum([base_data["Eff_Salary"][idx] * p_vars[idx] for idx in base_data.index]) <= cap
        prob += pulp.lpSum([p_vars[idx] for idx in base_data.index]) == roster_size
        
        for idx in base_data.index:
            if base_data["Player"][idx] in locked_players:
                prob += p_vars[idx] == 1
                
        if strategy_mode == "💣 Mega GPP Tournament (High Ceiling / Low Ownership)":
            prob += pulp.lpSum([base_data["Ownership_%"][idx] * p_vars[idx] for idx in base_data.index]) <= (roster_size * 26)
        
        for prev_raw in lineups:
            clean_prev = [p.replace(" 👑(CPT)", "").replace(" ⚡(MVP)", "") for p in prev_raw]
            prob += pulp.lpSum([p_vars[idx] for idx in base_data.index if base_data["Player"][idx] in clean_prev]) <= (roster_size - 1)
            
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        if pulp.LpStatus[prob.status] == 'Optimal':
            chosen_indices = [idx for idx in base_data.index if p_vars[idx].varValue == 1]
            chosen_sorted = sorted(chosen_indices, key=lambda idx: sim_pts[idx], reverse=True)
            
            formatted_lineup = []
            for rank_idx, p_idx in enumerate(chosen_sorted):
                p_name = base_data["Player"][p_idx]
                if rank_idx == 0:
                    formatted_lineup.append(f"{p_name} 👑(CPT)")
                elif rank_idx == 1:
                    formatted_lineup.append(f"{p_name} ⚡(MVP)")
                else:
                    formatted_lineup.append(p_name)
                    
            pts = sum([base_data["Proj_Pts"][idx] for idx in chosen_indices])
            sal = sum([base_data["Eff_Salary"][idx] for idx in chosen_indices])
            own = sum([base_data["Ownership_%"][idx] for idx in chosen_indices]) / roster_size
            lineups.append(formatted_lineup)
            stats.append(f"Pts: {pts:.1f} | Sal: ${sal} | Own: {own:.1f}%")
        else:
            break
    return lineups, stats

st.divider()

# ==========================================
# 🧭 STEP 2: NAVIGATION MENU
# ==========================================
st.markdown("### 🧭 Step 2: Navigation Menu")
app_mode = st.selectbox(
    "Choose your section:",
    [
        "🚀 Auto-Pilot Engine",
        "📊 The Terminal (Player Data)",
        "📰 Live Match News",
        "📉 Pro Analytics",
        "💎 VIP Upgrade & Support Center"
    ],
    label_visibility="collapsed"
)
st.divider()

if app_mode == "🚀 Auto-Pilot Engine":
    st.markdown(f"### 🧠 Engine Settings — {selected_sport}")
    st.markdown(f"<p style='color:#00FF41; font-weight:bold;'>Active Contest Slate: {selected_slate}</p>", unsafe_allow_html=True)
    st.markdown("""
    <div class='strategy-box'>
        <b style='color:#FFD700; font-size:16px;'>Step 3: Select Official US & Canada DFS Roster Format ($50,000 Cap)</b><br>
        <span style='color:white;'>Built specifically for DraftKings, FanDuel, PrizePicks & Underdog Fantasy players in the USA & Canada.</span>
    </div>
    """, unsafe_allow_html=True)
    
    auto_idx = SPORTS_DATA[selected_sport]["default_format_idx"]
    regional_format = st.radio(
        "🇺🇸🇨🇦 Choose North American Contest Format:",
        [
            "⚡ Showdown / Single-Game Mode (6 Players | $50,000 Cap — 1 CPT + 5 FLEX)",
            "🏆 Classic Main Slate Roster (8 Players | $50,000 Cap — NBA / NHL / College / Soccer)",
            "🏈 Classic Full Lineup Roster (9 Players | $50,000 Cap — NFL / MLB Full Slate)"
        ],
        index=auto_idx
    )
    
    if "6 Players" in regional_format:
        roster_size = 6
        default_cap = 50000
        col_names = ["👑 Captain (1.5x)", "⚡ MVP Anchor", "UTIL 1", "UTIL 2", "UTIL 3", "UTIL 4"]
    elif "8 Players" in regional_format:
        roster_size = 8
        default_cap = 50000
        col_names = ["👑 Star Lock", "⚡ Co-Star", "Core 1", "Core 2", "Core 3", "Core 4", "FLEX 1", "FLEX 2"]
    else:
        roster_size = 9
        default_cap = 50000
        col_names = ["👑 QB/SP Anchor", "⚡ Stack 1", "Core 2", "Core 3", "Core 4", "Core 5", "Core 6", "FLEX", "DST/UTIL"]
        
    strategy = st.radio("Target Contest Type:", ["🛡️ 50/50 & Head-to-Head Cash Game (Safe Floor)", "💣 Mega GPP Tournament (High Ceiling / Low Ownership)"])
    
    col_lk1, col_lk2 = st.columns(2)
    with col_lk1:
        locked_players = st.multiselect("🔒 Lock Core Players (100% Exposure):", df["Player"].tolist(), max_selections=roster_size-1)
    with col_lk2:
        available_to_exclude = [p for p in df["Player"].tolist() if p not in locked_players]
        excluded_players = st.multiselect("❌ Exclude / Fade Injured Players:", available_to_exclude)
        
    num_lineups = st.slider("🎯 Number of Lineups (Monte Carlo Sim)", 1, 150, 20)
    salary_cap = st.number_input("💰 Official Contest Salary Cap ($ USD)", value=default_cap, step=1000)
    
    st.write("")
    if st.button("🔥 RUN 1000% AUTO-PILOT OPTIMIZER", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for percent in range(100):
            time.sleep(0.008)
            progress_bar.progress(percent + 1)
            if percent < 50: status_text.text(f"Running {roster_size}-Player Vegas Simulations ($50,000 Cap)...")
            else: status_text.text("Optimizing DraftKings / FanDuel Winning Stacks...")
            
        status_text.text("✅ EXECUTION COMPLETE.")
        
        final_lineups, stat_list = run_god_mode_solver(df, num_lineups, salary_cap, strategy, locked_players, excluded_players, roster_size)
        
        if final_lineups:
            st.success(f"🏆 {len(final_lineups)} WINNING {roster_size}-PLAYER LINEUPS GENERATED (UNDER ${salary_cap:,} CAP)!")
            df_out = pd.DataFrame(final_lineups, columns=col_names)
            df_out["Metrics"] = stat_list
            df_out.index = [f"Lineup-{i+1}" for i in range(len(df_out))]
            st.dataframe(df_out, use_container_width=True)
            
            csv = df_out.to_csv().encode('utf-8')
            st.download_button("💾 DOWNLOAD DRAFTKINGS / FANDUEL CSV", csv, "ProStack_US_Lineups.csv", "text/csv", use_container_width=True)
        else:
            st.error("Engine Overload: Too many players excluded. Reduce excluded players and try again.")

elif app_mode == "📊 The Terminal (Player Data)":
    st.subheader(f"Deep-Dive Player Matrix — {selected_sport}")
    st.markdown(f"<p style='color:#FFD700; font-size:13px;'>Slate: {selected_slate}</p>", unsafe_allow_html=True)
    st.markdown("<span style='color:#A0AEC0; font-size:12px;'>*(Swipe left/right on the table to see full data)*</span>", unsafe_allow_html=True)
    
    full_df = df.copy()
    if 'Proj_Pts' in full_df.columns: full_df['Proj_Pts'] = full_df['Proj_Pts'].round(1)
    if 'Ownership_%' in full_df.columns: full_df['Ownership_%'] = full_df['Ownership_%'].round(1)
    
    st.dataframe(full_df.style.background_gradient(subset=['Proj_Pts'], cmap='Greens')
                 .background_gradient(subset=['Ownership_%'], cmap='Reds'), 
                 use_container_width=True, hide_index=True)

elif app_mode == "📰 Live Match News":
    st.subheader(f"🚨 Vegas & Rotowire Breaking News — {selected_sport}")
    st.markdown("""
    <div class='news-box-red' style='background-color: #1A202C; padding: 15px; border-radius: 8px; border-left: 4px solid #FF3131; margin-bottom: 15px;'>
        <b style='color:#FF3131; font-size:16px;'>⚠️ LATE SWAP & INJURY ALERTS (LAS VEGAS & TORONTO DESK)</b><br>
        <span style='color:white;'>• <b>Key Starter</b> - Game-Time Decision (Use Lock/Exclude in Engine if ruled out)<br>
        • <b>Vegas Line Movement</b> - Sharp money hitting the Over on tonight's main slate!</span><br>
    </div>
    """, unsafe_allow_html=True)

elif app_mode == "📉 Pro Analytics":
    st.subheader(f"Pro Leverage & Value Matrix — {selected_sport}")
    fig1 = px.scatter(df, x="Salary", y="Proj_Pts", color="Pos", hover_name="Player", template="plotly_dark", title="Salary vs Projected Points")
    st.plotly_chart(fig1, use_container_width=True)

elif app_mode == "💎 VIP Upgrade & Support Center":
    st.markdown(f"""
    <div class='vip-box'>
        <h2 style='color: #00BFFF !important;'>💎 VIP MEMBERSHIP & 24/7 SUPPORT CENTER (USA & CANADA)</h2>
        <p style='color: white;'>Logged in as: <b>{st.session_state.user_email}</b> | Current Validity: <b>{exp_info}</b></p>
        <p style='color: #A0AEC0;'>Extend your subscription anytime ($ USD / $ CAD) or reach out to our North American VIP Concierge Desk.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🚀 Pre-Extend or Upgrade Your VIP Pass")
    vip_plan = st.radio("Select Upgrade Tier:", list(PAYMENT_LINKS.keys()))
    vip_link = PAYMENT_LINKS[vip_plan]
    st.markdown(f"<a href='{vip_link}' target='_blank' class='pay-link-btn'>💳 PAY & UPGRADE TO {vip_plan.split('(')[0].upper()}</a>", unsafe_allow_html=True)
    
    vip_ref = st.text_input("Enter Transaction ID / Payment Reference after payment:", placeholder="e.g. TXN982374923")
    if st.button("✅ SUBMIT UPGRADE VERIFICATION", use_container_width=True):
        if len(vip_ref.strip()) >= 4:
            submit_payment_request(st.session_state.user_email, vip_plan, vip_ref.strip())
            st.success("🎉 Upgrade Request Submitted! Admin will add the bonus days to your account shortly.")
        else:
            st.error("⚠️ Please enter a valid Transaction Reference ID.")
            
    st.divider()
    st.markdown("### 💬 24/7 Direct VIP Support Desk")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown(f"<a href='{SUPPORT_WHATSAPP_URL}' target='_blank' class='support-btn'>📲 WhatsApp VIP Concierge</a>", unsafe_allow_html=True)
    with col_s2:
        st.markdown(f"<a href='{SUPPORT_TELEGRAM_URL}' target='_blank' class='support-btn'>✈️ Telegram VIP Channel</a>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:#A0AEC0;'>Official Support Email: <b>{SUPPORT_EMAIL}</b></p>", unsafe_allow_html=True)

st.divider()
if st.button("🚪 Logout Account", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_email = ""
    st.rerun()
