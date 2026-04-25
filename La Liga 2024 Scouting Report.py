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

# --- Data Loading ---
@st.cache_data
def load_data():
    player_stats = pd.read_csv('file/player.csv', sep=None, engine='python')
    shots = pd.read_csv('file/shot_data.csv', sep=None, engine='python')
    team_match_stats = pd.read_csv('file/match_info.csv', sep=None, engine='python')
    season = pd.read_csv('file/season.csv', sep=None, engine='python')
    return player_stats, shots, team_match_stats, season

player_stats, shots, team_match_stats, season = load_data()

# --- SEASON FILTER ---
st.sidebar.header("Season Filter")

available_seasons = sorted(season['year'].unique())
season_years = [str(y) for y in available_seasons]

col1, col2 = st.sidebar.columns(2)
with col1:
    min_season = st.selectbox("Min Season", options=['Any'] + season_years, index=0)
with col2:
    max_season = st.selectbox("Max Season", options=['Any'] + season_years, index=len(season_years))

mask = pd.Series([True] * len(season))
if min_season != 'Any':
    mask = mask & (season['year'] >= int(min_season))
if max_season != 'Any':
    mask = mask & (season['year'] <= int(max_season))

filtered_years = season[mask]['year'].unique().tolist()

# Filter player_stats
if 'season' in player_stats.columns:
    player_stats = player_stats[player_stats['season'].isin(filtered_years)]
elif 'year' in player_stats.columns:
    player_stats = player_stats[player_stats['year'].isin(filtered_years)]

# Filter shots by season
if 'date' in shots.columns:
    shots['year'] = pd.to_datetime(shots['date']).dt.year
    shots = shots[shots['year'].isin(filtered_years)]

# Filter team_match_stats by season
if 'date' in team_match_stats.columns:
    team_match_stats['year'] = pd.to_datetime(team_match_stats['date']).dt.year
    team_match_stats = team_match_stats[team_match_stats['year'].isin(filtered_years)]

# --- MERGE PLAYERS (multiple seasons) ---
numeric_cols = ['goals', 'assists', 'xG', 'xA', 'shots', 'key_passes', 'games', 'time', 'yellow_cards', 'xGBuildup']

for col in numeric_cols:
    if col in player_stats.columns:
        player_stats[col] = pd.to_numeric(player_stats[col], errors='coerce').fillna(0)

player_stats = player_stats.groupby('player_name').agg({
    'goals': 'sum',
    'assists': 'sum',
    'xG': 'sum',
    'xA': 'sum',
    'shots': 'sum',
    'key_passes': 'sum',
    'games': 'sum',
    'time': 'sum',
    'yellow_cards': 'sum',
    'xGBuildup': 'sum',
    'position': 'first',
    'team_title': 'first',
    'id': 'first'
}).reset_index()

# --- Calculate Threat Score ---
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


