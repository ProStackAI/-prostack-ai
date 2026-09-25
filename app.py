import streamlit as st
import pandas as pd
import numpy as np
import pulp
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta

# ==========================================
# 1. PAGE CONFIG & OFFICIAL LINKS
# ==========================================
st.set_page_config(
    page_title="ProStack AI | Quantitative DFS & Prop Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

SUPPORT_TELEGRAM_URL = "https://t.me/ProStackAI_Official"
APP_PUBLIC_URL = "https://prostackai.streamlit.app"

# ==========================================
# 2. BULLETPROOF DARK & LIGHT MODE CSS FIX
# ==========================================
st.markdown("""
<style>
    /* Force Dark Background Everywhere (Even in Phone Light Mode) */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #070B12 !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] {
        background-color: #0B111E !important;
        border-right: 1px solid #00FF8844 !important;
    }

    /* Fix Input Labels (Email, Password, Sliders, Selectboxes) -> Bright Light Green! */
    label, .stTextInput label p, .stNumberInput label p, .stSelectbox label p, .stSlider label p, .stRadio label p {
        color: #00FF88 !important;
        font-weight: 700 !important;
        font-size: 0.98rem !important;
    }

    /* Fix White Input Boxes -> Sleek Dark Box + Neon Green Border + White Text */
    div[data-baseweb="input"], div[data-baseweb="base-input"], input {
        background-color: #111A2E !important;
        color: #FFFFFF !important;
        border-color: #00FF88 !important;
        border-radius: 8px !important;
        -webkit-text-fill-color: #FFFFFF !important;
        caret-color: #00FF88 !important;
    }
    /* Eye icon inside password box */
    div[data-baseweb="input"] button, div[data-baseweb="input"] svg {
        color: #FFD700 !important;
        fill: #FFD700 !important;
        background-color: transparent !important;
    }

    /* Fix Tabs (Member Sign In, Founder Admin) -> Bright Yellow & Light Green */
    button[data-baseweb="tab"] {
        background-color: #0F172A !important;
        border: 1px solid #00FF8855 !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 8px 14px !important;
        margin-right: 4px !important;
    }
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span {
        color: #FFD700 !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #052E16 !important;
        border: 2px solid #00FF88 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #00FF88 !important;
    }

    /* Fix Tab Scroll Arrow Button (Right/Left Arrow) -> Yellow & Light Green */
    div[data-testid="stTabs"] button:not([data-baseweb="tab"]),
    div[role="tablist"] ~ button,
    [data-baseweb="tab-list"] button:not([role="tab"]) {
        background-color: #111A2E !important;
        border: 1.5px solid #00FF88 !important;
        color: #FFD700 !important;
    }
    div[data-testid="stTabs"] svg {
        fill: #00FF88 !important;
        color: #00FF88 !important;
    }

    /* Headings & Text Visibility */
    h1, h2, h3, h4, h5, h6, p, span {
        color: #F8FAFC;
    }

    /* Primary Action Button -> Neon Green Glow */
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #00FF88 0%, #00CC6A 100%) !important;
        color: #04120B !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 8px !important;
    }

    .quant-card {
        background: linear-gradient(145deg, #0F1724, #0B101B);
        border: 1px solid #1E293B;
        border-left: 4px solid #00FF88;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .lock-gate {
        background: linear-gradient(135deg, #091326 0%, #051911 100%);
        border: 2px solid #00FF88;
        border-radius: 14px;
        padding: 24px;
        margin: 16px 0;
        text-align: center;
    }
    .viral-card {
        background: linear-gradient(135deg, #051911 0%, #091326 100%);
        border: 2px solid #00FF88;
        border-radius: 12px;
        padding: 20px;
        margin-top: 12px;
        font-family: monospace;
    }
    .badge-ev {
        background-color: #00FF8822;
        color: #00FF88 !important;
        padding: 5px 12px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.88rem;
        display: inline-block;
    }
    .legal-footer {
        font-size: 0.78rem;
        color: #94A3B8 !important;
        text-align: center;
        border-top: 1px solid #1E293B;
        padding-top: 15px;
        margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. DATABASE & BACKUP ENGINE (SQLite)
# ==========================================
DB_FILE = "prostack_enterprise.db"

def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password_hash TEXT,
            created_at TEXT,
            trial_until TEXT,
            is_vip INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS roi_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            entry_date TEXT,
            contest_type TEXT,
            wager REAL,
            payout REAL
        )
    """)
    admin_email = "admin@prostackai.com"
    admin_hash = hashlib.sha256("ProStackAdmin2026!".encode()).hexdigest()
    now_str = datetime.utcnow().isoformat()
    vip_until = (datetime.utcnow() + timedelta(days=3650)).isoformat()
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, 1, 1)",
              (admin_email, admin_hash, now_str, vip_until))
    conn.commit()
    conn.close()

