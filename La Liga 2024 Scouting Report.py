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
    team_match_stats = pd.read_csv('file/match_info.csv')
    player_stats = pd.read_csv('file/player.csv')
    shots = pd.read_csv('file/shot_data.csv')
    return shots, team_match_stats, player_stats

shots, team_match_stats, player_stats = load_data()

# --- Calculate ranking_liga from player_stats ---
# Filter out goalkeepers (position = 'GK')
player_stats_no_g = player_stats[player_stats['position'] != 'GK'].copy()

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


# --- Visualization Functions ---

def display_basic_player_stats(player_name):
    player_data = player_stats[player_stats['player'] == player_name].iloc[0]
    player_pos = player_data['position']
    player_team = player_data['team']

    st.subheader(f"Basic Stats for {player_name}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Position", player_data['position'])
        st.metric("Goals", player_data['goals'])
    with col2:
        st.metric("Matches Played", player_data['matches'])
        st.metric("Assists", player_data['assists'])
    with col3:
        st.metric("Minutes Played", player_data['minutes'])
        st.metric("Yellow Cards", player_data['yellow_cards'])

    # --- Team Context ---
    team_matches = team_match_stats[
        (team_match_stats['home_team'] == player_team) |
        (team_match_stats['away_team'] == player_team)
    ]
    
    if not team_matches.empty:
        team_ppda = (team_matches['home_ppda'].mean() + team_matches['away_ppda'].mean()) / 2
        
        if team_ppda < 10:
            press_text = "**High Press**: Team presses high"
            press_icon = "🟢"
        elif team_ppda < 14:
            press_text = "**Balanced Press**: Team presses in mid-block"
            press_icon = "🟡"
        else:
            press_text = "**Low Block**: Team sits back, counters"
            press_icon = "🔴"
        
        st.subheader("Team Context")
        st.write(f"**{player_team}** {press_icon} {press_text}")
        st.caption(f"PPDA: **{team_ppda:.1f}** (lower = more pressing)")
        
        team_goals_total = (team_matches['home_goals'].sum() + team_matches['away_goals'].sum())
        if team_goals_total > 0 and player_data['goals'] > 0:
            dependency = (player_data['goals'] / team_goals_total) * 100
            if dependency > 25:
                st.write(f"**High dependency**: **{dependency:.0f}%** of team goals")
            elif dependency > 15:
                st.write(f"**Important contributor**: **{dependency:.0f}%** of team goals")
            else:
                st.write(f"**Collective contribution**: **{dependency:.0f}%** of team goals")

    # --- Offensive Threat Ranking ---
    st.subheader("Offensive Threat Ranking")
    player_rank_data = ranking_liga[ranking_liga['player'] == player_name].iloc[0]
    player_rank = player_rank_data['rank']
    player_threat_score = player_rank_data['threat_score']
    avg_threat = ranking_liga['threat_score'].mean()
    threat_ratio = player_threat_score / avg_threat

    st.write(f"**Rank:** #{player_rank} of {len(ranking_liga)} players")
    st.write(f"**Offensive Threat Score:** {player_threat_score:.1f}")
    st.write(f"**vs League Average:** **{threat_ratio:.2f}x** (1.0x = average)")
    
    if threat_ratio >= 1.5:
        st.success(f"Elite offensive threat ({threat_ratio:.2f}x above average)")
    elif threat_ratio >= 1.2:
        st.info(f"Above average threat ({threat_ratio:.2f}x)")
    elif threat_ratio >= 0.8:
        st.warning(f"Average threat ({threat_ratio:.2f}x)")
    else:
        st.error(f"Below average threat ({threat_ratio:.2f}x)")

    display_ratio = min(threat_ratio, 2.0)
    st.progress(display_ratio / 2.0, text=f"{threat_ratio:.1f}x average")

    # --- Player Profile with Ratios ---
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
        st.write(f"{color} **{name}**: **{ratio:.2f}x** (Player: {player_data[metric.split('_')[0]]:.2f} | Avg: {pos_avg[metric]:.2f})")


def plot_divergent_bars(selected_player):
    player_data = player_stats[player_stats['player'] == selected_player].iloc[0]
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
    
    bars = ax.barh(sorted_names, sorted_offsets, color=colors, edgecolor='black', linewidth=0.5, alpha=0.8)
    ax.axvline(x=0, color='black', linewidth=1.5, linestyle='-', alpha=0.7)
    
    for bar, offset, ratio in zip(bars, sorted_offsets, sorted_ratios):
        if offset > 0:
            ax.text(bar.get_width() + 0.03, bar.get_y() + bar.get_height()/2, f'{ratio:.2f}x', va='center', fontsize=10, fontweight='bold')
        else:
            ax.text(bar.get_width() - 0.03, bar.get_y() + bar.get_height()/2, f'{ratio:.2f}x', va='center', ha='right', fontsize=10, fontweight='bold')
    
    ax.set_xlabel('Difference from Position Average', fontsize=11)
    ax.set_title(f'{selected_player} - Performance Profile', fontsize=12)
    ax.text(0, -0.5, '← Worse | Average (1.0x) | Better →', ha='center', fontsize=9, color='gray')
    
    plt.tight_layout()
    st.pyplot(fig)


