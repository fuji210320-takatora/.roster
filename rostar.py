import streamlit as st
import pandas as pd
import re

# ページレイアウト（wideにしてCSSで制御）
st.set_page_config(page_title="NPB ROSTER LAB", layout="wide", initial_sidebar_state="collapsed")

# --- スマホ完全最適化 CSS ---
st.markdown("""
<style>
/* 1. 画面全体の左右余白を最小にしてスマホ幅をフル活用 */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
    padding-left: 6px !important;
    padding-right: 6px !important;
    max-width: 100% !important;
}

/* 2. チーム名見出しをスマホ向けにコンパクト化 */
.main-title {
    font-size: 1.5rem !important;
    font-weight: 800 !important;
    margin-bottom: 2px !important;
    line-height: 1.2 !important;
}
.sub-caption {
    font-size: 0.75rem !important;
    color: #666 !important;
    margin-bottom: 8px !important;
}

/* 3. 上部メトリクス（数字バッジ）の小型化・均等3分割 */
div[data-testid="stMetric"] {
    background-color: #f8f9fa;
    border-radius: 6px;
    padding: 4px 6px !important;
    border: 1px solid #eee;
}
div[data-testid="stMetricLabel"] p {
    font-size: 0.70rem !important;
    color: #555 !important;
    margin-bottom: 0px !important;
}
div[data-testid="stMetricValue"] div {
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    line-height: 1.2 !important;
}

/* 4. 水平コンテナ：横3列を絶対に崩さず均等配置 */
div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 4px !important;
    width: 100% !important;
}

/* 各列の幅を均等に3分割（約33%） */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    flex: 1 1 calc(33.333% - 4px) !important;
    min-width: 0 !important;
    width: calc(33.333% - 4px) !important;
    padding: 0 !important;
}

/* 5. 選手カードの枠線・余白の圧縮 */
div[data-testid="stVerticalBlockBorderWrapper"] {
    padding: 4px 3px !important;
    border-radius: 6px !important;
    border: 1px solid #e0e0e0 !important;
}

/* 選手カード内の文字（背番号＋名前） */
.card-player-name {
    font-size: 0.78rem !important;
    font-weight: bold !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.2 !important;
    color: #222;
}

/* 選手カード内の補足情報（年齢/投打） */
.card-player-info {
    font-size: 0.65rem !important;
    color: #777;
    margin-top: 1px !important;
    margin-bottom: 3px !important;
    line-height: 1.1 !important;
}

/* 6. セレクトボックス（プルダウン）の極小化 */
div[data-testid="stSelectbox"] {
    margin-top: 0px !important;
    margin-bottom: 0px !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    min-height: 26px !important;
    height: 26px !important;
    padding-left: 2px !important;
    padding-right: 2px !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] * {
    font-size: 0.72rem !important;
}

/* プルダウン右側の余分な矢印余白を縮小 */
div[data-testid="stSelectbox"] svg {
    width: 14px !important;
    height: 14px !important;
}
</style>
""", unsafe_allow_html=True)

# --- 1. 球団コード対応表 ---
TEAM_MAP = {
    "c": "広島東洋カープ",
    "t": "阪神タイガース",
    "g": "読売ジャイアンツ",
    "yb": "横浜DeNAベイスターズ",
    "d": "中日ドラゴンズ",
    "s": "東京ヤクルトスワローズ",
    "h": "福岡ソフトバンクホークス",
    "f": "北海道日本ハムファイターズ",
    "m": "千葉ロッテマリーンズ",
    "e": "東北楽天ゴールデンイーグルス",
    "b": "オリックス・バファローズ",
    "l": "埼玉西武ライオンズ",
}

STATUS_OPTIONS = ["残留", "戦力外", "育成移行", "現ドラ", "保留"]

# --- 2. データ読み込み（ネット経由） ---
SHEET_ID = "1I1JsaaQlYHj1zIsOKkFWkc1yAuoNDnpVdy_pLNW5na8"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(CSV_URL)
    df["年齢_num"] = df["年齢"].astype(str).str.extract(r'(\d+)').astype(float)
    df["球団名"] = df["コード"].map(TEAM_MAP).fillna(df["コード"])

    def check_shihai(no_str):
        s = str(no_str).strip()
        if len(s) >= 3 and s.lstrip('0') != "":
            return "育成"
        return "支配下"

    df["契約区分"] = df["背番号"].apply(check_shihai)
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")
    st.stop()

# --- 3. セッション管理 ---
if "roster_status" not in st.session_state:
    st.session_state.roster_status = {}
