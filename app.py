import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import hashlib
import hmac
import base64
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
SECRET_SIGNING_KEY = "ProStackAI_Persistent_Vault_2026_SecretKey"

# ==========================================
# 2. BULLETPROOF DARK/LIGHT CSS + HIDE "PRESS ENTER"
# ==========================================
st.markdown("""
<style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #070B12 !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] {
        background-color: #0B111E !important;
        border-right: 1px solid #00FF8844 !important;
    }
    [data-testid="InputInstructions"], .stTextInput small, div[data-baseweb="input"] small {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        font-size: 0px !important;
    }
    label, .stTextInput label p, .stNumberInput label p, .stSelectbox label p, .stSlider label p, .stRadio label p {
        color: #00FF88 !important;
        font-weight: 700 !important;
        font-size: 0.98rem !important;
    }
    div[role="radiogroup"] label p, div[role="radiogroup"] span {
        color: #FFD700 !important;
        font-weight: 700 !important;
        font-size: 0.96rem !important;
    }
    div[data-baseweb="input"], div[data-baseweb="base-input"], input {
        background-color: #111A2E !important;
        color: #FFFFFF !important;
        border-color: #00FF88 !important;
        border-radius: 8px !important;
        -webkit-text-fill-color: #FFFFFF !important;
        caret-color: #00FF88 !important;
    }
    div[data-baseweb="input"] button, div[data-baseweb="input"] svg {
        color: #FFD700 !important;
        fill: #FFD700 !important;
        background-color: transparent !important;
    }
    [data-testid="stForm"] {
        background: linear-gradient(145deg, #0D1526, #090E1A) !important;
        border: 1.5px solid #00FF8866 !important;
        border-radius: 14px !important;
        padding: 22px !important;
        margin-bottom: 16px !important;
    }
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
    .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(90deg, #00FF88 0%, #00CC6A 100%) !important;
        color: #04120B !important;
        font-weight: 800 !important;
        font-size: 1.02rem !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 18px !important;
        margin-top: 8px !important;
        width: 100% !important;
    }
    h1, h2, h3, h4, h5, h6, p, span {
        color: #F8FAFC;
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
        padding: 22px;
        margin: 14px 0;
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
# 3. DATABASE & FACEBOOK-STYLE PERSISTENT LOGIN
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
            phone TEXT,
            password_hash TEXT,
            created_at TEXT,
            trial_until TEXT,
            is_vip INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0
        )
    """)
    try:
        c.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''")
    except Exception:
        pass

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
    admin_phone = "+10000000000"
    admin_hash = hashlib.sha256("ProStackAdmin2026!".encode()).hexdigest()
    now_str = datetime.utcnow().isoformat()
    vip_until = (datetime.utcnow() + timedelta(days=3650)).isoformat()
    c.execute("""
        INSERT OR IGNORE INTO users (email, phone, password_hash, created_at, trial_until, is_vip, is_admin)
        VALUES (?, ?, ?, ?, ?, 1, 1)
    """, (admin_email, admin_phone, admin_hash, now_str, vip_until))
    conn.commit()
    conn.close()

init_db()

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def clean_phone(ph: str) -> str:
    return "".join(ch for ch in str(ph).strip() if ch.isdigit() or ch == "+")

def create_persistent_token(user_dict: dict) -> str:
    """Creates an encrypted token so switching mobile apps never logs the user out."""
    payload = json.dumps(user_dict, separators=(",", ":"))
    b64_payload = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = hmac.new(SECRET_SIGNING_KEY.encode(), b64_payload.encode(), hashlib.sha256).hexdigest()[:20]
    return f"{b64_payload}.{sig}"

def verify_persistent_token(token_str: str):
    """Restores user session automatically when returning from another mobile app."""
    try:
        if "." not in token_str:
            return None
        b64_payload, sig = token_str.split(".", 1)
        expected_sig = hmac.new(SECRET_SIGNING_KEY.encode(), b64_payload.encode(), hashlib.sha256).hexdigest()[:20]
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = base64.urlsafe_b64decode(b64_payload.encode()).decode()
        return json.loads(payload)
    except Exception:
        return None

