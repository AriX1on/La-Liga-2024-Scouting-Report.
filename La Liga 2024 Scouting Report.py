import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- Streamlit Configuration ---
st.set_page_config(layout="wide", page_title="La Liga Player Scouting Report")
st.title("⚽ La Liga Player Scouting Report")

# --- Custom CSS for larger tab font ---
st.markdown("""
    <style>
        button[data-baseweb="tab"] {
            font-size: 20px !important;
            font-weight: 500 !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- Data Loading Functions (cached for performance) ---
@st.cache_data
def load_data():
    player_stats = pd.read_csv('file/player.csv')
    shots = pd.read_csv('file/shot_data.csv')
    team_match_stats = pd.read_csv('file/match_info.csv')
    return player_stats, shots, team_match_stats

player_stats, shots, team_match_stats = load_data()

# --- Columnas esperadas (nombres originales de Understat) ---
required_player_cols = {
    'player', 'position', 'team', 'goals', 'assists', 'xg', 'xa',
    'shots', 'key_passes', 'matches', 'minutes', 'yellow_cards', 'xg_buildup'
}
required_shot_cols = {
    'player_id', 'location_x', 'location_y', 'result', 'xg'
}
required_match_cols = {
    'home_team', 'away_team', 'home_xg', 'away_xg', 'home_ppda', 'away_ppda',
    'home_goals', 'away_goals'
}

missing_player_cols = required_player_cols - set(player_stats.columns)
missing_shot_cols = required_shot_cols - set(shots.columns)
missing_match_cols = required_match_cols - set(team_match_stats.columns)

if missing_player_cols or missing_shot_cols or missing_match_cols:
    st.error("Los archivos no tienen el formato esperado.")
    if missing_player_cols:
        st.write(f"Faltan en player.csv: {sorted(missing_player_cols)}")
    if missing_shot_cols:
        st.write(f"Faltan en shot_data.csv: {sorted(missing_shot_cols)}")
    if missing_match_cols:
        st.write(f"Faltan en match_info.csv: {sorted(missing_match_cols)}")
    st.stop()

# Convertir a numérico
numeric_cols = ['goals', 'assists', 'xg', 'xa', 'shots', 'key_passes', 'matches', 'minutes', 'yellow_cards', 'xg_buildup']
for col in numeric_cols:
    player_stats[col] = pd.to_numeric(player_stats[col], errors='coerce').fillna(0)

# --- Additional Metrics Calculation ---
player_stats['threat_score'] = (
    player_stats['goals'] * 1.0 +
    player_stats['assists'] * 0.8 +
    player_stats['xg'] * 0.7 +
    player_stats['xa'] * 0.6 +
    player_stats['shots'] * 0.3 +
    player_stats['key_passes'] * 0.4
)

ranking_liga = player_stats.sort_values('threat_score', ascending=False).copy()
ranking_liga['rank'] = range(1, len(ranking_liga) + 1)

# Per game metrics
player_stats['goals_assists_pg'] = player_stats['goals_assists_pg'] = (player_stats['goals'] + player_stats['assists']) / player_stats['matches'].replace(0, np.nan)
player_stats['key_passes_pg'] = player_stats['key_passes'] / player_stats['matches'].replace(0, np.nan)
player_stats['xg_pg'] = player_stats['xg'] / player_stats['matches'].replace(0, np.nan)
player_stats['xa_pg'] = player_stats['xa'] / player_stats['matches'].replace(0, np.nan)
player_stats['shots_pg'] = player_stats['shots'] / player_stats['matches'].replace(0, np.nan)
player_stats['xg_buildup_pg'] = player_stats['xg_buildup'] / player_stats['matches'].replace(0, np.nan)

player_stats.fillna(0, inplace=True)

# Position averages
position_avg = player_stats.groupby('position')[[
    'goals_assists_pg', 'key_passes_pg', 'xg_pg', 'xa_pg', 'shots_pg', 'xg_buildup_pg'
]].mean().reset_index()

# --- Resto de tus funciones (display_basic_player_stats, plot_divergent_bars, plot_team_impact) ---
# ... (copia aquí tus funciones adaptadas) ...

# --- Sidebar ---
st.sidebar.header("Player Selection")
sort_option = st.sidebar.radio("Sort Players By:", ('Alphabetical', 'By Threat Rank'))

if sort_option == 'Alphabetical':
    player_list = sorted(player_stats['player'].unique().tolist())
else:
    player_list = ranking_liga['player'].tolist()

selected_player = st.sidebar.selectbox("Select a Player:", player_list)

# --- Main Content ---
if selected_player:
    st.header(f"Scouting Report for {selected_player}")
    tab1, tab2, tab3 = st.tabs(["Full Report", "Performance Profile", "Team Impact"])

    with tab1:
        display_basic_player_stats(selected_player)
    with tab2:
        st.subheader("Performance Profile (vs Position Average)")
        plot_divergent_bars(selected_player)
    with tab3:
        st.subheader("Team Impact")
        plot_team_impact(selected_player)
else:
    st.info("Select a player from the left sidebar")