if "promoted_players" not in st.session_state:
    st.session_state.promoted_players = {}

# --- 4. サイドバー設定 ---
st.sidebar.title("⚾ 設定")
available_teams = [t for t in TEAM_MAP.values() if t in df_raw["球団名"].values]
if not available_teams:
    available_teams = df_raw["球団名"].unique().tolist()

selected_team = st.sidebar.selectbox("球団を選択", available_teams)

if st.sidebar.button("🔄 データを最新に更新"):
    st.cache_data.clear()
    st.rerun()

# チームデータ抽出
team_all_df = df_raw[df_raw["球団名"] == selected_team].copy()
shihai_df = team_all_df[team_all_df["契約区分"] == "支配下"].copy()
ikusei_df = team_all_df[team_all_df["契約区分"] == "育成"].copy()

# セッション初期化
if selected_team not in st.session_state.roster_status:
    st.session_state.roster_status[selected_team] = {
        row["No"]: "残留" for _, row in shihai_df.iterrows()
    }
if selected_team not in st.session_state.promoted_players:
    st.session_state.promoted_players[selected_team] = []

current_status = st.session_state.roster_status[selected_team]
promoted_list = st.session_state.promoted_players[selected_team]

# 支配下＋育成昇格組の合流
promoted_df = ikusei_df[ikusei_df["No"].isin(promoted_list)].copy()
target_df = pd.concat([shihai_df, promoted_df], ignore_index=True)

for p_no in promoted_list:
    if p_no not in current_status:
        current_status[p_no] = "残留"

target_df["区分"] = target_df["No"].map(current_status).fillna("残留")

# --- 5. 集計計算 ---
status_counts = {opt: (target_df["区分"] == opt).sum() for opt in STATUS_OPTIONS}
current_shihai_count = len(shihai_df)
promoted_count = len(promoted_list)
# 支配下に残る選手（残留＋現ドラ＋保留）
retained_total = status_counts["残留"] + status_counts["現ドラ"] + status_counts["保留"]

# --- 6. メインヘッダー（スマホ最適化） ---
st.markdown(f"<div class='main-title'>{selected_team}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-caption'>支配下: {current_shihai_count}名 / 育成: {len(ikusei_df)}名</div>", unsafe_allow_html=True)

# ダッシュボード（均等3分割 × 2行）
c1, c2, c3 = st.columns(3)
c1.metric("現在支配下", f"{current_shihai_count}人")
c2.metric("残留", f"{status_counts['残留']}人")
c3.metric("戦力外", f"{status_counts['戦力外']}人")

c4, c5, c6 = st.columns(3)
c4.metric("育成移行", f"{status_counts['育成移行']}人")
c5.metric("現ドラ候補", f"{status_counts['現ドラ']}人")
c6.metric("育成昇格", f"{promoted_count}人")

st.markdown("<hr style='margin: 10px 0;'/>", unsafe_allow_html=True)

# --- 7. メインコンテンツ（タブ文字サイズはそのまま保持） ---
tab_roster, tab_ikusei, tab_depth, tab_raw = st.tabs(["📋 戦力整理", "🌱 育成昇格", "📊 デプス", "📄 出力"])

# 【タブ1: 戦力整理（完全3列カード）】
with tab_roster:
    pos_list = ["投手", "捕手", "内野手", "外野手"]
    pos_tabs = st.tabs([f"{p} ({len(target_df[target_df['守備位置'] == p])})" for p in pos_list])

    for p_tab, pos in zip(pos_tabs, pos_list):
        with p_tab:
            p_df = target_df[target_df["守備位置"] == pos]
            
            # 3人ずつ1行に並べる
            for row_idx in range(0, len(p_df), 3):
                row_players = p_df.iloc[row_idx:row_idx+3]
                cols = st.columns(3)
                
                for col_idx, (_, player) in enumerate(row_players.iterrows()):
                    p_no = player["No"]
                    p_name = player["選手名"]
                    p_age = int(player["年齢_num"]) if pd.notnull(player["年齢_num"]) else "-"
                    is_promoted = p_no in promoted_list

                    with cols[col_idx]:
                        with st.container(border=True):
                            badge = "🌱" if is_promoted else ""
                            st.markdown(f"<div class='card-player-name'>#{player['背番号']} {p_name}{badge}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div class='card-player-info'>{p_age}歳 / {player['投打']}</div>", unsafe_allow_html=True)

                            cur_stat = current_status.get(p_no, "残留")
                            # 「現役ドラフト」を「現ドラ」に短縮して幅を取らないように
                            if cur_stat == "現役ドラフト":
                                cur_stat = "現ドラ"

                            new_stat = st.selectbox(
                                "区分",
                                STATUS_OPTIONS,
                                index=STATUS_OPTIONS.index(cur_stat),
                                key=f"sel_{selected_team}_{p_no}",
                                label_visibility="collapsed"
                            )
                            if new_stat != cur_stat:
                                st.session_state.roster_status[selected_team][p_no] = new_stat
                                st.rerun()