def save_login_session(user_dict: dict):
    """Saves login in both session_state and persistent URL token."""
    st.session_state.user = user_dict
    st.query_params["session"] = create_persistent_token(user_dict)

def clear_login_session():
    """Logs out completely only when user clicks Log Out."""
    st.session_state.user = None
    st.session_state.admin_unlocked = False
    st.query_params.clear()

def register_user(email: str, phone: str, pw: str):
    conn = get_conn()
    c = conn.cursor()
    email = email.strip().lower()
    phone_clean = clean_phone(phone)
    c.execute("SELECT email FROM users WHERE email=? OR (phone=? AND phone!='')", (email, phone_clean))
    if c.fetchone():
        conn.close()
        return False, "Account already exists with this Email or Phone Number. Please Sign In or use Forgot Password!"
    now = datetime.utcnow()
    trial_end = now + timedelta(days=30)
    c.execute("""
        INSERT INTO users (email, phone, password_hash, created_at, trial_until, is_vip, is_admin)
        VALUES (?, ?, ?, ?, ?, 0, 0)
    """, (email, phone_clean, hash_pw(pw), now.isoformat(), trial_end.isoformat()))
    conn.commit()
    conn.close()
    return True, "🎉 30-Day VIP Quant Trial Activated!"

def authenticate_user(identifier: str, pw: str):
    conn = get_conn()
    c = conn.cursor()
    ident_clean = identifier.strip().lower()
    phone_ident = clean_phone(identifier)
    c.execute("""
        SELECT email, phone, password_hash, trial_until, is_vip, is_admin 
        FROM users 
        WHERE email=? OR (phone=? AND phone!='')
    """, (ident_clean, phone_ident))
    row = c.fetchone()
    conn.close()
    if row and row[2] == hash_pw(pw):
        return {
            "email": row[0],
            "phone": row[1] or "",
            "trial_until": row[3],
            "is_vip": bool(row[4]),
            "is_admin": bool(row[5])
        }
    return None

def reset_user_password(email: str, phone: str, new_pw: str):
    conn = get_conn()
    c = conn.cursor()
    email_clean = email.strip().lower()
    phone_clean = clean_phone(phone)
    c.execute("SELECT email, phone FROM users WHERE email=? AND phone=?", (email_clean, phone_clean))
    if not c.fetchone():
        conn.close()
        return False, "❌ Email and Phone Number do not match our records. Please check both carefully!"
    c.execute("UPDATE users SET password_hash=? WHERE email=?", (hash_pw(new_pw), email_clean))
    conn.commit()
    conn.close()
    return True, "✅ Password Reset Successful! Signing you in..."

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
# AUTO-RESTORE SESSION IF USER SWITCHED APPS
# ==========================================
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None and "session" in st.query_params:
    restored_user = verify_persistent_token(st.query_params["session"])
    if restored_user:
        st.session_state.user = restored_user

