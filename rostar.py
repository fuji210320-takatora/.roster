import streamlit as st
import pandas as pd
import re

# ページ基本設定
st.set_page_config(
    page_title="NPB ROSTER LAB",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 状態ごとの背景色・文字色・枠線色の定義 ---
STATUS_COLORS = {
    "残留": {"bg": "#ffffff", "text": "#1e293b", "border": "#cbd5e1"},
    "戦力外": {"bg": "#fee2e2", "text": "#991b1b", "border": "#f87171"},
    "育成移行": {"bg": "#dbeafe", "text": "#1e40af", "border": "#60a5fa"},
    "現ドラ": {"bg": "#fef3c7", "text": "#92400e", "border": "#f59e0b"},
    "保留": {"bg": "#f1f5f9", "text": "#475569", "border": "#94a3b8"}
}

STATUS_LIST = ["残留", "戦力外", "育成移行", "現ドラ", "保留"]

# --- スタイリングCSS ---
st.markdown("""
<style>
/* 画面全体の余白を最小化 */
.block-container {
    padding-top: 6px !important;
    padding-bottom: 30px !important;
    padding-left: 6px !important;
    padding-right: 6px !important;
    max-width: 100% !important;
}

/* 上部メトリクス（人数表示）の小型化・均等配置 */
div[data-testid="stMetric"] {
    background-color: #f8fafc;
    border-radius: 6px;
    padding: 3px 4px !important;
    border: 1px solid #e2e8f0;
}
div[data-testid="stMetricLabel"] p {
    font-size: 0.65rem !important;
    margin: 0 !important;
}
div[data-testid="stMetricValue"] div {
    font-size: 1.0rem !important;
    font-weight: 700 !important;
}

/* スマホでも強制的に横3列均等配置にするグリッドコンテナ */
.roster-grid {
    display: grid !important;
    grid-template-columns: repeat(3, 1fr) !important;
    gap: 5px !important;
    width: 100% !important;
    margin-bottom: 10px !important;
}

/* 選手カードのスタイル */
.player-card-box {
    border-radius: 6px;
    padding: 6px 2px;
    text-align: center;
    cursor: pointer;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    user-select: none;
    transition: transform 0.05s ease;
}
.player-card-box:active {
    transform: scale(0.96);
}
.p-name {
    font-size: 0.76rem;
    font-weight: bold;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.2;
}
.p-sub {
    font-size: 0.63rem;
    margin-top: 2px;
    line-height: 1.1;
    opacity: 0.85;
}
.p-status {
    font-size: 0.65rem;
    font-weight: 600;
    margin-top: 3px;
    border-top: 1px dashed rgba(0,0,0,0.15);
    padding-top: 2px;
}

/* ダイアログ内の選択ボタン */
div[data-testid="stDialog"] div[data-testid="stButton"] > button {
    width: 100% !important;
    height: 42px !important;
    margin-bottom: 6px !important;
    font-size: 0.95rem !important;
    font-weight: bold !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# --- 1. 球団コード対応表 ---
TEAM_MAP = {
    "c": "広島東洋カープ", "t": "阪神タイガース", "g": "読売ジャイアンツ",
    "yb": "横浜DeNAベイスターズ", "d": "中日ドラゴンズ", "s": "東京ヤクルトスワローズ",
    "h": "福岡ソフトバンクホークス", "f": "北海道日本ハムファイターズ", "m": "千葉ロッテマリーンズ",
    "e": "東北楽天ゴールデンイーグルス", "b": "オリックス・バファローズ", "l": "埼玉西武ライオンズ",
}

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
    st.error(f"スプレッドシート読込エラー: {e}")
    st.stop()

# --- 3. セッション管理 ---
if "roster_status" not in st.session_state:
    st.session_state.roster_status = {}
if "promoted_players" not in st.session_state:
    st.session_state.promoted_players = {}

st.sidebar.title("設定")
available_teams = [t for t in TEAM_MAP.values() if t in df_raw["球団名"].values]
if not available_teams:
    available_teams = df_raw["球団名"].unique().tolist()
selected_team = st.sidebar.selectbox("球団を選択", available_teams)

if st.sidebar.button("🔄 データを最新に更新"):
    st.cache_data.clear()
    st.rerun()

team_all_df = df_raw[df_raw["球団名"] == selected_team].copy()
shihai_df = team_all_df[team_all_df["契約区分"] == "支配下"].copy()
ikusei_df = team_all_df[team_all_df["契約区分"] == "育成"].copy()

if selected_team not in st.session_state.roster_status:
    st.session_state.roster_status[selected_team] = {
        row["No"]: "残留" for _, row in shihai_df.iterrows()
    }
if selected_team not in st.session_state.promoted_players:
    st.session_state.promoted_players[selected_team] = []

current_status = st.session_state.roster_status[selected_team]
promoted_list = st.session_state.promoted_players[selected_team]

# 支配下に育成昇格組を合流
promoted_df = ikusei_df[ikusei_df["No"].isin(promoted_list)].copy()
target_df = pd.concat([shihai_df, promoted_df], ignore_index=True)

for p_no in promoted_list:
    if p_no not in current_status:
        current_status[p_no] = "残留"

target_df["区分"] = target_df["No"].map(current_status).fillna("残留")

# --- 4. 集計計算 ---
status_counts = {opt: (target_df["区分"] == opt).sum() for opt in STATUS_LIST}
current_shihai_count = len(shihai_df)
promoted_count = len(promoted_list)
retained_total = status_counts["残留"] + status_counts["現ドラ"] + status_counts["保留"]

# --- 5. 選択モーダル（ダイアログ） ---
@st.dialog("区分を選択")
def open_status_dialog(p_no, p_name, cur_stat):
    st.write(f"**{p_name}** の区分を選択してください")
    st.caption(f"現在の設定: 【{cur_stat}】")
    
    for opt in STATUS_LIST:
        col_info = STATUS_COLORS[opt]
        # ボタン押下で即反映＆再描画
        if st.button(f"{opt}", key=f"dlg_btn_{opt}", use_container_width=True):
            st.session_state.roster_status[selected_team][p_no] = opt
            st.rerun()

# --- 6. メインヘッダー ---
st.markdown(f"<h3 style='margin:0 0 2px 0; font-size:1.3rem; font-weight:bold;'>{selected_team}</h3>", unsafe_allow_html=True)
st.caption(f"支配下: {current_shihai_count}名 / 育成: {len(ikusei_df)}名")

# ダッシュボード（均等3列 × 2段）
c1, c2, c3 = st.columns(3)
c1.metric("支配下", f"{current_shihai_count}人")
c2.metric("残留", f"{status_counts['残留']}人")
c3.metric("戦力外", f"{status_counts['戦力外']}人")

c4, c5, c6 = st.columns(3)
c4.metric("育成落", f"{status_counts['育成移行']}人")
c5.metric("現ドラ", f"{status_counts['現ドラ']}人")
c6.metric("昇格", f"{promoted_count}人")

st.markdown("<hr style='margin: 8px 0;'/>", unsafe_allow_html=True)

# --- 7. タブ切り替え ---
tab_roster, tab_ikusei, tab_depth, tab_raw = st.tabs(["📋 戦力整理", "🌱 育成昇格", "📊 デプス", "📄 出力"])

# 【タブ1: 戦力整理（完全横3列タイル表示）】
with tab_roster:
    pos_list = ["投手", "捕手", "内野手", "外野手"]
    pos_tabs = st.tabs([f"{p} ({len(target_df[target_df['守備位置'] == p])})" for p in pos_list])

    for p_tab, pos in zip(pos_tabs, pos_list):
        with p_tab:
            p_df = target_df[target_df["守備位置"] == pos]
            
            # 3人ずつ一行に並べ、ボタンの背景色をステータス色に設定
            for row_idx in range(0, len(p_df), 3):
                row_players = p_df.iloc[row_idx:row_idx+3]
                cols = st.columns(3)
                
                for col_idx, (_, player) in enumerate(row_players.iterrows()):
                    p_no = player["No"]
                    p_name = player["選手名"]
                    is_promoted = p_no in promoted_list
                    badge = "🌱" if is_promoted else ""

                    cur_stat = current_status.get(p_no, "残留")
                    c_style = STATUS_COLORS.get(cur_stat, STATUS_COLORS["残留"])

                    with cols[col_idx]:
                        # カードの見た目（背景色＋枠線色＋文字色）を反映するインラインスタイル
                        btn_html_key = f"p_btn_{selected_team}_{p_no}"
                        
                        # カスタムボタンスタイル注入
                        st.markdown(f"""
                        <style>
                        div[data-testid="stButton"] button[key="{btn_html_key}"] {{
                            background-color: {c_style['bg']} !important;
                            border: 1.5px solid {c_style['border']} !important;
                            color: {c_style['text']} !important;
                        }}
                        </style>
                        """, unsafe_allow_html=True)

                        # タップすると選択肢モーダルを表示
                        btn_label = f"#{player['背番号']} {p_name}{badge}\n{cur_stat}"
                        if st.button(btn_label, key=btn_html_key, help="タップして区分を変更"):
                            open_status_dialog(p_no, f"#{player['背番号']} {p_name}", cur_stat)

# 【タブ2: 育成昇格】
with tab_ikusei:
    st.caption("チェックを入れると支配下へ昇格します")
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
                    st.markdown(f"<div style='border:1px solid #cbd5e1; border-radius:5px; padding:3px; text-align:center; background:#fff;'><b style='font-size:0.72rem;'>#{player['背番号']} {p_name}</b><br><span style='font-size:0.6rem; color:#666;'>{player['守備位置']} {p_age}歳</span></div>", unsafe_allow_html=True)
                    checked = st.checkbox("昇格", value=is_checked, key=f"promo_{p_no}")
                    if checked != is_checked:
                        if checked:
                            st.session_state.promoted_players[selected_team].append(p_no)
                        else:
                            st.session_state.promoted_players[selected_team].remove(p_no)
                        st.rerun()

# 【タブ3: 年齢別デプス】
with tab_depth:
    active_df = target_df[target_df["区分"].isin(["残留", "現ドラ", "保留"])].copy()
    bins = [0, 22, 25, 29, 34, 100]
    labels = ["〜22", "23-25", "26-29", "30-34", "35〜"]
    active_df["年代"] = pd.cut(active_df["年齢_num"], bins=bins, labels=labels, right=True)
    depth_matrix = pd.crosstab(active_df["守備位置"], active_df["年代"], dropna=False).reindex(pos_list)
    st.dataframe(depth_matrix, use_container_width=True)

# 【タブ4: データ出力】
with tab_raw:
    st.dataframe(target_df[["背番号", "選手名", "守備位置", "年齢", "区分"]], use_container_width=True)
    csv_data = target_df[["背番号", "選手名", "守備位置", "年齢", "区分"]].to_csv(index=False).encode("utf-8_sig")
    st.download_button(label="📥 CSV保存", data=csv_data, file_name=f"{selected_team}_sim.csv", mime="text/csv")

# --- 8. 最下部：補強シミュレーション & 枠計算 ---
st.markdown("<hr style='margin: 12px 0 6px 0;'/>", unsafe_allow_html=True)
st.markdown("<b style='font-size:0.9rem;'>📥 補強シミュレーション</b>", unsafe_allow_html=True)

b1, b2 = st.columns(2)
with b1:
    draft_in = st.number_input("ドラフト支配下", min_value=0, max_value=15, value=5)
    foreign_in = st.number_input("新外国人", min_value=0, max_value=10, value=1)
with b2:
    fa_trade_in = st.number_input("FA・トレード", min_value=0, max_value=10, value=0)
    other_in = st.number_input("その他", min_value=0, max_value=10, value=0)

total_new_acquisitions = draft_in + fa_trade_in + foreign_in + other_in
next_year_total = retained_total + total_new_acquisitions
remaining_slots = 70 - next_year_total

res1, res2 = st.columns(2)
with res1:
    st.markdown(f"**翌年支配下: {next_year_total}人**")
    st.caption(f"(所属 {retained_total} + 新規 {total_new_acquisitions})")
with res2:
    if remaining_slots >= 0:
        st.markdown(f"**70枠まで: あと <span style='color:#16a34a; font-size:1.15rem; font-weight:bold;'>{remaining_slots}</span> 枠**", unsafe_allow_html=True)
    else:
        st.markdown(f"**超過: <span style='color:#dc2626; font-size:1.15rem; font-weight:bold;'>{-remaining_slots}</span> 人**", unsafe_allow_html=True)
