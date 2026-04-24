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

# --- Data Loading (con separador correcto ';') ---
@st.cache_data
def load_data():
    player_stats = pd.read_csv('file/player.csv', sep=None, engine='python')
    shots = pd.read_csv('file/shot_data.csv', sep=None, engine='python')
    team_match_stats = pd.read_csv('file/match_info.csv', sep=None, engine='python')
    return player_stats, shots, team_match_stats

player_stats, shots, team_match_stats = load_data()

# --- Convertir a numérico ---
player_stats['goals'] = pd.to_numeric(player_stats['goals'], errors='coerce').fillna(0)
player_stats['assists'] = pd.to_numeric(player_stats['assists'], errors='coerce').fillna(0)
player_stats['xG'] = pd.to_numeric(player_stats['xG'], errors='coerce').fillna(0)
player_stats['xA'] = pd.to_numeric(player_stats['xA'], errors='coerce').fillna(0)
player_stats['shots'] = pd.to_numeric(player_stats['shots'], errors='coerce').fillna(0)
player_stats['key_passes'] = pd.to_numeric(player_stats['key_passes'], errors='coerce').fillna(0)
player_stats['games'] = pd.to_numeric(player_stats['games'], errors='coerce').fillna(0)
player_stats['time'] = pd.to_numeric(player_stats['time'], errors='coerce').fillna(0)
player_stats['yellow_cards'] = pd.to_numeric(player_stats['yellow_cards'], errors='coerce').fillna(0)
player_stats['xGBuildup'] = pd.to_numeric(player_stats['xGBuildup'], errors='coerce').fillna(0)

# --- Calcular Threat Score ---
player_stats['threat_score'] = (
    player_stats['goals'] * 1.0 +
    player_stats['assists'] * 0.8 +
    player_stats['xG'] * 0.7 +
    player_stats['xA'] * 0.6 +
    player_stats['shots'] * 0.3 +
    player_stats['key_passes'] * 0.4
)

ranking_liga = player_stats.sort_values('threat_score', ascending=False).copy()
ranking_liga['rank'] = range(1, len(ranking_liga) + 1)

# --- Per game metrics ---
player_stats['goals_assists_pg'] = (player_stats['goals'] + player_stats['assists']) / player_stats['games'].replace(0, np.nan)
player_stats['key_passes_pg'] = player_stats['key_passes'] / player_stats['games'].replace(0, np.nan)
player_stats['xg_pg'] = player_stats['xG'] / player_stats['games'].replace(0, np.nan)
player_stats['xa_pg'] = player_stats['xA'] / player_stats['games'].replace(0, np.nan)
player_stats['shots_pg'] = player_stats['shots'] / player_stats['games'].replace(0, np.nan)
player_stats['xg_buildup_pg'] = player_stats['xGBuildup'] / player_stats['games'].replace(0, np.nan)

player_stats.fillna(0, inplace=True)

# --- Position averages ---
position_avg = player_stats.groupby('position')[[
    'goals_assists_pg', 'key_passes_pg', 'xg_pg', 'xa_pg', 'shots_pg', 'xg_buildup_pg'
]].mean().reset_index()

# --- Funciones de visualización ---