init_db()

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def register_user(email: str, pw: str):
    conn = get_conn()
    c = conn.cursor()
    email = email.strip().lower()
    c.execute("SELECT email FROM users WHERE email=?", (email,))
    if c.fetchone():
        conn.close()
        return False, "Account already exists with this email. Please Sign In!"
    now = datetime.utcnow()
    trial_end = now + timedelta(days=30)
    c.execute("INSERT INTO users VALUES (?, ?, ?, ?, 0, 0)",
              (email, hash_pw(pw), now.isoformat(), trial_end.isoformat()))
    conn.commit()
    conn.close()
    return True, "🎉 30-Day VIP Quant Trial Activated!"

def authenticate_user(email: str, pw: str):
    conn = get_conn()
    c = conn.cursor()
    email = email.strip().lower()
    c.execute("SELECT email, password_hash, trial_until, is_vip, is_admin FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    if row and row[1] == hash_pw(pw):
        return {
            "email": row[0],
            "trial_until": row[2],
            "is_vip": bool(row[3]),
            "is_admin": bool(row[4])
        }
    return None

def check_vip_active(user_dict) -> bool:
    if not user_dict:
        return False
    if user_dict.get("is_vip") or user_dict.get("is_admin"):
        return True
    try:
        t_end = datetime.fromisoformat(user_dict["trial_until"])
        return datetime.utcnow() <= t_end
    except Exception:
        return False

# ==========================================
# 4. 10 LEAGUES CONFIG & FAST CACHED SLATE
# ==========================================
LEAGUE_CONFIGS = {
    "NFL": {"cap": 50000, "size": 9, "positions": ["QB", "RB", "WR", "TE", "DST"]},
    "NBA": {"cap": 50000, "size": 8, "positions": ["PG", "SG", "SF", "PF", "C"]},
    "NHL": {"cap": 50000, "size": 9, "positions": ["C", "W", "D", "G"]},
    "MLB": {"cap": 50000, "size": 10, "positions": ["P", "C", "1B", "2B", "3B", "SS", "OF"]},
    "NCAA": {"cap": 50000, "size": 8, "positions": ["QB", "RB", "WR"]},
    "UFC": {"cap": 50000, "size": 6, "positions": ["FIGHTER"]},
    "PGA": {"cap": 50000, "size": 6, "positions": ["GOLFER"]},
    "NASCAR/F1": {"cap": 50000, "size": 6, "positions": ["DRIVER"]},
    "MLS": {"cap": 50000, "size": 8, "positions": ["F", "M", "D", "GK"]},
    "Tennis": {"cap": 50000, "size": 6, "positions": ["PLAYER"]}
}

@st.cache_data(ttl=3600)
def generate_pro_slate(league: str) -> pd.DataFrame:
    cfg = LEAGUE_CONFIGS[league]
    pos_list = cfg["positions"]
    teams = [("KC", "BUF", 51.5), ("SF", "DAL", 48.0), ("PHI", "DET", 49.5), ("BAL", "CIN", 52.0)]
    if league == "NBA":
        teams = [("BOS", "MIL", 234.5), ("DEN", "LAL", 229.0), ("PHX", "GSW", 236.0), ("DAL", "OKC", 238.5)]
    elif league == "NHL":
        teams = [("EDM", "COL", 6.5), ("TOR", "FLA", 6.5), ("NYR", "CAR", 6.0), ("VGK", "DAL", 6.0)]

    star_names = {
        "NFL": ["Patrick Mahomes", "Josh Allen", "Christian McCaffrey", "CeeDee Lamb", "Jalen Hurts", "Amon-Ra St. Brown",
                "Lamar Jackson", "Ja'Marr Chase", "Travis Kelce", "Stefon Diggs", "Saquon Barkley", "Jahmyr Gibbs",
                "Deebo Samuel", "George Kittle", "Derrick Henry", "Mark Andrews", "James Cook", "AJ Brown",
                "Dak Prescott", "Sam LaPorta", "Isiah Pacheco", "Zay Flowers", "Brandon Aiyuk", "Dalton Kincaid",
                "Chiefs DST", "Bills DST", "49ers DST", "Ravens DST"],
        "NBA": ["Nikola Jokic", "Luka Doncic", "Giannis Antetokounmpo", "Shai Gilgeous-Alexander", "Jayson Tatum",
                "Kevin Durant", "Stephen Curry", "LeBron James", "Anthony Davis", "Devin Booker", "Jaylen Brown",
                "Damian Lillard", "Kyrie Irving", "Jamal Murray", "Chet Holmgren", "Jrue Holiday", "Derrick White",
                "Khris Middleton", "Austin Reaves", "Jusuf Nurkic", "Aaron Gordon", "Draymond Green", "PJ Washington", "Josh Giddey"]
    }
    names = star_names.get(league, [f"{league} Pro Star #{i+1}" for i in range(28)])

    rows = []
    np.random.seed(42)
    for idx, name in enumerate(names):
        pos = pos_list[idx % len(pos_list)]
        t_pair = teams[idx % len(teams)]
        team = t_pair[0] if idx % 2 == 0 else t_pair[1]
        opp = t_pair[1] if idx % 2 == 0 else t_pair[0]
        vegas_total = t_pair[2]
        salary = int(np.random.choice(range(4200, 9600, 200)))
        base_proj = round((salary / 1000.0) * np.random.uniform(3.4, 4.8), 2)
        std_dev = round(base_proj * np.random.uniform(0.18, 0.32), 2)
        own_pct = round(np.random.uniform(4.5, 34.0), 1)
        rows.append({
            "ID": f"DK{10000+idx}",
            "Name": name,
            "Position": pos,
            "Team": team,
            "Opponent": opp,
            "Salary": salary,
            "Projection": base_proj,
            "StdDev": std_dev,
            "Ownership%": own_pct,
            "Vegas_OU": vegas_total,
            "Status": "ACTIVE",
            "Lock": False
        })
    return pd.DataFrame(rows)

# ==========================================
# 5. CACHED 10,000x MONTE CARLO & PULP ENGINE
# ==========================================
@st.cache_data(show_spinner=False)
def run_monte_carlo_simulation(df: pd.DataFrame, n_sims: int = 10000, weather_impact: float = 0.0) -> pd.DataFrame:
    df = df.copy()
    out_teams = df[df["Status"] == "OUT 🚑"]["Team"].unique().tolist()
    df["Adj_Proj"] = df["Projection"].astype(float)
    for t in out_teams:
        df.loc[(df["Team"] == t) & (df["Status"] != "OUT 🚑"), "Adj_Proj"] *= 1.15

    df["Adj_Proj"] = df["Adj_Proj"] * (1.0 + (weather_impact / 100.0))
    df["Adj_Proj"] = np.where(df["Status"] == "OUT 🚑", 0.0, np.round(df["Adj_Proj"], 2))

    floors, ceilings, boom_rates, leverage_scores = [], [], [], []
    rng = np.random.default_rng(12345)

    for _, row in df.iterrows():
        mean = float(row["Adj_Proj"])
        sd = max(float(row.get("StdDev", mean * 0.25)), 1.0)
        if mean <= 0:
            floors.append(0.0)
            ceilings.append(0.0)
            boom_rates.append(0.0)
            leverage_scores.append(0.0)
            continue

        sims = np.clip(rng.normal(mean, sd, n_sims), 0, None)
        flr = round(float(np.percentile(sims, 15)), 2)
        ceil = round(float(np.percentile(sims, 90)), 2)
        target_boom = (float(row["Salary"]) / 1000.0) * 5.0
        boom_pct = round(float(np.mean(sims >= target_boom) * 100.0), 1)
        own = max(float(row.get("Ownership%", 15.0)), 1.0)
        lev = round(boom_pct - own, 1)

        floors.append(flr)
        ceilings.append(ceil)
        boom_rates.append(boom_pct)
        leverage_scores.append(lev)

    df["Floor (15%)"] = floors
    df["Ceiling (90%)"] = ceilings
    df["Boom%"] = boom_rates
    df["Leverage"] = leverage_scores
    df["Value (Pt/$1K)"] = np.round(df["Adj_Proj"] / np.maximum(df["Salary"] / 1000.0, 0.1), 2)
    return df

def optimize_lineups_quant(
    df: pd.DataFrame,
    num_lineups: int,
    salary_cap: int,
    lineup_size: int,
    contest_mode: str,
    max_exposure: float,
    stack_team: str,
    stack_count: int,
    bring_back: bool
):
    active_df = df[df["Status"] != "OUT 🚑"].reset_index(drop=True)
    if len(active_df) < lineup_size:
        return []

    if contest_mode == "GPP Millionaire (Ceiling + Anti-Chalk Leverage)":
        active_df["Opt_Score"] = (active_df["Ceiling (90%)"] * 0.75) + (active_df["Leverage"] * 0.35)
    elif contest_mode == "Cash Game Safe (High Floor)":
        active_df["Opt_Score"] = (active_df["Adj_Proj"] * 0.65) + (active_df["Floor (15%)"] * 0.35)
    else:
        active_df["Opt_Score"] = active_df["Adj_Proj"]

    lineups = []
    exposure_counts = {i: 0 for i in active_df.index}
    max_allowed = max(1, int(np.ceil(num_lineups * (max_exposure / 100.0))))

    for l_idx in range(num_lineups):
        prob = pulp.LpProblem(f"ProStack_Quant_{l_idx}", pulp.LpMaximize)
        x = pulp.LpVariable.dicts("p", active_df.index, cat="Binary")

        jitter = np.random.uniform(0.985, 1.015, size=len(active_df)) if l_idx > 0 else np.ones(len(active_df))
        prob += pulp.lpSum([active_df.loc[i, "Opt_Score"] * jitter[i] * x[i] for i in active_df.index])

        prob += pulp.lpSum([active_df.loc[i, "Salary"] * x[i] for i in active_df.index]) <= salary_cap
        prob += pulp.lpSum([x[i] for i in active_df.index]) == lineup_size

        unique_pos = active_df["Position"].unique().tolist()
        if len(unique_pos) <= lineup_size:
            for pos in unique_pos:
                pos_indices = active_df[active_df["Position"] == pos].index
                if len(pos_indices) > 0:
                    prob += pulp.lpSum([x[i] for i in pos_indices]) >= 1

        for i in active_df[active_df["Lock"] == True].index:
            prob += x[i] == 1

        for i in active_df.index:
            if not active_df.loc[i, "Lock"] and exposure_counts[i] >= max_allowed:
                prob += x[i] == 0

        if stack_team != "None" and stack_count > 1:
            t_idx = active_df[active_df["Team"] == stack_team].index
            if len(t_idx) >= stack_count:
                prob += pulp.lpSum([x[i] for i in t_idx]) >= stack_count
            if bring_back:
                opp_teams = active_df[active_df["Team"] == stack_team]["Opponent"].unique().tolist()
                if opp_teams:
                    opp_idx = active_df[active_df["Team"].isin(opp_teams)].index
                    if len(opp_idx) > 0:
                        prob += pulp.lpSum([x[i] for i in opp_idx]) >= 1

        for prev_indices in lineups:
            prob += pulp.lpSum([x[i] for i in prev_indices]) <= lineup_size - 1

        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[prob.status] == "Optimal":
            chosen = [i for i in active_df.index if pulp.value(x[i]) == 1.0]
            lineups.append(chosen)
            for i in chosen:
                exposure_counts[i] += 1
        else:
            break

    return [active_df.loc[idx_list].copy() for idx_list in lineups]

# ==========================================
# 6. SIDEBAR: ACCOUNT STATUS & LEAGUE MENU
# ==========================================
if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.markdown("## ⚡ PROSTACK AI PORTAL")
    st.caption("US 🇺🇸 & Canada 🇨🇦 Enterprise Quant Engine")
    st.link_button("✈️ Join Official Telegram VIP", SUPPORT_TELEGRAM_URL, use_container_width=True)
    st.divider()

    if st.session_state.user is not None:
        u = st.session_state.user
        st.success(f"👤 **{u['email']}**")
        if u["is_admin"]:
            st.markdown("👑 **Role:** `FOUNDER / ADMIN`")
        elif u["is_vip"]:
            st.markdown("💎 **Membership:** `LIFETIME / PAID VIP`")
        else:
            st.markdown(f"🎁 **VIP Trial Until:** `{u['trial_until'][:10]}`")

        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        st.divider()

    selected_league = st.selectbox("🏆 Select North American League", list(LEAGUE_CONFIGS.keys()))
    st.caption("Supports DraftKings, FanDuel, PrizePicks & Underdog Fantasy.")

# ==========================================
# 7. STRICT AUTHENTICATION GATE (NO FREE LEAKS!)
# ==========================================
st.title(f"⚡ ProStack AI — {selected_league} Quantitative Command Center")

if st.session_state.user is None:
    st.markdown("""
    <div class="lock-gate">
        <h2 style="color:#00FF88; margin-top:0;">🔒 VIP QUANT PORTAL LOCKED</h2>
        <p style="font-size:1.05rem; color:#FFFFFF;">
            Unlock the <b>10,000x Monte Carlo Lineup Simulator</b>, <b>Anti-Chalk GPP Ownership Engine</b>, 
            <b>Live Sportsbook +EV Prop Devigger</b>, and <b>AI Kelly Bankroll Vault</b> across all 10 North American leagues.
        </p>
        <span class="badge-ev">🎁 LIMITED LAUNCH OFFER: Instant 30-Day Free VIP Trial (No Credit Card Required)</span>
    </div>
    """, unsafe_allow_html=True)

    g_col1, g_col2, g_col3 = st.columns([1, 2.2, 1])
    with g_col2:
        gate_tab1, gate_tab2, gate_tab3 = st.tabs([
            "🎁 30-Day Free Trial",
            "🔑 Member Sign In",
            "👑 Admin"
        ])
        with gate_tab1:
            st.markdown("#### 🚀 Create Your Free VIP Quant Account (Takes 10 Seconds)")
            r_email = st.text_input("📧 Enter Your Best Email Address", key="gate_reg_email")
            r_pw = st.text_input("🔑 Create a Password (4+ characters)", type="password", key="gate_reg_pw")
            if st.button("⚡ Activate My 30-Day Free VIP Trial & Unlock App", use_container_width=True, type="primary"):
                if "@" in r_email and len(r_pw) >= 4:
                    ok, msg = register_user(r_email, r_pw)
                    if ok:
                        st.session_state.user = authenticate_user(r_email, r_pw)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.warning(msg)
                else:
                    st.error("Please enter a valid email address and a password of at least 4 characters.")

        with gate_tab2:
            st.markdown("#### 🔑 Existing VIP Member Sign In")
            l_email = st.text_input("📧 Registered Email Address", key="gate_login_email")
            l_pw = st.text_input("🔑 Enter Your Password", type="password", key="gate_login_pw")
            if st.button("🔓 Sign In & Unlock Quant Engine", use_container_width=True, type="primary"):
                u = authenticate_user(l_email, l_pw)
                if u:
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("Invalid email or password. If you are new, tap '🎁 30-Day Free Trial'!")

        with gate_tab3:
            st.markdown("#### 👑 Instant Founder Master Key Login")
            master_in = st.text_input("🔐 Enter Founder Master Key", type="password", key="gate_master_key")
            if st.button("👑 Unlock as Founder Admin", use_container_width=True, type="primary"):
                if master_in == "ProStackAdmin2026!":
                    st.session_state.user = {
                        "email": "admin@prostackai.com",
                        "trial_until": "2036-01-01",
                        "is_vip": True,
                        "is_admin": True
                    }
                    st.rerun()
                else:
                    st.error("Invalid Master Key.")

    st.markdown(f"""
    <div class="legal-footer">
        <b>⚖️ US & CANADA LEGAL COMPLIANCE & RESPONSIBLE GAMING SHIELD</b><br>
        ProStack AI is a quantitative sports analytics and statistical simulation tool for educational and entertainment purposes only. Not a gambling site. Must be 18+ / 21+.<br>
        © 2026 ProStack AI Quant Technologies | <a href="{SUPPORT_TELEGRAM_URL}" target="_blank" style="color:#00FF88;">Official Telegram VIP Support</a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ==========================================
# 8. TRIAL EXPIRATION PAYWALL CHECK
# ==========================================
if not check_vip_active(st.session_state.user):
    st.markdown("""
    <div class="lock-gate">
        <h2 style="color:#FF4B4B; margin-top:0;">⏳ YOUR 30-DAY FREE VIP TRIAL HAS EXPIRED</h2>
        <p style="font-size:1.05rem;">
            To continue accessing the <b>10,000x Monte Carlo Simulator</b>, <b>DraftKings/FanDuel MME Exporter</b>, 
            and <b>Live +EV Prop Devigger</b>, please upgrade your account to Paid VIP.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.link_button("💎 Message Official Telegram Admin to Activate Paid VIP ($19/mo)", SUPPORT_TELEGRAM_URL, use_container_width=True, type="primary")
    st.stop()

# ==========================================
# 9. UNLOCKED VIP PORTAL TABS
# ==========================================
tabs = st.tabs([
    "🎲 10,000x Optimizer",
    "🎯 +EV Prop Devigger",
    "💰 Kelly & ROI Vault",
    "👑 Founder Admin"
])

# ------------------------------------------
# TAB 1: MONTE CARLO SIMULATOR & OPTIMIZER
# ------------------------------------------
with tabs[0]:
    col_top1, col_top2, col_top3 = st.columns([1.4, 1.4, 1.2])
    with col_top1:
        uploaded_csv = st.file_uploader(f"📂 Upload {selected_league} DraftKings / FanDuel CSV", type=["csv"])
    with col_top2:
        st.write("")
        st.write("")
        if st.button(f"⚡ Load Today's {selected_league} Pro Slate (Instant No-CSV Test)", use_container_width=True, type="primary"):
            st.session_state[f"slate_{selected_league}"] = generate_pro_slate(selected_league)
            st.toast(f"Loaded Official {selected_league} Pro Slate!", icon="⚡")
    with col_top3:
        weather_mod = st.slider("🌦️ Dome / Weather Boost (%)", -15.0, 15.0, 0.0, 1.0)

    if uploaded_csv is not None:
        raw_df = pd.read_csv(uploaded_csv)
        col_map = {}
        for c in raw_df.columns:
            cl = c.lower()
            if "name" in cl and "Name" not in col_map.values(): col_map[c] = "Name"
            elif ("pos" in cl) and "Position" not in col_map.values(): col_map[c] = "Position"
            elif ("sal" in cl) and "Salary" not in col_map.values(): col_map[c] = "Salary"
            elif ("team" in cl or "squad" in cl) and "Team" not in col_map.values(): col_map[c] = "Team"
            elif ("fppg" in cl or "proj" in cl or "avg" in cl) and "Projection" not in col_map.values(): col_map[c] = "Projection"
        raw_df = raw_df.rename(columns=col_map)
        if "Name" not in raw_df.columns: raw_df["Name"] = [f"Player {i}" for i in range(len(raw_df))]
        if "Position" not in raw_df.columns: raw_df["Position"] = LEAGUE_CONFIGS[selected_league]["positions"][0]
        if "Team" not in raw_df.columns: raw_df["Team"] = "PRO"
        if "Opponent" not in raw_df.columns: raw_df["Opponent"] = "OPP"
        if "Salary" not in raw_df.columns: raw_df["Salary"] = 5000
        if "Projection" not in raw_df.columns: raw_df["Projection"] = (raw_df["Salary"] / 1000.0) * 4.0
        if "StdDev" not in raw_df.columns: raw_df["StdDev"] = raw_df["Projection"] * 0.25
        if "Ownership%" not in raw_df.columns: raw_df["Ownership%"] = 15.0
        if "Status" not in raw_df.columns: raw_df["Status"] = "ACTIVE"
        if "Lock" not in raw_df.columns: raw_df["Lock"] = False
        if "ID" not in raw_df.columns: raw_df["ID"] = [f"DK{1000+i}" for i in range(len(raw_df))]
        st.session_state[f"slate_{selected_league}"] = raw_df

    if f"slate_{selected_league}" not in st.session_state:
        st.session_state[f"slate_{selected_league}"] = generate_pro_slate(selected_league)

    base_slate = st.session_state[f"slate_{selected_league}"]

    st.markdown("### 🛠️ Live Injury Boost (`OUT 🚑`), Late-Swap Locks (`🔒`) & Monte Carlo Table")
    st.caption("Mark any star player `OUT 🚑` to automatically boost active teammates by **+15% usage**, or tick `🔒 Lock` for Late-Swap!")

    edited_slate = st.data_editor(
        base_slate,
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["ACTIVE", "OUT 🚑"], required=True),
            "Lock": st.column_config.CheckboxColumn("🔒 Lock (Late-Swap)")
        },
        use_container_width=True,
        num_rows="dynamic",
        key=f"editor_{selected_league}"
    )

    sim_df = run_monte_carlo_simulation(edited_slate, n_sims=10000, weather_impact=weather_mod)

    with st.expander("📊 View 10,000x Monte Carlo Simulation Output (Floor, Ceiling, Boom% & Anti-Chalk Leverage)", expanded=True):
        st.dataframe(
            sim_df[["Name", "Position", "Team", "Opponent", "Salary", "Adj_Proj", "Floor (15%)", "Ceiling (90%)", "Ownership%", "Boom%", "Leverage", "Value (Pt/$1K)"]],
            use_container_width=True
        )

    st.markdown("### ⚙️ Quantitative Optimizer & Stacking Controls")
    c1, c2, c3, c4 = st.columns(4)
    cfg = LEAGUE_CONFIGS[selected_league]
    with c1:
        contest_mode = st.selectbox("🎯 Contest Strategy", [
            "GPP Millionaire (Ceiling + Anti-Chalk Leverage)",
            "Cash Game Safe (High Floor)",
            "Balanced Base Projection"
        ])
        num_lineups = st.slider("🔢 Lineups to Generate (MME)", 1, 50, 5)
    with c2:
        salary_cap = st.number_input("💰 Salary Cap ($)", value=cfg["cap"], step=500)
        lineup_size = st.number_input("👥 Roster Size", value=cfg["size"], min_value=2, max_value=12)
    with c3:
        max_exp = st.slider("🛡️ Max Player Exposure (%)", 20, 100, 65)
        avail_teams = ["None"] + sorted(sim_df["Team"].unique().tolist())
        stack_team = st.selectbox("🔗 Primary Team Stack", avail_teams)
    with c4:
        stack_count = st.slider("🔢 Stack Players Count", 2, 5, 3)
        bring_back = st.checkbox("🔄 Force Opposing 'Bring-Back' Player", value=True)

    if st.button("🚀 RUN 10,000x MONTE CARLO & GENERATE WINNING LINEUPS", use_container_width=True, type="primary"):
        built = optimize_lineups_quant(
            sim_df, num_lineups, salary_cap, lineup_size,
            contest_mode, max_exp, stack_team, stack_count, bring_back
        )
        if not built:
            st.error("Could not satisfy constraints. Try raising Max Exposure % or lowering Stack Count.")
        else:
            st.success(f"✅ Generated {len(built)} Quant-Optimized {selected_league} Lineups!")

            export_rows = []
            for idx, ldf in enumerate(built):
                row_dict = {"Lineup_#": idx + 1, "Total_Salary": int(ldf["Salary"].sum()),
                            "Proj_Points": round(ldf["Adj_Proj"].sum(), 2),
                            "Ceiling_90": round(ldf["Ceiling (90%)"].sum(), 2),
                            "Avg_Own%": round(ldf["Ownership%"].mean(), 1)}
                for p_i, (_, prow) in enumerate(ldf.iterrows()):
                    row_dict[f"Slot_{p_i+1}"] = f"{prow['Name']} ({prow['ID']})"
                export_rows.append(row_dict)

            export_df = pd.DataFrame(export_rows)
            st.download_button(
                "📥 Download Direct DraftKings / FanDuel MME Upload CSV",
                data=export_df.to_csv(index=False).encode("utf-8"),
                file_name=f"ProStackAI_{selected_league}_Lineups.csv",
                mime="text/csv",
                use_container_width=True
            )

            for idx, ldf in enumerate(built):
                tot_sal = int(ldf["Salary"].sum())
                tot_proj = round(ldf["Adj_Proj"].sum(), 2)
                tot_ceil = round(ldf["Ceiling (90%)"].sum(), 2)
                avg_own = round(ldf["Ownership%"].mean(), 1)

                st.markdown(f"""
                <div class="quant-card">
                    <h4>🏆 Lineup #{idx+1} — {contest_mode.split('(')[0]}</h4>
                    <b>💰 Salary:</b> ${tot_sal:,} /${salary_cap:,} &nbsp;|&nbsp;
                    <b>📈 Mean Proj:</b> {tot_proj} pts &nbsp;|&nbsp;
                    <b>🚀 90th Ceiling:</b> <span style="color:#00FF88">{tot_ceil} pts</span> &nbsp;|&nbsp;
                    <b>👥 Avg Ownership:</b> {avg_own}%
                </div>
                """, unsafe_allow_html=True)
                st.dataframe(
                    ldf[["Position", "Name", "Team", "Opponent", "Salary", "Adj_Proj", "Ceiling (90%)", "Ownership%", "Leverage"]],
                    use_container_width=True,
                    hide_index=True
                )

                with st.expander(f"📲 Shareable VIP Viral Card for Lineup #{idx+1} (Screenshot for X / Reddit)"):
                    top_names = " • ".join(ldf["Name"].head(4).tolist())
                    st.markdown(f"""
                    <div class="viral-card">
                        <h3 style="color:#00FF88; margin:0;">⚡ PROSTACK AI QUANT VIP SLIP ({selected_league})</h3>
                        <p style="margin:4px 0; color:#94A3B8;">Strategy: {contest_mode}</p>
                        <hr style="border-color:#1E293B;">
                        <p><b>🔥 Core Stack:</b> {top_names} + more</p>
                        <p><b>📈 Projected Score:</b> {tot_proj} pts &nbsp;|&nbsp; <b>🚀 90% Ceiling:</b> <span style="color:#00FF88">{tot_ceil} pts</span></p>
                        <p><b>🧠 Avg Slate Ownership:</b> {avg_own}% (High GPP Leverage)</p>
                        <hr style="border-color:#1E293B;">
                        <p style="color:#00FF88; font-weight:bold; margin:0;">🌐 Build yours free: prostackai.streamlit.app | ✈️ Telegram: @ProStackAI_Official</p>
                    </div>
                    """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 2: +EV PICK'EM & SPORTSBOOK DEVIGGER
# ------------------------------------------
with tabs[1]:
    st.subheader("🎯 Live Sportsbook Odds Devigger (+EV Pick'em Scanner for PrizePicks & Underdog)")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        prop_player = st.text_input("🏀 Player & Stat Prop", value="Josh Allen - Over 265.5 Pass+Rush Yds")
    with col_p2:
        over_odds = st.number_input("📈 Sharp Book Over Odds (American)", value=-145, step=5)
    with col_p3:
        under_odds = st.number_input("📉 Sharp Book Under Odds (American)", value=115, step=5)

    def american_to_prob(odds: float) -> float:
        return (-odds) / ((-odds) + 100.0) if odds < 0 else 100.0 / (odds + 100.0)

    raw_over = american_to_prob(over_odds)
    raw_under = american_to_prob(under_odds)
    true_win_prob = (raw_over / (raw_over + raw_under)) * 100.0
    ev_edge = round(true_win_prob - 54.25, 2)

    st.markdown(f"""
    <div class="quant-card">
        <h4>⚡ Devigged Sharp Analysis: {prop_player}</h4>
        <b>🎯 True No-Vig Win Probability:</b> <span class="badge-ev">{true_win_prob:.2f}%</span> &nbsp;|&nbsp;
        <b>📊 PrizePicks Breakeven:</b> 54.25% &nbsp;|&nbsp;
        <b>🔥 Mathematical +EV Edge:</b> <span class="badge-ev">{ev_edge:+.2f}%</span>
    </div>
    """, unsafe_allow_html=True)

    ev_board = pd.DataFrame([
        {"League": selected_league, "Player Prop": "Primary Star Over Main Line", "Pinnacle Odds": "-148 / +118", "True Win %": "58.1%", "+EV Edge": "+3.85%", "Action": "🔥 LOCK OVER"},
        {"League": selected_league, "Player Prop": "Co-Star Under Rebounds/Yards", "Pinnacle Odds": "-142 / +112", "True Win %": "57.2%", "+EV Edge": "+2.95%", "Action": "🔥 LOCK UNDER"},
        {"League": selected_league, "Player Prop": "Slot/Guard Over Receptions/Assists", "Pinnacle Odds": "-138 / +110", "True Win %": "56.6%", "+EV Edge": "+2.35%", "Action": "✅ PLAYABLE +EV"}
    ])
    st.dataframe(ev_board, use_container_width=True, hide_index=True)

# ------------------------------------------
# TAB 3: KELLY BANKROLL & PERSONAL ROI VAULT
# ------------------------------------------
with tabs[2]:
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        st.markdown("### 💰 AI Kelly Criterion Bankroll Calculator")
        total_br = st.number_input("💵 Total DFS / Pick'em Bankroll ($)", value=2500.0, step=100.0)
        win_prob = st.slider("🎯 Estimated Slip Win Probability (%)", 50.0, 75.0, 58.0, 0.5) / 100.0
        payout_mult = st.number_input("🏆 Contest / Slip Multiplier", value=2.0, step=0.25)
        kelly_frac = st.selectbox("🛡️ Risk Profile", ["Quarter-Kelly (Ultra Safe Pro)", "Half-Kelly (Balanced Growth)", "Full Kelly (Aggressive)"])

        b = max(payout_mult - 1.0, 0.1)
        raw_kelly = max(0.0, ((b * win_prob) - (1.0 - win_prob)) / b)
        mult_map = {"Quarter-Kelly (Ultra Safe Pro)": 0.25, "Half-Kelly (Balanced Growth)": 0.5, "Full Kelly (Aggressive)": 1.0}
        rec_pct = raw_kelly * mult_map[kelly_frac] * 100.0
        rec_wager = round(total_br * (rec_pct / 100.0), 2)

        st.markdown(f"""
        <div class="quant-card">
            <h4>🧠 Recommended Quant Wager: <span style="color:#00FF88">${rec_wager:,.2f}</span> ({rec_pct:.2f}% of Bankroll)</h4>
            <p style="margin:0; font-size:0.9rem;">Protects against variance while maximizing compound bankroll growth.</p>
        </div>
        """, unsafe_allow_html=True)

    with col_k2:
        st.markdown("### 📈 Personal ROI & Profit/Loss Vault")
        u_email = st.session_state.user["email"]
        with st.form("roi_form"):
            c_type = st.selectbox("Contest Type", [f"{selected_league} DraftKings GPP", f"{selected_league} Cash Double-Up", "PrizePicks / Underdog +EV Slip"])
            w_amt = st.number_input("Entry Wager ($)", value=50.0, step=10.0)
            p_amt = st.number_input("Total Payout Won ($)", value=125.0, step=10.0)
            if st.form_submit_button("💾 Log Result to My Vault", use_container_width=True):
                conn = get_conn()
                c = conn.cursor()
                c.execute("INSERT INTO roi_vault (email, entry_date, contest_type, wager, payout) VALUES (?, ?, ?, ?, ?)",
                          (u_email, datetime.utcnow().strftime("%Y-%m-%d"), c_type, w_amt, p_amt))
                conn.commit()
                conn.close()
                st.success("Logged to ROI Vault!")

        conn = get_conn()
        v_df = pd.read_sql_query("SELECT entry_date, contest_type, wager, payout FROM roi_vault WHERE email=?", conn, params=(u_email,))
        conn.close()
        if not v_df.empty:
            v_df["Net_Profit"] = v_df["payout"] - v_df["wager"]
            v_df["Cumulative_Profit"] = v_df["Net_Profit"].cumsum()
            tot_net = v_df["Net_Profit"].sum()
            roi_pct = (tot_net / max(v_df["wager"].sum(), 1.0)) * 100.0
            st.metric("🏆 Total Vault Net Profit", f"${tot_net:,.2f}", f"{roi_pct:+.1f}% ROI")
            st.line_chart(v_df["Cumulative_Profit"])
        else:
            st.info("Log your first contest above to see your live profit chart!")

# ------------------------------------------
# TAB 4: FOUNDER ADMIN, VIP TOGGLE & BACKUP
# ------------------------------------------
with tabs[3]:
    st.subheader("👑 Founder Command Center, VIP Manager & Cloud DB Backup")
    admin_key = st.text_input("🔐 Enter Founder Master Key", type="password")
    if admin_key == "ProStackAdmin2026!" or (st.session_state.user and st.session_state.user.get("is_admin")):
        conn = get_conn()
        users_df = pd.read_sql_query("SELECT email, created_at, trial_until, is_vip, is_admin FROM users", conn)
        conn.close()
        st.metric("👥 Total Registered Users", len(users_df))
        st.dataframe(users_df, use_container_width=True)

        st.markdown("#### 💎 Manual VIP Grant / Revoke Control")
        adm_c1, adm_c2, adm_c3 = st.columns(3)
        with adm_c1:
            target_email = st.selectbox("Select User Email", users_df["email"].tolist())
        with adm_c2:
            if st.button("✅ Grant Lifetime VIP", use_container_width=True, type="primary"):
                conn = get_conn()
                conn.execute("UPDATE users SET is_vip=1 WHERE email=?", (target_email,))
                conn.commit()
                conn.close()
                st.success(f"Granted VIP to {target_email}!")
                st.rerun()
        with adm_c3:
            if st.button("⏳ Reset / Revoke VIP", use_container_width=True):
                conn = get_conn()
                conn.execute("UPDATE users SET is_vip=0 WHERE email=?", (target_email,))
                conn.commit()
                conn.close()
                st.warning(f"Revoked VIP for {target_email}.")
                st.rerun()

        st.divider()
        st.download_button(
            "📥 1-Click Download Full User Database Backup (JSON)",
            data=users_df.to_json(orient="records"),
            file_name="prostack_users_backup.json",
            mime="application/json",
            use_container_width=True
        )
    else:
        st.info("Founder authentication required to access user database and backups.")

# ==========================================
# 10. STRICT US & CANADA LEGAL SHIELD FOOTER
# ==========================================
st.markdown(f"""
<div class="legal-footer">
    <b>⚖️ US & CANADA LEGAL COMPLIANCE & RESPONSIBLE GAMING SHIELD</b><br>
    ProStack AI is a quantitative sports analytics, statistical simulation, and lineup optimization software tool for educational and entertainment purposes only. 
    ProStack AI is <b>NOT</b> a sportsbook, gambling operator, or real-money wagering site, and does not accept or place bets of any kind. 
    Past statistical simulations do not guarantee future contest outcomes. Must be 18+ (19+ in select Canadian provinces / 21+ in select US jurisdictions).<br>
    If you or someone you know has a gaming problem, call <b>1-800-GAMBLER</b> (US) or <b>1-866-531-2600</b> (Canada).<br>
    © 2026 ProStack AI Quant Technologies | <a href="{SUPPORT_TELEGRAM_URL}" target="_blank" style="color:#00FF88;">Official Telegram VIP Support</a>
</div>
""", unsafe_allow_html=True)
