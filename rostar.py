import streamlit as st
import pandas as pd
import re

# ★ 1番最初に記述（centered でスマホの横スクロールを防止）
st.set_page_config(
    page_title="NPB ROSTER LAB",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 最小限の調整用CSS（画面を潰さない安全な設定） ---
st.markdown("""
<style>
/* 画面左右の余白を詰めてスマホ幅を有効活用 */
.block-container {
    padding-top: 8px !important;
    padding-bottom: 30px !important;
    padding-left: 6px !important;
    padding-right: 6px !important;
}

/* 3列の隙間を詰める */
div[data-testid="stHorizontalBlock"] {
    gap: 4px !important;
}

/* ボタンをカード化（タップで状態切り替え） */
div[data-testid="stButton"] > button {
    width: 100% !important;
    min-height: 46px !important;
    padding: 2px 2px !important;
    border-radius: 6px !important;
    line-height: 1.2 !important;
}
div[data-testid="stButton"] > button p {
    font-size: 0.70rem !important;
    white-space: pre-line !important;
    text-align: center !important;
    margin: 0 !important;
}

/* 上部メトリクス（人数表示）のサイズ調整 */
div[data-testid="stMetric"] {
    background-color: #f8fafc;
    border-radius: 6px;
    padding: 4px 6px !important;
    border: 1px solid #e2e8f0;
}
div[data-testid="stMetricLabel"] p {
    font-size: 0.65rem !important;
    margin: 0 !important;
}
div[data-testid="stMetricValue"] div {
    font-size: 1.05rem !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

# --- 1. 球団設定 ---
TEAM_MAP = {
    "c": "広島東洋カープ", "t": "阪神タイガース", "g": "読売ジャイアンツ",
    "yb": "横浜DeNAベイスターズ", "d": "中日ドラゴンズ", "s": "東京ヤクルトスワローズ",
    "h": "福岡ソフトバンクホークス", "f": "北海道日本ハムファイターズ", "m": "千葉ロッテマリーンズ",
    "e": "東北楽天ゴールデンイーグルス", "b": "オリックス・バファローズ", "l": "埼玉西武ライオンズ",
}

STATUS_CYCLE = ["残留", "戦力外", "育成移行", "現ドラ", "保留"]
STATUS_EMOJI = {
    "残留": "⚪残留",
    "戦力外": "🔴戦力外",
    "育成移行": "🔵育成落",
    "現ドラ": "🟡現ドラ",
    "保留": "⚫保留"
}

# --- 2. データ読み込み（Googleスプレッドシート直接） ---
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

# サイドバー
st.sidebar.title("設定")
available_teams = [t for t in TEAM_MAP.values() if t in df_raw["球団名"].values]
if not available_teams:
    available_teams = df_raw["球団名"].unique().tolist()
selected_team = st.sidebar.selectbox("球団を選択", available_teams)

if st.sidebar.button("🔄 データを最新に更新"):
    st.cache_data.clear()
    st.rerun()

# 選択球団のデータ抽出
team_all_df = df_raw[df_raw["球団名"] == selected_team].copy()
shihai_df = team_all_df[team_all_df["契約区分"] == "支配下"].copy()
ikusei_df = team_all_df[team_all_df["契約区分"] == "育成"].copy()

# セッション辞書の初期化
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
status_counts = {opt: (target_df["区分"] == opt).sum() for opt in STATUS_CYCLE}
current_shihai_count = len(shihai_df)
promoted_count = len(promoted_list)
retained_total = status_counts["残留"] + status_counts["現ドラ"] + status_counts["保留"]

# --- 5. メインヘッダー ---
st.markdown(f"<h3 style='margin:0 0 2px 0; font-size:1.3rem;'>{selected_team}</h3>", unsafe_allow_html=True)
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

# --- 6. タブ切り替え ---
tab_roster, tab_ikusei, tab_depth, tab_raw = st.tabs(["📋 戦力整理", "🌱 育成昇格", "📊 デプス", "📄 出力"])

# 【タブ1: 戦力整理】
with tab_roster:
    pos_list = ["投手", "捕手", "内野手", "外野手"]
    pos_tabs = st.tabs([f"{p} ({len(target_df[target_df['守備位置'] == p])})" for p in pos_list])

    for p_tab, pos in zip(pos_tabs, pos_list):
        with p_tab:
            p_df = target_df[target_df["守備位置"] == pos]
            
            # 3人ずつ1行に配置
            for row_idx in range(0, len(p_df), 3):
                row_players = p_df.iloc[row_idx:row_idx+3]
                cols = st.columns(3)
                
                for col_idx, (_, player) in enumerate(row_players.iterrows()):
                    p_no = player["No"]
                    p_name = player["選手名"]
                    is_promoted = p_no in promoted_list
                    badge = "🌱" if is_promoted else ""

                    cur_stat = current_status.get(p_no, "残留")
                    if cur_stat == "現役ドラフト":
                        cur_stat = "現ドラ"

                    with cols[col_idx]:
                        btn_text = f"#{player['背番号']} {p_name}{badge}\n{STATUS_EMOJI.get(cur_stat, cur_stat)}"
                        if st.button(btn_text, key=f"btn_{selected_team}_{p_no}"):
                            next_idx = (STATUS_CYCLE.index(cur_stat) + 1) % len(STATUS_CYCLE)
                            st.session_state.roster_status[selected_team][p_no] = STATUS_CYCLE[next_idx]
                            st.rerun()

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
                    st.markdown(f"<div style='border:1px solid #cbd5e1; border-radius:4px; padding:2px; text-align:center;'><b style='font-size:0.7rem;'>#{player['背番号']} {p_name}</b><br><span style='font-size:0.6rem; color:#666;'>{player['守備位置']} {p_age}歳</span></div>", unsafe_allow_html=True)
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

# --- 7. 最下部：補強シミュレーション ---
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
