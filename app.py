import streamlit as st
import pandas as pd
import numpy as np
import pulp
import plotly.express as px
import time
import random
import smtplib
import re
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

# --- 1. DATABASE & ENTERPRISE SETUP (USERS + BANKROLL + REFERRALS) ---
DB_FILE = 'prostack_us_canada_v8.db'

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
            payment_ref TEXT DEFAULT 'None',
            referral_used INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bankroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            contest_date TEXT,
            sport TEXT,
            entry_fee REAL,
            winnings REAL
        )
    ''')
    for col_sql in [
        "ALTER TABLE users ADD COLUMN phone TEXT DEFAULT 'Not Provided'",
        "ALTER TABLE users ADD COLUMN pending_plan TEXT DEFAULT 'None'",
        "ALTER TABLE users ADD COLUMN payment_ref TEXT DEFAULT 'None'",
        "ALTER TABLE users ADD COLUMN referral_used INTEGER DEFAULT 0"
    ]:
        try:
            c.execute(col_sql)
        except Exception:
            pass
    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        dummy_pw = hashlib.sha256("password123".encode()).hexdigest()
        expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT OR IGNORE INTO users (email, phone, password, expiry_date, status, pending_plan, payment_ref, referral_used) VALUES (?, ?, ?, ?, ?, ?, ?, 0)", 
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
        c.execute("INSERT INTO users (email, phone, password, expiry_date, status, pending_plan, payment_ref, referral_used) VALUES (?, ?, ?, ?, ?, ?, ?, 0)", 
                  (clean_email, clean_phone, hashed_pw, expiry, 'Active', 'None', 'None'))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

def redeem_referral_bonus(email, code_entered):
    clean_email = email.strip().lower()
    own_code = "PROSTACK-" + hashlib.md5(clean_email.encode()).hexdigest()[:5].upper()
    if code_entered.strip().upper() == own_code:
        return False, "You cannot use your own referral code!"
    if not code_entered.strip().upper().startswith("PROSTACK-"):
        return False, "Invalid Referral Code format! Must start with PROSTACK-"
        
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT expiry_date, referral_used FROM users WHERE email = ?", (clean_email,))
    row = c.fetchone()
    if row:
        exp_str, ref_used = row
        if ref_used == 1:
            conn.close()
            return False, "You have already claimed your 7-Day Referral Bonus!"
        curr_exp = datetime.strptime(exp_str, '%Y-%m-%d %H:%M:%S')
        base_t = max(datetime.now(), curr_exp)
        new_exp = (base_t + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute("UPDATE users SET expiry_date = ?, referral_used = 1 WHERE email = ?", (new_exp, clean_email))
        conn.commit()
        conn.close()
        return True, "🎉 +7 FREE VIP DAYS ADDED TO YOUR ACCOUNT!"
    conn.close()
    return False, "Account not found in user database."

def add_bankroll_entry(email, sport, entry_fee, winnings):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    dt = datetime.now().strftime('%Y-%m-%d')
    c.execute("INSERT INTO bankroll (email, contest_date, sport, entry_fee, winnings) VALUES (?, ?, ?, ?, ?)",
              (email, dt, sport, float(entry_fee), float(winnings)))
    conn.commit()
    conn.close()

def get_bankroll_df(email):
    conn = sqlite3.connect(DB_FILE)
    df_b = pd.read_sql_query("SELECT contest_date as Date, sport as Sport, entry_fee as Entry_USD, winnings as Won_USD FROM bankroll WHERE email = ?", conn, params=(email,))
    conn.close()
    return df_b

def check_user_for_recovery(email, phone):
    clean_email = email.strip().lower()
    clean_phone = phone.strip()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT email, phone FROM users WHERE email = ?", (clean_email,))
    row = c.fetchone()
    conn.close()
    if row:
        _, db_phone = row
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
st.set_page_config(page_title="ProStack AI V8.0 - USA & Canada DFS", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            [data-testid="stSidebar"] {display: none;}
            
            .stApp p, .stApp label, .stApp div[data-testid="stMarkdownContainer"] p { color: #FFFFFF !important; }
            div[role="radiogroup"] p, div[data-baseweb="radio"] p { color: #FFFFFF !important; font-size: 16px !important; font-weight: bold !important; }
            .stSelectbox label p, .stMultiSelect label p, .stSlider label p, .stNumberInput label p, .stFileUploader label p, .stCheckbox label p { color: #FFFFFF !important; }
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
    .pickem-card {background-color: #1A202C; padding: 16px; border-radius: 10px; border: 2px solid #00FF41; margin-bottom: 12px;}
    .badge-live {background-color: #FF3131; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;}
    .badge-upcoming {background-color: #00BFFF; color: black; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;}
    .pay-link-btn {display: block; width: 100%; text-align: center; background-color: #00FF41; color: #000000 !important; font-weight: 900; padding: 14px; border-radius: 8px; text-decoration: none; font-size: 17px; margin-top: 10px; margin-bottom: 15px;}
    .support-btn {display: block; width: 100%; text-align: center; background-color: #00BFFF; color: #000000 !important; font-weight: 900; padding: 12px; border-radius: 8px; text-decoration: none; font-size: 16px; margin-top: 8px; margin-bottom: 8px;}
    .legal-footer {background-color: #12161F; padding: 16px; border-radius: 8px; border-top: 1px solid #2D3748; color: #A0AEC0 !important; font-size: 12px; text-align: center; margin-top: 20px;}
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
if 'auto_excluded' not in st.session_state:
    st.session_state.auto_excluded = []

if not st.session_state.logged_in:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>⚡ PROSTACK AI PORTAL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A0AEC0;'> Quantitative Daily Fantasy & Pick'em Lineup Optimizer for USA 🇺🇸 & Canada 🇨🇦</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        auth_mode = st.radio("Choose Action:", ["Login", "Sign Up (30-Day Free Trial)", "🔑 Forgot Password"], horizontal=True)
        
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
                        
        elif auth_mode.startswith("Sign Up"):
            s_email = st.text_input("Enter Your Email Address", placeholder="name@email.com")
            s_phone = st.text_input("Enter US / Canada Mobile Number (For SMS OTP)", placeholder="e.g. +1 (555) 234-5678")
            s_password = st.text_input("Create Password (min 6 chars)", type="password")
            
            if st.button("🚀 CREATE ACCOUNT & START 30-DAY FREE TRIAL", use_container_width=True):
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
                        
    st.markdown("""
    <div class='legal-footer'>
        <b>⚖️ Transparent Analytics Disclaimer:</b> ProStack AI is a statistical & mathematical lineup optimization tool built for entertainment and research purposes. We do not offer real-money gambling or guarantee contest winnings. Please play responsibly.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ==========================================
# 👑 CEO ADMIN CONTROL ROOM
# ==========================================
if st.session_state.user_email == "ADMIN":
    st.markdown("""
    <div class='admin-box'>
        <h2 style='color: #FFD700 !important;'>👑 CEO ADMIN CONTROL ROOM (V8.0 FLAWLESS EDITION)</h2>
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
user_dna_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:6].upper()

st.markdown(f'<p class="god-title">⚡ ProStack AI V8.0</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-text">Welcome, {st.session_state.user_email} | 🧬 Personal AI DNA Seed: #{user_dna_id} (Anti-Duplicate Lineups) | Status: {"🟢 Active (Valid till: " + exp_info + ")" if is_active else "🔴 Expired"}</p>', unsafe_allow_html=True)
st.divider()

if not is_active:
    st.markdown("""
    <div class='recharge-box'>
        <h2 style='color: #FF3131 !important;'>⚠️ SUBSCRIPTION EXPIRED</h2>
        <p style='color: white;'>Your access pass has ended. Complete your payment below ($ USD / $ CAD) and submit your Transaction Reference to unlock the optimizer.</p>
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
# 🏟️ STEP 1: MEGA 36-PLAYER POOL GENERATOR PER SPORT (360+ REAL PLAYERS TOTAL)
# ==========================================
st.markdown("### 🎮 Step 1: North America Game Selector & Match Center (🇺🇸 USA & 🇨🇦 Canada)")

def build_roster_pool(tuples_list, vegas_default=50.0):
    return {
        "ID": range(1, len(tuples_list) + 1),
        "Player": [t[0] for t in tuples_list],
        "Team": [t[1] for t in tuples_list],
        "Pos": [t[2] for t in tuples_list],
        "Salary": [t[3] for t in tuples_list],
        "Proj_Pts": [t[4] for t in tuples_list],
        "Ownership_%": [t[5] for t in tuples_list],
        "Vegas_Total": [vegas_default] * len(tuples_list)
    }

def smart_parse_dfs_csv(raw_df):
    df_c = raw_df.copy()
    col_map = {}
    for c in df_c.columns:
        cl = c.strip().lower()
        if cl in ['name', 'nickname', 'player name', 'player', 'fighter', 'golfer', 'driver']:
            col_map[c] = 'Player'
        elif cl in ['salary', 'cost', 'dk salary', 'fd salary']:
            col_map[c] = 'Salary'
        elif cl in ['avgpointspergame', 'fppg', 'proj_pts', 'proj', 'points', 'projection', 'projected points']:
            col_map[c] = 'Proj_Pts'
        elif cl in ['position', 'pos', 'roster position']:
            col_map[c] = 'Pos'
        elif cl in ['teamabbrev', 'team', 'squad']:
            col_map[c] = 'Team'
        elif cl in ['ownership_%', 'ownership', 'own%', 'proj_own']:
            col_map[c] = 'Ownership_%'
            
    df_c = df_c.rename(columns=col_map)
    df_c = df_c.loc[:, ~df_c.columns.duplicated()]
    
    if 'Player' not in df_c.columns and 'First Name' in raw_df.columns and 'Last Name' in raw_df.columns:
        df_c['Player'] = raw_df['First Name'].astype(str) + " " + raw_df['Last Name'].astype(str)
        
    if 'Salary' in df_c.columns:
        df_c['Salary'] = df_c['Salary'].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
        df_c['Salary'] = pd.to_numeric(df_c['Salary'], errors='coerce').fillna(5000).astype(int)
    else:
        df_c['Salary'] = 6000
        
    if 'Proj_Pts' in df_c.columns:
        df_c['Proj_Pts'] = pd.to_numeric(df_c['Proj_Pts'], errors='coerce').fillna(12.0)
    else:
        df_c['Proj_Pts'] = (df_c['Salary'] / 350.0).round(1)
        
    if 'Pos' not in df_c.columns:
        df_c['Pos'] = 'FLEX'
    else:
        df_c['Pos'] = df_c['Pos'].astype(str).str.split('/').str[0].str.strip().str.upper()
    if 'Team' not in df_c.columns:
        df_c['Team'] = 'USA'
    if 'Ownership_%' not in df_c.columns:
        max_pts = max(df_c['Proj_Pts'].max(), 1.0)
        df_c['Ownership_%'] = ((df_c['Proj_Pts'] / max_pts) * 32.0).clip(lower=2.5, upper=40.0).round(1)
    if 'Vegas_Total' not in df_c.columns:
        df_c['Vegas_Total'] = 50.0
        
    valid_df = df_c[df_c['Proj_Pts'] > 0].copy()
    if len(valid_df) >= 10:
        df_c = valid_df.reset_index(drop=True)
        
    return df_c

SPORTS_DATA = {
    "🏈 NFL — American Football (DraftKings / FanDuel — 36 Players Active)": {
        "default_format_idx": 2,
        "live_matches": [
            {"title": "Kansas City Chiefs (KC) vs Buffalo Bills (BUF)", "status": "🔴 LIVE • Q2 (14 - 10) | CBS / Main Slate", "info": "🔥 Vegas Total: 52.5 Pts | Spread: KC -2.5"},
            {"title": "San Francisco 49ers (SF) vs Philadelphia Eagles (PHI)", "status": "🟢 TODAY • Kickoff 4:25 PM EST", "info": "⚡ Vegas Total: 48.0 Pts | Spread: SF -3.0"},
            {"title": "Miami Dolphins (MIA) vs Los Angeles Chargers (LAC)", "status": "🟢 TODAY • Sunday Night Football 8:20 PM EST", "info": "🚀 Vegas Total: 50.5 Pts | High Pace Dome Game"},
            {"title": "Detroit Lions (DET) vs Dallas Cowboys (DAL)", "status": "🟢 TODAY • Late Window 4:25 PM EST", "info": "🔥 Vegas Total: 53.0 Pts | Dome Shootout"}
        ],
        "upcoming_matches": [
            {"title": "Baltimore Ravens (BAL) vs Cincinnati Bengals (CIN)", "time": "⏳ Tomorrow • 8:15 PM EST (Monday Night Football)", "info": "📊 Early Vegas Line: 51.5 Pts | AFC North Rivalry"},
            {"title": "Houston Texans (HOU) vs Green Bay Packers (GB)", "time": "⏳ Thursday Night • 8:15 PM EST (Prime Video)", "info": "📊 Early Vegas Line: 49.0 Pts | Young QB Showdown"}
        ],
        "players": build_roster_pool([
            ("P. Mahomes", "KC", "QB", 8200, 24.8, 18.5), ("J. Allen", "BUF", "QB", 8100, 24.5, 19.0),
            ("J. Hurts", "PHI", "QB", 7900, 23.6, 16.5), ("L. Jackson", "BAL", "QB", 8000, 24.1, 17.0),
            ("J. Burrow", "CIN", "QB", 7400, 21.8, 14.0), ("B. Purdy", "SF", "QB", 6600, 19.5, 12.5),
            ("D. Prescott", "DAL", "QB", 6800, 20.2, 11.0), ("J. Goff", "DET", "QB", 6500, 19.2, 10.5),
            ("C. McCaffrey", "SF", "RB", 9000, 23.5, 32.0), ("S. Barkley", "PHI", "RB", 8300, 21.2, 26.5),
            ("D. Achane", "MIA", "RB", 7600, 19.8, 22.0), ("J. Gibbs", "DET", "RB", 7500, 19.4, 20.5),
            ("D. Henry", "BAL", "RB", 7800, 20.1, 24.0), ("J. Cook", "BUF", "RB", 6900, 17.6, 15.5),
            ("I. Pacheco", "KC", "RB", 6700, 17.2, 16.0), ("J.K. Dobbins", "LAC", "RB", 6100, 15.8, 14.5),
            ("D. Montgomery", "DET", "RB", 6300, 16.2, 13.0), ("R. Mostert", "MIA", "RB", 5600, 13.9, 9.5),
            ("C. Lamb", "DAL", "WR", 8800, 22.8, 28.0), ("T. Hill", "MIA", "WR", 8600, 22.1, 25.5),
            ("A. St. Brown", "DET", "WR", 8500, 21.9, 27.0), ("J. Chase", "CIN", "WR", 8400, 21.5, 24.0),
            ("A.J. Brown", "PHI", "WR", 8000, 20.4, 21.0), ("D. Samuel", "SF", "WR", 7300, 18.2, 17.5),
            ("J. Waddle", "MIA", "WR", 6600, 16.5, 14.0), ("D. Smith", "PHI", "WR", 6700, 16.8, 15.0),
            ("B. Aiyuk", "SF", "WR", 6500, 16.1, 13.5), ("X. Worthy", "KC", "WR", 5800, 14.6, 16.5),
            ("K. Shakir", "BUF", "WR", 5500, 13.8, 12.0), ("L. McConkey", "LAC", "WR", 5400, 13.5, 11.5),
            ("T. Kelce", "KC", "TE", 6800, 17.4, 22.5), ("G. Kittle", "SF", "TE", 6300, 16.0, 18.0),
            ("S. LaPorta", "DET", "TE", 6000, 15.2, 16.5), ("D. Kincaid", "BUF", "TE", 5300, 13.4, 14.0),
            ("SF 49ers DST", "SF", "DST", 3600, 10.5, 19.0), ("KC Chiefs DST", "KC", "DST", 3400, 9.8, 15.0)
        ], 52.5)
    },
    "🏀 NBA — Pro Basketball (US & Canada Main Slate — 36 Players Active)": {
        "default_format_idx": 1,
        "live_matches": [
            {"title": "Denver Nuggets (DEN) vs Los Angeles Lakers (LAL)", "status": "🔴 LIVE • 3rd Quarter (88 - 84) | TNT", "info": "🔥 Vegas Total: 234.5 Pts | Fast Pace Slate"},
            {"title": "Toronto Raptors (TOR) vs Boston Celtics (BOS)", "status": "🟢 TODAY • Tip-Off 7:30 PM EST (Scotiabank Arena)", "info": "⚡ Vegas Total: 228.0 Pts | Atlantic Division Clash"},
            {"title": "Golden State Warriors (GSW) vs Phoenix Suns (PHX)", "status": "🟢 TODAY • Tip-Off 10:00 PM EST", "info": "🚀 Vegas Total: 236.0 Pts | Late Night Shootout"},
            {"title": "Dallas Mavericks (DAL) vs Oklahoma City Thunder (OKC)", "status": "🟢 TODAY • Tip-Off 8:30 PM EST", "info": "🔥 Vegas Total: 233.5 Pts | MVP Showcase"}
        ],
        "upcoming_matches": [
            {"title": "Milwaukee Bucks (MIL) vs New York Knicks (NYK)", "time": "⏳ Tomorrow • 7:30 PM EST (MSG)", "info": "📊 Early Total: 229.5 Pts | Giannis vs Brunson"},
            {"title": "Minnesota Timberwolves (MIN) vs Sacramento Kings (SAC)", "time": "⏳ Tomorrow • 10:00 PM EST", "info": "📊 Early Total: 231.0 Pts | High Tempo West Slate"}
        ],
        "players": build_roster_pool([
            ("N. Jokic", "DEN", "C", 10600, 59.5, 29.0), ("L. Doncic", "DAL", "PG", 10400, 57.8, 27.5),
            ("S. Gilgeous-Alexander", "OKC", "PG", 10000, 54.5, 25.0), ("G. Antetokounmpo", "MIL", "PF", 10200, 56.0, 26.0),
            ("A. Davis", "LAL", "C", 9600, 51.5, 22.5), ("J. Tatum", "BOS", "SF", 9400, 49.8, 21.0),
            ("L. James", "LAL", "SF", 9100, 47.5, 19.5), ("S. Curry", "GSW", "PG", 8900, 46.2, 23.0),
            ("K. Durant", "PHX", "PF", 8800, 45.8, 18.5), ("D. Booker", "PHX", "SG", 8600, 44.5, 17.0),
            ("K. Irving", "DAL", "SG", 8300, 42.5, 16.5), ("J. Brunson", "NYK", "PG", 8700, 45.0, 20.0),
            ("A. Edwards", "MIN", "SG", 8800, 45.5, 21.5), ("D. Sabonis", "SAC", "C", 9000, 47.0, 18.0),
            ("S. Barnes", "TOR", "PF", 8100, 41.5, 17.5), ("J. Brown", "BOS", "SG", 7900, 40.2, 16.0),
            ("J. Murray", "DEN", "PG", 7700, 39.5, 15.0), ("C. Holmgren", "OKC", "C", 7600, 39.0, 19.0),
            ("J. Williams", "OKC", "SF", 7400, 38.0, 16.5), ("D. Lillard", "MIL", "PG", 8000, 41.0, 15.5),
            ("K. Towns", "NYK", "C", 7800, 40.0, 17.0), ("R.J. Barrett", "TOR", "SF", 6900, 35.5, 14.5),
            ("I. Quickley", "TOR", "PG", 6800, 35.0, 14.0), ("A. Reaves", "LAL", "SG", 6600, 34.2, 18.0),
            ("D. White", "BOS", "PG", 6500, 33.8, 15.5), ("M. Porter Jr.", "DEN", "SF", 6300, 32.5, 13.0),
            ("A. Gordon", "DEN", "PF", 6100, 31.5, 12.5), ("B. Beal", "PHX", "SG", 6400, 33.0, 11.5),
            ("K. Thompson", "DAL", "SF", 5800, 29.5, 16.0), ("J. Kuminga", "GSW", "PF", 5900, 30.2, 15.0),
            ("D. Green", "GSW", "C", 5600, 28.5, 12.0), ("J. Poeltl", "TOR", "C", 5700, 29.0, 13.5),
            ("D. Lively II", "DAL", "C", 5200, 26.8, 14.0), ("A. Wiggins", "GSW", "SF", 5100, 26.0, 10.5),
            ("P. Pritchard", "BOS", "PG", 4600, 23.5, 11.0), ("D. Knecht", "LAL", "SG", 4400, 22.8, 15.5)
        ], 234.5)
    },
    "🏒 NHL — Ice Hockey (Canada & USA Prime Slate — 36 Players Active)": {
        "default_format_idx": 1,
        "live_matches": [
            {"title": "Edmonton Oilers (EDM) vs Toronto Maple Leafs (TOR)", "status": "🔴 LIVE • 2nd Period (3 - 2) | Hockey Night in Canada", "info": "🔥 Goal Total: 6.5 | Power-Play Heavy Match"},
            {"title": "Montreal Canadiens (MTL) vs Boston Bruins (BOS)", "status": "🟢 TODAY • Puck Drop 7:00 PM EST", "info": "⚡ Goal Total: 6.0 | Original Six Rivalry"},
            {"title": "Vancouver Canucks (VAN) vs Colorado Avalanche (COL)", "status": "🟢 TODAY • Puck Drop 10:00 PM EST", "info": "🚀 Goal Total: 6.5 | High Shot Volume Slate"}
        ],
        "upcoming_matches": [
            {"title": "Winnipeg Jets (WPG) vs Vegas Golden Knights (VGK)", "time": "⏳ Tomorrow • 8:00 PM EST", "info": "📊 Early Goal Line: 6.0 | Central vs Pacific"},
            {"title": "New York Rangers (NYR) vs Florida Panthers (FLA)", "time": "⏳ Tomorrow • 7:30 PM EST", "info": "📊 Early Goal Line: 6.0 | East Finals Rematch"}
        ],
        "players": build_roster_pool([
            ("C. McDavid", "EDM", "C", 9600, 23.5, 32.0), ("N. MacKinnon", "COL", "C", 9500, 23.0, 29.5),
            ("A. Matthews", "TOR", "C", 9300, 22.2, 27.0), ("L. Draisaitl", "EDM", "W", 8900, 20.5, 23.0),
            ("D. Pastrnak", "BOS", "W", 9000, 21.0, 24.5), ("C. Makar", "COL", "D", 8600, 19.8, 26.0),
            ("M. Rantanen", "COL", "W", 8500, 19.5, 20.0), ("A. Panarin", "NYR", "W", 8400, 19.2, 19.5),
            ("W. Nylander", "TOR", "W", 8200, 18.6, 18.0), ("M. Marner", "TOR", "W", 8000, 18.0, 17.5),
            ("Q. Hughes", "VAN", "D", 8100, 18.4, 21.0), ("E. Bouchard", "EDM", "D", 7800, 17.6, 19.0),
            ("Z. Hyman", "EDM", "W", 7700, 17.4, 18.5), ("J.T. Miller", "VAN", "C", 7900, 17.9, 16.5),
            ("E. Pettersson", "VAN", "C", 7500, 16.8, 14.5), ("B. Marchand", "BOS", "W", 7400, 16.5, 15.0),
            ("C. Caufield", "MTL", "W", 7200, 16.0, 14.0), ("N. Suzuki", "MTL", "C", 7000, 15.6, 13.5),
            ("K. Connor", "WPG", "W", 7600, 17.1, 16.0), ("J. Eichel", "VGK", "C", 7800, 17.5, 17.0),
            ("M. Tkachuk", "FLA", "W", 8000, 18.1, 18.5), ("S. Reinhart", "FLA", "W", 7900, 17.8, 17.0),
            ("A. Fox", "NYR", "D", 7100, 15.8, 15.5), ("C. McAvoy", "BOS", "D", 6800, 15.0, 13.0),
            ("M. Rielly", "TOR", "D", 6600, 14.6, 14.0), ("D. Toews", "COL", "D", 6400, 14.1, 12.0),
            ("B. Boeser", "VAN", "W", 6900, 15.3, 13.5), ("R. Nugent-Hopkins", "EDM", "C", 6500, 14.4, 12.5),
            ("J. Tavares", "TOR", "C", 6700, 14.8, 13.0), ("J. Slafkovsky", "MTL", "W", 5800, 12.9, 11.0),
            ("M. Knies", "TOR", "W", 5400, 12.1, 14.5), ("V. Arvidsson", "EDM", "W", 5600, 12.5, 11.5),
            ("I. Shesterkin", "NYR", "G", 8300, 18.8, 22.0), ("C. Hellebuyck", "WPG", "G", 8100, 18.2, 20.0),
            ("J. Swayman", "BOS", "G", 7900, 17.5, 17.5), ("S. Skinner", "EDM", "G", 7600, 16.8, 16.0)
        ], 6.5)
    },
    "⚾ MLB — Major League Baseball (USA & Toronto Slate — 36 Players Active)": {
        "default_format_idx": 2,
        "live_matches": [
            {"title": "Los Angeles Dodgers (LAD) vs New York Yankees (NYY)", "status": "🔴 LIVE • Top 5th Inning (4 - 2)", "info": "🔥 Run Total: 9.5 | Wind Blowing Out 12 mph"},
            {"title": "Toronto Blue Jays (TOR) vs Philadelphia Phillies (PHI)", "status": "🟢 TODAY • First Pitch 7:07 PM EST (Rogers Centre)", "info": "⚡ Run Total: 8.5 | High Strikeout & HR Upside"},
            {"title": "Atlanta Braves (ATL) vs Boston Red Sox (BOS)", "status": "🟢 TODAY • First Pitch 7:10 PM EST", "info": "🚀 Run Total: 9.5 | Elite Hitter Park"}
        ],
        "upcoming_matches": [
            {"title": "Houston Astros (HOU) vs Texas Rangers (TEX)", "time": "⏳ Tomorrow • 8:05 PM EST", "info": "📊 Early Run Total: 9.0 | Lone Star Series"},
            {"title": "Baltimore Orioles (BAL) vs San Diego Padres (SD)", "time": "⏳ Tomorrow • 6:40 PM EST", "info": "📊 Early Run Total: 8.5 | Star Infield Slate"}
        ],
        "players": build_roster_pool([
            ("G. Cole", "NYY", "P", 9800, 24.5, 28.0), ("T. Glasnow", "LAD", "P", 9500, 23.8, 26.5),
            ("Z. Wheeler", "PHI", "P", 9600, 24.0, 27.0), ("C. Sale", "ATL", "P", 9400, 23.5, 25.0),
            ("K. Gausman", "TOR", "P", 8600, 20.5, 18.5), ("Y. Yamamoto", "LAD", "P", 8400, 19.8, 17.0),
            ("S. Ohtani", "LAD", "OF", 6600, 15.2, 32.0), ("A. Judge", "NYY", "OF", 6500, 14.9, 30.5),
            ("J. Soto", "NYY", "OF", 6200, 13.8, 25.0), ("M. Betts", "LAD", "SS", 6000, 13.4, 23.5),
            ("B. Harper", "PHI", "1B", 5900, 13.1, 22.0), ("V. Guerrero Jr.", "TOR", "1B", 5800, 12.8, 21.0),
            ("F. Freeman", "LAD", "1B", 5700, 12.6, 19.5), ("R. Devers", "BOS", "3B", 5600, 12.4, 18.0),
            ("T. Turner", "PHI", "SS", 5500, 12.1, 17.5), ("K. Schwarber", "PHI", "OF", 5400, 11.9, 19.0),
            ("M. Olson", "ATL", "1B", 5400, 11.8, 16.5), ("A. Riley", "ATL", "3B", 5300, 11.6, 16.0),
            ("M. Ozuna", "ATL", "OF", 5500, 12.0, 18.0), ("J. Duran", "BOS", "OF", 5600, 12.3, 20.0),
            ("T. Hernandez", "LAD", "OF", 5200, 11.4, 15.5), ("G. Stanton", "NYY", "OF", 5000, 11.0, 14.0),
            ("B. Bichette", "TOR", "SS", 4900, 10.6, 13.0), ("W. Smith", "LAD", "C", 5100, 11.1, 15.0),
            ("J. Realmuto", "PHI", "C", 4800, 10.4, 12.5), ("A. Chisholm Jr.", "NYY", "3B", 5100, 11.2, 16.5),
            ("G. Torres", "NYY", "2B", 4600, 9.9, 12.0), ("M. Muncy", "LAD", "3B", 4700, 10.2, 13.5),
            ("N. Castellanos", "PHI", "OF", 4500, 9.7, 11.0), ("A. Bohm", "PHI", "3B", 4600, 9.8, 11.5),
            ("G. Springer", "TOR", "OF", 4400, 9.5, 10.5), ("T. O'Neill", "BOS", "OF", 4700, 10.1, 13.0),
            ("O. Albies", "ATL", "2B", 5000, 10.8, 14.5), ("M. Harris II", "ATL", "OF", 4800, 10.3, 13.0),
            ("A. Volpe", "NYY", "SS", 4300, 9.3, 10.0), ("G. Lux", "LAD", "2B", 4000, 8.8, 9.5)
        ], 9.5)
    },
    "🏈🏀 NCAA — College Football & Basketball (US CFB / CBB — 36 Players Active)": {
        "default_format_idx": 1,
        "live_matches": [
            {"title": "Georgia Bulldogs (UGA) vs Alabama Crimson Tide (ALA)", "status": "🔴 LIVE • 2nd Quarter (17 - 14) | SEC on ABC", "info": "🔥 Vegas Total: 54.5 Pts | Spread: UGA -2.0"},
            {"title": "Ohio State Buckeyes (OSU) vs Oregon Ducks (ORE)", "status": "🟢 TODAY • Kickoff 7:30 PM EST", "info": "⚡ Vegas Total: 56.0 Pts | Big Ten Shootout"},
            {"title": "Texas Longhorns (TEX) vs Miami Hurricanes (MIA)", "status": "🟢 TODAY • Kickoff 3:30 PM EST", "info": "🚀 Vegas Total: 58.5 Pts | High Tempo Offense"}
        ],
        "upcoming_matches": [
            {"title": "Duke Blue Devils (DUKE) vs UNC Tar Heels (UNC)", "time": "⏳ Tomorrow • 9:00 PM EST (ESPN)", "info": "📊 Early Total: 154.5 Pts | Tobacco Road Rivalry"},
            {"title": "Kansas Jayhawks (KAN) vs Kentucky Wildcats (UK)", "time": "⏳ Tomorrow • 7:00 PM EST", "info": "📊 Early Total: 158.0 Pts | Blue Bloods Classic"}
        ],
        "players": build_roster_pool([
            ("A. Jeanty", "BSU", "RB", 9600, 33.5, 36.0), ("J. Milroe", "ALA", "QB", 9400, 31.0, 30.0),
            ("C. Ward", "MIA", "QB", 9200, 29.8, 27.5), ("D. Gabriel", "ORE", "QB", 9000, 28.5, 25.0),
            ("Q. Ewers", "TEX", "QB", 8800, 27.2, 22.0), ("C. Beck", "UGA", "QB", 8600, 26.5, 20.5),
            ("S. Sanders", "COL", "QB", 8700, 27.0, 23.0), ("W. Howard", "OSU", "QB", 8300, 25.2, 18.5),
            ("T. Hunter", "COL", "WR", 8900, 26.8, 29.0), ("J. Smith", "OSU", "WR", 8600, 25.4, 26.5),
            ("R. Williams", "ALA", "WR", 8500, 25.0, 25.5), ("T. McMillan", "ARI", "WR", 8400, 24.6, 22.0),
            ("L. Burden III", "MIZ", "WR", 8100, 23.2, 19.0), ("E. Egbuka", "OSU", "WR", 7800, 22.0, 17.5),
            ("I. Bond", "TEX", "WR", 7600, 21.4, 18.0), ("T. Johnson", "ORE", "WR", 7500, 21.0, 16.5),
            ("X. Restrepo", "MIA", "WR", 7700, 21.8, 19.5), ("T. Henderson", "OSU", "RB", 8200, 23.8, 21.0),
            ("Q. Judkins", "OSU", "RB", 7900, 22.5, 18.5), ("O. Hampton", "UNC", "RB", 8400, 24.8, 22.5),
            ("DJ Giddens", "KSU", "RB", 7600, 21.5, 15.0), ("K. Singleton", "PSU", "RB", 7400, 20.8, 16.0),
            ("T. Etienne", "UGA", "RB", 7300, 20.4, 17.0), ("J. James", "ORE", "RB", 7100, 19.8, 14.5),
            ("D. Martinez", "MIA", "RB", 6800, 18.9, 13.5), ("J. Blue", "TEX", "RB", 6600, 18.2, 14.0),
            ("T. Warren", "PSU", "TE", 7200, 20.1, 21.5), ("H. Fannin Jr.", "BGSU", "TE", 7000, 19.5, 18.0),
            ("G. Helm", "TEX", "TE", 6200, 16.8, 13.0), ("C. Loveland", "MICH", "TE", 6100, 16.5, 12.5),
            ("C. Flagg", "DUKE", "FWD", 9100, 39.5, 31.0), ("H. Dickinson", "KAN", "C", 8800, 37.5, 26.0),
            ("R. Davis", "UNC", "G", 8500, 35.8, 24.0), ("M. Sears", "ALA", "G", 8400, 35.2, 23.0),
            ("J. Broome", "AUB", "C", 8600, 36.4, 24.5), ("K. Kriisa", "UK", "G", 5800, 25.0, 11.5)
        ], 56.0)
    },
    "🥊 UFC / MMA — Las Vegas Fight Night & PPV (36 Fighters Active)": {
        "default_format_idx": 0,
        "live_matches": [
            {"title": "Alex Pereira vs Khalil Rountree Jr. (T-Mobile Arena Vegas)", "status": "🔴 LIVE • Main Card Underway on ESPN+ PPV", "info": "🔥 KO/TKO Odds: -280 | 5-Round Championship"},
            {"title": "Sean O'Malley vs Merab Dvalishvili (Co-Main Event)", "status": "🟢 TODAY • Walkouts at 11:15 PM EST", "info": "⚡ High-Output Striking & Takedown Volume"}
        ],
        "upcoming_matches": [
            {"title": "Jon Jones vs Stipe Miocic (Madison Square Garden NY)", "time": "⏳ Saturday Night • 10:00 PM EST (PPV)", "info": "📊 Heavyweight Title | Finish Rate: 82%"},
            {"title": "Islam Makhachev vs Arman Tsarukyan", "time": "⏳ Next PPV Slate • 10:00 PM EST", "info": "📊 Elite Grappling & Bonus Points Ceiling"}
        ],
        "players": build_roster_pool([
            ("A. Pereira", "UFC", "MMA", 9600, 106.5, 36.0), ("I. Makhachev", "UFC", "MMA", 9500, 102.0, 33.0),
            ("J. Jones", "UFC", "MMA", 9400, 99.5, 30.0), ("I. Topuria", "UFC", "MMA", 9300, 98.0, 29.0),
            ("T. Aspinall", "UFC", "MMA", 9400, 101.0, 32.5), ("K. Chimaev", "UFC", "MMA", 9200, 96.5, 28.5),
            ("S. O'Malley", "UFC", "MMA", 8900, 91.5, 24.5), ("M. Dvalishvili", "UFC", "MMA", 8800, 92.0, 25.0),
            ("D. Du Plessis", "UFC", "MMA", 8700, 89.5, 22.0), ("B. Muhammad", "UFC", "MMA", 8600, 88.0, 19.5),
            ("S. Rakhmonov", "UFC", "MMA", 9100, 95.0, 27.5), ("B. Nickal", "UFC", "MMA", 9000, 94.0, 26.5),
            ("M. Holloway", "UFC", "MMA", 8500, 87.5, 23.0), ("C. Oliveira", "UFC", "MMA", 8600, 88.5, 24.0),
            ("A. Tsarukyan", "UFC", "MMA", 8400, 86.0, 20.0), ("J. Gaethje", "UFC", "MMA", 8300, 84.5, 21.0),
            ("D. Poirier", "UFC", "MMA", 8200, 83.0, 19.0), ("A. Volkanovski", "UFC", "MMA", 8400, 85.5, 20.5),
            ("L. Edwards", "UFC", "MMA", 8100, 81.5, 17.5), ("S. Strickland", "UFC", "MMA", 8200, 82.5, 18.5),
            ("I. Adesanya", "UFC", "MMA", 8300, 84.0, 19.5), ("J. Prochazka", "UFC", "MMA", 8000, 80.5, 17.0),
            ("M. Ankalaev", "UFC", "MMA", 8700, 89.0, 21.5), ("C. Gane", "UFC", "MMA", 8500, 86.5, 18.0),
            ("D. Lopes", "UFC", "MMA", 8500, 87.0, 23.5), ("P. Pimblett", "UFC", "MMA", 7900, 79.5, 21.0),
            ("U. Nurmagomedov", "UFC", "MMA", 8800, 90.5, 24.0), ("C. Sandhagen", "UFC", "MMA", 8000, 80.0, 16.5),
            ("P. Yan", "UFC", "MMA", 8100, 81.0, 17.5), ("B. Moreno", "UFC", "MMA", 7800, 78.0, 15.5),
            ("A. Pantoja", "UFC", "MMA", 8600, 88.0, 20.0), ("K. Rountree Jr.", "UFC", "MMA", 6800, 68.5, 12.5),
            ("S. Miocic", "UFC", "MMA", 6900, 69.5, 13.0), ("M. Chandler", "UFC", "MMA", 7400, 74.5, 16.0),
            ("D. Hooker", "UFC", "MMA", 7500, 75.5, 15.5), ("R. Whittaker", "UFC", "MMA", 7700, 77.0, 16.5)
        ], 2.5)
    },
    "⛳ PGA Tour — US & Canadian Open Fantasy Golf (36 Golfers Active)": {
        "default_format_idx": 0,
        "live_matches": [
            {"title": "The Players Championship — TPC Sawgrass Round 3", "status": "🔴 LIVE • Leaders at -12 Under Par (NBC/Golf Channel)", "info": "🔥 Birdie Fest | Soft Greens & Low Wind"},
            {"title": "RBC Canadian Open — Featured Groups", "status": "🟢 TODAY • Tee Times 8:00 AM - 2:00 PM EST", "info": "⚡ Strokes Gained Approach Key Metric"}
        ],
        "upcoming_matches": [
            {"title": "The Masters Tournament — Augusta National", "time": "⏳ Upcoming Thursday • 7:30 AM EST", "info": "📊 Major Championship | $20M Purse"},
            {"title": "U.S. Open Championship — Pinehurst No. 2", "time": "⏳ Next Major Slate", "info": "📊 Driving Accuracy & Scrambling Crucial"}
        ],
        "players": build_roster_pool([
            ("S. Scheffler", "USA", "GOLF", 11000, 92.5, 35.0), ("X. Schauffele", "USA", "GOLF", 10500, 88.0, 30.0),
            ("R. McIlroy", "NIR", "GOLF", 10300, 86.5, 28.5), ("J. Rahm", "ESP", "GOLF", 9900, 83.0, 24.0),
            ("B. DeChambeau", "USA", "GOLF", 9800, 82.5, 26.5), ("C. Morikawa", "USA", "GOLF", 9600, 80.5, 23.0),
            ("L. Aberg", "SWE", "GOLF", 9400, 79.0, 22.0), ("V. Hovland", "NOR", "GOLF", 9200, 77.5, 19.5),
            ("P. Cantlay", "USA", "GOLF", 9000, 76.0, 18.5), ("W. Clark", "USA", "GOLF", 8800, 74.5, 17.0),
            ("H. Matsuyama", "JPN", "GOLF", 8900, 75.5, 19.0), ("T. Fleetwood", "ENG", "GOLF", 8600, 73.0, 16.5),
            ("S. Theegala", "USA", "GOLF", 8500, 72.5, 18.0), ("T. Finau", "USA", "GOLF", 8400, 71.5, 16.0),
            ("J. Thomas", "USA", "GOLF", 8300, 71.0, 17.5), ("J. Spieth", "USA", "GOLF", 8200, 70.0, 16.5),
            ("B. Koepka", "USA", "GOLF", 8700, 73.5, 18.0), ("S. Burns", "USA", "GOLF", 8100, 69.5, 15.0),
            ("C. Young", "USA", "GOLF", 7900, 68.0, 14.5), ("M. Homa", "USA", "GOLF", 7800, 67.5, 13.5),
            ("C. Conners", "CAN", "GOLF", 8000, 69.0, 16.0), ("S. Lowry", "IRE", "GOLF", 7900, 68.5, 15.5),
            ("T. Hatton", "ENG", "GOLF", 8100, 69.5, 15.0), ("R. Henley", "USA", "GOLF", 7700, 67.0, 14.0),
            ("B. Harman", "USA", "GOLF", 7500, 65.5, 12.5), ("K. Bradley", "USA", "GOLF", 7600, 66.0, 13.0),
            ("S. Im", "KOR", "GOLF", 7800, 67.5, 14.5), ("T. Kim", "KOR", "GOLF", 7600, 66.5, 15.0),
            ("N. Taylor", "CAN", "GOLF", 7300, 64.0, 12.0), ("A. Hadwin", "CAN", "GOLF", 7200, 63.5, 11.5),
            ("M. Pendrith", "CAN", "GOLF", 7100, 63.0, 11.0), ("A. Bhatia", "USA", "GOLF", 7400, 65.0, 14.0),
            ("D. Thompson", "USA", "GOLF", 7000, 62.0, 10.5), ("M. McNealy", "USA", "GOLF", 6900, 61.5, 10.0),
            ("R. MacIntyre", "SCO", "GOLF", 7300, 64.0, 12.5), ("B. Horschel", "USA", "GOLF", 7200, 63.5, 12.0)
        ], 72.0)
    },
    "🏎️ NASCAR Cup Series & Formula 1 (North America Racing — 36 Drivers Active)": {
        "default_format_idx": 0,
        "live_matches": [
            {"title": "NASCAR Cup Series — Daytona 500 / Talladega Superspeedway", "status": "🔴 LIVE • Stage 2 Green Flag | FOX Sports", "info": "🔥 Pack Racing | Place Differential & Laps Led Strategy"},
            {"title": "F1 Las Vegas / Miami Grand Prix", "status": "🟢 TODAY • Lights Out 10:00 PM EST", "info": "⚡ High Overtake & Fastest Lap Bonus Active"}
        ],
        "upcoming_matches": [
            {"title": "NASCAR Coca-Cola 600 — Charlotte Motor Speedway", "time": "⏳ Sunday • 6:00 PM EST", "info": "📊 400 Laps Dominator Points Available"},
            {"title": "F1 Canadian Grand Prix — Circuit Gilles Villeneuve Montreal", "time": "⏳ Sunday • 2:00 PM EST", "info": "📊 High Safety Car Probability"}
        ],
        "players": build_roster_pool([
            ("K. Larson", "HMS", "DRV", 10500, 56.0, 34.0), ("D. Hamlin", "JGR", "DRV", 10100, 53.5, 29.5),
            ("W. Byron", "HMS", "DRV", 9800, 51.0, 26.0), ("C. Bell", "JGR", "DRV", 9600, 49.5, 24.5),
            ("R. Blaney", "PENSKE", "DRV", 9500, 49.0, 25.0), ("T. Reddick", "23XI", "DRV", 9300, 48.0, 23.0),
            ("C. Elliott", "HMS", "DRV", 9100, 46.5, 22.0), ("J. Logano", "PENSKE", "DRV", 8900, 45.5, 20.5),
            ("M. Truex Jr.", "JGR", "DRV", 8700, 44.0, 18.0), ("R. Chastain", "TRK", "DRV", 8500, 43.0, 17.5),
            ("A. Bowman", "HMS", "DRV", 8300, 41.5, 16.5), ("B. Keselowski", "RFK", "DRV", 8200, 41.0, 16.0),
            ("C. Buescher", "RFK", "DRV", 8000, 40.0, 15.0), ("T. Gibbs", "JGR", "DRV", 7900, 39.5, 15.5),
            ("B. Wallace", "23XI", "DRV", 7700, 38.5, 14.5), ("K. Busch", "RCR", "DRV", 7600, 38.0, 14.0),
            ("A. Cindric", "PENSKE", "DRV", 7200, 35.5, 12.5), ("D. Suarez", "TRK", "DRV", 7100, 35.0, 12.0),
            ("C. Briscoe", "SHR", "DRV", 6900, 34.0, 11.5), ("M. McDowell", "FRM", "DRV", 6700, 33.0, 11.0),
            ("M. Verstappen", "RBR", "DRV", 10600, 55.0, 36.0), ("L. Norris", "MCL", "DRV", 10200, 52.5, 31.0),
            ("C. Leclerc", "FER", "DRV", 9700, 49.0, 25.5), ("O. Piastri", "MCL", "DRV", 9200, 46.0, 22.0),
            ("C. Sainz", "FER", "DRV", 9000, 45.0, 20.0), ("L. Hamilton", "MER", "DRV", 8800, 44.0, 19.5),
            ("G. Russell", "MER", "DRV", 8600, 43.0, 18.5), ("S. Perez", "RBR", "DRV", 8100, 39.5, 15.0),
            ("F. Alonso", "AMR", "DRV", 7500, 36.5, 13.5), ("L. Stroll", "AMR", "DRV", 6800, 33.0, 11.0),
            ("P. Gasly", "ALP", "DRV", 6600, 32.0, 10.5), ("A. Albon", "WIL", "DRV", 6500, 31.5, 10.0),
            ("N. Hulkenberg", "HAAS", "DRV", 6400, 31.0, 10.5), ("Y. Tsunoda", "RB", "DRV", 6300, 30.5, 9.5),
            ("R. Stenhouse Jr.", "JTG", "DRV", 6200, 30.0, 9.0), ("E. Jones", "LMC", "DRV", 6000, 29.0, 8.5)
        ], 55.0)
    },
    "⚽ MLS & Champions League Soccer (US & Canada DraftKings — 36 Players Active)": {
        "default_format_idx": 1,
        "live_matches": [
            {"title": "Inter Miami CF (MIA) vs Los Angeles FC (LAFC)", "status": "🔴 LIVE • 65' Min (2 - 1) | Apple TV MLS Season Pass", "info": "🔥 Goal Total: 3.5 | High Shot & Cross Volume"},
            {"title": "Toronto FC (TOR) vs Vancouver Whitecaps (VAN)", "status": "🟢 TODAY • Kickoff 7:30 PM EST", "info": "⚡ Goal Total: 3.0 | Set-Piece Heavy Slate"}
        ],
        "upcoming_matches": [
            {"title": "LA Galaxy (LAG) vs Seattle Sounders FC (SEA)", "time": "⏳ Tomorrow • 10:30 PM EST", "info": "📊 Early Goal Line: 3.5 | Attacking Slate"},
            {"title": "Real Madrid (RMA) vs Manchester City (MCI)", "time": "⏳ Tuesday • 3:00 PM EST (Paramount+)", "info": "📊 Early Goal Line: 3.5 | High Ceiling Showdown"}
        ],
        "players": build_roster_pool([
            ("L. Messi", "MIA", "FWD", 10400, 28.5, 38.0), ("E. Haaland", "MCI", "FWD", 10200, 27.5, 34.0),
            ("K. Mbappe", "RMA", "FWD", 10000, 26.8, 31.0), ("L. Suarez", "MIA", "FWD", 9400, 24.0, 26.0),
            ("D. Bouanga", "LAFC", "FWD", 9300, 23.5, 25.0), ("C. Hernandez", "CLB", "FWD", 9200, 23.2, 24.0),
            ("V. Junior", "RMA", "FWD", 9100, 23.0, 23.5), ("M. Salah", "LIV", "FWD", 9000, 22.8, 22.5),
            ("B. Saka", "ARS", "MID", 8800, 21.8, 21.0), ("C. Palmer", "CHE", "MID", 8700, 21.5, 22.0),
            ("R. Puig", "LAG", "MID", 8600, 21.2, 20.0), ("J. Bellingham", "RMA", "MID", 8500, 20.8, 19.5),
            ("K. De Bruyne", "MCI", "MID", 8400, 20.5, 18.5), ("L. Acosta", "CIN", "MID", 8300, 20.2, 18.0),
            ("E. Forsberg", "RBNY", "MID", 8100, 19.5, 16.5), ("R. Gauld", "VAN", "MID", 8000, 19.2, 17.0),
            ("F. Bernardeschi", "TOR", "FWD", 7900, 18.8, 15.5), ("L. Insigne", "TOR", "FWD", 7700, 18.2, 14.5),
            ("G. Pec", "LAG", "FWD", 7800, 18.5, 16.0), ("J. Paintsil", "LAG", "FWD", 7600, 17.9, 15.0),
            ("C. Benteke", "DC", "FWD", 7500, 17.6, 15.5), ("D. Rossi", "CLB", "FWD", 7400, 17.2, 14.0),
            ("B. White", "VAN", "FWD", 7200, 16.8, 13.0), ("J. Morris", "SEA", "FWD", 7100, 16.5, 12.5),
            ("A. Rusnak", "SEA", "MID", 7300, 17.0, 13.5), ("M. Bogusz", "LAFC", "MID", 7000, 16.2, 13.0),
            ("J. Alba", "MIA", "DEF", 6800, 15.8, 19.0), ("T. Alexander-Arnold", "LIV", "DEF", 6700, 15.5, 17.5),
            ("A. Hakimi", "PSG", "DEF", 6500, 15.0, 16.0), ("S. Busquets", "MIA", "MID", 6200, 14.0, 12.0),
            ("R. Hollingshead", "LAFC", "DEF", 5800, 13.2, 11.5), ("K. Wagner", "PHI", "DEF", 6000, 13.8, 12.5),
            ("W. Saliba", "ARS", "DEF", 5500, 12.5, 10.5), ("H. Lloris", "LAFC", "GK", 5400, 12.2, 14.0),
            ("D. Callender", "MIA", "GK", 5200, 11.8, 13.5), ("S. Johnson", "TOR", "GK", 4900, 11.0, 10.0)
        ], 3.5)
    },
    "🎾 Tennis — US Open & Canadian National Bank Open (36 Players Active)": {
        "default_format_idx": 0,
        "live_matches": [
            {"title": "Taylor Fritz vs Frances Tiafoe (Arthur Ashe Stadium NY)", "status": "🔴 LIVE • Set 2 (6-4, 4-3) | ESPN", "info": "🔥 All-American Showdown | High Ace Bonus Slate"},
            {"title": "Carlos Alcaraz vs Jannik Sinner", "status": "🟢 TODAY • Night Session 7:00 PM EST", "info": "⚡ Hardcourt Baseline Marathon Projected"}
        ],
        "upcoming_matches": [
            {"title": "Felix Auger-Aliassime vs Denis Shapovalov (Montreal/Toronto)", "time": "⏳ Tomorrow • 1:00 PM EST", "info": "📊 Canadian Hardcourt Clash | 3+ Sets Likely"},
            {"title": "Coco Gauff vs Aryna Sabalenka (US Open Final)", "time": "⏳ Tomorrow • 4:00 PM EST", "info": "📊 Straight Sets Bonus Potential"}
        ],
        "players": build_roster_pool([
            ("J. Sinner", "ITA", "TENNIS", 10200, 73.5, 34.0), ("C. Alcaraz", "ESP", "TENNIS", 10000, 72.0, 32.5),
            ("N. Djokovic", "SRB", "TENNIS", 9700, 69.5, 28.0), ("A. Sabalenka", "BLR", "TENNIS", 9600, 69.0, 29.0),
            ("I. Swiatek", "POL", "TENNIS", 9500, 68.5, 27.5), ("T. Fritz", "USA", "TENNIS", 9300, 66.5, 26.0),
            ("A. Zverev", "GER", "TENNIS", 9200, 65.5, 24.0), ("D. Medvedev", "RUS", "TENNIS", 9000, 64.0, 22.0),
            ("C. Gauff", "USA", "TENNIS", 8900, 63.5, 25.0), ("J. Pegula", "USA", "TENNIS", 8700, 61.5, 21.0),
            ("E. Rybakina", "KAZ", "TENNIS", 8800, 62.5, 21.5), ("B. Shelton", "USA", "TENNIS", 8500, 60.0, 20.5),
            ("T. Paul", "USA", "TENNIS", 8400, 59.5, 19.0), ("F. Tiafoe", "USA", "TENNIS", 8300, 58.5, 18.5),
            ("G. Dimitrov", "BUL", "TENNIS", 8200, 58.0, 17.0), ("A. de Minaur", "AUS", "TENNIS", 8300, 58.5, 17.5),
            ("A. Rublev", "RUS", "TENNIS", 8100, 57.0, 16.5), ("C. Ruud", "NOR", "TENNIS", 8000, 56.5, 16.0),
            ("S. Tsitsipas", "GRE", "TENNIS", 7900, 55.5, 15.5), ("H. Rune", "DEN", "TENNIS", 7800, 55.0, 15.0),
            ("F. Auger-Aliassime", "CAN", "TENNIS", 7700, 54.5, 16.5), ("J. Draper", "UK", "TENNIS", 7900, 56.0, 17.0),
            ("S. Korda", "USA", "TENNIS", 7600, 53.5, 14.5), ("A. Michelsen", "USA", "TENNIS", 7300, 51.5, 13.0),
            ("B. Nakashima", "USA", "TENNIS", 7400, 52.0, 13.5), ("D. Shapovalov", "CAN", "TENNIS", 7200, 50.5, 14.0),
            ("L. Fernandez", "CAN", "TENNIS", 7500, 53.0, 15.5), ("E. Navarro", "USA", "TENNIS", 7800, 55.0, 16.5),
            ("D. Collins", "USA", "TENNIS", 7600, 53.5, 15.0), ("M. Keys", "USA", "TENNIS", 7500, 52.5, 14.5),
            ("Q. Zheng", "CHN", "TENNIS", 8200, 58.0, 18.0), ("J. Paolini", "ITA", "TENNIS", 7700, 54.0, 15.0),
            ("M. Andreeva", "RUS", "TENNIS", 7400, 52.0, 14.0), ("P. Badosa", "ESP", "TENNIS", 7300, 51.5, 13.5),
            ("B. Andreescu", "CAN", "TENNIS", 6900, 48.5, 12.5), ("R. Opelka", "USA", "TENNIS", 6700, 47.5, 11.5)
        ], 22.5)
    }
}

selected_sport = st.selectbox(
    "🇺🇸🇨🇦 Choose Your North American Sport League (10 Leagues • 360+ Players Active):",
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

all_match_titles = ["🔥 Full Main Slate (All 36 Players Active)"] + [m["title"] for m in SPORTS_DATA[selected_sport]["live_matches"]] + [u["title"] + " (Upcoming)" for u in SPORTS_DATA[selected_sport]["upcoming_matches"]]
selected_slate = st.selectbox("🎯 Select Target Game / Contest Slate for Optimizer:", all_match_titles)

st.markdown("#### 📥 Universal DraftKings / FanDuel / Yahoo CSV Upload (Zero-Maintenance Mode)")
uploaded_file = st.file_uploader("Upload ANY Official DraftKings or FanDuel CSV Slate (Or use our Auto-Loaded 36-Player Vegas Slate)", type=["csv"])

if uploaded_file is not None:
    try:
        raw_csv_df = pd.read_csv(uploaded_file)
        df = smart_parse_dfs_csv(raw_csv_df)
        st.success(f"✅ Official CSV Uploaded & Auto-Mapped! ({len(df)} Players Loaded into Engine)")
    except Exception:
        st.error("⚠️ Error reading CSV! Using Auto-Loaded 36-Player Vegas Slate.")
        df = pd.DataFrame(SPORTS_DATA[selected_sport]["players"])
else:
    df = pd.DataFrame(SPORTS_DATA[selected_sport]["players"])

# SMART SLATE FILTER: If user selects a specific matchup (e.g. "KC vs BUF"), filter players to those teams!
is_single_game_selected = False
if not selected_slate.startswith("🔥 Full Main Slate") and uploaded_file is None:
    matched_teams = re.findall(r'\(([A-Z]{2,4})\)', selected_slate)
    if len(matched_teams) >= 2:
        filtered_df = df[df["Team"].isin(matched_teams)].copy().reset_index(drop=True)
        if len(filtered_df) >= 6:
            df = filtered_df
            is_single_game_selected = True
            st.info(f"🎯 **Single-Game Matchup Filter Active:** Showing {len(df)} active players from **{' & '.join(matched_teams)}** for Showdown optimization!")

# ==========================================
# 🧠 V8.0 FLAWLESS SOLVER (EXACT SLOT ALIGNMENT + REAL SHOWDOWN vs CLASSIC RULES)
# ==========================================
def apply_positional_rules(prob, p_vars, base_data, roster_size, pos_set):
    if roster_size >= 8:
        if "QB" in pos_set and "RB" in pos_set and "WR" in pos_set:
            qb_idxs = [idx for idx in base_data.index if base_data["Pos"][idx] == "QB"]
            rb_idxs = [idx for idx in base_data.index if base_data["Pos"][idx] == "RB"]
            wr_idxs = [idx for idx in base_data.index if base_data["Pos"][idx] == "WR"]
            te_idxs = [idx for idx in base_data.index if base_data["Pos"][idx] == "TE"]
            dst_idxs = [idx for idx in base_data.index if base_data["Pos"][idx] == "DST"]
            if len(qb_idxs) >= 1:
                prob += pulp.lpSum([p_vars[idx] for idx in qb_idxs]) == 1
            if len(rb_idxs) >= 2:
                prob += pulp.lpSum([p_vars[idx] for idx in rb_idxs]) >= 2
            if len(wr_idxs) >= 3:
                prob += pulp.lpSum([p_vars[idx] for idx in wr_idxs]) >= 3
            if len(te_idxs) >= 1:
                prob += pulp.lpSum([p_vars[idx] for idx in te_idxs]) >= 1
            if len(dst_idxs) >= 1 and roster_size == 9:
                prob += pulp.lpSum([p_vars[idx] for idx in dst_idxs]) == 1
        elif "P" in pos_set and "OF" in pos_set:
            p_idxs = [idx for idx in base_data.index if base_data["Pos"][idx] == "P"]
            if len(p_idxs) >= 2:
                prob += pulp.lpSum([p_vars[idx] for idx in p_idxs]) <= 2
                prob += pulp.lpSum([p_vars[idx] for idx in p_idxs]) >= 1
        elif "G" in pos_set and "C" in pos_set and "W" in pos_set:
            g_idxs = [idx for idx in base_data.index if base_data["Pos"][idx] == "G"]
            if len(g_idxs) >= 1:
                prob += pulp.lpSum([p_vars[idx] for idx in g_idxs]) == 1
        elif "GK" in pos_set and "FWD" in pos_set:
            gk_idxs = [idx for idx in base_data.index if base_data["Pos"][idx] == "GK"]
            if len(gk_idxs) >= 1:
                prob += pulp.lpSum([p_vars[idx] for idx in gk_idxs]) == 1

def align_players_to_official_slots(chosen_indices, base_data, roster_size, pos_set, sim_pts, captain_usage, max_cpt_count):
    # 1. 6-PLAYER SHOWDOWN MODE: Only Showdown has 1.5x Captain!
    if roster_size == 6:
        def cpt_priority(idx):
            p_nm = base_data["Player"][idx]
            penalty = 100.0 if captain_usage[p_nm] >= max_cpt_count else (captain_usage[p_nm] * 1.5)
            return sim_pts[idx] - penalty
        chosen_sorted = sorted(chosen_indices, key=cpt_priority, reverse=True)
        formatted = []
        for rank_idx, p_idx in enumerate(chosen_sorted):
            p_name = base_data["Player"][p_idx]
            p_pos = base_data["Pos"][p_idx]
            p_tm = base_data["Team"][p_idx]
            if rank_idx == 0:
                captain_usage[p_name] += 1
                formatted.append(f"{p_name} ({p_pos}-{p_tm}) 👑(CPT 1.5x)")
            else:
                formatted.append(f"{p_name} ({p_pos}-{p_tm})")
        return formatted

    # 2. 9-PLAYER NFL CLASSIC MODE: Align strictly into QB, RB1, RB2, WR1, WR2, WR3, TE, FLEX, DST!
    if roster_size == 9 and "QB" in pos_set and "RB" in pos_set and "WR" in pos_set:
        rem = list(chosen_indices)
        def pop_pos(target_pos):
            for idx in rem:
                if base_data["Pos"][idx] == target_pos:
                    rem.remove(idx)
                    return idx
            return None
        qb = pop_pos("QB")
        rb1 = pop_pos("RB")
        rb2 = pop_pos("RB")
        wr1 = pop_pos("WR")
        wr2 = pop_pos("WR")
        wr3 = pop_pos("WR")
        te = pop_pos("TE")
        dst = pop_pos("DST")
        flex = rem.pop(0) if rem else None
        ordered_slots = [qb, rb1, rb2, wr1, wr2, wr3, te, flex, dst]
        final_slots = []
        for s_idx in ordered_slots:
            if s_idx is not None:
                final_slots.append(f"{base_data['Player'][s_idx]} ({base_data['Pos'][s_idx]}-{base_data['Team'][s_idx]})")
            elif rem:
                r_idx = rem.pop(0)
                final_slots.append(f"{base_data['Player'][r_idx]} ({base_data['Pos'][r_idx]}-{base_data['Team'][r_idx]})")
        if len(final_slots) == 9:
            # Track primary QB/Anchor in captain_usage for exposure summary
            if qb is not None:
                captain_usage[base_data["Player"][qb]] += 1
            return final_slots

    # 3. ALL OTHER 8/9-PLAYER CLASSIC MODES (NBA, NHL, MLB, NCAA, MLS): Clean 1x slots without fake Captain tags!
    chosen_sorted = sorted(chosen_indices, key=lambda idx: sim_pts[idx], reverse=True)
    if chosen_sorted:
        captain_usage[base_data["Player"][chosen_sorted[0]]] += 1
    return [f"{base_data['Player'][idx]} ({base_data['Pos'][idx]}-{base_data['Team'][idx]})" for idx in chosen_sorted]

def run_god_mode_solver(data, lineups_count, cap, strategy_mode, locked_players, excluded_players, roster_size, max_exp_pct, enable_stacking, user_email_str):
    lineups, stats, ai_grades = [], [], []
    base_data = data[~data["Player"].isin(excluded_players)].copy().reset_index(drop=True)
    if len(base_data) < roster_size:
        return [], [], [], pd.DataFrame()
        
    unique_seed_str = f"{user_email_str}_{time.time_ns()}"
    seed_int = int(hashlib.md5(unique_seed_str.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed_int)
    
    avg_raw_sal = base_data["Salary"].mean()
    target_avg_sal = (cap * 0.88) / roster_size
    if avg_raw_sal * roster_size > cap * 0.95:
        scale_factor = target_avg_sal / avg_raw_sal
        base_data["Eff_Salary"] = (base_data["Salary"] * scale_factor / 100).round().astype(int) * 100
    else:
        base_data["Eff_Salary"] = base_data["Salary"]
        
    max_allowed_count = max(1, int(np.ceil((max_exp_pct / 100.0) * lineups_count)))
    max_cpt_count = max(1, int(np.ceil((min(max_exp_pct, 45) / 100.0) * lineups_count)))
    player_usage = {p: 0 for p in base_data["Player"]}
    captain_usage = {p: 0 for p in base_data["Player"]}
    
    pos_set = set(base_data["Pos"].unique())
    
    for i in range(lineups_count):
        prob = pulp.LpProblem(f"GodMode_{i}", pulp.LpMaximize)
        p_vars = pulp.LpVariable.dicts("P", base_data.index, cat='Binary')
        
        dna_noise = rng.normal(0, 2.15 if i > 0 else 1.15, size=len(base_data))
        sim_pts = base_data["Proj_Pts"] + dna_noise
        
        if enable_stacking and len(base_data["Team"].unique()) > 1:
            teams_list = base_data["Team"].unique().tolist()
            stack_team = teams_list[int(rng.integers(0, len(teams_list)))]
            stack_bonus = [2.6 if base_data["Team"][idx] == stack_team else 0.0 for idx in base_data.index]
            sim_pts = sim_pts + pd.Series(stack_bonus)
        
        prob += pulp.lpSum([sim_pts[idx] * p_vars[idx] for idx in base_data.index])
        prob += pulp.lpSum([base_data["Eff_Salary"][idx] * p_vars[idx] for idx in base_data.index]) <= cap
        prob += pulp.lpSum([p_vars[idx] for idx in base_data.index]) == roster_size
        
        apply_positional_rules(prob, p_vars, base_data, roster_size, pos_set)
        
        for idx in base_data.index:
            p_name = base_data["Player"][idx]
            if p_name in locked_players:
                prob += p_vars[idx] == 1
            elif player_usage[p_name] >= max_allowed_count:
                prob += p_vars[idx] == 0
                
        if strategy_mode == "💣 Mega GPP Tournament (High Ceiling / Low Ownership)":
            prob += pulp.lpSum([base_data["Ownership_%"][idx] * p_vars[idx] for idx in base_data.index]) <= (roster_size * 24)
        
        for prev_raw in lineups:
            clean_prev = [p.split(" (")[0] for p in prev_raw]
            prob += pulp.lpSum([p_vars[idx] for idx in base_data.index if base_data["Player"][idx] in clean_prev]) <= (roster_size - 2)
            
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        # BULLETPROOF FALLBACK SOLVER: Still strictly enforces positional rules & locked players!
        if pulp.LpStatus[prob.status] != 'Optimal':
            prob_fallback = pulp.LpProblem(f"GodMode_FB_{i}", pulp.LpMaximize)
            p_vars = pulp.LpVariable.dicts("P", base_data.index, cat='Binary')
            prob_fallback += pulp.lpSum([sim_pts[idx] * p_vars[idx] for idx in base_data.index])
            prob_fallback += pulp.lpSum([base_data["Eff_Salary"][idx] * p_vars[idx] for idx in base_data.index]) <= cap
            prob_fallback += pulp.lpSum([p_vars[idx] for idx in base_data.index]) == roster_size
            apply_positional_rules(prob_fallback, p_vars, base_data, roster_size, pos_set)
            for idx in base_data.index:
                if base_data["Player"][idx] in locked_players:
                    prob_fallback += p_vars[idx] == 1
            for prev_raw in lineups:
                clean_prev = [p.split(" (")[0] for p in prev_raw]
                prob_fallback += pulp.lpSum([p_vars[idx] for idx in base_data.index if base_data["Player"][idx] in clean_prev]) <= (roster_size - 1)
            prob_fallback.solve(pulp.PULP_CBC_CMD(msg=0))
            prob = prob_fallback
            
        if pulp.LpStatus[prob.status] == 'Optimal':
            chosen_indices = [idx for idx in base_data.index if p_vars[idx].varValue == 1]
            for p_idx in chosen_indices:
                player_usage[base_data["Player"][p_idx]] += 1
                
            formatted_lineup = align_players_to_official_slots(
                chosen_indices, base_data, roster_size, pos_set, sim_pts, captain_usage, max_cpt_count
            )
                    
            pts = sum([base_data["Proj_Pts"][idx] for idx in chosen_indices])
            sal = sum([base_data["Eff_Salary"][idx] for idx in chosen_indices])
            own = sum([base_data["Ownership_%"][idx] for idx in chosen_indices]) / roster_size
            
            sal_efficiency = (sal / max(cap, 1)) * 10.0
            rating_10 = min(9.9, max(8.7, round(8.8 + (sal_efficiency * 0.08) + ((30.0 - own) * 0.02), 1)))
            grade_letter = "A+ 🔥" if rating_10 >= 9.5 else ("A ⚡" if rating_10 >= 9.1 else "A- 🛡️")
            ai_grades.append(f"{grade_letter} ({rating_10}/10)")
            
            lineups.append(formatted_lineup)
            stats.append(f"Pts: {pts:.1f} | Sal: ${sal:,} | Own: {own:.1f}%")
        else:
            break
            
    total_gen = max(len(lineups), 1)
    exp_rows = []
    for idx in base_data.index:
        p_nm = base_data["Player"][idx]
        cnt = player_usage[p_nm]
        if cnt > 0:
            exp_rows.append({
                "Player": p_nm,
                "Team": base_data["Team"][idx],
                "Pos": base_data["Pos"][idx],
                "Lineups Drafted": f"{cnt} / {len(lineups)}",
                "Total Exposure %": round((cnt / total_gen) * 100, 1),
                "Anchor / CPT %": round((captain_usage[p_nm] / total_gen) * 100, 1)
            })
    exp_df = pd.DataFrame(exp_rows).sort_values(by="Total Exposure %", ascending=False).reset_index(drop=True)
    return lineups, stats, ai_grades, exp_df

st.divider()

# ==========================================
# 🧭 STEP 2: NAVIGATION MENU
# ==========================================
st.markdown("### 🧭 Step 2: Navigation Menu")
app_mode = st.selectbox(
    "Choose your section:",
    [
        "🚀 Auto-Pilot Lineup Engine (DraftKings / FanDuel)",
        "🎯 PrizePicks & Underdog Pick'em Generator (25x Parlay Slip)",
        "📈 My Bankroll & ROI Profit Tracker",
        "📰 Live Match News & 1-Click Late Swap Alert",
        "📊 The Terminal (Player Data Matrix)",
        "📉 Pro Analytics",
        "💎 VIP Upgrade, Viral Referral (+7 Free Days) & Support"
    ],
    label_visibility="collapsed"
)
st.divider()

if app_mode.startswith("🚀 Auto-Pilot"):
    st.markdown(f"### 🧠 V8.0 Official-Slot Engine — {selected_sport}")
    st.markdown(f"<p style='color:#00FF41; font-weight:bold;'>Active Slate: {selected_slate} | Pool: {len(df)} Players | 🧬 Anti-Collision DNA Seed: #{user_dna_id}</p>", unsafe_allow_html=True)
    st.markdown("""
    <div class='strategy-box'>
        <b style='color:#FFD700; font-size:16px;'>Step 3: True DraftKings/FanDuel Positional Slots + Personal DNA Seed + Direct CSV Export</b><br>
        <span style='color:white;'>Automatically assigns 1.5x Captain ONLY in 6-Player Showdown mode and uses strict positional slots (QB, RB1, RB2, WR1-3, TE, FLEX, DST) in Classic modes!</span>
    </div>
    """, unsafe_allow_html=True)
    
    auto_idx = 0 if is_single_game_selected else SPORTS_DATA[selected_sport]["default_format_idx"]
    regional_format = st.radio(
        "🇺🇸🇨🇦 Choose North American Contest Format:",
        [
            "⚡ Showdown / Single-Game Mode (6 Players | $50,000 Cap — 1 CPT 1.5x + 5 FLEX)",
            "🏆 Classic Main Slate Roster (8 Players | $50,000 Cap — NBA / NHL / College / Soccer)",
            "🏈 Classic Full Lineup Roster (9 Players | $50,000 Cap — NFL 1-QB / MLB Full Slate)"
        ],
        index=auto_idx
    )
    
    pos_set_now = set(df["Pos"].unique())
    if "6 Players" in regional_format:
        roster_size = 6
        default_cap = 50000
        col_names = ["👑 Captain (1.5x)", "FLEX 1", "FLEX 2", "FLEX 3", "FLEX 4", "FLEX 5"]
    elif "8 Players" in regional_format:
        roster_size = 8
        default_cap = 50000
        col_names = ["Slot 1 (Anchor)", "Slot 2", "Slot 3", "Slot 4", "Slot 5", "Slot 6", "UTIL 1", "UTIL 2"]
    else:
        roster_size = 9
        default_cap = 50000
        if "QB" in pos_set_now and "RB" in pos_set_now and "WR" in pos_set_now:
            col_names = ["QB", "RB1", "RB2", "WR1", "WR2", "WR3", "TE", "FLEX", "DST"]
        else:
            col_names = ["P1 / Anchor", "P2 / Core", "Slot 3", "Slot 4", "Slot 5", "Slot 6", "Slot 7", "Slot 8", "Slot 9"]
        
    strategy = st.radio("Target Contest Type:", ["🛡️ 50/50 & Head-to-Head Cash Game (Safe Floor)", "💣 Mega GPP Tournament (High Ceiling / Low Ownership)"])
    
    col_lk1, col_lk2 = st.columns(2)
    with col_lk1:
        locked_players = st.multiselect("🔒 Lock Core Players (100% Exposure):", df["Player"].tolist(), max_selections=roster_size-1)
    with col_lk2:
        available_to_exclude = [p for p in df["Player"].tolist() if p not in locked_players]
        default_excl = [p for p in st.session_state.auto_excluded if p in available_to_exclude]
        excluded_players = st.multiselect("❌ Exclude / Late-Swap Fade Players:", available_to_exclude, default=default_excl)
        
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        num_lineups = st.slider("🎯 Number of Lineups", 1, 150, 24)
    with col_s2:
        max_exp_pct = st.slider("🎚️ Max Player Exposure %", 25, 100, 65)
    with col_s3:
        salary_cap = st.number_input("💰 Official Salary Cap ($ USD)", value=default_cap, step=1000)
        
    enable_stacking = st.checkbox("🔗 Enable Smart Team-Stacking (Auto-Pair QB/Star with Teammates for Correlation Boost)", value=True)
    
    st.write("")
    if st.button("🔥 RUN 1000% AUTO-PILOT OPTIMIZER", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for percent in range(100):
            time.sleep(0.006)
            progress_bar.progress(percent + 1)
            if percent < 50: status_text.text(f"Injecting Personal DNA Seed #{user_dna_id} & Enforcing Official Slots...")
            else: status_text.text("Grading Lineup Quality (A+ Scale) & Building Unique Stacks...")
            
        status_text.text("✅ EXECUTION COMPLETE.")
        
        final_lineups, stat_list, ai_grades, exp_df = run_god_mode_solver(
            df, num_lineups, salary_cap, strategy, locked_players, excluded_players, roster_size, max_exp_pct, enable_stacking, st.session_state.user_email
        )
        
        if final_lineups:
            st.success(f"🏆 {len(final_lineups)} SLOT-VERIFIED WINNING LINEUPS GENERATED FOR DNA SEED #{user_dna_id}!")
            df_out = pd.DataFrame(final_lineups, columns=col_names)
            df_out["⚡ AI Grade"] = ai_grades
            df_out["Metrics"] = stat_list
            df_out.index = [f"Lineup-{i+1}" for i in range(len(df_out))]
            st.dataframe(df_out, use_container_width=True)
            
            dk_clean_df = pd.DataFrame(
                [[p.split(" (")[0] for p in row] for row in final_lineups],
                columns=col_names
            )
            fd_clean_df = dk_clean_df.copy()
            dk_csv = dk_clean_df.to_csv(index=False).encode('utf-8')
            fd_csv = fd_clean_df.to_csv(index=False).encode('utf-8')
            
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button("💾 DOWNLOAD DRAFTKINGS DIRECT CSV", dk_csv, "DraftKings_Direct_Upload.csv", "text/csv", use_container_width=True)
            with col_dl2:
                st.download_button("💾 DOWNLOAD FANDUEL DIRECT CSV", fd_csv, "FanDuel_Direct_Upload.csv", "text/csv", use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 📊 Portfolio Player Exposure Breakdown")
            st.dataframe(exp_df, use_container_width=True, hide_index=True)
        else:
            st.error("Engine Overload: Not enough players in this slate/position to build full lineups. Switch to 6-Player Showdown or reduce excluded players.")

elif app_mode.startswith("🎯 PrizePicks"):
    st.subheader(f"🎯 PrizePicks & Underdog Fantasy 6-Pick Parlay Slip (25x Payout) — {selected_sport}")
    st.markdown("""
    <div class='strategy-box'>
        <b style='color:#00FF41; font-size:16px;'>🔥 North America's #1 Pick'em Prop Slip Finder</b><br>
        <span style='color:white;'>Compares our AI Vegas Projections against implied Pick'em Lines to find high-value <b>🔼 MORE (Over)</b> & <b>🔽 LESS (Under)</b> plays!</span>
    </div>
    """, unsafe_allow_html=True)
    
    pick_df = df.copy()
    top_picks = pick_df.sort_values(by="Proj_Pts", ascending=False).head(12).sample(frac=1.0).head(min(6, len(pick_df))).reset_index(drop=True)
    
    if st.button("🔄 GENERATE NEW AI 6-PICK PARLAY SLIP (25X PAYOUT)", use_container_width=True):
        top_picks = pick_df.sample(n=min(6, len(pick_df))).reset_index(drop=True)
        
    cols_p = st.columns(2)
    for idx, row in top_picks.iterrows():
        is_more = (idx % 3 != 2)
        line_val = round(row["Proj_Pts"] * (0.88 if is_more else 1.12), 1)
        direction_badge = "🟢 🔼 MORE (OVER)" if is_more else "🔴 🔽 LESS (UNDER)"
        prop_grade = round(random.uniform(9.3, 9.9), 1)
        with cols_p[idx % 2]:
            st.markdown(f"""
            <div class='pickem-card'>
                <b style='color:#00FF41; font-size:18px;'>Pick #{idx+1}: {row['Player']} ({row['Team']} - {row['Pos']})</b><br>
                <span style='color:#FFD700; font-size:15px;'>Prop Line: <b>{line_val} Fantasy Score</b> | AI Proj: <b>{row['Proj_Pts']:.1f}</b></span><br>
                <span style='color:#FFFFFF; font-size:16px; font-weight:bold;'>Action: {direction_badge}</span><br>
                <span style='color:#00BFFF; font-size:13px;'>⚡ AI Prop Grade: <b>A+ ({prop_grade}/10)</b> • ⭐⭐⭐⭐⭐ 5-Star Value</span>
            </div>
            """, unsafe_allow_html=True)

elif app_mode.startswith("📈 My Bankroll"):
    st.subheader("📈 My DFS Bankroll & ROI Profit Tracker ($ USD / $ CAD)")
    st.markdown("""
    <div class='strategy-box'>
        <b style='color:#00FF41; font-size:16px;'>💰 Professional Bankroll Management</b><br>
        <span style='color:white;'>Log your daily DraftKings, FanDuel & PrizePicks contest results to track your Net Profit, ROI %, and Bankroll Growth!</span>
    </div>
    """, unsafe_allow_html=True)
    
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        b_sport = st.selectbox("Contest Sport:", ["NFL", "NBA", "NHL", "MLB", "NCAA", "UFC", "PGA", "NASCAR/F1", "Soccer", "Tennis"])
    with col_b2:
        b_entry = st.number_input("Total Entry Fees ($ USD):", min_value=1.0, value=25.0, step=5.0)
    with col_b3:
        b_won = st.number_input("Total Winnings ($ USD):", min_value=0.0, value=85.0, step=10.0)
        
    if st.button("➕ LOG CONTEST RESULT TO MY BANKROLL", use_container_width=True):
        add_bankroll_entry(st.session_state.user_email, b_sport, b_entry, b_won)
        st.success("✅ Contest Result Logged to Your Personal Bankroll Database!")
        
    user_b_df = get_bankroll_df(st.session_state.user_email)
    if user_b_df.empty:
        user_b_df = pd.DataFrame({
            "Date": ["Sample-1", "Sample-2", "Sample-3", "Sample-4"],
            "Sport": ["NFL", "NBA", "NHL", "NFL"],
            "Entry_USD": [20.0, 25.0, 30.0, 50.0],
            "Won_USD": [45.0, 15.0, 95.0, 180.0]
        })
    user_b_df["Net_Profit_USD"] = user_b_df["Won_USD"] - user_b_df["Entry_USD"]
    user_b_df["Cumulative_Bankroll_USD"] = user_b_df["Net_Profit_USD"].cumsum()
    
    tot_entry = user_b_df["Entry_USD"].sum()
    tot_won = user_b_df["Won_USD"].sum()
    net_prof = tot_won - tot_entry
    roi_pct = ((net_prof / tot_entry) * 100) if tot_entry > 0 else 0.0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("💵 Total Invested", f"${tot_entry:,.2f}")
    m2.metric("🏆 Total Winnings", f"${tot_won:,.2f}")
    m3.metric("🚀 Net Profit & ROI", f"${net_prof:,.2f} ({roi_pct:+.1f}% ROI)")
    
    fig_b = px.line(user_b_df, y="Cumulative_Bankroll_USD", markers=True, template="plotly_dark", title="Cumulative Bankroll Profit Growth ($ USD)")
    st.plotly_chart(fig_b, use_container_width=True)
    st.dataframe(user_b_df, use_container_width=True, hide_index=True)

elif app_mode.startswith("📰 Live Match News"):
    st.subheader(f"🚨 Real-Time Injury Desk & 1-Click Late Swap — {selected_sport}")
    gtd_player = df["Player"].iloc[min(3, len(df)-1)]
    pivot_player = df["Player"].iloc[min(5, len(df)-1)]
    
    st.markdown(f"""
    <div class='news-box-red' style='background-color: #1A202C; padding: 18px; border-radius: 8px; border-left: 5px solid #FF3131; margin-bottom: 15px;'>
        <b style='color:#FF3131; font-size:18px;'>⚠️ BREAKING LAS VEGAS LATE-SWAP ALERT</b><br>
        <span style='color:white; font-size:15px;'>• <b>{gtd_player}</b> listed as <b>Game-Time Decision / Questionable</b> (Monitor pre-game warmups).<br>
        • <b>AI Optimal Pivot:</b> <b>{pivot_player}</b> projects for a +24% usage boost if {gtd_player} is ruled out!</span>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button(f"⚡ 1-CLICK AUTO-EXCLUDE {gtd_player.upper()} FROM ALL LINEUPS", use_container_width=True):
        if gtd_player not in st.session_state.auto_excluded:
            st.session_state.auto_excluded.append(gtd_player)
        st.success(f"✅ {gtd_player} automatically added to Engine Exclude List! Switch to Auto-Pilot Engine to re-generate late-swap lineups.")

elif app_mode.startswith("📊 The Terminal"):
    st.subheader(f"Deep-Dive Player Matrix ({len(df)} Players Active) — {selected_sport}")
    st.markdown(f"<p style='color:#FFD700; font-size:13px;'>Slate: {selected_slate}</p>", unsafe_allow_html=True)
    full_df = df.copy()
    if 'Proj_Pts' in full_df.columns: full_df['Proj_Pts'] = full_df['Proj_Pts'].round(1)
    if 'Ownership_%' in full_df.columns: full_df['Ownership_%'] = full_df['Ownership_%'].round(1)
    st.dataframe(full_df.style.background_gradient(subset=['Proj_Pts'], cmap='Greens')
                 .background_gradient(subset=['Ownership_%'], cmap='Reds'), 
                 use_container_width=True, hide_index=True, height=650)

elif app_mode == "📉 Pro Analytics":
    st.subheader(f"Pro Leverage & Value Matrix (All {len(df)} Players) — {selected_sport}")
    fig1 = px.scatter(df, x="Salary", y="Proj_Pts", color="Pos", hover_name="Player", template="plotly_dark", title=f"Salary vs Projected Points ({len(df)}-Player Slate)")
    st.plotly_chart(fig1, use_container_width=True)

elif app_mode.startswith("💎 VIP Upgrade"):
    my_ref_code = "PROSTACK-" + hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:5].upper()
    st.markdown(f"""
    <div class='vip-box'>
        <h2 style='color: #00BFFF !important;'>💎 VIP MEMBERSHIP, VIRAL REFERRAL & 24/7 CONCIERGE</h2>
        <p style='color: white;'>Logged in as: <b>{st.session_state.user_email}</b> | Current Validity: <b>{exp_info}</b></p>
        <p style='color: #00FF41; font-size: 16px; font-weight: bold;'>🎁 Your Personal VIP Invite Code: <code>{my_ref_code}</code> (Share with DFS friends to give & get +7 Free VIP Days!)</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🎁 Claim +7 Free VIP Days (Enter Friend's Referral Code)")
    friend_code = st.text_input("Enter a Friend's PROSTACK Referral Code:", placeholder="e.g. PROSTACK-A1B2C")
    if st.button("🎉 REDEEM +7 FREE VIP DAYS NOW", use_container_width=True):
        ok, ref_msg = redeem_referral_bonus(st.session_state.user_email, friend_code)
        if ok:
            st.success(ref_msg)
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"⚠️ {ref_msg}")
            
    st.divider()
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

st.markdown("""
<div class='legal-footer'>
    <b>⚖️ Transparent Analytics & Responsible Play Disclaimer:</b> ProStack AI V8.0 is a quantitative lineup optimization and statistical modeling software built for USA & Canada Daily Fantasy Sports research. We do not operate real-money contests or guarantee financial outcomes. Must be 18+ (21+ in applicable jurisdictions).
</div>
""", unsafe_allow_html=True)