# --- VISUALIZATION FUNCTIONS ---

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

    # Team Context
    team_matches = team_match_stats[
        (team_match_stats['team_h'] == player_team) |
        (team_match_stats['team_a'] == player_team)
    ]

    if not team_matches.empty:
        team_ppda = (team_matches['h_ppda'].mean() + team_matches['a_ppda'].mean()) / 2
        league_ppda = (team_match_stats['h_ppda'].mean() + team_match_stats['a_ppda'].mean()) / 2
        relative_ppda = team_ppda / league_ppda if league_ppda else 1

        if relative_ppda < 0.9:
            press_text = "**High Press**: Team presses more than league average."
            press_icon = "🟢"
        elif relative_ppda <= 1.1:
            press_text = "**Balanced Press**: Team presses near league average."
            press_icon = "🟡"
        else:
            press_text = "**Low Block**: Team presses less than league average."
            press_icon = "🔴"

        st.subheader("Team Context")
        st.write(f"**{player_team}** {press_icon} {press_text}")
        st.caption(f"Team PPDA: **{team_ppda:.1f}** | League PPDA: **{league_ppda:.1f}** (lower = more pressing)")

        team_goals_total = (team_matches['h_goals'].sum() + team_matches['a_goals'].sum())
        if team_goals_total > 0 and player_data['goals'] > 0:
            dependency = (player_data['goals'] / team_goals_total) * 100
            if dependency > 25:
                st.write(f"**High dependency**: Involved in **{dependency:.0f}%** of team goals.")
            elif dependency > 15:
                st.write(f"**Important contributor**: Involved in **{dependency:.0f}%** of team goals.")
            else:
                st.write(f"**Collective contribution**: Involved in **{dependency:.0f}%** of team goals.")

    # Offensive Threat Ranking
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

    # Player Profile Ratios
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
    st.caption("Ratio > 1.0 = Better | Ratio = 1.0 = Average | Ratio < 1.0 = Worse")

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
    player_row = player_stats[player_stats['player_name'] == selected_player]
    if len(player_row) == 0:
        st.warning(f"No player ID for {selected_player}")
        return

    player_id = player_row['id'].values[0] if 'id' in player_row.columns else None
    if player_id is None:
        st.warning("No ID column found in player data")
        return

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
        'BlockedShot': 'gray',
        'ShotOnPost': 'orange'
    }

    for _, shot in player_shots.iterrows():
        x = shot['X'] * 120
        y = (1 - shot['Y']) * 80
        result = shot['result']
        color = color_map.get(result, None)
        if color:
            pitch.scatter(x, y, s=150, c=color, edgecolor='black', alpha=0.8, ax=ax)

    ax.set_title(f'{selected_player} - Shot Map ({len(player_shots)} shots)')
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='green', edgecolor='black', label='Goal'),
        Patch(facecolor='orange', edgecolor='black', label='Saved'),
        Patch(facecolor='red', edgecolor='black', label='Missed'),
        Patch(facecolor='gray', edgecolor='black', label='Blocked')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    st.pyplot(fig)


def plot_player_impact_estimate(selected_player):
    player_data = player_stats[player_stats['player_name'] == selected_player].iloc[0]
    player_team = player_data['team_title']
    player_minutes = player_data['time']
    player_games = player_data['games']
    
    # --- Get team's max minutes + 15% margin ---
    team_players = player_stats[player_stats['team_title'] == player_team]
    max_team_minutes = team_players['time'].max()
    max_possible_minutes = max_team_minutes * 1.15  # +15% realistic margin
    
    # Minutes percentage (with margin)
    minutes_pct = player_minutes / max_possible_minutes if max_possible_minutes > 0 else 0
    minutes_pct = min(minutes_pct, 1.0)
    
    # Filter team data by season
    if 'date' in team_match_stats.columns and 'year' not in team_match_stats.columns:
        team_match_stats['year'] = pd.to_datetime(team_match_stats['date'], errors='coerce').dt.year
    
    min_year = int(min_season) if min_season != 'Any' else None
    max_year = int(max_season) if max_season != 'Any' else None
    
    team_stats = team_match_stats.copy()
    if 'year' in team_stats.columns:
        if min_year: team_stats = team_stats[team_stats['year'] >= min_year]
        if max_year: team_stats = team_stats[team_stats['year'] <= max_year]
    
    team_matches = team_stats[(team_stats['team_h'] == player_team) | (team_stats['team_a'] == player_team)]
    if team_matches.empty:
        st.info(f"No matches found for {player_team}")
        return
    
    # Team actual values
    team_xg = team_matches['h_xg'].mean() + team_matches['a_xg'].mean()
    team_ppda = (team_matches['h_ppda'].mean() + team_matches['a_ppda'].mean()) / 2
    
    # Player estimate (proportional to minutes)
    estimated_xg = team_xg * minutes_pct
    estimated_ppda = team_ppda * minutes_pct
    
    # -----------------------------------------------------------------
    # CHART 1: xG
    # -----------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    categories_xg = [f'{player_team} (team)', f'{selected_player} (estimated)']
    values_xg = [team_xg, estimated_xg]
    colors_xg = ['#3498db', '#2ecc71']
    
    bars1 = ax1.barh(categories_xg, values_xg, color=colors_xg, edgecolor='black', linewidth=1.5, height=0.5)
    ax1.set_xlabel('xG per game')
    ax1.set_title(f'Estimated xG Impact - {selected_player}')
    
    for bar, val in zip(bars1, values_xg):
        ax1.text(bar.get_width() + 0.03, bar.get_y() + bar.get_height()/2, f'{val:.2f}', 
                va='center', fontweight='bold')
    
    ax1.text(0.5, -0.15, f'Based on {minutes_pct*100:.1f}% of minutes (15% margin over team max)', 
             transform=ax1.transAxes, ha='center', fontsize=9, style='italic')
    
    # -----------------------------------------------------------------
    # CHART 2: PPDA
    # -----------------------------------------------------------------
    categories_ppda = [f'{player_team} (team)', f'{selected_player} (estimated)']
    values_ppda = [team_ppda, estimated_ppda]
    colors_ppda = ['#3498db', '#2ecc71']
    
    bars2 = ax2.barh(categories_ppda, values_ppda, color=colors_ppda, edgecolor='black', linewidth=1.5, height=0.5)
    ax2.set_xlabel('PPDA (lower = better pressing)')
    ax2.set_title(f'Estimated Pressing Impact - {selected_player}')
    
    for bar, val in zip(bars2, values_ppda):
        ax2.text(bar.get_width() + 0.03, bar.get_y() + bar.get_height()/2, f'{val:.1f}', 
                va='center', fontweight='bold')
    
    ax2.text(0.5, -0.15, f'Based on {minutes_pct*100:.1f}% of minutes (15% margin over team max)', 
             transform=ax2.transAxes, ha='center', fontsize=9, style='italic')
    
    plt.tight_layout()
    st.pyplot(fig)
    
    # --- NUMERIC METRICS ---
    st.subheader(f"📊 Summary - {selected_player}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Minutes played", f"{player_minutes:,}")
        st.metric("Games played", f"{player_games}")
        st.metric("Team max minutes", f"{max_team_minutes:,} min")
        st.metric("% minutes (with margin)", f"{minutes_pct*100:.1f}%")
    
    with col2:
        st.metric("Team xG", f"{team_xg:.2f} per game")
        st.metric("Estimated player xG", f"{estimated_xg:.2f} per game")
    
    with col3:
        st.metric("Team PPDA", f"{team_ppda:.1f}")
        st.metric("Estimated player PPDA", f"{estimated_ppda:.1f}")


