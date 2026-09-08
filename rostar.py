import streamlit as st
import pandas as pd
import re

# ページレイアウト
st.set_page_config(page_title="NPB ROSTER LAB", layout="wide")

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

# --- 2. データ読み込み＆前処理（ネット経由） ---
# スプレッドシートID
SHEET_ID = "1I1JsaaQlYHj1zIsOKkFWkc1yAuoNDnpVdy_pLNW5na8"
# 直接CSVとして取得できるGoogleの公開エンドポイントURL
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

# キャッシュを有効にしつつ、スプレッドシート更新時にも追従できるようにTTL（有効期限）を設定
@st.cache_data(ttl=600)  # 10分ごとに自動再取得
def load_data():
    # ネット経由でGoogleスプレッドシートを直接CSVとして読み込む
    df = pd.read_csv(CSV_URL)

    # 年齢の「32歳」から数値を抽出
    df["年齢_num"] = df["年齢"].astype(str).str.extract(r'(\d+)').astype(float)
    
    # 球団コードマッピング
    df["球団名"] = df["コード"].map(TEAM_MAP).fillna(df["コード"])

    # 支配下 / 育成 の判定（背番号が3桁なら育成、それ以外は支配下）
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
    # {球団名: {選手ID(No): "ステータス"}}
    st.session_state.roster_status = {}

# --- 4. サイドバー設定 ---
st.sidebar.title("⚾ 設定パネル")
available_teams = [t for t in TEAM_MAP.values() if t in df_raw["球団名"].values]
if not available_teams:
    available_teams = df_raw["球団名"].unique().tolist()

selected_team = st.sidebar.selectbox("球団を選択", available_teams)

# 選択球団のデータ抽出（基本は支配下のみをシミュレーション対象にする）
team_all_df = df_raw[df_raw["球団名"] == selected_team].copy()
target_df = team_all_df[team_all_df["契約区分"] == "支配下"].copy()

# セッション辞書の初期化
if selected_team not in st.session_state.roster_status:
    st.session_state.roster_status[selected_team] = {
        row["No"]: "残留" for _, row in target_df.iterrows()
    }

current_team_status = st.session_state.roster_status[selected_team]

st.sidebar.markdown("---")
st.sidebar.subheader("📥 補強シミュレーション")
draft_in = st.sidebar.number_input("ドラフト支配下指名数", min_value=0, max_value=15, value=5)
fa_trade_in = st.sidebar.number_input("FA・トレード獲得", min_value=0, max_value=10, value=0)
foreign_in = st.sidebar.number_input("新外国人獲得", min_value=0, max_value=10, value=1)
other_in = st.sidebar.number_input("育成昇格など", min_value=0, max_value=10, value=0)
total_new = draft_in + fa_trade_in + foreign_in + other_in

# --- 5. 集計計算 ---
target_df["区分"] = target_df["No"].map(current_team_status).fillna("残留")

status_counts = {opt: (target_df["区分"] == opt).sum() for opt in STATUS_OPTIONS}
current_total = len(target_df)
retained_total = status_counts["残留"] + status_counts["現役ドラフト"] + status_counts["保留"]
next_year_total = retained_total + total_new
remaining_slots = 70 - next_year_total

# --- 6. メインヘッダー ---
st.title(f"NPB ROSTER LAB - {selected_team}")
st.caption(f"登録選手総数: {len(team_all_df)}名（支配下: {current_total}名 / 育成: {len(team_all_df) - current_total}名）")

# ダッシュボード表示
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("現在支配下", f"{current_total}人")
m2.metric("残留", f"{status_counts['残留']}人")
m3.metric("戦力外", f"{status_counts['戦力外']}人", delta=f"-{status_counts['戦力外']}" if status_counts['戦力外'] > 0 else None, delta_color="inverse")
m4.metric("育成移行", f"{status_counts['育成移行']}人")
m5.metric("現ドラ候補", f"{status_counts['現役ドラフト']}人")
m6.metric("整理対象計", f"{status_counts['戦力外'] + status_counts['育成移行'] + status_counts['現役ドラフト']}人")

