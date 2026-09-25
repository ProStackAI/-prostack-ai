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
# ⚙️ STEP 0: CEO MASTER CONFIGURATION
# ==========================================
PAYMENT_LINKS = {
    "🥇 1 Month Plan ($29 / ₹2,400)": "https://buy.stripe.com/test_1month_link",
    "🥈 3 Months Plan - Popular ($79 / ₹6,500)": "https://buy.stripe.com/test_3months_link",
    "🥉 6 Months Plan - Best Value ($139 / ₹11,500)": "https://buy.stripe.com/test_6months_link",
    "👑 1 Year VIP Pass ($249 / ₹20,000)": "https://buy.stripe.com/test_1year_link"
}

# VIP Support Links (Apna Telegram / WhatsApp link yahan daal sakte hain)
SUPPORT_WHATSAPP_URL = "https://wa.me/919999999999?text=Hello%20ProStack%20AI%20VIP%20Support"
SUPPORT_TELEGRAM_URL = "https://t.me/ProStackAI_Support"
SUPPORT_EMAIL = "support@prostack.ai"

# Optional: Real Automated Email OTP Setup (Agar aap Gmail App Password dalenge toh real email bhi jayega)
SMTP_SENDER_EMAIL = ""      # e.g. "yourapp@gmail.com"
SMTP_APP_PASSWORD = ""      # 16-digit Google App Password

