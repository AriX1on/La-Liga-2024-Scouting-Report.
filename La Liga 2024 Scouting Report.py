import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsbombpy import sb
from mplsoccer import Pitch
import soccerdata as sd

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
    ranking_liga = ranking_liga()
    shots = pd.read_csv('file/shot_data.csv')
    team_match_stats = pd.read_csv('file/match_info.csv')
    return shots, team_match_stats, player_stats, ranking_liga

shots, team_match_stats, player_stats, ranking_liga = load_data()

shots, team_match_stats, player_stats = load_understat_data()

# --- Additional Metrics Calculation ---
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


# --- Visualization Functions ---

def display_basic_player_stats(player_name):
    player_data = player_stats[player_stats['player'] == player_name].iloc[0]
    player_pos = player_data['position']
    player_team = player_data['team']

    # --- Basic Stats ---
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

    # --- Team Context (Pressing Style) ---
    team_matches = team_match_stats[
        (team_match_stats['home_team'] == player_team) |
        (team_match_stats['away_team'] == player_team)
    ]

    if not team_matches.empty:
        team_ppda = (team_matches['home_ppda'].mean() + team_matches['away_ppda'].mean()) / 2

        if team_ppda < 10:
            press_text = "**High Press**: Team presses high, doesn't let opponent build up."
            press_icon = "🟢"
        elif team_ppda < 14:
            press_text = "**Balanced Press**: Team presses in mid-block, waits for mistakes."
            press_icon = "🟡"
        else:
            press_text = "**Low Block**: Team sits back, protects their area, counters."
            press_icon = "🔴"

        st.subheader("Team Context")
        st.write(f"**{player_team}** {press_icon} {press_text}")
        st.caption(f"PPDA (Passes Allowed Per Defensive Action): **{team_ppda:.1f}** (lower = more pressing)")

        # Player dependency
        team_goals_total = (team_matches['home_goals'].sum() + team_matches['away_goals'].sum())
        if team_goals_total > 0 and player_data['goals'] > 0:
            dependency = (player_data['goals'] / team_goals_total) * 100
            if dependency > 25:
                st.write(f"**High dependency**: Involved in **{dependency:.0f}%** of team goals.")
            elif dependency > 15:
                st.write(f"**Important contributor**: Involved in **{dependency:.0f}%** of team goals.")
            else:
                st.write(f"**Collective contribution**: Involved in **{dependency:.0f}%** of team goals.")

    # --- Offensive Threat Ranking ---
    st.subheader("Offensive Threat Ranking")
    player_rank_data = ranking_liga[ranking_liga['player'] == player_name].iloc[0]
    player_rank = player_rank_data['rank']
    player_threat_score = player_rank_data['threat_score']

    # Calculate threat ratio vs average
    avg_threat = ranking_liga['threat_score'].mean()
    threat_ratio = player_threat_score / avg_threat

    st.write(f"**Rank:** #{player_rank} out of {len(ranking_liga)} players")
    st.write(f"**Offensive Threat Score:** {player_threat_score:.1f}")
    st.write(f"**vs League Average:** **{threat_ratio:.2f}x** (1.0x = average)")

    # Color code the ratio
    if threat_ratio >= 1.5:
        st.success(f"Elite offensive threat ({threat_ratio:.2f}x above average)")
    elif threat_ratio >= 1.2:
        st.info(f"Above average threat ({threat_ratio:.2f}x)")
    elif threat_ratio >= 0.8:
        st.warning(f"Average threat ({threat_ratio:.2f}x)")
    else:
        st.error(f"Below average threat ({threat_ratio:.2f}x)")

    # Progress bar using ratio (capped at 2.0 for display)
    display_ratio = min(threat_ratio, 2.0)
    st.progress(display_ratio / 2.0, text=f"{threat_ratio:.1f}x average")

    # --- Player Profile with RATIOS ---
    metrics = ['goals_assists_pg', 'key_passes_pg', 'xg_pg', 'xa_pg', 'shots_pg', 'xg_buildup_pg']
    metric_names = ['Goals+Assists', 'Key passes', 'xG', 'xA', 'Shots', 'xBuildup']

    # Get position average
    pos_avg = position_avg[position_avg['position'] == player_pos].iloc[0]

    # Calculate ratios
    ratios = []
    for metric in metrics:
        player_val = player_data[metric]
        avg_val = pos_avg[metric]
        if avg_val > 0:
            ratio = player_val / avg_val
        else:
            ratio = 1.0
        ratios.append(ratio)

    # Sort by ratio (best first)
    sorted_metrics = sorted(zip(metric_names, ratios, metrics), key=lambda x: x[1], reverse=True)

    st.subheader("Player Profile (vs Position Average)")
    st.caption("Ratio > 1.0 = Better than average | Ratio = 1.0 = Average | Ratio < 1.0 = Below average")

    # Display all metrics in order
    for name, ratio, metric in sorted_metrics:
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

        st.write(f"{color} **{name}**: **{ratio:.2f}x** (Player: {player_data[metric]:.2f} | Position avg: {pos_avg[metric]:.2f})")

