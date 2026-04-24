import os

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
    player_path = os.path.join('file', 'season.csv')
    shots_path = os.path.join('file', 'shot_data.csv')
    match_path = os.path.join('file', 'match_info.csv')

    if not os.path.exists(player_path) or not os.path.exists(shots_path) or not os.path.exists(match_path):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    player_stats = pd.read_csv(player_path)
    shots = pd.read_csv(shots_path)
    team_match_stats = pd.read_csv(match_path, sep=';')

    return player_stats, shots, team_match_stats

player_stats, shots, team_match_stats = load_data()

# --- Data validation ---
if player_stats.empty or shots.empty or team_match_stats.empty:
    st.error(
        "No se pudieron cargar los datos necesarios. "
        "Asegúrate de que existen los archivos file/season.csv, file/shot_data.csv y file/match_info.csv."
    )
    st.stop()

player_stats = player_stats.rename(columns={
    'id': 'player_id',
    'player_name': 'player',
    'team_title': 'team',
    'games': 'matches',
    'time': 'minutes',
    'xA': 'xa',
    'xG': 'xg',
    'xGBuildup': 'xg_buildup'
})

required_player_cols = {
    'player_id', 'player', 'position', 'team', 'goals', 'assists', 'xg', 'xa',
    'shots', 'key_passes', 'matches', 'minutes', 'yellow_cards', 'xg_buildup'
}
required_shot_cols = {'title', 'xG', 'xGA', 'deep', 'deep_allowed', 'scored', 'missed', 'ppda.att', 'result', 'h_a'}
required_match_cols = {'h_title', 'a_title', 'goals_h', 'goals_a', 'xG_h', 'xG_a'}

missing_player_cols = required_player_cols - set(player_stats.columns)
missing_shot_cols = required_shot_cols - set(shots.columns)
missing_match_cols = required_match_cols - set(team_match_stats.columns)

if missing_player_cols or missing_shot_cols or missing_match_cols:
    st.error("Los archivos no tienen el formato esperado para el reporte.")
    if missing_player_cols:
        st.write(f"Faltan columnas en season.csv: {sorted(missing_player_cols)}")
    if missing_shot_cols:
        st.write(f"Faltan columnas en shot_data.csv: {sorted(missing_shot_cols)}")
    if missing_match_cols:
        st.write(f"Faltan columnas en match_info.csv: {sorted(missing_match_cols)}")
    st.stop()

player_stats[['goals', 'assists', 'xg', 'xa', 'shots', 'key_passes', 'matches', 'minutes', 'yellow_cards', 'xg_buildup']] = (
    player_stats[['goals', 'assists', 'xg', 'xa', 'shots', 'key_passes', 'matches', 'minutes', 'yellow_cards', 'xg_buildup']]
    .apply(pd.to_numeric, errors='coerce')
).fillna(0)

shots[['xG', 'xGA', 'deep', 'deep_allowed', 'scored', 'missed', 'ppda.att']] = (
    shots[['xG', 'xGA', 'deep', 'deep_allowed', 'scored', 'missed', 'ppda.att']]
    .apply(pd.to_numeric, errors='coerce')
).fillna(0)

player_stats['position'] = player_stats['position'].astype(str).str.strip()

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

player_stats['goals_assists_pg'] = np.where(
    player_stats['matches'] > 0,
    (player_stats['goals'] + player_stats['assists']) / player_stats['matches'],
    0
)
player_stats['key_passes_pg'] = np.where(player_stats['matches'] > 0, player_stats['key_passes'] / player_stats['matches'], 0)
player_stats['xg_pg'] = np.where(player_stats['matches'] > 0, player_stats['xg'] / player_stats['matches'], 0)
player_stats['xa_pg'] = np.where(player_stats['matches'] > 0, player_stats['xa'] / player_stats['matches'], 0)
player_stats['shots_pg'] = np.where(player_stats['matches'] > 0, player_stats['shots'] / player_stats['matches'], 0)
player_stats['xg_buildup_pg'] = np.where(player_stats['matches'] > 0, player_stats['xg_buildup'] / player_stats['matches'], 0)

