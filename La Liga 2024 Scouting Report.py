import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch

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

# --- Data Loading from CSV files ---
@st.cache_data
def load_data():
    match_data = pd.read_csv('file/match_data.csv')
    team_match_stats = pd.read_csv('file/match_info.csv')
    player_stats = pd.read_csv('file/player.csv')
    season = pd.read_csv('season.csv')
    shots = pd.read_csv('file/shot_data.csv')
    return shots, team_match_stats, player_stats, match_data, season

shots, team_match_stats, player_stats = load_data()

# --- Calculate ranking_liga from player_stats (no separate CSV needed) ---
# Filter out goalkeepers for threat score
player_stats_no_g = player_stats[player_stats['position'] != 'GK S'].copy()

# Calculate attacking threat score
player_stats_no_g['threat_score'] = (
    player_stats_no_g['goals'] * 1.0 +
    player_stats_no_g['assists'] * 0.8 +
    player_stats_no_g['xg'] * 0.7 +
    player_stats_no_g['xa'] * 0.6 +
    player_stats_no_g['shots'] * 0.3 +
    player_stats_no_g['key_passes'] * 0.4
)

# Sort by threat score and add rank
ranking_liga = player_stats_no_g.sort_values('threat_score', ascending=False).copy()
ranking_liga['rank'] = range(1, len(ranking_liga) + 1)

# Calculate per game metrics
player_stats['goals_assists_pg'] = (player_stats['goals'] + player_stats['assists']) / player_stats['matches']
player_stats['key_passes_pg'] = player_stats['key_passes'] / player_stats['matches']
player_stats['xg_pg'] = player_stats['xg'] / player_stats['matches']
player_stats['xa_pg'] = player_stats['xa'] / player_stats['matches']
player_stats['shots_pg'] = player_stats['shots'] / player_stats['matches']
player_stats['xg_buildup_pg'] = player_stats['xg_buildup'] / player_stats['matches']

# Calculate position averages for ratios
position_avg = player_stats.groupby('position')[['goals_assists_pg', 'key_passes_pg', 'xg_pg', 
                                                   'xa_pg', 'shots_pg', 'xg_buildup_pg']].mean().reset_index()

# --- All your visualization functions go here (unchanged) ---
# (display_basic_player_stats, plot_divergent_bars, plot_shot_map, plot_team_impact)

# --- Sidebar for Player Selection ---
st.sidebar.header("Player Selection")

sort_option = st.sidebar.radio("Sort Players By:", ('Alphabetical', 'By Threat Rank'))

if sort_option == 'Alphabetical':
    player_list = sorted(player_stats['player'].unique().tolist())
else:
    player_list = ranking_liga['player'].tolist()

selected_player = st.sidebar.selectbox("Select a Player:", player_list)


# --- Main App Content ---
if selected_player:
    st.header(f"Scouting Report for {selected_player}")

    tab1, tab2, tab3, tab4 = st.tabs(["Full Report", "Performance Profile", "Shot Map", "Team Impact"])

    with tab1:
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**Instructions or notes for this report:**")
            st.write("- Add your manual information here")
            st.write("- Explain what percentiles and ratios mean")
            st.write("- Data context (La Liga 2023-24)")
        display_basic_player_stats(selected_player)

    with tab2:
        st.subheader("Performance Profile (vs Position Average)")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**How to interpret this chart:**")
            st.write("- Bars to the right (green): Better than position average")
            st.write("- Bars to the left (red): Worse than position average")
            st.write("- Vertical line at 0: Position average (1.0x)")
        st.caption("→ Better than average | ← Worse than average | = Average (1.0x)")
        plot_divergent_bars(selected_player)

    with tab3:
        st.subheader("Shot Map")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**How to interpret the shot map:**")
            st.write("- 🟢 Green: Goal")
            st.write("- 🟠 Orange: Saved or hit post")
            st.write("- 🔴 Red: Missed")
            st.write("- ⚪ Gray: Blocked")
        plot_shot_map(selected_player)

    with tab4:
        st.subheader("Player Impact on Team")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**How to interpret player impact:**")
            st.write("- xG Generated: Expected goals created by team with the player")
            st.write("- PPDA: Pressing intensity (lower = better pressing)")
            st.write("- Δ positive (green) = Better than league average")
            st.write("- Δ negative (red) = Worse than league average")
        plot_team_impact(selected_player)
else:
    st.info("Please select a player from the left sidebar to view their scouting report.")