def plot_divergent_bars(selected_player):
    """Divergent bar chart showing ratios vs position average (positive/negative)"""
    player_data = player_stats[player_stats['player'] == selected_player].iloc[0]
    player_pos = player_data['position']

    # Get position average
    pos_avg = position_avg[position_avg['position'] == player_pos].iloc[0]

    metrics = ['goals_assists_pg', 'key_passes_pg', 'xg_pg', 'xa_pg', 'shots_pg', 'xg_buildup_pg']
    metric_names = ['Goals+Assists', 'Key passes', 'xG', 'xA', 'Shots', 'xBuildup']

    # Calculate offsets (ratio - 1.0)
    offsets = []
    ratios = []
    for metric in metrics:
        player_val = player_data[metric]
        avg_val = pos_avg[metric]
        if avg_val > 0:
            ratio = player_val / avg_val
        else:
            ratio = 1.0
        ratios.append(ratio)
        offsets.append(ratio - 1.0)

    # Sort by offset for better visualization
    sorted_pairs = sorted(zip(metric_names, offsets, ratios), key=lambda x: x[1], reverse=True)
    sorted_names = [p[0] for p in sorted_pairs]
    sorted_offsets = [p[1] for p in sorted_pairs]
    sorted_ratios = [p[2] for p in sorted_pairs]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Colors: green for positive, red for negative
    colors = ['#2ecc71' if offset > 0 else '#e74c3c' for offset in sorted_offsets]

    # Create horizontal bars
    bars = ax.barh(sorted_names, sorted_offsets, color=colors, edgecolor='black', linewidth=0.5, alpha=0.8)

    # Vertical line at 0 (average = 1.0x)
    ax.axvline(x=0, color='black', linewidth=1.5, linestyle='-', alpha=0.7)

    # Add value labels
    for bar, offset, ratio in zip(bars, sorted_offsets, sorted_ratios):
        if offset > 0:
            ax.text(bar.get_width() + 0.03, bar.get_y() + bar.get_height()/2,
                    f'{ratio:.2f}x', va='center', fontsize=10, fontweight='bold')
        else:
            ax.text(bar.get_width() - 0.03, bar.get_y() + bar.get_height()/2,
                    f'{ratio:.2f}x', va='center', ha='right', fontsize=10, fontweight='bold')

    ax.set_xlabel('Difference from Position Average', fontsize=11)
    ax.set_title(f'{selected_player} - Performance Profile\n(Right = Better than average | Left = Worse than average)', fontsize=12)

    # Add reference line label
    ax.text(0, -0.5, '← Worse | Average (1.0x) | Better →', ha='center', fontsize=9, color='gray')

    plt.tight_layout()
    st.pyplot(fig)

def plot_shot_map(selected_player):
    player_id_val = player_stats[player_stats['player'] == selected_player]['player_id'].values
    if not player_id_val.size > 0:
        st.warning(f"No player ID found for {selected_player}.")
        return
    player_id = player_id_val[0]

    player_shots = shots[shots['player_id'] == player_id].copy()

    if len(player_shots) == 0:
        st.info(f"No shot data found for {selected_player}.")
        return

    pitch = Pitch(pitch_type='statsbomb', half=True, pitch_color='grass', line_color='white')
    fig, ax = pitch.draw(figsize=(10, 7))

    color_map = {
        'Goal': 'green',
        'Saved Shot': 'orange',
        'Missed Shot': 'red',
        'Blocked Shot': 'gray',
        'Shot On Post': 'orange'
    }

    for _, shot in player_shots.iterrows():
        x = shot['location_x'] * 120
        y = (1 - shot['location_y']) * 80
        result = shot['result']
        color = color_map.get(result, 'blue')

        pitch.scatter(x, y, s=150, c=color, marker='o', edgecolor='black',
                     linewidth=1, alpha=0.8, ax=ax)

    ax.set_title(f'{selected_player} - Shot Map ({len(player_shots)} shots)', fontsize=14)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='green', edgecolor='black', label='Goal'),
        Patch(facecolor='orange', edgecolor='black', label='Saved Shot'),
        Patch(facecolor='red', edgecolor='black', label='Missed Shot'),
        Patch(facecolor='gray', edgecolor='black', label='Blocked Shot'),
        Patch(facecolor='orange', edgecolor='black', label='Shot On Post')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    st.pyplot(fig)