position_avg = player_stats.groupby('position')[[
    'goals_assists_pg', 'key_passes_pg', 'xg_pg', 'xa_pg', 'shots_pg', 'xg_buildup_pg'
]].mean().reset_index()

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
        st.metric("Matches Played", int(player_data['matches']))
        st.metric("Assists", player_data['assists'])
    with col3:
        st.metric("Minutes Played", int(player_data['minutes']))
        st.metric("Yellow Cards", int(player_data['yellow_cards']))

    team_matches = shots[shots['title'] == player_team]
    if not team_matches.empty:
        team_ppda = team_matches['ppda.att'].mean()
        league_ppda = shots['ppda.att'].mean()
        relative_ppda = team_ppda / league_ppda if league_ppda else 1

        if relative_ppda < 0.9:
            press_text = "**High Press**: el equipo es más agresivo que el promedio de la liga."
            press_icon = "🟢"
        elif relative_ppda <= 1.1:
            press_text = "**Balanced Press**: el equipo presiona cerca del promedio de la liga."
            press_icon = "🟡"
        else:
            press_text = "**Low Block**: el equipo presiona menos que el promedio de la liga."
            press_icon = "🔴"

        st.subheader("Team Context")
        st.write(f"**{player_team}** {press_icon} {press_text}")
        st.caption(f"PPDA Attack average: **{team_ppda:.1f}** (menor = más presión) | Liga: **{league_ppda:.1f}**")

        team_goals_total = team_matches['scored'].sum()
        if team_goals_total > 0 and player_data['goals'] > 0:
            dependency = (player_data['goals'] / team_goals_total) * 100
            if dependency > 25:
                st.write(f"**High dependency**: Involucrado en **{dependency:.0f}%** de los goles del equipo.")
            elif dependency > 15:
                st.write(f"**Important contributor**: Involucrado en **{dependency:.0f}%** de los goles del equipo.")
            else:
                st.write(f"**Collective contribution**: Involucrado en **{dependency:.0f}%** de los goles del equipo.")

    st.subheader("Offensive Threat Ranking")
    player_rank_data = ranking_liga[ranking_liga['player'] == player_name].iloc[0]
    player_rank = player_rank_data['rank']
    player_threat_score = player_rank_data['threat_score']
    avg_threat = ranking_liga['threat_score'].mean()
    threat_ratio = player_threat_score / avg_threat if avg_threat else 1

    st.write(f"**Rank:** #{player_rank} out of {len(ranking_liga)} players")
    st.write(f"**Offensive Threat Score:** {player_threat_score:.1f}")
    st.write(f"**vs League Average:** **{threat_ratio:.2f}x**")

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

    metrics = ['goals_assists_pg', 'key_passes_pg', 'xg_pg', 'xa_pg', 'shots_pg', 'xg_buildup_pg']
    metric_names = ['Goals+Assists', 'Key passes', 'xG', 'xA', 'Shots', 'xBuildup']

    pos_avg = position_avg[position_avg['position'] == player_pos].iloc[0]
    ratios = []
    for metric in metrics:
        player_val = player_data[metric]
        avg_val = pos_avg[metric]
        ratios.append(player_val / avg_val if avg_val > 0 else 1.0)

    sorted_metrics = sorted(zip(metric_names, ratios, metrics), key=lambda x: x[1], reverse=True)

    st.subheader("Player Profile (vs Position Average)")
    st.caption("Ratio > 1.0 = Mejor que el promedio | Ratio = 1.0 = Promedio | Ratio < 1.0 = Por debajo")
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
        st.write(f"{color} **{name}**: **{ratio:.2f}x** (Player: {player_data[metric]:.2f} | Pos avg: {pos_avg[metric]:.2f})")


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
            ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height() / 2,
                    f'{ratio:.2f}x', va='center', fontsize=10, fontweight='bold')
        else:
            ax.text(bar.get_width() - 0.02, bar.get_y() + bar.get_height() / 2,
                    f'{ratio:.2f}x', va='center', ha='right', fontsize=10, fontweight='bold')

    ax.set_xlabel('Diferencia frente al promedio de la posición', fontsize=11)
    ax.set_title(f'{selected_player} - Performance Profile\n(Right = Mejor | Left = Peor)', fontsize=12)
    ax.text(0, -0.5, '← Peor | Promedio (1.0x) | Mejor →', ha='center', fontsize=9, color='gray')
    plt.tight_layout()
    st.pyplot(fig)


def plot_team_summary(selected_player):
    player_data = player_stats[player_stats['player'] == selected_player].iloc[0]
    player_team = player_data['team']
    team_matches = shots[shots['title'] == player_team]

    if team_matches.empty:
        st.info(f"No se encontraron datos de equipo para {player_team}.")
        return

    metrics = ['xG', 'xGA', 'deep', 'deep_allowed', 'scored', 'missed']
    metric_names = ['xG', 'xGA', 'Deep', 'Deep Allowed', 'Goals', 'Missed Shots']
    averages = [team_matches[col].mean() for col in metrics]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(metric_names, averages, color=['#2ecc71', '#e74c3c', '#3498db', '#95a5a6', '#2c3e50', '#e67e22'])
    ax.set_ylabel('Valor promedio por partido')
    ax.set_title(f'{player_team} - Team Shooting & Chance Creation')
    ax.set_xticks(range(len(metric_names)))
    ax.set_xticklabels(metric_names, rotation=25, ha='right')

    for bar, value in zip(bars, averages):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f'{value:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    st.pyplot(fig)