st.markdown("---")

b1, b2 = st.columns(2)
b1.subheader(f"翌年の予想支配下: **{next_year_total}人**")
if remaining_slots >= 0:
    b2.subheader(f"70人まで: **あと {remaining_slots} 枠**")
else:
    b2.error(f"⚠️ 70人枠を **{-remaining_slots}人 超過**しています")

st.markdown("---")

# --- 7. タブ表示 ---
tab_roster, tab_depth, tab_raw = st.tabs(["📋 戦力整理", "📊 年齢別デプス", "📄 全データ一覧"])

# 【タブ1: 戦力整理】
with tab_roster:
    pos_list = ["投手", "捕手", "内野手", "外野手"]
    pos_tabs = st.tabs([f"{p} ({len(target_df[target_df['守備位置'] == p])}名)" for p in pos_list])

    for p_tab, pos in zip(pos_tabs, pos_list):
        with p_tab:
            p_df = target_df[target_df["守備位置"] == pos]
            cols = st.columns(3)
            
            for idx, (_, player) in enumerate(p_df.iterrows()):
                p_no = player["No"]
                p_name = player["選手名"]
                p_age = int(player["年齢_num"]) if pd.notnull(player["年齢_num"]) else "-"
                
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.markdown(f"**#{player['背番号']} {p_name}** ({p_age}歳 / {player['投打']})")
                        st.caption(f"年俸: {player['年俸']} / 出身: {player['出身']}")

                        current_stat = current_team_status.get(p_no, "残留")
                        new_stat = st.selectbox(
                            "区分",
                            STATUS_OPTIONS,
                            index=STATUS_OPTIONS.index(current_stat),
                            key=f"sel_{selected_team}_{p_no}",
                            label_visibility="collapsed"
                        )
                        if new_stat != current_stat:
                            st.session_state.roster_status[selected_team][p_no] = new_stat
                            st.rerun()

# 【タブ2: 年齢別デプス】
with tab_depth:
    st.subheader("残留戦力の年齢別デプスチャート（支配下ベース）")
    active_df = target_df[target_df["区分"].isin(["残留", "現役ドラフト", "保留"])].copy()

    # 年代区分
    bins = [0, 22, 25, 29, 34, 100]
    labels = ["〜22歳 (高卒若手)", "23〜25歳 (大卒/若手)", "26〜29歳 (中堅/主力)", "30〜34歳 (ベテラン)", "35歳〜 (大ベテラン)"]
    active_df["年代"] = pd.cut(active_df["年齢_num"], bins=bins, labels=labels, right=True)

    depth_matrix = pd.crosstab(active_df["守備位置"], active_df["年代"], dropna=False).reindex(pos_list)
    st.dataframe(depth_matrix, use_container_width=True)

    for label in labels:
        with st.expander(f"📌 {label}"):
            sub = active_df[active_df["年代"] == label]
            if len(sub) == 0:
                st.caption("該当者なし")
            else:
                for _, r in sub.iterrows():
                    st.write(f"- **{r['守備位置']}** : #{r['背番号']} {r['選手名']} ({int(r['年齢_num'])}歳) - 【{r['区分']}】 (年俸: {r['年俸']})")

# 【タブ3: 生データ・CSV出力】
with tab_raw:
    st.subheader("チーム全選手一覧（育成含む）")
    st.dataframe(team_all_df[["背番号", "選手名", "守備位置", "契約区分", "年齢", "投打", "年俸"]], use_container_width=True)

    csv_data = target_df[["背番号", "選手名", "守備位置", "年齢", "年俸", "区分"]].to_csv(index=False).encode("utf-8_sig")
    st.download_button(
        label=f"📥 {selected_team}のシミュレーション結果をCSVダウンロード",
        data=csv_data,
        file_name=f"{selected_team}_sim_result.csv",
        mime="text/csv"
)
