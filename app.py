import streamlit as st
import pandas as pd
import pulp

st.set_page_config(page_title="ProStack AI - Pro", page_icon="🚀", layout="wide")

st.title("🚀 ProStack AI - NFL DFS Optimizer")
st.markdown("**Phase 2: CSV Upload, Injury Controls & Mass Entry Download**")

# --- SIDEBAR: SETTINGS & UPLOAD ---
st.sidebar.header("⚙️ Settings & Data")
uploaded_file = st.sidebar.file_uploader("Upload Player Pool (CSV)", type=["csv"])
num_lineups = st.sidebar.slider("Number of Lineups", 1, 150, 10)
salary_cap = st.sidebar.number_input("Max Salary Cap", value=50000, step=1000)

# --- LOAD DATA ---
@st.cache_data
def load_dummy_data():
    return pd.DataFrame({
        "Name": ["Patrick Mahomes", "Josh Allen", "C. McCaffrey", "Austin Ekeler", "Tyreek Hill", "J. Jefferson", "Travis Kelce", "Stefon Diggs", "D. Adams"],
        "Pos": ["QB", "QB", "RB", "RB", "WR", "WR", "TE", "WR", "WR"],
        "Salary": [8000, 7800, 9000, 8500, 8800, 8600, 7500, 8200, 8100],
        "Points": [24.5, 23.0, 21.0, 19.5, 22.0, 20.5, 18.0, 19.0, 18.5]
    })

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.sidebar.success("Real Data Uploaded Successfully! ✅")
    except Exception as e:
        st.sidebar.error("Error reading CSV. Check format.")
        df = load_dummy_data()
else:
    st.sidebar.info("Using Demo Data. Upload real CSV for actual matches.")
    df = load_dummy_data()

# --- MAIN UI: INJURY & LOCK CONTROL ---
st.subheader("📊 Player Pool & Manual Adjustments")
st.markdown("News aayi hai? Khiladi injured hai? Yahan se turant bahar nikalein (Exclude) ya pakka slect karein (Lock).")

col1, col2 = st.columns(2)
with col1:
    exclude_players = st.multiselect("❌ Exclude Players (Injured/Out)", df["Name"].tolist())
with col2:
    lock_players = st.multiselect("🔒 Lock Players (Must Have)", df["Name"].tolist())

st.dataframe(df, use_container_width=True)

# --- ENGINE ---
def generate_lineups(data, num_lineups, cap, exclude_list, lock_list):
    lineups = []
    # Remove Excluded Players
    data = data[~data["Name"].isin(exclude_list)].copy()
    data = data.reset_index(drop=True)
    
    for i in range(num_lineups):
        prob = pulp.LpProblem(f"Lineup_{i}", pulp.LpMaximize)
        player_vars = pulp.LpVariable.dicts("Players", data.index, cat='Binary')
        
        # Maximize Points
        prob += pulp.lpSum([data["Points"][i] * player_vars[i] for i in data.index])
        
        # Keep under Salary Cap
        prob += pulp.lpSum([data["Salary"][i] * player_vars[i] for i in data.index]) <= cap
        
        # Select exactly 5 players (Simplified for MVP)
        prob += pulp.lpSum([player_vars[i] for i in data.index]) == 5
        
        # Apply Locks
        for lock_name in lock_list:
            lock_idx = data[data["Name"] == lock_name].index
            if len(lock_idx) > 0:
                prob += player_vars[lock_idx[0]] == 1
                
        # Diversity (Don't repeat same lineup)
        for prev_lineup in lineups:
            prob += pulp.lpSum([player_vars[idx] for idx in data.index if data["Name"][idx] in prev_lineup]) <= 4
            
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        if pulp.LpStatus[prob.status] == 'Optimal':
            selected = [data["Name"][idx] for idx in data.index if player_vars[idx].varValue == 1]
            lineups.append(selected)
        else:
            break
    return lineups

# --- OUTPUT & DOWNLOAD ---
if st.button("⚡ Generate Winning Lineups"):
    with st.spinner("AI is calculating probabilities..."):
        final_lineups = generate_lineups(df, num_lineups, salary_cap, exclude_players, lock_players)
        
    if final_lineups:
        st.success(f"✅ Successfully generated {len(final_lineups)} optimized lineups!")
        
        # Create Table
        lineup_df = pd.DataFrame(final_lineups, columns=["Player 1", "Player 2", "Player 3", "Player 4", "Player 5"])
        lineup_df.index = [f"Lineup {i+1}" for i in range(len(lineup_df))]
        st.table(lineup_df)
        
        # Download Button
        csv_data = lineup_df.to_csv().encode('utf-8')
        st.download_button(
            label="💾 Download Lineups for DFS (CSV)",
            data=csv_data,
            file_name="ProStack_Lineups.csv",
            mime="text/csv",
        )
    else:
        st.warning("Constraints are too tight! Try removing some locks or increasing salary cap.")