def plot_shot_map(selected_player):
    player_id_val = player_stats[player_stats['player'] == selected_player]['player_id'].values
    if len(player_id_val) == 0:
        st.warning(f"No player ID for {selected_player}")
        return
    player_id = player_id_val[0]
    
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
        x = shot['location_x'] * 120
        y = (1 - shot['location_y']) * 80
        result = shot['result']
        color = color_map.get(result, 'blue')
        pitch.scatter(x, y, s=150, c=color, marker='o', edgecolor='black', linewidth=1, alpha=0.8, ax=ax)
    
    ax.set_title(f'{selected_player} - Shot Map ({len(player_shots)} shots)', fontsize=14)
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='green', edgecolor='black', label='Goal'),
        Patch(facecolor='orange', edgecolor='black', label='Saved'),
        Patch(facecolor='red', edgecolor='black', label='Missed'),
        Patch(facecolor='gray', edgecolor='black', label='Blocked')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    st.pyplot(fig)


def plot_team_impact(selected_player):
    player_team_val = player_stats[player_stats['player'] == selected_player]['team'].values
    if len(player_team_val) == 0:
        st.warning(f"No team for {selected_player}")
        return
    player_team = player_team_val[0]
    
    team_matches = team_match_stats[
        (team_match_stats['home_team'] == player_team) |
        (team_match_stats['away_team'] == player_team)
    ]
    if team_matches.empty:
        st.info(f"No matches for {player_team}")
        return
    
    team_xg = (team_matches['home_xg'].mean() + team_matches['away_xg'].mean())
    team_ppda = (team_matches['home_ppda'].mean() + team_matches['away_ppda'].mean()) / 2
    league_xg = (team_match_stats['home_xg'].mean() + team_match_stats['away_xg'].mean()) / 2
    league_ppda = (team_match_stats['home_ppda'].mean() + team_match_stats['away_ppda'].mean()) / 2
    
    xg_diff = team_xg - league_xg
    ppda_diff = league_ppda - team_ppda
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # xG Chart
    metrics_xg = ['League Average', 'Team Average']
    values_xg = [league_xg, team_xg]
    colors_xg = ['gray', 'green' if xg_diff > 0 else 'red']
    bars1 = ax1.barh(metrics_xg, values_xg, color=colors_xg, edgecolor='black', linewidth=1.5)
    ax1.axvline(x=league_xg, color='gray', linestyle='--', alpha=0.5)
    ax1.set_xlabel('xG per game')
    ax1.set_title(f'xG Generated: {player_team}')
    for bar, val in zip(bars1, values_xg):
        ax1.text(val + 0.05, bar.get_y() + bar.get_height()/2, f'{val:.2f}', ha='left', va='center', fontweight='bold')
    ax1.text(max(values_xg) * 0.7, 0.5, f'Δ = {xg_diff:+.2f}', ha='center', va='center', fontsize=11, fontweight='bold', color='green' if xg_diff > 0 else 'red', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # PPDA Chart
    metrics_ppda = ['League Average', 'Team Average']
    values_ppda = [league_ppda, team_ppda]
    colors_ppda = ['gray', 'green' if team_ppda < league_ppda else 'red']
    bars2 = ax2.barh(metrics_ppda, values_ppda, color=colors_ppda, edgecolor='black', linewidth=1.5)
    ax2.axvline(x=league_ppda, color='gray', linestyle='--', alpha=0.5)
    ax2.set_xlabel('PPDA (lower = better pressing)')
    ax2.set_title(f'Pressing: {player_team}')
    for bar, val in zip(bars2, values_ppda):
        ax2.text(val + 0.5, bar.get_y() + bar.get_height()/2, f'{val:.1f}', ha='left', va='center', fontweight='bold')
    ax2.text(max(values_ppda) * 0.7, 0.5, f'Δ = {team_ppda - league_ppda:+.1f}', ha='center', va='center', fontsize=11, fontweight='bold', color='green' if team_ppda < league_ppda else 'red', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    st.pyplot(fig)


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
            st.write("**Instructions for this report:**")
            st.write("- Add your manual information here")
        display_basic_player_stats(selected_player)

    with tab2:
        st.subheader("Performance Profile (vs Position Average)")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**How to interpret:**")
            st.write("- Green bars → Better than average")
            st.write("- Red bars → Worse than average")
            st.write("- Line at 0 → Position average")
        plot_divergent_bars(selected_player)

    with tab3:
        st.subheader("Shot Map")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**Shot colors:**")
            st.write("- Green: Goal")
            st.write("- Orange: Saved")
            st.write("- Red: Missed")
            st.write("- Gray: Blocked")
        plot_shot_map(selected_player)

    with tab4:
        st.subheader("Player Impact on Team")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**How to interpret:**")
            st.write("- Green Δ = Better than league average")
            st.write("- Red Δ = Worse than league average")
        plot_team_impact(selected_player)
else:
    st.info("Select a player from the left sidebar")
