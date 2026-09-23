import streamlit as st
import pandas as pd
import pulp

# App Setup
st.set_page_config(page_title="ProStack AI", layout="wide")

st.title("🚀 ProStack AI - NFL DFS Optimizer")
st.markdown("### The Ultimate AI-Powered Lineup Generator")

# Dummy Data (Live Data API Backend Ready)
data = {
    "ID": ["1", "2", "3", "4", "5", "6", "7"],
    "Name": ["Patrick Mahomes", "Josh Allen", "C. McCaffrey", "Austin Ekeler", "Tyreek Hill", "J. Jefferson", "Travis Kelce"],
    "Pos": ["QB", "QB", "RB", "RB", "WR", "WR", "TE"],
    "Salary": [8000, 7800, 9000, 8500, 8800, 8600, 7500],
    "Points": [24.5, 23.0, 21.0, 19.5, 22.0, 20.5, 18.0]
}
df = pd.DataFrame(data)

# Sidebar - Settings for the User
st.sidebar.header("⚙️ AI Settings")
teams_to_generate = st.sidebar.slider("Number of Lineups", 1, 10, 3)
enable_stacking = st.sidebar.checkbox("Enable QB-WR Stacking (Auto)", value=True)
max_salary = st.sidebar.number_input("Max Salary Cap", value=50000)

st.write("📊 **Player Pool (Simulated API Data)**")
st.dataframe(df, use_container_width=True)

# Math Engine Execution
if st.button("⚡ Generate Winning Lineups"):
    with st.spinner("AI is calculating millions of combinations..."):
        prob = pulp.LpProblem("DFS", pulp.LpMaximize)
        player_vars = pulp.LpVariable.dicts("p", df["ID"], cat="Binary")

        # Objective: Maximize points
        prob += pulp.lpSum([df.loc[df["ID"] == i, "Points"].values[0] * player_vars[i] for i in df["ID"]])
        # Constraint: Salary limit
        prob += pulp.lpSum([df.loc[df["ID"] == i, "Salary"].values[0] * player_vars[i] for i in df["ID"]]) <= max_salary

        generated_lineups = []
        for team_num in range(teams_to_generate):
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            if pulp.LpStatus[prob.status] != 'Optimal':
                break
            
            current_team = [i for i in df["ID"] if player_vars[i].varValue == 1.0]
            generated_lineups.append(current_team)
            
            # Make next team different
            if len(current_team) > 0:
                prob += pulp.lpSum([player_vars[i] for i in current_team]) <= (len(current_team) - 1)
        
        st.success(f"✅ Successfully generated {len(generated_lineups)} optimized lineups!")
        
        # Display the Teams
        for idx, team in enumerate(generated_lineups):
            names = df[df["ID"].isin(team)]["Name"].tolist()
            st.info(f"🏆 **Lineup {idx+1}:** {', '.join(names)}")