def plot_team_impact(selected_player):
    player_team_val = player_stats[player_stats['player'] == selected_player]['team'].values
    if not player_team_val.size > 0:
        st.warning(f"No team found for {selected_player}.")
        return
    player_team = player_team_val[0]

    team_matches = team_match_stats[
        (team_match_stats['home_team'] == player_team) |
        (team_match_stats['away_team'] == player_team)
    ]

    if team_matches.empty:
        st.info(f"No matches found for {player_team}.")
        return

    team_home_xg = team_matches[team_matches['home_team'] == player_team]['home_xg'].mean()
    team_away_xg = team_matches[team_matches['away_team'] == player_team]['away_xg'].mean()
    team_xg = np.nanmean([team_home_xg, team_away_xg]) if not pd.isna(team_home_xg) or not pd.isna(team_away_xg) else 0

    team_home_ppda = team_matches[team_matches['home_team'] == player_team]['home_ppda'].mean()
    team_away_ppda = team_matches[team_matches['away_team'] == player_team]['away_ppda'].mean()
    team_ppda = np.nanmean([team_home_ppda, team_away_ppda]) if not pd.isna(team_home_ppda) or not pd.isna(team_away_ppda) else 0

    league_xg = (team_match_stats['home_xg'].mean() + team_match_stats['away_xg'].mean()) / 2
    league_ppda = (team_match_stats['home_ppda'].mean() + team_match_stats['away_ppda'].mean()) / 2

    xg_diff = team_xg - league_xg
    ppda_diff = league_ppda - team_ppda

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # xG Chart (horizontal)
    metrics_xg = ['League Average', 'Team Average']
    values_xg = [league_xg, team_xg]
    colors_xg = ['gray', 'green' if xg_diff > 0 else 'red']

    bars1 = ax1.barh(metrics_xg, values_xg, color=colors_xg, edgecolor='black', linewidth=1.5)
    ax1.axvline(x=league_xg, color='gray', linestyle='--', alpha=0.5)
    ax1.set_xlabel('xG per game')
    ax1.set_title(f'xG Generated: {player_team}')
    for bar, val in zip(bars1, values_xg):
        ax1.text(val + 0.05, bar.get_y() + bar.get_height()/2,
                 f'{val:.2f}', ha='left', va='center', fontweight='bold')
    ax1.text(max(values_xg) * 0.7, 0.5, f'Δ = {xg_diff:+.2f}',
             ha='center', va='center', fontsize=11, fontweight='bold',
             color='green' if xg_diff > 0 else 'red',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # PPDA Chart (horizontal - lower is better)
    metrics_ppda = ['League Average', 'Team Average']
    values_ppda = [league_ppda, team_ppda]
    colors_ppda = ['gray', 'green' if team_ppda < league_ppda else 'red']

    bars2 = ax2.barh(metrics_ppda, values_ppda, color=colors_ppda, edgecolor='black', linewidth=1.5)
    ax2.axvline(x=league_ppda, color='gray', linestyle='--', alpha=0.5)
    ax2.set_xlabel('PPDA (lower = better pressing)')
    ax2.set_title(f'Pressing Intensity: {player_team}')
    for bar, val in zip(bars2, values_ppda):
        ax2.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                 f'{val:.1f}', ha='left', va='center', fontweight='bold')
    ax2.text(max(values_ppda) * 0.7, 0.5, f'Δ = {team_ppda - league_ppda:+.1f}',
             ha='center', va='center', fontsize=11, fontweight='bold',
             color='green' if team_ppda < league_ppda else 'red',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

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
            st.write("**Instrucciones o notas para este reporte:**")
            st.write("- Aquí puedes añadir información manualmente")
            st.write("- Explicar qué significan los percentiles y ratios")
            st.write("- Contexto sobre los datos (La Liga 2023-24)")
        display_basic_player_stats(selected_player)

    with tab2:
        st.subheader("Performance Profile (vs Position Average)")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**Cómo interpretar este gráfico:**")
            st.write("- Barras hacia la derecha (verde): Mejor que el promedio de su posición")
            st.write("- Barras hacia la izquierda (rojo): Peor que el promedio de su posición")
            st.write("- Línea vertical en 0: Promedio de la posición (1.0x)")
        st.caption("→ Better than average | ← Worse than average | = Average (1.0x)")
        plot_divergent_bars(selected_player)

    with tab3:
        st.subheader("Shot Map")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**Interpretación del mapa de tiros:**")
            st.write("- 🟢 Verde: Gol")
            st.write("- 🟠 Naranja: Tiro atajado o al poste")
            st.write("- 🔴 Rojo: Tiro fallado")
            st.write("- ⚪ Gris: Tiro bloqueado")
        plot_shot_map(selected_player)

    with tab4:
        st.subheader("Player Impact on Team")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**Cómo interpretar el impacto del jugador:**")
            st.write("- xG Generado: Goles esperados creados por el equipo con el jugador")
            st.write("- PPDA: Presión ejercida (menor = mejor presión)")
            st.write("- Δ positivo (verde) = Mejor que el promedio de la liga")
            st.write("- Δ negativo (rojo) = Peor que el promedio de la liga")
        plot_team_impact(selected_player)
else:
    st.info("Please select a player from the left sidebar to view their scouting report.")