def display_basic_player_stats(player_name):
    player_data = player_stats[player_stats['player_name'] == player_name].iloc[0]
    player_pos = player_data['position']
    player_team = player_data['team_title']

    st.subheader(f"Basic Stats for {player_name}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Position", player_data['position'])
        st.metric("Goals", int(player_data['goals']))
    with col2:
        st.metric("Matches", int(player_data['games']))
        st.metric("Assists", int(player_data['assists']))
    with col3:
        st.metric("Minutes", int(player_data['time']))
        st.metric("Yellow Cards", int(player_data['yellow_cards']))

    # --- Offensive Threat Ranking ---
    st.subheader("Offensive Threat Ranking")
    player_rank_data = ranking_liga[ranking_liga['player_name'] == player_name].iloc[0]
    player_rank = player_rank_data['rank']
    player_threat_score = player_rank_data['threat_score']
    avg_threat = ranking_liga['threat_score'].mean()
    threat_ratio = player_threat_score / avg_threat if avg_threat > 0 else 1.0

    st.write(f"**Rank:** #{player_rank} of {len(ranking_liga)} players")
    st.write(f"**Threat Score:** {player_threat_score:.1f}")
    st.write(f"**vs League Avg:** **{threat_ratio:.2f}x**")

    if threat_ratio >= 1.5:
        st.success(f"Elite threat ({threat_ratio:.2f}x above average)")
    elif threat_ratio >= 1.2:
        st.info(f"Above average ({threat_ratio:.2f}x)")
    elif threat_ratio >= 0.8:
        st.warning(f"Average threat ({threat_ratio:.2f}x)")
    else:
        st.error(f"Below average ({threat_ratio:.2f}x)")

    # --- Player Profile Ratios ---
    metrics = ['goals_assists_pg', 'key_passes_pg', 'xg_pg', 'xa_pg', 'shots_pg', 'xg_buildup_pg']
    metric_names = ['Goals+Assists', 'Key passes', 'xG', 'xA', 'Shots', 'xBuildup']

    pos_avg = position_avg[position_avg['position'] == player_pos].iloc[0]

    ratios = []
    for metric in metrics:
        player_val = player_data[metric]
        avg_val = pos_avg[metric]
        ratio = player_val / avg_val if avg_val > 0 else 1.0
        ratios.append(ratio)

    sorted_metrics = sorted(zip(metric_names, ratios), key=lambda x: x[1], reverse=True)

    st.subheader("Player Profile (vs Position Average)")
    for name, ratio in sorted_metrics:
        if ratio >= 1.5:
            color = "🟢"
        elif ratio >= 1.2:
            color = "🔵"
        elif ratio >= 0.8:
            color = "⚪"
        elif ratio >= 0.5:
            color = "🟡"
        else:
            color = "🔴"
        st.write(f"{color} **{name}**: **{ratio:.2f}x**")

def plot_divergent_bars(selected_player):
    player_data = player_stats[player_stats['player_name'] == selected_player].iloc[0]
    player_pos = player_data['position']
    pos_avg = position_avg[position_avg['position'] == player_pos].iloc[0]

    metrics = ['goals_assists_pg', 'key_passes_pg', 'xg_pg', 'xa_pg', 'shots_pg', 'xg_buildup_pg']
    metric_names = ['Goals+Assists', 'Key passes', 'xG', 'xA', 'Shots', 'xBuildup']

    offsets = []
    ratios = []
    for metric in metrics:
        player_val = player_data[metric]
        avg_val = pos_avg[metric]
        ratio = player_val / avg_val if avg_val > 0 else 1.0
        ratios.append(ratio)
        offsets.append(ratio - 1.0)

    sorted_pairs = sorted(zip(metric_names, offsets, ratios), key=lambda x: x[1], reverse=True)
    sorted_names = [p[0] for p in sorted_pairs]
    sorted_offsets = [p[1] for p in sorted_pairs]
    sorted_ratios = [p[2] for p in sorted_pairs]

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['#2ecc71' if offset > 0 else '#e74c3c' for offset in sorted_offsets]

    bars = ax.barh(sorted_names, sorted_offsets, color=colors, edgecolor='black', alpha=0.8)
    ax.axvline(x=0, color='black', linewidth=1.5, linestyle='-')

    for bar, offset, ratio in zip(bars, sorted_offsets, sorted_ratios):
        if offset > 0:
            ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2, f'{ratio:.2f}x', va='center')
        else:
            ax.text(bar.get_width() - 0.02, bar.get_y() + bar.get_height()/2, f'{ratio:.2f}x', va='center', ha='right')

    ax.set_xlabel('Difference from position average')
    ax.set_title(f'{selected_player} - Performance Profile')
    plt.tight_layout()
    st.pyplot(fig)