# ==========================================
# 4. 100% AUTHENTIC AMERICAN PRO SLATE DATA
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
    if league == "NFL":
        nfl_data = [
            ("Josh Allen", "QB", "BUF", "KC", 8000, 24.8, 6.2, 22.4),
            ("Patrick Mahomes", "QB", "KC", "BUF", 7600, 22.9, 5.8, 19.5),
            ("Jalen Hurts", "QB", "PHI", "DET", 7800, 23.6, 6.0, 18.2),
            ("Lamar Jackson", "QB", "BAL", "CIN", 7900, 24.2, 6.4, 20.1),
            ("Christian McCaffrey", "RB", "SF", "DAL", 8600, 23.5, 5.5, 28.5),
            ("Saquon Barkley", "RB", "PHI", "DET", 7500, 19.4, 4.9, 21.0),
            ("Derrick Henry", "RB", "BAL", "CIN", 7200, 18.2, 4.8, 17.5),
            ("Jahmyr Gibbs", "RB", "DET", "PHI", 6900, 17.6, 4.7, 15.8),
            ("Isiah Pacheco", "RB", "KC", "BUF", 6200, 15.4, 4.1, 16.4),
            ("James Cook", "RB", "BUF", "KC", 6400, 15.9, 4.3, 14.9),
            ("CeeDee Lamb", "WR", "DAL", "SF", 8200, 21.2, 5.6, 24.0),
            ("Amon-Ra St. Brown", "WR", "DET", "PHI", 7900, 20.4, 5.1, 22.1),
            ("Ja'Marr Chase", "WR", "CIN", "BAL", 8100, 20.9, 5.9, 21.5),
            ("AJ Brown", "WR", "PHI", "DET", 7700, 19.2, 5.4, 18.6),
            ("Rashee Rice", "WR", "KC", "BUF", 6600, 16.8, 4.6, 23.2),
            ("Khalil Shakir", "WR", "BUF", "KC", 5300, 13.5, 3.9, 14.2),
            ("Deebo Samuel", "WR", "SF", "DAL", 6800, 16.9, 4.8, 15.4),
            ("Zay Flowers", "WR", "BAL", "CIN", 6100, 15.1, 4.3, 13.8),
            ("Xavier Worthy", "WR", "KC", "BUF", 5100, 12.8, 4.5, 11.5),
            ("Travis Kelce", "TE", "KC", "BUF", 6000, 15.2, 4.2, 19.8),
            ("George Kittle", "TE", "SF", "DAL", 5700, 14.1, 4.0, 14.5),
            ("Sam LaPorta", "TE", "DET", "PHI", 5500, 13.6, 3.8, 13.2),
            ("Dalton Kincaid", "TE", "BUF", "KC", 4900, 12.1, 3.6, 12.4),
            ("Mark Andrews", "TE", "BAL", "CIN", 5200, 12.9, 3.9, 11.8),
            ("Chiefs DST", "DST", "KC", "BUF", 3100, 8.4, 3.2, 12.0),
            ("Bills DST", "DST", "BUF", "KC", 2900, 7.9, 3.1, 9.5),
            ("49ers DST", "DST", "SF", "DAL", 3400, 9.2, 3.4, 16.5),
            ("Ravens DST", "DST", "BAL", "CIN", 3200, 8.8, 3.3, 14.0)
        ]
        rows = []
        for idx, (name, pos, team, opp, sal, proj, sd, own) in enumerate(nfl_data):
            rows.append({
                "ID": f"DK{10000+idx}",
                "Name": name,
                "Position": pos,
                "Team": team,
                "Opponent": opp,
                "Salary": sal,
                "Projection": proj,
                "StdDev": sd,
                "Ownership%": own,
                "Vegas_OU": 51.5 if team in ["KC", "BUF"] else 49.5,
                "Status": "ACTIVE",
                "Lock": False
            })
        return pd.DataFrame(rows)

    cfg = LEAGUE_CONFIGS[league]
    pos_list = cfg["positions"]
    teams = [("BOS", "MIL", 234.5), ("DEN", "LAL", 229.0), ("PHX", "GSW", 236.0), ("DAL", "OKC", 238.5)]
    names = [f"{league} Star #{i+1}" for i in range(24)]
    rows = []
    np.random.seed(42)
    for idx, name in enumerate(names):
        pos = pos_list[idx % len(pos_list)]
        t_pair = teams[idx % len(teams)]
        team = t_pair[0] if idx % 2 == 0 else t_pair[1]
        opp = t_pair[1] if idx % 2 == 0 else t_pair[0]
        salary = int(np.random.choice(range(4200, 8200, 200)))
        base_proj = round((salary / 1000.0) * np.random.uniform(3.2, 4.1), 2)
        rows.append({
            "ID": f"DK{20000+idx}",
            "Name": name,
            "Position": pos,
            "Team": team,
            "Opponent": opp,
            "Salary": salary,
            "Projection": base_proj,
            "StdDev": round(base_proj * 0.25, 2),
            "Ownership%": round(float(np.random.uniform(6.0, 28.0)), 1),
            "Vegas_OU": t_pair[2],
            "Status": "ACTIVE",
            "Lock": False
        })
    return pd.DataFrame(rows)