# 【タブ2: 育成昇格】
with tab_ikusei:
    st.markdown("##### 育成選手の支配下昇格")
    if len(ikusei_df) == 0:
        st.info("育成選手はいません。")
    else:
        for row_idx in range(0, len(ikusei_df), 3):
            row_players = ikusei_df.iloc[row_idx:row_idx+3]
            ikusei_cols = st.columns(3)
            
            for col_idx, (_, player) in enumerate(row_players.iterrows()):
                p_no = player["No"]
                p_name = player["選手名"]
                p_age = int(player["年齢_num"]) if pd.notnull(player["年齢_num"]) else "-"
                is_checked = p_no in promoted_list
                
                with ikusei_cols[col_idx]:
                    with st.container(border=True):
                        st.markdown(f"<div class='card-player-name'>#{player['背番号']} {p_name}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='card-player-info'>{player['守備位置']} / {p_age}歳</div>", unsafe_allow_html=True)
                        checked = st.checkbox("昇格", value=is_checked, key=f"promo_{p_no}")
                        
                        if checked != is_checked:
                            if checked:
                                st.session_state.promoted_players[selected_team].append(p_no)
                            else:
                                st.session_state.promoted_players[selected_team].remove(p_no)
                            st.rerun()

# 【タブ3: 年齢別デプス】
with tab_depth:
    st.markdown("##### 翌年の所属戦力デプス")
    active_df = target_df[target_df["区分"].isin(["残留", "現ドラ", "保留"])].copy()

    bins = [0, 22, 25, 29, 34, 100]
    labels = ["〜22", "23-25", "26-29", "30-34", "35〜"]
    active_df["年代"] = pd.cut(active_df["年齢_num"], bins=bins, labels=labels, right=True)

    depth_matrix = pd.crosstab(active_df["守備位置"], active_df["年代"], dropna=False).reindex(pos_list)
    st.dataframe(depth_matrix, use_container_width=True)

# 【タブ4: 一覧出力】
with tab_raw:
    st.markdown("##### データ出力")
    st.dataframe(target_df[["背番号", "選手名", "守備位置", "年齢", "区分"]], use_container_width=True)
    csv_data = target_df[["背番号", "選手名", "守備位置", "年齢", "区分"]].to_csv(index=False).encode("utf-8_sig")
    st.download_button(
        label="📥 CSV保存",
        data=csv_data,
        file_name=f"{selected_team}_sim.csv",
        mime="text/csv"
    )

# --- 8. 最下部：補強シミュレーション & 翌年枠 ---
st.markdown("<hr style='margin: 15px 0 10px 0;'/>", unsafe_allow_html=True)
st.markdown("##### 📥 補強シミュレーション")

b1, b2 = st.columns(2)
with b1:
    draft_in = st.number_input("ドラフト支配下", min_value=0, max_value=15, value=5)
    foreign_in = st.number_input("新外国人", min_value=0, max_value=10, value=1)
with b2:
    fa_trade_in = st.number_input("FA・トレード", min_value=0, max_value=10, value=0)
    other_in = st.number_input("その他新加入", min_value=0, max_value=10, value=0)

total_new_acquisitions = draft_in + fa_trade_in + foreign_in + other_in
next_year_total = retained_total + total_new_acquisitions
remaining_slots = 70 - next_year_total

res1, res2 = st.columns(2)
with res1:
    st.markdown(f"**翌年予想支配下: {next_year_total}人**")
    st.caption(f"(所属 {retained_total} + 獲得 {total_new_acquisitions})")
with res2:
    if remaining_slots >= 0:
        st.markdown(f"**70人まで: あと <span style='color: #2e7d32; font-size:1.2rem; font-weight:bold;'>{remaining_slots}</span> 枠**", unsafe_allow_html=True)
    else:
        st.markdown(f"**超過: <span style='color: #d32f2f; font-size:1.2rem; font-weight:bold;'>{-remaining_slots}</span> 人**", unsafe_allow_html=True)
