import streamlit as st
import pandas as pd
import re

# ページレイアウト
st.set_page_config(page_title="NPB ROSTER LAB", layout="wide", initial_sidebar_state="collapsed")

# --- スマホでも横3列を崩さないためのカスタムCSS ---
st.markdown("""
<style>
/* スマホ画面でもcolumnsが1列に落ちずに横3列をキープする設定 */
[data-testid="column"] {
    min-width: 0px !important;
    padding: 0 4px !important;
}
div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 6px !important;
}
/* カード内の余白と文字サイズをスマホ向けにコンパクト化 */
div[data-testid="stVerticalBlockBorderWrapper"] {
    padding: 8px 6px !important;
    border-radius: 8px !important;
}
.player-name {
    font-weight: bold;
    font-size: 0.95rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.player-info {
    font-size: 0.75rem;
    color: #666;
    margin-bottom: 4px;
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

STATUS_OPTIONS = ["残留", "戦力外", "育成移行", "現役ドラフト", "保留"]

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
    # 育成から支配下に昇格させた選手のNoリスト {球団: [No1, No2]}
    st.session_state.promoted_players = {}

# --- 4. サイドバー設定（球団選択のみ） ---
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

# 支配下リストに育成昇格組を合流
promoted_df = ikusei_df[ikusei_df["No"].isin(promoted_list)].copy()
target_df = pd.concat([shihai_df, promoted_df], ignore_index=True)

# 昇格した選手の初期ステータス登録
for p_no in promoted_list:
    if p_no not in current_status:
        current_status[p_no] = "残留"

target_df["区分"] = target_df["No"].map(current_status).fillna("残留")

# --- 5. 集計の事前計算 ---
status_counts = {opt: (target_df["区分"] == opt).sum() for opt in STATUS_OPTIONS}
current_shihai_count = len(shihai_df)
promoted_count = len(promoted_list)
retained_total = status_counts["残留"] + status_counts["現役ドラフト"] + status_counts["保留"]

# --- 6. メインヘッダー（ダッシュボード） ---
st.title(f"{selected_team}")
st.caption(f"登録選手：支配下 {current_shihai_count}名 / 育成 {len(ikusei_df)}名")

# バッジ表示（2行3列でスマホでも見やすく）
c1, c2, c3 = st.columns(3)
c1.metric("現在支配下", f"{current_shihai_count}人")
c2.metric("残留", f"{status_counts['残留']}人")
c3.metric("戦力外", f"{status_counts['戦力外']}人", delta=f"-{status_counts['戦力外']}" if status_counts['戦力外'] > 0 else None, delta_color="inverse")

c4, c5, c6 = st.columns(3)
c4.metric("育成移行", f"{status_counts['育成移行']}人")
c5.metric("現ドラ候補", f"{status_counts['現役ドラフト']}人")
c6.metric("育成昇格", f"{promoted_count}人", delta=f"+{promoted_count}" if promoted_count > 0 else None)

st.markdown("---")

# --- 7. メインコンテンツ（タブ） ---
tab_roster, tab_ikusei, tab_depth, tab_raw = st.tabs(["📋 戦力整理", "🌱 育成昇格", "📊 年齢別デプス", "📄 一覧出力"])

# 【タブ1: 戦力整理（スマホ対応3列カード）】
with tab_roster:
    pos_list = ["投手", "捕手", "内野手", "外野手"]
    pos_tabs = st.tabs([f"{p} ({len(target_df[target_df['守備位置'] == p])})" for p in pos_list])

    for p_tab, pos in zip(pos_tabs, pos_list):
        with p_tab:
            p_df = target_df[target_df["守備位置"] == pos]
            
            # 3列グリッドで並べる
            cols = st.columns(3)
            for idx, (_, player) in enumerate(p_df.iterrows()):
                p_no = player["No"]
                p_name = player["選手名"]
                p_age = int(player["年齢_num"]) if pd.notnull(player["年齢_num"]) else "-"
                is_promoted = p_no in promoted_list

                with cols[idx % 3]:
                    with st.container(border=True):
                        label_promoted = " 🟢" if is_promoted else ""
                        st.markdown(f"<div class='player-name'>#{player['背番号']} {p_name}{label_promoted}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='player-info'>{p_age}歳 | {player['投打']}</div>", unsafe_allow_html=True)

                        cur_stat = current_status.get(p_no, "残留")
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

# 【タブ2: 育成から支配下への昇格設定】
with tab_ikusei:
    st.subheader("育成選手の支配下登録")
    st.caption("チェックを入れると支配下リストに追加され、枠計算・デプスチャートに反映されます。")
    
    if len(ikusei_df) == 0:
        st.info("この球団には育成登録の選手がいません。")
    else:
        ikusei_cols = st.columns(3)
        for idx, (_, player) in enumerate(ikusei_df.iterrows()):
            p_no = player["No"]
            p_name = player["選手名"]
            p_age = int(player["年齢_num"]) if pd.notnull(player["年齢_num"]) else "-"
            
            is_checked = p_no in promoted_list
            with ikusei_cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"**#{player['背番号']} {p_name}**")
                    st.caption(f"{player['守備位置']} / {p_age}歳")
                    checked = st.checkbox("支配下昇格", value=is_checked, key=f"promo_{p_no}")
                    
                    if checked != is_checked:
                        if checked:
                            st.session_state.promoted_players[selected_team].append(p_no)
                        else:
                            st.session_state.promoted_players[selected_team].remove(p_no)
                        st.rerun()

# 【タブ3: 年齢別デプス】
with tab_depth:
    st.subheader("翌年の所属戦力デプス（支配下＋昇格）")
    active_df = target_df[target_df["区分"].isin(["残留", "現役ドラフト", "保留"])].copy()

    bins = [0, 22, 25, 29, 34, 100]
    labels = ["〜22歳 (若手)", "23〜25歳", "26〜29歳 (主力)", "30〜34歳", "35歳〜"]
    active_df["年代"] = pd.cut(active_df["年齢_num"], bins=bins, labels=labels, right=True)

    depth_matrix = pd.crosstab(active_df["守備位置"], active_df["年代"], dropna=False).reindex(pos_list)
    st.dataframe(depth_matrix, use_container_width=True)

# 【タブ4: 一覧出力】
with tab_raw:
    st.subheader("シミュレーション結果一覧")
    st.dataframe(target_df[["背番号", "選手名", "守備位置", "年齢", "年俸", "区分"]], use_container_width=True)
    csv_data = target_df[["背番号", "選手名", "守備位置", "年齢", "年俸", "区分"]].to_csv(index=False).encode("utf-8_sig")
    st.download_button(
        label="📥 結果をCSV保存",
        data=csv_data,
        file_name=f"{selected_team}_sim.csv",
        mime="text/csv"
    )

# --- 8. 一番下に配置：補強シミュレーション & 翌年枠計算 ---
st.markdown("---")
st.subheader("📥 補強シミュレーション & 翌年支配下枠")

b_col1, b_col2, b_col3, b_col4 = st.columns(4)
with b_col1:
    draft_in = st.number_input("ドラフト支配下", min_value=0, max_value=15, value=5)
with b_col2:
    fa_trade_in = st.number_input("FA・トレード", min_value=0, max_value=10, value=0)
with b_col3:
    foreign_in = st.number_input("新外国人", min_value=0, max_value=10, value=1)
with b_col4:
    other_in = st.number_input("その他新加入", min_value=0, max_value=10, value=0)

# 翌年総数計算（残留ベース ＋ 外部獲得人数）
# ※育成昇格は既に target_df 内で残留／戦力外等の判定に含まれています
total_new_acquisitions = draft_in + fa_trade_in + foreign_in + other_in
next_year_total = retained_total + total_new_acquisitions
remaining_slots = 70 - next_year_total

res_col1, res_col2 = st.columns(2)
with res_col1:
    st.markdown(f"### 翌年の予想支配下: **{next_year_total}人**")
    st.caption(f"(残留・現ドラ等 {retained_total}人 ＋ 新規獲得 {total_new_acquisitions}人)")
with res_col2:
    if remaining_slots >= 0:
        st.markdown(f"### 70人まで: あと **{remaining_slots} 枠**")
    else:
        st.error(f"### ⚠️ 70人枠を **{-remaining_slots}人 超過**しています！")