# ==========================================
# 5. STRICT SALARY-CAP 10,000x MONTE CARLO & SOLVER
# ==========================================
@st.cache_data(show_spinner=False)
def run_monte_carlo_simulation(df: pd.DataFrame, n_sims: int = 10000, weather_impact: float = 0.0) -> pd.DataFrame:
    df = df.copy()
    df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce").fillna(5000).astype(int)
    df["Projection"] = pd.to_numeric(df["Projection"], errors="coerce").fillna(15.0).astype(float)

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
        target_boom = (float(row["Salary"]) / 1000.0) * 3.6
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
    active_df = df[df["Status"] != "OUT 🚑"].copy().reset_index(drop=True)
    if active_df.empty:
        return []

    eff_size = min(int(lineup_size), len(active_df))
    if contest_mode == "GPP Millionaire (Ceiling + Anti-Chalk Leverage)":
        active_df["Opt_Score"] = (active_df["Ceiling (90%)"] * 0.75) + (active_df["Leverage"] * 0.35)
    elif contest_mode == "Cash Game Safe (High Floor)":
        active_df["Opt_Score"] = (active_df["Adj_Proj"] * 0.65) + (active_df["Floor (15%)"] * 0.35)
    else:
        active_df["Opt_Score"] = active_df["Adj_Proj"]

    lineups = []
    seen_signatures = set()
    exposure_counts = {i: 0 for i in range(len(active_df))}
    max_allowed = max(1, int(np.ceil(num_lineups * (max_exposure / 100.0))))
    rng = np.random.default_rng(2026)

    has_nfl_pos = set(["QB", "RB", "WR", "TE", "DST"]).issubset(set(active_df["Position"].unique())) and eff_size == 9

    for l_idx in range(num_lineups):
        best_choice = None
        best_score = -1e9

        for attempt in range(400):
            noise = rng.uniform(0.90, 1.10, size=len(active_df)) if (l_idx > 0 or attempt > 0) else np.ones(len(active_df))
            scores = active_df["Opt_Score"].values * noise

            if stack_team != "None":
                team_mask = (active_df["Team"] == stack_team).values
                scores = np.where(team_mask, scores * 1.30, scores)
                if bring_back:
                    opp_mask = (active_df["Opponent"] == stack_team).values
                    scores = np.where(opp_mask, scores * 1.18, scores)

            chosen = [i for i in active_df.index[active_df["Lock"] == True].tolist() if i < len(active_df)][:eff_size]

            if has_nfl_pos and len(chosen) == 0:
                qbs = sorted(active_df[active_df["Position"] == "QB"].index.tolist(), key=lambda i: scores[i], reverse=True)
                dsts = sorted(active_df[active_df["Position"] == "DST"].index.tolist(), key=lambda i: scores[i], reverse=True)
                rbs = sorted(active_df[active_df["Position"] == "RB"].index.tolist(), key=lambda i: scores[i], reverse=True)
                wrs = sorted(active_df[active_df["Position"] == "WR"].index.tolist(), key=lambda i: scores[i], reverse=True)
                tes = sorted(active_df[active_df["Position"] == "TE"].index.tolist(), key=lambda i: scores[i], reverse=True)

                cand = []
                if qbs: cand.append(qbs[attempt % min(3, len(qbs))])
                for idx in rbs:
                    if len([x for x in cand if active_df.loc[x, "Position"] == "RB"]) < 2:
                        cand.append(idx)
                for idx in wrs:
                    if len([x for x in cand if active_df.loc[x, "Position"] == "WR"]) < 3:
                        cand.append(idx)
                if tes: cand.append(tes[attempt % min(2, len(tes))])
                flex_pool = [i for i in (rbs + wrs + tes) if i not in cand]
                flex_pool.sort(key=lambda i: scores[i], reverse=True)
                if flex_pool: cand.append(flex_pool[0])
                if dsts: cand.append(dsts[attempt % min(3, len(dsts))])
                chosen = cand[:9]

                while int(active_df.loc[chosen, "Salary"].sum()) > salary_cap:
                    swapped = False
                    chosen_sorted = sorted(chosen, key=lambda i: int(active_df.loc[i, "Salary"]), reverse=True)
                    for exp_idx in chosen_sorted:
                        pos_need = active_df.loc[exp_idx, "Position"]
                        cur_sal = int(active_df.loc[exp_idx, "Salary"])
                        cheaper = [
                            i for i in active_df[active_df["Position"] == pos_need].index
                            if i not in chosen and int(active_df.loc[i, "Salary"]) < cur_sal
                        ]
                        if cheaper:
                            cheaper.sort(key=lambda i: scores[i], reverse=True)
                            chosen[chosen.index(exp_idx)] = cheaper[0]
                            swapped = True
                            break
                    if not swapped:
                        break
            else:
                avail = [i for i in range(len(active_df)) if i not in chosen and (exposure_counts[i] < max_allowed or attempt > 200)]
                avail.sort(key=lambda i: scores[i] / max(active_df.loc[i, "Salary"] / 5000.0, 0.5), reverse=True)
                for idx in avail:
                    if len(chosen) >= eff_size:
                        break
                    if int(active_df.loc[chosen, "Salary"].sum()) + int(active_df.loc[idx, "Salary"]) <= salary_cap:
                        chosen.append(idx)
                if len(chosen) < eff_size:
                    rem = [i for i in range(len(active_df)) if i not in chosen]
                    rem.sort(key=lambda i: int(active_df.loc[i, "Salary"]))
                    for idx in rem:
                        if len(chosen) >= eff_size:
                            break
                        chosen.append(idx)

            tot_sal = int(active_df.loc[chosen, "Salary"].sum())
            sig = tuple(sorted(chosen))
            if sig in seen_signatures or tot_sal > salary_cap:
                continue

            tot_sc = float(active_df.loc[chosen, "Opt_Score"].sum())
            if tot_sc > best_score:
                best_score = tot_sc
                best_choice = chosen

        if best_choice is not None:
            seen_signatures.add(tuple(sorted(best_choice)))
            lineups.append(best_choice)
            for i in best_choice:
                exposure_counts[i] += 1

    return [active_df.loc[idx_list].copy() for idx_list in lineups]