def plot_shot_map(selected_player):
    # Buscar player_id usando la columna 'id' de player_stats
    player_id_row = player_stats[player_stats['player_name'] == selected_player]
    if len(player_id_row) == 0:
        st.warning(f"No player ID for {selected_player}")
        return
    
    player_id = player_id_row['id'].values[0]

    # Filtrar disparos del jugador
    player_shots = shots[shots['player_id'] == player_id].copy()
    if len(player_shots) == 0:
        st.info(f"No shots found for {selected_player}")
        return

    pitch = Pitch(pitch_type='statsbomb', half=True, pitch_color='grass', line_color='white')
    fig, ax = pitch.draw(figsize=(10, 7))

    color_map = {
        'Goal': 'green',
        'SavedShot': 'orange',
        'MissedShot': 'red',
        'BlockedShot': 'gray'
    }

    for _, shot in player_shots.iterrows():
        x = shot['X'] * 120
        y = (1 - shot['Y']) * 80
        result = shot['result']
        color = color_map.get(result, 'blue')
        pitch.scatter(x, y, s=150, c=color, edgecolor='black', alpha=0.8, ax=ax)

    ax.set_title(f'{selected_player} - Shot Map ({len(player_shots)} shots)')
    st.pyplot(fig)

def plot_team_impact(selected_player):
    player_team_row = player_stats[player_stats['player_name'] == selected_player]['team_title']
    if len(player_team_row) == 0:
        st.warning(f"No team for {selected_player}")
        return
    player_team = player_team_row.values[0]

    team_matches = team_match_stats[
        (team_match_stats['team_h'] == player_team) |
        (team_match_stats['team_a'] == player_team)
    ]

    if team_matches.empty:
        st.info(f"No matches for {player_team}")
        return

    # Calcular promedios
    team_xg = (team_matches['h_xg'].mean() + team_matches['a_xg'].mean())
    team_ppda = (team_matches['h_ppda'].mean() + team_matches['a_ppda'].mean()) / 2
    league_xg = (team_match_stats['h_xg'].mean() + team_match_stats['a_xg'].mean()) / 2
    league_ppda = (team_match_stats['h_ppda'].mean() + team_match_stats['a_ppda'].mean()) / 2

    xg_diff = team_xg - league_xg
    ppda_diff = league_ppda - team_ppda

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # xG
    ax1.barh(['League Avg', 'Team Avg'], [league_xg, team_xg], color=['gray', 'green' if xg_diff > 0 else 'red'])
    ax1.axvline(x=league_xg, color='gray', linestyle='--')
    ax1.set_xlabel('xG per game')
    ax1.set_title(f'xG Generated: {player_team}')

    # PPDA
    ax2.barh(['League Avg', 'Team Avg'], [league_ppda, team_ppda], color=['gray', 'green' if team_ppda < league_ppda else 'red'])
    ax2.axvline(x=league_ppda, color='gray', linestyle='--')
    ax2.set_xlabel('PPDA (lower = better)')
    ax2.set_title(f'Pressing: {player_team}')

    plt.tight_layout()
    st.pyplot(fig)


# --- Sidebar ---
st.sidebar.header("Player Selection")
sort_option = st.sidebar.radio("Sort Players By:", ('Alphabetical', 'By Threat Rank'))

if sort_option == 'Alphabetical':
    player_list = sorted(player_stats['player_name'].unique().tolist())
else:
    player_list = ranking_liga['player_name'].tolist()

selected_player = st.sidebar.selectbox("Select a Player:", player_list)

# --- Main Content ---
if selected_player:
    st.header(f"Scouting Report for {selected_player}")

    tab1, tab2, tab3, tab4 = st.tabs(["Full Report", "Performance Profile", "Shot Map", "Team Impact"])

    with tab1:
        display_basic_player_stats(selected_player)
    with tab2:
        plot_divergent_bars(selected_player)
    with tab3:
        plot_shot_map(selected_player)
    with tab4:
        plot_team_impact(selected_player)
else:
    st.info("Select a player from the left sidebar")