def plot_team_impact(selected_player):
    player_team = player_stats[player_stats['player'] == selected_player]['team'].values
    if not player_team.size:
        st.warning(f"No se encontró equipo para {selected_player}.")
        return

    player_team = player_team[0]
    team_matches = shots[shots['title'] == player_team]
    if team_matches.empty:
        st.info(f"No se encontraron partidos de {player_team}.")
        return

    team_xg = team_matches['xG'].mean()
    team_ppda = team_matches['ppda.att'].mean()
    league_xg = shots['xG'].mean()
    league_ppda = shots['ppda.att'].mean()

    xg_diff = team_xg - league_xg
    ppda_diff = league_ppda - team_ppda

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    metrics_xg = ['League Average', 'Team Average']
    values_xg = [league_xg, team_xg]
    colors_xg = ['gray', 'green' if xg_diff > 0 else 'red']
    bars1 = ax1.barh(metrics_xg, values_xg, color=colors_xg, edgecolor='black', linewidth=1.5)
    ax1.axvline(x=league_xg, color='gray', linestyle='--', alpha=0.5)
    ax1.set_xlabel('xG promedio por partido')
    ax1.set_title(f'xG generado: {player_team}')
    for bar, val in zip(bars1, values_xg):
        ax1.text(val + 0.02, bar.get_y() + bar.get_height() / 2,
                 f'{val:.2f}', ha='left', va='center', fontweight='bold')
    ax1.text(max(values_xg) * 0.7, 0.5, f'Δ = {xg_diff:+.2f}', ha='center', va='center', fontsize=11,
             fontweight='bold', color='green' if xg_diff > 0 else 'red', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    metrics_ppda = ['League Average', 'Team Average']
    values_ppda = [league_ppda, team_ppda]
    colors_ppda = ['gray', 'green' if team_ppda < league_ppda else 'red']
    bars2 = ax2.barh(metrics_ppda, values_ppda, color=colors_ppda, edgecolor='black', linewidth=1.5)
    ax2.axvline(x=league_ppda, color='gray', linestyle='--', alpha=0.5)
    ax2.set_xlabel('PPDA (lower = better)')
    ax2.set_title(f'Presión media: {player_team}')
    for bar, val in zip(bars2, values_ppda):
        ax2.text(val + 0.02, bar.get_y() + bar.get_height() / 2,
                 f'{val:.1f}', ha='left', va='center', fontweight='bold')
    ax2.text(max(values_ppda) * 0.7, 0.5, f'Δ = {ppda_diff:+.1f}', ha='center', va='center', fontsize=11,
             fontweight='bold', color='green' if team_ppda < league_ppda else 'red',
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
    tab1, tab2, tab3, tab4 = st.tabs(["Full Report", "Performance Profile", "Team Summary", "Team Impact"])

    with tab1:
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**Instrucciones o notas para este reporte:**")
            st.write("- El dataset actual proviene de file/season.csv y file/shot_data.csv.")
            st.write("- El reporte muestra métricas de jugador y contexto de equipo.")
        display_basic_player_stats(selected_player)

    with tab2:
        st.subheader("Performance Profile (vs Position Average)")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**Cómo interpretar este gráfico:**")
            st.write("- Barras hacia la derecha: mejor que el promedio de la posición")
            st.write("- Barras hacia la izquierda: peor que el promedio de la posición")
            st.write("- Línea vertical en 0: promedio de la posición (1.0x)")
        st.caption("→ Mejor | ← Peor | = Promedio (1.0x)")
        plot_divergent_bars(selected_player)

    with tab3:
        st.subheader("Team Shooting & Chance Creation")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**Interpretación:**")
            st.write("- xG y xGA promedio por partido")
            st.write("- Deep y Deep Allowed muestran la creación y concesión de oportunidades peligrosas")
            st.write("- 'Goals' es el promedio de goles por partido y 'Missed Shots' muestra la cantidad de tiros fallados")
        plot_team_summary(selected_player)

    with tab4:
        st.subheader("Player Impact on Team")
        with st.expander("ℹ️ Information", expanded=False):
            st.write("**Cómo interpretar el impacto del jugador:**")
            st.write("- xG promedio del equipo vs promedio de liga")
            st.write("- PPDA promedio del equipo vs promedio de liga")
            st.write("- Δ positivo (verde) indica mejor rendimiento respecto a liga")
        plot_team_impact(selected_player)
else:
    st.info("Selecciona un jugador en la barra lateral para ver su scouting report.")