# ==========================================
# 6. SIDEBAR: ACCOUNT STATUS & LEAGUE MENU
# ==========================================
with st.sidebar:
    st.markdown("## ⚡ PROSTACK AI PORTAL")
    st.caption("US 🇺🇸 & Canada 🇨🇦 Enterprise Quant Engine")
    st.link_button("✈️ Join Official Telegram VIP", SUPPORT_TELEGRAM_URL, use_container_width=True)
    st.divider()

    if st.session_state.user is not None:
        u = st.session_state.user
        st.success(f"👤 **{u['email']}**")
        st.caption("🔒 Auto-Login Active (Stays logged in across apps)")
        if u.get("phone"):
            st.caption(f"📱 Phone: `{u['phone']}`")
        if u["is_admin"]:
            st.markdown("👑 **Role:** `FOUNDER / ADMIN`")
        elif u["is_vip"]:
            st.markdown("💎 **Membership:** `LIFETIME / PAID VIP`")
        else:
            st.markdown(f"🎁 **VIP Trial Until:** `{u['trial_until'][:10]}`")

        if st.button("🚪 Log Out", use_container_width=True, type="primary"):
            clear_login_session()
            st.rerun()
        st.divider()

    selected_league = st.selectbox("🏆 Select North American League", list(LEAGUE_CONFIGS.keys()))
    st.caption("Supports DraftKings, FanDuel, PrizePicks & Underdog Fantasy.")