# --- Sidebar ---
st.sidebar.header("Player Selection")
sort_option = st.sidebar.radio("Sort Players By:", ('Alphabetical', 'By Threat Rank'))

if sort_option == 'Alphabetical':
    player_list = sorted(player_stats['player_name'].unique().tolist())
else:
    player_list = ranking_liga['player_name'].tolist()

selected_player = st.sidebar.selectbox("Select a Player:", player_list, index=0 if player_list else None)


# --- Main Content ---
if selected_player:
    st.header(f"Scouting Report for {selected_player}")

    tab1, tab2, tab3, tab4 = st.tabs(["Full Report", "Performance Profile", "Shot Map", "Impact Estimate"])

    with tab1:
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**Instructions for this report:**")
            st.write("- This report shows basic stats, threat ranking, and player profile")
            st.write("- Ratios compare the player to position average (1.0x = average)")
        display_basic_player_stats(selected_player)

    with tab2:
        st.subheader("Performance Profile (vs Position Average)")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**How to interpret this chart:**")
            st.write("- Green bars (right) = Better than position average")
            st.write("- Red bars (left) = Worse than position average")
            st.write("- Vertical line at 0 = Position average (1.0x)")
        plot_divergent_bars(selected_player)

    with tab3:
        st.subheader("Shot Map")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**Shot colors:**")
            st.write("- 🟢 Green: Goal")
            st.write("- 🟠 Orange: Saved")
            st.write("- 🔴 Red: Missed")
            st.write("- ⚪ Gray: Blocked")
        plot_shot_map(selected_player)

    with tab4:
        st.subheader("Player Impact Estimate")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**⚠️ This is an ESTIMATE based on minutes played.**")
            st.write("- xG attribution = Team xG × (player minutes / total possible minutes)")
            st.write("- For precise analysis, lineup data per match would be needed")
        plot_player_impact_estimate(selected_player)
else:
    st.info("Select a player from the left sidebar")