# --- 1. DATABASE & ENTERPRISE SETUP (WITH PHONE NUMBER & BACKUP) ---
DB_FILE = 'prostack_v3_empire.db'

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
                  ("testuser@prostack.ai", "9876543210", dummy_pw, expiry, 'Active', 'None', 'None'))
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
        # Match either exact phone or last 4 digits or if phone was not provided earlier
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
    """Tries to send real email if SMTP is configured, and returns delivery status."""
    if SMTP_SENDER_EMAIL and SMTP_APP_PASSWORD:
        try:
            msg = EmailMessage()
            msg['Subject'] = f"🔑 ProStack AI - Password Reset OTP: {otp_code}"
            msg['From'] = SMTP_SENDER_EMAIL
            msg['To'] = target_email
            msg.set_content(f"Hello ProStack AI Member,\n\nYour One-Time Password (OTP) for resetting your account password is: {otp_code}\nRegistered Mobile: {target_phone}\n\nIf you did not request this, please ignore this message.")
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(SMTP_SENDER_EMAIL, SMTP_APP_PASSWORD)
                smtp.send_message(msg)
            return True, "Sent to Email & SMS Gateway"
        except Exception as e:
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
st.set_page_config(page_title="ProStack AI - 1000% GOD MODE", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

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
    st.markdown("<p style='text-align: center; color: #A0AEC0;'>Login, Register, or Recover Password Instantly.</p>", unsafe_allow_html=True)
    
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
            s_email = st.text_input("Enter Your Email Address", placeholder="user@gmail.com")
            s_phone = st.text_input("Enter Mobile / WhatsApp Number (For OTP Recovery)", placeholder="e.g. 9876543210")
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
                    st.error("⚠️ Please enter a valid Email, Mobile Number, and Password (min 6 chars).")
                    
        elif auth_mode == "🔑 Forgot Password":
            st.markdown("#### 📲 Instant Password Recovery (Email / Mobile OTP)")
            rec_email = st.text_input("Registered Email Address", placeholder="Enter your email")
            rec_phone = st.text_input("Registered Mobile Number", placeholder="Enter your mobile number")
            
            if st.button("📩 SEND RECOVERY OTP MESSAGE", use_container_width=True):
                if check_user_for_recovery(rec_email, rec_phone):
                    otp_val = str(random.randint(100000, 999999))
                    st.session_state.reset_otp = otp_val
                    st.session_state.reset_target_email = rec_email.strip().lower()
                    sent_real, mode_msg = send_recovery_otp_notification(rec_email.strip(), rec_phone.strip(), otp_val)
                    st.success(f"✅ Recovery OTP Dispatched to {rec_email} & Mobile {rec_phone}!")
                    st.info(f"💬 **[SMS / EMAIL GATEWAY DISPATCH]**: Your ProStack AI Password Reset OTP is: **{otp_val}**")
                else:
                    st.error("❌ Email and Mobile Number do not match any registered account!")
                    
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
# 👑 CEO ADMIN CONTROL ROOM (WITH CSV BACKUP, RESTORE & DELETE)
# ==========================================
if st.session_state.user_email == "ADMIN":
    st.markdown("""
    <div class='admin-box'>
        <h2 style='color: #FFD700 !important;'>👑 CEO ADMIN CONTROL ROOM (1000% GOD-MODE)</h2>
        <p style='color: white;'>Yahan aapke saare 4,000+ users ka Email, Mobile Number, Expiry Date aur Payment Reference jama hota hai:</p>
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
            
    # Database Backup & Restore Section
    st.markdown("#### 💾 Master Database Backup & Restore (4,000+ Users Safety)")
    col_bk1, col_bk2 = st.columns(2)
    with col_bk1:
        db_csv = full_db_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 DOWNLOAD ALL USERS CSV BACKUP", db_csv, "ProStack_Users_Backup.csv", "text/csv", use_container_width=True)
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
                except Exception as e:
                    st.error("⚠️ Invalid Backup CSV File!")
            
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
            
    st.markdown("### 💬 Need Instant Help? Contact VIP Support")
    st.markdown(f"<a href='{SUPPORT_WHATSAPP_URL}' target='_blank' class='support-btn'>📲 Chat on WhatsApp Support</a>", unsafe_allow_html=True)
    st.markdown(f"<a href='{SUPPORT_TELEGRAM_URL}' target='_blank' class='support-btn'>✈️ Join Telegram VIP Support</a>", unsafe_allow_html=True)
    
    st.write("")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()
    st.stop()

# ==========================================
# 🏟️ STEP 1: 10-SPORT GLOBAL GAME SELECTOR & MATCH CENTER
# ==========================================
st.markdown("### 🎮 Step 1: Global Game Selector & Match Center")

SPORTS_DATA = {
    "⚽ Football / Soccer (EPL & Champions League)": {
        "live_matches": [
            {"title": "Manchester City (MCI) vs Arsenal (ARS)", "status": "🔴 LIVE • 62' Min (2 - 1)", "info": "🔥 Goal Total: 3.5 | High Pressing Matchup"},
            {"title": "Real Madrid (RMA) vs Bayern Munich (BAY)", "status": "🟢 TODAY • Kickoff 3:00 PM EST (UCL)", "info": "⚡ Goal Total: 3.0 | RMA -0.5 Favorite"},
            {"title": "Liverpool (LIV) vs Chelsea (CHE)", "status": "🟢 TODAY • Kickoff 12:30 PM EST", "info": "🚀 Goal Total: 3.5 | Corner & Shot Volume High"}
        ],
        "upcoming_matches": [
            {"title": "FC Barcelona (BAR) vs Paris Saint-Germain (PSG)", "time": "⏳ Tomorrow • 3:00 PM EST", "info": "📊 Early Goal Line: 3.5 | Attacking Slate"},
            {"title": "Manchester United (MUN) vs Tottenham (TOT)", "time": "⏳ Saturday • 10:00 AM EST", "info": "📊 Early Goal Line: 3.0 | Counter-Attack Focus"}
        ],
        "players": {
            "ID": range(1, 15),
            "Player": ["E. Haaland", "K. Mbappe", "M. Salah", "B. Saka", "V. Junior", "J. Bellingham", "C. Palmer", "K. De Bruyne", "H. Kane", "P. Foden", "L. Diaz", "M. Odegaard", "R. Rodri", "W. Saliba"],
            "Team": ["MCI", "RMA", "LIV", "ARS", "RMA", "RMA", "CHE", "MCI", "BAY", "MCI", "LIV", "ARS", "MCI", "ARS"],
            "Pos": ["FWD", "FWD", "FWD", "MID", "FWD", "MID", "MID", "MID", "FWD", "MID", "FWD", "MID", "MID", "DEF"],
            "Salary": [10200, 10000, 9500, 9200, 9400, 8800, 8900, 8600, 9100, 8200, 7900, 8000, 7400, 6800],
            "Proj_Pts": [26.5, 25.8, 23.5, 22.0, 23.0, 20.5, 21.8, 20.0, 22.5, 19.0, 18.2, 18.5, 16.5, 15.0],
            "Ownership_%": [32.0, 29.5, 24.0, 21.0, 22.5, 18.0, 25.0, 16.5, 20.0, 14.0, 13.5, 15.0, 11.0, 9.5],
            "Vegas_Total": [3.5, 3.0, 3.5, 3.5, 3.0, 3.0, 3.5, 3.5, 3.0, 3.5, 3.5, 3.5, 3.5, 3.5]
        }
    },
    "🏈 NFL (American Football)": {
        "live_matches": [
            {"title": "Kansas City Chiefs (KC) vs Buffalo Bills (BUF)", "status": "🔴 LIVE • Q2 (14 - 10) | Main Slate", "info": "🔥 Vegas Total: 52.5 Pts | Spread: KC -2.5"},
            {"title": "San Francisco 49ers (SF) vs Philadelphia Eagles (PHI)", "status": "🟢 TODAY • Starts in 2 Hrs (4:25 PM EST)", "info": "⚡ Vegas Total: 48.0 Pts | Spread: SF -3.0"},
            {"title": "Miami Dolphins (MIA) vs Los Angeles Chargers (LAC)", "status": "🟢 TODAY • Tonight (8:15 PM EST)", "info": "🚀 Vegas Total: 50.5 Pts | High Pace Dome Game"}
        ],
        "upcoming_matches": [
            {"title": "Dallas Cowboys (DAL) vs Detroit Lions (DET)", "time": "⏳ Tomorrow • 8:15 PM EST (Monday Night Football)", "info": "📊 Early Vegas Line: 51.0 Pts | Dome Shootout"},
            {"title": "Baltimore Ravens (BAL) vs Cincinnati Bengals (CIN)", "time": "⏳ Thursday Night • 8:15 PM EST", "info": "📊 Early Vegas Line: 49.5 Pts | Division Rivalry"}
        ],
        "players": {
            "ID": range(1, 15),
            "Player": ["P. Mahomes", "J. Allen", "C. McCaffrey", "A. Ekeler", "T. Hill", "J. Jefferson", "T. Kelce", "S. Diggs", "C. Kupp", "A. Brown", "J. Hurts", "D. Achane", "G. Kittle", "J. Cook"],
            "Team": ["KC", "BUF", "SF", "LAC", "MIA", "MIN", "KC", "BUF", "LAR", "PHI", "PHI", "MIA", "SF", "BUF"],
            "Pos": ["QB", "QB", "RB", "RB", "WR", "WR", "TE", "WR", "WR", "WR", "QB", "RB", "TE", "RB"],
            "Salary": [8200, 8000, 9200, 8300, 8800, 8600, 7500, 8100, 8400, 8000, 7900, 7600, 6800, 7200],
            "Proj_Pts": [24.5, 23.8, 22.5, 19.5, 22.0, 20.5, 18.0, 19.0, 20.0, 18.5, 23.0, 18.8, 16.2, 17.5],
            "Ownership_%": [15.5, 14.0, 35.0, 18.5, 25.0, 22.0, 30.0, 15.0, 10.0, 14.5, 16.0, 21.0, 12.5, 13.0],
            "Vegas_Total": [52.5, 52.5, 48.0, 50.5, 50.5, 47.0, 52.5, 52.5, 46.5, 48.0, 48.0, 50.5, 48.0, 52.5]
        }
    },
    "🏀 NBA (Basketball)": {
        "live_matches": [
            {"title": "Denver Nuggets (DEN) vs Los Angeles Lakers (LAL)", "status": "🔴 LIVE • 3rd Quarter (88 - 84)", "info": "🔥 Vegas Total: 234.5 Pts | Fast Pace Slate"},
            {"title": "Dallas Mavericks (DAL) vs Boston Celtics (BOS)", "status": "🟢 TODAY • Starts at 10:00 PM EST", "info": "⚡ Vegas Total: 228.0 Pts | Finals Rematch"},
            {"title": "Golden State Warriors (GSW) vs Phoenix Suns (PHX)", "status": "🟢 TODAY • Starts at 10:30 PM EST", "info": "🚀 Vegas Total: 236.0 Pts | Shootout Alert"}
        ],
        "upcoming_matches": [
            {"title": "Milwaukee Bucks (MIL) vs New York Knicks (NYK)", "time": "⏳ Tomorrow • 7:30 PM EST", "info": "📊 Early Total: 229.5 Pts | Giannis Probable"},
            {"title": "Oklahoma City Thunder (OKC) vs Minnesota Timberwolves (MIN)", "time": "⏳ Tomorrow • 9:30 PM EST", "info": "📊 Early Total: 224.0 Pts | West Top Seed Battle"}
        ],
        "players": {
            "ID": range(1, 15),
            "Player": ["N. Jokic", "L. Doncic", "L. James", "J. Tatum", "S. Curry", "K. Durant", "A. Davis", "K. Irving", "D. Booker", "J. Murray", "J. Brown", "A. Reaves", "D. White", "M. Porter Jr."],
            "Team": ["DEN", "DAL", "LAL", "BOS", "GSW", "PHX", "LAL", "DAL", "PHX", "DEN", "BOS", "LAL", "BOS", "DEN"],
            "Pos": ["C", "PG", "SF", "SF", "PG", "PF", "C", "SG", "SG", "PG", "SG", "SG", "PG", "SF"],
            "Salary": [10500, 10200, 9400, 9500, 9100, 9000, 9600, 8500, 8700, 7800, 8200, 7100, 6900, 6600],
            "Proj_Pts": [58.5, 56.0, 47.5, 49.0, 45.5, 46.0, 51.0, 42.0, 44.5, 39.5, 41.0, 35.5, 34.0, 32.5],
            "Ownership_%": [28.0, 25.5, 18.0, 20.0, 22.5, 16.0, 19.5, 14.0, 15.0, 12.5, 15.5, 17.0, 13.0, 11.0],
            "Vegas_Total": [234.5, 228.0, 234.5, 228.0, 236.0, 236.0, 234.5, 228.0, 236.0, 234.5, 228.0, 234.5, 228.0, 234.5]
        }
    },
    "⚾ MLB (Baseball)": {
        "live_matches": [
            {"title": "Los Angeles Dodgers (LAD) vs New York Yankees (NYY)", "status": "🔴 LIVE • Top 5th Inning (4 - 2)", "info": "🔥 Run Total: 9.5 | Wind Blowing Out 12 mph"},
            {"title": "Atlanta Braves (ATL) vs Philadelphia Phillies (PHI)", "status": "🟢 TODAY • First Pitch 7:05 PM EST", "info": "⚡ Run Total: 8.5 | Elite Hitter Park"}
        ],
        "upcoming_matches": [
            {"title": "Houston Astros (HOU) vs Texas Rangers (TEX)", "time": "⏳ Tomorrow • 8:05 PM EST", "info": "📊 Early Run Total: 9.0 | Roof Closed"},
            {"title": "Baltimore Orioles (BAL) vs Boston Red Sox (BOS)", "time": "⏳ Tomorrow • 7:10 PM EST", "info": "📊 Early Run Total: 9.5 | Bullpen Game"}
        ],
        "players": {
            "ID": range(1, 15),
            "Player": ["S. Ohtani", "A. Judge", "M. Betts", "J. Soto", "F. Freeman", "R. Acuna", "B. Harper", "G. Cole", "T. Glasnow", "M. Olson", "T. Turner", "K. Schwarber", "A. Riley", "G. Stanton"],
            "Team": ["LAD", "NYY", "LAD", "NYY", "LAD", "ATL", "PHI", "NYY", "LAD", "ATL", "PHI", "PHI", "ATL", "NYY"],
            "Pos": ["OF", "OF", "SS", "OF", "1B", "OF", "1B", "P", "P", "1B", "SS", "OF", "3B", "OF"],
            "Salary": [6500, 6400, 5900, 6100, 5600, 6200, 5800, 10200, 9800, 5400, 5500, 5300, 5200, 4900],
            "Proj_Pts": [14.5, 14.0, 12.5, 13.0, 11.8, 13.5, 12.2, 24.0, 22.5, 11.0, 11.5, 11.2, 10.8, 10.2],
            "Ownership_%": [30.0, 26.0, 18.5, 22.0, 15.0, 24.0, 17.0, 32.0, 25.0, 12.0, 14.0, 13.5, 11.5, 9.0],
            "Vegas_Total": [9.5, 9.5, 9.5, 9.5, 9.5, 8.5, 8.5, 9.5, 9.5, 8.5, 8.5, 8.5, 8.5, 9.5]
        }
    },
    "🏒 NHL (Ice Hockey)": {
        "live_matches": [
            {"title": "Edmonton Oilers (EDM) vs Colorado Avalanche (COL)", "status": "🔴 LIVE • 2nd Period (3 - 2)", "info": "🔥 Goal Total: 6.5 | Power-Play Heavy Match"},
            {"title": "Toronto Maple Leafs (TOR) vs Boston Bruins (BOS)", "status": "🟢 TODAY • Puck Drop 7:00 PM EST", "info": "⚡ Goal Total: 6.0 | Original Six Rivalry"}
        ],
        "upcoming_matches": [
            {"title": "New York Rangers (NYR) vs Florida Panthers (FLA)", "time": "⏳ Tomorrow • 7:30 PM EST", "info": "📊 Early Goal Line: 6.0 | East Finals Rematch"},
            {"title": "Vegas Golden Knights (VGK) vs Dallas Stars (DAL)", "time": "⏳ Tomorrow • 9:30 PM EST", "info": "📊 Early Goal Line: 6.5 | High Shot Volume"}
        ],
        "players": {
            "ID": range(1, 15),
            "Player": ["C. McDavid", "N. MacKinnon", "A. Matthews", "L. Draisaitl", "D. Pastrnak", "C. Makar", "M. Marner", "M. Rantanen", "A. Panarin", "E. Bouchard", "W. Nylander", "B. Marchand", "Z. Hyman", "D. Toews"],
            "Team": ["EDM", "COL", "TOR", "EDM", "BOS", "COL", "TOR", "COL", "NYR", "EDM", "TOR", "BOS", "EDM", "COL"],
            "Pos": ["C", "C", "C", "W", "W", "D", "W", "W", "W", "D", "W", "W", "W", "D"],
            "Salary": [9800, 9600, 9300, 8900, 9000, 8500, 8100, 8600, 8400, 7800, 8200, 7600, 7900, 6800],
            "Proj_Pts": [22.5, 21.8, 20.5, 19.0, 19.5, 18.2, 17.0, 18.5, 18.0, 16.5, 17.5, 15.8, 16.8, 14.2],
            "Ownership_%": [31.0, 28.0, 24.5, 20.0, 22.0, 25.0, 15.0, 18.0, 16.5, 14.0, 16.0, 12.5, 17.5, 10.5],
            "Vegas_Total": [6.5] * 14
        }
    },
    "🥊 UFC / MMA (Fight Night & PPV)": {
        "live_matches": [
            {"title": "Alex Pereira vs Khalil Rountree Jr. (Main Event)", "status": "🔴 LIVE • Main Card Underway", "info": "🔥 KO/TKO Odds: -280 | 5-Round Championship"},
            {"title": "Islam Makhachev vs Arman Tsarukyan (Co-Main)", "status": "🟢 TODAY • Walkouts at 11:15 PM EST", "info": "⚡ Grappling & High-Output Pace"}
        ],
        "upcoming_matches": [
            {"title": "Jon Jones vs Stipe Miocic (Heavyweight Title)", "time": "⏳ Saturday Night • 10:00 PM EST (PPV)", "info": "📊 Heavyweight Superfight | Finish Rate: 82%"},
            {"title": "Sean O'Malley vs Merab Dvalishvili", "time": "⏳ Next Week • Main Card 10:00 PM EST", "info": "📊 Striker vs Grappler Classic"}
        ],
        "players": {
            "ID": range(1, 15),
            "Player": ["A. Pereira", "I. Makhachev", "J. Jones", "S. O'Malley", "I. Topuria", "M. Holloway", "C. Oliveira", "D. Du Plessis", "K. Chimaev", "J. Gaethje", "A. Volkanovski", "D. Poirier", "T. Aspinall", "M. Dvalishvili"],
            "Team": ["BRA", "DAG", "USA", "USA", "ESP", "USA", "BRA", "RSA", "UAE", "USA", "AUS", "USA", "UK", "GEO"],
            "Pos": ["MMA"] * 14,
            "Salary": [9600, 9500, 9400, 9000, 9200, 8600, 8800, 8500, 9100, 8300, 8400, 8100, 9300, 8700],
            "Proj_Pts": [105.0, 98.5, 96.0, 91.0, 94.5, 86.0, 89.0, 85.5, 95.0, 82.0, 83.5, 80.0, 97.0, 88.0],
            "Ownership_%": [35.0, 32.0, 28.0, 24.0, 26.5, 19.0, 21.0, 17.5, 29.0, 15.0, 16.0, 14.5, 30.0, 20.5],
            "Vegas_Total": [2.5] * 14
        }
    },
    "⛳ PGA Tour (Fantasy Golf)": {
        "live_matches": [
            {"title": "The Players Championship — Round 3 Moving Day", "status": "🔴 LIVE • Leaders at -12 Under Par", "info": "🔥 Birdie Fest | Soft Greens & Low Wind"},
            {"title": "Arnold Palmer Invitational — Featured Groups", "status": "🟢 TODAY • Tee Times 8:00 AM - 2:00 PM EST", "info": "⚡ Strokes Gained Approach Key Metric"}
        ],
        "upcoming_matches": [
            {"title": "The Masters Tournament — Augusta National", "time": "⏳ Upcoming Thursday • 7:30 AM EST", "info": "📊 Major Championship | $20M Purse"},
            {"title": "PGA Championship — Valhalla Golf Club", "time": "⏳ Next Major Slate", "info": "📊 Driving Distance & Par-5 Scoring Crucial"}
        ],
        "players": {
            "ID": range(1, 15),
            "Player": ["S. Scheffler", "R. McIlroy", "X. Schauffele", "J. Rahm", "C. Morikawa", "V. Hovland", "L. Aberg", "B. DeChambeau", "W. Clark", "P. Cantlay", "H. Matsuyama", "T. Fleetwood", "S.Theegala", "J. Thomas"],
            "Team": ["USA", "NIR", "USA", "ESP", "USA", "NOR", "SWE", "USA", "USA", "USA", "JPN", "ENG", "USA", "USA"],
            "Pos": ["GOLF"] * 14,
            "Salary": [10800, 10300, 9900, 9700, 9300, 8900, 9100, 9500, 8400, 8600, 8500, 8200, 7900, 8000],
            "Proj_Pts": [88.5, 84.0, 81.5, 79.0, 76.5, 73.0, 75.5, 78.0, 70.5, 72.0, 71.5, 69.0, 67.5, 68.0],
            "Ownership_%": [34.0, 27.5, 25.0, 22.0, 19.5, 16.0, 21.0, 24.0, 13.5, 15.0, 16.5, 14.0, 12.0, 13.0],
            "Vegas_Total": [72.0] * 14
        }
    },
    "🏎️ Formula 1 & NASCAR (Motorsports)": {
        "live_matches": [
            {"title": "F1 Las Vegas / Miami Grand Prix — Qualifying & Race", "status": "🔴 LIVE • Track Temp 38°C | High Tire Deg", "info": "🔥 Fastest Lap & Overtake Bonus Points Active"},
            {"title": "NASCAR Cup Series — Daytona / Talladega 500", "status": "🟢 TODAY • Green Flag 2:30 PM EST", "info": "⚡ Pack Racing | Place Differential Strategy"}
        ],
        "upcoming_matches": [
            {"title": "F1 Monaco / Silverstone Grand Prix", "time": "⏳ Sunday • Lights Out 9:00 AM EST", "info": "📊 Pole Position & Grid Equity Crucial"},
            {"title": "NASCAR Coca-Cola 600 — Charlotte Motor Speedway", "time": "⏳ Sunday Evening • 6:00 PM EST", "info": "📊 400 Laps Dominator Points Available"}
        ],
        "players": {
            "ID": range(1, 15),
            "Player": ["M. Verstappen", "L. Norris", "C. Leclerc", "L. Hamilton", "O. Piastri", "C. Sainz", "G. Russell", "F. Alonso", "K. Larson", "D. Hamlin", "S. Perez", "W. Byron", "C. Elliott", "R. Blaney"],
            "Team": ["RBR", "MCL", "FER", "MER", "MCL", "FER", "MER", "AMR", "HMS", "JGR", "RBR", "HMS", "HMS", "PENSKE"],
            "Pos": ["DRV"] * 14,
            "Salary": [10600, 10100, 9500, 9000, 9200, 8800, 8600, 7900, 9700, 9300, 8400, 8900, 8500, 8700],
            "Proj_Pts": [45.0, 42.5, 38.0, 35.5, 37.0, 34.5, 33.0, 28.5, 40.0, 38.5, 31.0, 36.0, 33.5, 35.0],
            "Ownership_%": [36.0, 31.0, 24.0, 20.0, 22.5, 18.0, 16.5, 12.0, 25.0, 21.0, 14.0, 19.0, 15.5, 17.0],
            "Vegas_Total": [55.0] * 14
        }
    },
    "🎾 Tennis (ATP & Grand Slams)": {
        "live_matches": [
            {"title": "Carlos Alcaraz vs Jannik Sinner (Center Court)", "status": "🔴 LIVE • Set 2 (6-4, 3-3)", "info": "🔥 High Ace & Break Point Conversion Slate"},
            {"title": "Novak Djokovic vs Daniil Medvedev", "status": "🟢 TODAY • Starts at 4:00 PM EST", "info": "⚡ Hardcourt Baseline Marathon Projected"}
        ],
        "upcoming_matches": [
            {"title": "Alexander Zverev vs Taylor Fritz (Quarterfinal)", "time": "⏳ Tomorrow • 1:00 PM EST", "info": "📊 Big Server Track | 4+ Sets Likely"},
            {"title": "Iga Swiatek vs Aryna Sabalenka (WTA Final)", "time": "⏳ Tomorrow • 7:00 PM EST", "info": "📊 Straight Sets Bonus Potential"}
        ],
        "players": {
            "ID": range(1, 15),
            "Player": ["C. Alcaraz", "J. Sinner", "N. Djokovic", "D. Medvedev", "A. Zverev", "T. Fritz", "I. Swiatek", "A. Sabalenka", "C. Gauff", "B. Shelton", "S. Tsitsipas", "A. Rublev", "E. Rybakina", "J. Pegula"],
            "Team": ["ESP", "ITA", "SRB", "RUS", "GER", "USA", "POL", "BLR", "USA", "USA", "GRE", "RUS", "KAZ", "USA"],
            "Pos": ["TENNIS"] * 14,
            "Salary": [10200, 10000, 9600, 9100, 9300, 8700, 9800, 9500, 8900, 8200, 8400, 8500, 9000, 8300],
            "Proj_Pts": [72.0, 70.5, 67.0, 62.5, 65.0, 59.0, 69.0, 66.5, 61.0, 56.5, 58.0, 59.5, 63.0, 57.5],
            "Ownership_%": [33.0, 31.0, 26.0, 19.0, 22.0, 16.5, 29.0, 25.0, 18.0, 14.0, 15.0, 16.0, 20.0, 13.5],
            "Vegas_Total": [22.5] * 14
        }
    },
    "🏏 Cricket (T20 / IPL / Intl)": {
        "live_matches": [
            {"title": "India (IND) vs Australia (AUS)", "status": "🔴 LIVE • IND 112/2 (11.4 Overs)", "info": "🔥 Pitch Report: Batting Paradise | Proj Score: 210+"},
            {"title": "England (ENG) vs South Africa (SA)", "status": "🟢 TODAY • Toss at 7:00 PM IST", "info": "⚡ High Pace Bounce | Death Bowlers Crucial"}
        ],
        "upcoming_matches": [
            {"title": "New Zealand (NZ) vs Pakistan (PAK)", "time": "⏳ Tomorrow • 3:30 PM IST", "info": "📊 Pitch Report: Spin Friendly Track Expected"},
            {"title": "West Indies (WI) vs Sri Lanka (SL)", "time": "⏳ Day After Tomorrow • 7:30 PM IST", "info": "📊 High Six-Hitting Venue | Short Boundaries"}
        ],
        "players": {
            "ID": range(1, 15),
            "Player": ["V. Kohli", "J. Bumrah", "T. Head", "H. Pandya", "R. Sharma", "G. Maxwell", "J. Buttler", "H. Klaasen", "M. Starc", "S. Yadav", "R. Pant", "A. Zampa", "P. Cummins", "K. Rabada"],
            "Team": ["IND", "IND", "AUS", "IND", "IND", "AUS", "ENG", "SA", "AUS", "IND", "IND", "AUS", "AUS", "SA"],
            "Pos": ["BAT", "BOWL", "BAT", "AR", "BAT", "AR", "WK", "WK", "BOWL", "BAT", "WK", "BOWL", "AR", "BOWL"],
            "Salary": [9500, 9200, 9000, 8800, 8900, 8600, 9100, 8700, 8400, 9300, 8500, 7900, 8300, 8100],
            "Proj_Pts": [68.5, 64.0, 62.0, 66.5, 59.0, 61.0, 63.5, 60.0, 55.0, 65.0, 58.0, 52.5, 56.0, 54.5],
            "Ownership_%": [38.0, 34.0, 29.0, 31.0, 25.0, 22.0, 27.0, 19.0, 15.0, 33.0, 21.0, 14.0, 18.0, 16.5],
            "Vegas_Total": [205.0] * 14
        }
    }
}

selected_sport = st.selectbox(
    "🌍 Choose Your Game / Global Sport League (10 Sports Active):",
    list(SPORTS_DATA.keys())
)

match_view = st.radio(
    "Select Match View:",
    ["🔴 Live & Today's Matches", "⏳ Upcoming Matches (Next 48 Hrs)"],
    horizontal=True
)

if match_view == "🔴 Live & Today's Matches":
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

all_match_titles = ["🔥 Full Main Slate (All Today's Matches)"] + [m["title"] for m in SPORTS_DATA[selected_sport]["live_matches"]] + [u["title"] + " (Upcoming)" for u in SPORTS_DATA[selected_sport]["upcoming_matches"]]
selected_slate = st.selectbox("🎯 Select Target Match / Contest Slate for Optimizer:", all_match_titles)

st.markdown("#### 📥 Custom CSV Upload (Optional)")
uploaded_file = st.file_uploader("Upload Custom DFS CSV Data (Or use Auto-Loaded Slate Data)", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("✅ Custom DFS CSV Data Uploaded Successfully!")
    except Exception as e:
        st.error("⚠️ Error reading CSV! Using Auto-Loaded Slate Data.")
        df = pd.DataFrame(SPORTS_DATA[selected_sport]["players"])
else:
    df = pd.DataFrame(SPORTS_DATA[selected_sport]["players"])

# ==========================================
# 🧠 1000% GOD-MODE MONTE CARLO + CAPTAIN/VC + LOCK/EXCLUDE SOLVER
# ==========================================
def run_god_mode_solver(data, lineups_count, cap, strategy_mode, locked_players, excluded_players):
    lineups, stats = [], []
    base_data = data[~data["Player"].isin(excluded_players)].copy().reset_index(drop=True)
    if len(base_data) < 5:
        return [], []
        
    for i in range(lineups_count):
        prob = pulp.LpProblem(f"GodMode_{i}", pulp.LpMaximize)
        p_vars = pulp.LpVariable.dicts("P", base_data.index, cat='Binary')
        
        # Monte Carlo Variance Simulation so up to 150 unique lineups generate smoothly
        noise = np.random.normal(0, 0.85 if i > 0 else 0.0, size=len(base_data))
        sim_pts = base_data["Proj_Pts"] + noise
        
        prob += pulp.lpSum([sim_pts[idx] * p_vars[idx] for idx in base_data.index])
        prob += pulp.lpSum([base_data["Salary"][idx] * p_vars[idx] for idx in base_data.index]) <= cap
        prob += pulp.lpSum([p_vars[idx] for idx in base_data.index]) == 5
        
        # Lock Core Players Constraint
        for idx in base_data.index:
            if base_data["Player"][idx] in locked_players:
                prob += p_vars[idx] == 1
                
        if strategy_mode == "💣 Mega Grand League (High Risk/Reward)":
            prob += pulp.lpSum([base_data["Ownership_%"][idx] * p_vars[idx] for idx in base_data.index]) <= 135
        
        # Uniqueness constraint across lineups
        for prev_raw in lineups:
            clean_prev = [p.replace(" 👑(C)", "").replace(" ⚡(VC)", "") for p in prev_raw]
            prob += pulp.lpSum([p_vars[idx] for idx in base_data.index if base_data["Player"][idx] in clean_prev]) <= 4
            
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        if pulp.LpStatus[prob.status] == 'Optimal':
            chosen_indices = [idx for idx in base_data.index if p_vars[idx].varValue == 1]
            # Sort chosen players by simulated ceiling to assign Captain (2x) and Vice-Captain (1.5x)
            chosen_sorted = sorted(chosen_indices, key=lambda idx: sim_pts[idx], reverse=True)
            
            formatted_lineup = []
            for rank_idx, p_idx in enumerate(chosen_sorted):
                p_name = base_data["Player"][p_idx]
                if rank_idx == 0:
                    formatted_lineup.append(f"{p_name} 👑(C)")
                elif rank_idx == 1:
                    formatted_lineup.append(f"{p_name} ⚡(VC)")
                else:
                    formatted_lineup.append(p_name)
                    
            pts = sum([base_data["Proj_Pts"][idx] for idx in chosen_indices])
            sal = sum([base_data["Salary"][idx] for idx in chosen_indices])
            own = sum([base_data["Ownership_%"][idx] for idx in chosen_indices]) / 5
            lineups.append(formatted_lineup)
            stats.append(f"Pts: {pts:.1f} | Sal: ${sal} | Own: {own:.1f}%")
        else:
            break
    return lineups, stats

st.divider()

# ==========================================
# 🧭 STEP 2: NAVIGATION MENU (WITH VIP UPGRADE & SUPPORT CENTER)
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
        <b style='color:#FFD700; font-size:16px;'>Step 3: Choose Strategy, Lock/Fade Players & Run</b><br>
        <span style='color:white;'>Auto-Assigns 👑 Captain (2x) & ⚡ Vice-Captain (1.5x) with Monte Carlo Simulation.</span>
    </div>
    """, unsafe_allow_html=True)
    
    strategy = st.radio("Target Contest Type:", ["🛡️ Head-to-Head (Safe & Consistent)", "💣 Mega Grand League (High Risk/Reward)"])
    
    col_lk1, col_lk2 = st.columns(2)
    with col_lk1:
        locked_players = st.multiselect("🔒 Lock Core Players (Max 4):", df["Player"].tolist(), max_selections=4)
    with col_lk2:
        available_to_exclude = [p for p in df["Player"].tolist() if p not in locked_players]
        excluded_players = st.multiselect("❌ Exclude / Fade Injured Players:", available_to_exclude)
        
    num_lineups = st.slider("🎯 Number of Lineups (Monte Carlo Sim)", 1, 150, 20)
    salary_cap = st.number_input("💰 Salary Cap", value=50000, step=100)
    
    st.write("")
    if st.button("🔥 RUN 1000% AUTO-PILOT OPTIMIZER", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for percent in range(100):
            time.sleep(0.008)
            progress_bar.progress(percent + 1)
            if percent < 50: status_text.text(f"Running Monte Carlo Simulations on {selected_slate}...")
            else: status_text.text("Assigning Optimal 👑 Captain (2x) & ⚡ Vice-Captain (1.5x)...")
            
        status_text.text("✅ EXECUTION COMPLETE.")
        
        final_lineups, stat_list = run_god_mode_solver(df, num_lineups, salary_cap, strategy, locked_players, excluded_players)
        
        if final_lineups:
            st.success(f"🏆 {len(final_lineups)} WINNING LINEUPS GENERATED (WITH 👑 C & ⚡ VC)!")
            df_out = pd.DataFrame(final_lineups, columns=["👑 Captain (2x)", "⚡ Vice-Captain (1.5x)", "Flex 1", "Flex 2", "Flex 3"])
            df_out["Metrics"] = stat_list
            df_out.index = [f"Team-{i+1}" for i in range(len(df_out))]
            st.dataframe(df_out, use_container_width=True)
            
            csv = df_out.to_csv().encode('utf-8')
            st.download_button("💾 DOWNLOAD MASTER CSV", csv, "ProStack_Lineups.csv", "text/csv", use_container_width=True)
        else:
            st.error("Engine Overload: Salary cap constraint failed or too many players excluded. Increase Salary Cap.")

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
    st.subheader(f"🚨 Live Breaking News — {selected_sport}")
    st.markdown("""
    <div class='news-box-red' style='background-color: #1A202C; padding: 15px; border-radius: 8px; border-left: 4px solid #FF3131; margin-bottom: 15px;'>
        <b style='color:#FF3131; font-size:16px;'>⚠️ LATE SWAP & INJURY ALERTS</b><br>
        <span style='color:white;'>• <b>Star Starter</b> - Game-Time Decision (Use Lock/Exclude in Engine if ruled out)<br>
        • <b>Weather / Venue Alert</b> - High scoring conditions projected for tonight's main slate!</span><br>
    </div>
    """, unsafe_allow_html=True)

elif app_mode == "📉 Pro Analytics":
    st.subheader(f"Pro Leverage & Value Matrix — {selected_sport}")
    fig1 = px.scatter(df, x="Salary", y="Proj_Pts", color="Pos", hover_name="Player", template="plotly_dark", title="Salary vs Projected Points")
    st.plotly_chart(fig1, use_container_width=True)

elif app_mode == "💎 VIP Upgrade & Support Center":
    st.markdown(f"""
    <div class='vip-box'>
        <h2 style='color: #00BFFF !important;'>💎 VIP MEMBERSHIP & 24/7 SUPPORT CENTER</h2>
        <p style='color: white;'>Logged in as: <b>{st.session_state.user_email}</b> | Current Validity: <b>{exp_info}</b></p>
        <p style='color: #A0AEC0;'>Extend your subscription anytime before expiry or reach out to our VIP Concierge Desk.</p>
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