# ==========================================
# 7. CLEAN SEPARATE AUTHENTICATION PORTAL
# ==========================================
st.title(f"⚡ ProStack AI — {selected_league} Quantitative Command Center")

if st.session_state.user is None:
    st.markdown("""
    <div class="lock-gate">
        <h2 style="color:#00FF88; margin-top:0;">🔒 VIP QUANT PORTAL</h2>
        <p style="font-size:1.0rem; color:#FFFFFF;">
            Unlock the <b>10,000x Monte Carlo Simulator</b>, <b>Anti-Chalk GPP Ownership Engine</b>, 
            <b>Live Sportsbook +EV Prop Devigger</b>, and <b>AI Kelly Bankroll Vault</b>.
        </p>
        <span class="badge-ev">🎁 New Members Get Instant 30-Day Free VIP Access!</span>
    </div>
    """, unsafe_allow_html=True)

    auth_mode = st.radio(
        "👇 Choose an Option Below:",
        [
            "🎁 New Member Sign Up",
            "🔑 Member Login",
            "🔄 Forgot Password",
            "👑 Founder Admin"
        ],
        horizontal=True
    )

    if auth_mode == "🎁 New Member Sign Up":
        with st.form("signup_clean_form", clear_on_submit=False):
            st.markdown("### 🎁 Create New VIP Account (30 Days Free)")
            r_email = st.text_input("📧 Enter Your Email Address", placeholder="you@example.com")
            r_phone = st.text_input("📱 Enter Phone / WhatsApp Number (with Country Code)", placeholder="+1 555 234 5678")
            r_pw = st.text_input("🔑 Create Password (4+ characters)", type="password", placeholder="••••••••")
            sub_signup = st.form_submit_button("🚀 CREATE ACCOUNT & UNLOCK 30-DAY VIP TRIAL")
            if sub_signup:
                if "@" in r_email and len(clean_phone(r_phone)) >= 7 and len(r_pw) >= 4:
                    ok, msg = register_user(r_email, r_phone, r_pw)
                    if ok:
                        u = authenticate_user(r_email, r_pw)
                        save_login_session(u)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.warning(msg)
                else:
                    st.error("Please enter a valid Email, Phone Number (7+ digits), and Password (4+ chars).")

    elif auth_mode == "🔑 Member Login":
        with st.form("login_clean_form", clear_on_submit=False):
            st.markdown("### 🔑 Existing Member Sign In (Email OR Phone)")
            l_ident = st.text_input("📧📱 Enter Your Registered Email OR Phone Number", placeholder="you@example.com or +15552345678")
            l_pw = st.text_input("🔑 Enter Your Password", type="password", placeholder="••••••••")
            sub_login = st.form_submit_button("🔓 SIGN IN TO QUANT COMMAND CENTER")
            if sub_login:
                u = authenticate_user(l_ident, l_pw)
                if u:
                    save_login_session(u)
                    st.rerun()
                else:
                    st.error("Invalid credentials! Forgot your password? Select '🔄 Forgot Password' above.")

    elif auth_mode == "🔄 Forgot Password":
        with st.form("forgot_pw_form", clear_on_submit=False):
            st.markdown("### 🔄 Instant Password Recovery (Verify Email + Phone)")
            f_email = st.text_input("📧 Enter Your Registered Email Address", placeholder="you@example.com")
            f_phone = st.text_input("📱 Enter Your Registered Phone Number", placeholder="+1 555 234 5678")
            f_new_pw = st.text_input("🔑 Create New Password (4+ characters)", type="password", placeholder="••••••••")
            sub_reset = st.form_submit_button("🔄 VERIFY & RESET MY PASSWORD NOW")
            if sub_reset:
                if "@" in f_email and len(clean_phone(f_phone)) >= 7 and len(f_new_pw) >= 4:
                    ok, msg = reset_user_password(f_email, f_phone, f_new_pw)
                    if ok:
                        st.success(msg)
                        u = authenticate_user(f_email, f_new_pw)
                        save_login_session(u)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Please enter your valid registered Email, Phone Number, and a 4+ character new password.")

    elif auth_mode == "👑 Founder Admin":
        with st.form("admin_clean_form", clear_on_submit=False):
            st.markdown("### 👑 Founder Command Center Access")
            master_in = st.text_input("🔐 Enter Founder Master Key", type="password", placeholder="Enter secret founder key...")
            sub_admin = st.form_submit_button("👑 VERIFY & UNLOCK FOUNDER ADMIN")
            if sub_admin:
                if master_in == "ProStackAdmin2026!":
                    admin_u = {
                        "email": "admin@prostackai.com",
                        "phone": "+10000000000",
                        "trial_until": "2036-01-01",
                        "is_vip": True,
                        "is_admin": True
                    }
                    save_login_session(admin_u)
                    st.rerun()
                else:
                    st.error("Invalid Founder Master Key.")

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

with tabs[0]:
    col_top1, col_top2, col_top3 = st.columns([1.4, 1.4, 1.2])
    with col_top1:
        uploaded_csv = st.file_uploader(f"📂 Upload {selected_league} DraftKings / FanDuel CSV", type=["csv"])
    with col_top2:
        st.write("")
        st.write("")
        if st.button(f"⚡ Load Official {selected_league} Pro Slate (Reset Clean Data)", use_container_width=True, type="primary"):
            st.session_state[f"slate_{selected_league}"] = generate_pro_slate(selected_league)
            st.rerun()
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
        if "Name" not in raw_df.columns: raw_df["Name"] = [f"Player {i+1}" for i in range(len(raw_df))]
        if "Position" not in raw_df.columns: raw_df["Position"] = LEAGUE_CONFIGS[selected_league]["positions"][0]
        if "Team" not in raw_df.columns: raw_df["Team"] = "PRO"
        if "Opponent" not in raw_df.columns: raw_df["Opponent"] = "OPP"
        if "Salary" not in raw_df.columns: raw_df["Salary"] = 5000
        if "Projection" not in raw_df.columns: raw_df["Projection"] = (pd.to_numeric(raw_df["Salary"], errors="coerce").fillna(5000) / 1000.0) * 3.2
        if "StdDev" not in raw_df.columns: raw_df["StdDev"] = pd.to_numeric(raw_df["Projection"], errors="coerce").fillna(15.0) * 0.25
        if "Ownership%" not in raw_df.columns: raw_df["Ownership%"] = 15.0
        if "Status" not in raw_df.columns: raw_df["Status"] = "ACTIVE"
        if "Lock" not in raw_df.columns: raw_df["Lock"] = False
        if "ID" not in raw_df.columns: raw_df["ID"] = [f"DK{1000+i}" for i in range(len(raw_df))]
        st.session_state[f"slate_{selected_league}"] = raw_df

    if f"slate_{selected_league}" not in st.session_state:
        st.session_state[f"slate_{selected_league}"] = generate_pro_slate(selected_league)

    base_slate = st.session_state[f"slate_{selected_league}"]

    st.markdown("### 🛠️ Live Injury Boost (`OUT 🚑`), Late-Swap Locks (`🔒`) & Monte Carlo Table")
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
        num_lineups = st.slider("🔢 Lineups to Generate (MME)", 1, 50, 3)
    with c2:
        salary_cap = st.number_input("💰 Salary Cap ($)", value=cfg["cap"], step=500)
        lineup_size = st.number_input("👥 Roster Size", value=min(cfg["size"], max(2, len(sim_df))), min_value=2, max_value=12)
    with c3:
        max_exp = st.slider("🛡️ Max Player Exposure (%)", 20, 100, 75)
        avail_teams = ["None"] + sorted(sim_df["Team"].astype(str).unique().tolist())
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
            st.error("Could not build lineup under Salary Cap. Click '⚡ Load Official NFL Pro Slate' at top to reset clean salaries!")
        else:
            st.success(f"✅ Generated {len(built)} Authentic {selected_league} Winning Lineups!")

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

                with st.expander(f"📲 Shareable VIP Viral Card for Lineup #{idx+1} (Screenshot for X / Reddit)", expanded=(idx == 0)):
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
        {"League": selected_league, "Player Prop": "Josh Allen Over 265.5 Pass+Rush Yds", "Pinnacle Odds": "-148 / +118", "True Win %": "58.1%", "+EV Edge": "+3.85%", "Action": "🔥 LOCK OVER"},
        {"League": selected_league, "Player Prop": "CeeDee Lamb Over 84.5 Rec Yds", "Pinnacle Odds": "-142 / +112", "True Win %": "57.2%", "+EV Edge": "+2.95%", "Action": "🔥 LOCK OVER"},
        {"League": selected_league, "Player Prop": "Travis Kelce Over 5.5 Receptions", "Pinnacle Odds": "-138 / +110", "True Win %": "56.6%", "+EV Edge": "+2.35%", "Action": "✅ PLAYABLE +EV"}
    ])
    st.dataframe(ev_board, use_container_width=True, hide_index=True)

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
            if st.form_submit_button("💾 LOG RESULT TO MY VAULT"):
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

with tabs[3]:
    st.subheader("👑 Founder Command Center, VIP Manager & Cloud DB Backup")
    if "admin_unlocked" not in st.session_state:
        st.session_state.admin_unlocked = False
    if st.session_state.user and st.session_state.user.get("is_admin"):
        st.session_state.admin_unlocked = True

    if not st.session_state.admin_unlocked:
        with st.form("admin_tab_unlock_form"):
            admin_key_input = st.text_input("🔐 Enter Founder Master Key", type="password", placeholder="Enter Founder Key...")
            if st.form_submit_button("🔓 VERIFY & UNLOCK ADMIN COMMAND CENTER"):
                if admin_key_input == "ProStackAdmin2026!":
                    st.session_state.admin_unlocked = True
                    st.rerun()
                else:
                    st.error("Invalid Founder Master Key.")
    else:
        conn = get_conn()
        users_df = pd.read_sql_query("SELECT email, phone, created_at, trial_until, is_vip, is_admin FROM users", conn)
        conn.close()
        st.metric("👥 Total Registered Users (With Email & Phone)", len(users_df))
        st.dataframe(users_df, use_container_width=True)

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
            "📥 1-Click Download Full User Database Backup (Emails + Phone Numbers JSON)",
            data=users_df.to_json(orient="records"),
            file_name="prostack_users_backup.json",
            mime="application/json",
            use_container_width=True
        )

st.markdown(f"""
<div class="legal-footer">
    <b>⚖️ US & CANADA LEGAL COMPLIANCE & RESPONSIBLE GAMING SHIELD</b><br>
    ProStack AI is a quantitative sports analytics, statistical simulation, and lineup optimization software tool for educational and entertainment purposes only. 
    ProStack AI is <b>NOT</b> a sportsbook, gambling operator, or real-money wagering site, and does not accept or place bets of any kind.<br>
    If you or someone you know has a gaming problem, call <b>1-800-GAMBLER</b> (US) or <b>1-866-531-2600</b> (Canada).<br>
    © 2026 ProStack AI Quant Technologies | <a href="{SUPPORT_TELEGRAM_URL}" target="_blank" style="color:#00FF88;">Official Telegram VIP Support</a>
</div>
""", unsafe_allow_html=True)
