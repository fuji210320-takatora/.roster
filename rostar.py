import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import re

# ページ基本設定
st.set_page_config(
    page_title="NPB ROSTER LAB",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 1. 球団コード対応表 ---
TEAM_MAP = {
    "c": "広島東洋カープ", "t": "阪神タイガース", "g": "読売ジャイアンツ",
    "yb": "横浜DeNAベイスターズ", "d": "中日ドラゴンズ", "s": "東京ヤクルトスワローズ",
    "h": "福岡ソフトバンクホークス", "f": "北海道日本ハムファイターズ", "m": "千葉ロッテマリーンズ",
    "e": "東北楽天ゴールデンイーグルス", "b": "オリックス・バファローズ", "l": "埼玉西武ライオンズ",
}

STATUS_LIST = ["残留", "戦力外", "育成移行", "現ドラ", "保留"]

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
    st.error(f"データ読込エラー: {e}")
    st.stop()

# --- 3. セッション管理 ---
if "roster_status" not in st.session_state:
    st.session_state.roster_status = {}
if "promoted_players" not in st.session_state:
    st.session_state.promoted_players = {}

# サイドバー
st.sidebar.title("⚾ 設定")
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
        int(row["No"]): "残留" for _, row in shihai_df.iterrows()
    }
if selected_team not in st.session_state.promoted_players:
    st.session_state.promoted_players[selected_team] = []

# クエリパラメータによる区分変更の受信処理（HTMLからの変更を受け取る）
qp = st.query_params
if "p_no" in qp and "p_stat" in qp:
    try:
        req_no = int(qp["p_no"])
        req_stat = str(qp["p_stat"])
        st.session_state.roster_status[selected_team][req_no] = req_stat
    except Exception:
        pass
    st.query_params.clear()
    st.rerun()

current_status = st.session_state.roster_status[selected_team]
promoted_list = st.session_state.promoted_players[selected_team]

# 支配下に育成昇格組を合流
promoted_df = ikusei_df[ikusei_df["No"].isin(promoted_list)].copy()
target_df = pd.concat([shihai_df, promoted_df], ignore_index=True)

for p_no in promoted_list:
    p_no_int = int(p_no)
    if p_no_int not in current_status:
        current_status[p_no_int] = "残留"

target_df["区分"] = target_df["No"].astype(int).map(current_status).fillna("残留")

# --- 4. 集計計算 ---
status_counts = {opt: (target_df["区分"] == opt).sum() for opt in STATUS_LIST}
current_shihai_count = len(shihai_df)
promoted_count = len(promoted_list)
retained_total = status_counts["残留"] + status_counts["現ドラ"] + status_counts["保留"]

# --- 5. メインヘッダー（好評だったレイアウトを完全維持） ---
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:4px;">
    <h3 style="margin:0; font-size:1.25rem; font-weight:800;">{selected_team}</h3>
    <span style="font-size:0.7rem; color:#666;">支配下 {current_shihai_count}名 / 育成 {len(ikusei_df)}名</span>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<style>
.metric-row {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
    margin-bottom: 4px;
}}
.metric-box {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 3px 4px;
    text-align: center;
}}
.m-label {{ font-size: 0.65rem; color: #64748b; }}
.m-val {{ font-size: 1.05rem; font-weight: bold; color: #0f172a; line-height: 1.1; }}
</style>
<div class="metric-row">
    <div class="metric-box"><div class="m-label">支配下</div><div class="m-val">{current_shihai_count}人</div></div>
    <div class="metric-box"><div class="m-label">残留</div><div class="m-val">{status_counts['残留']}人</div></div>
    <div class="metric-box"><div class="m-label">戦力外</div><div class="m-val" style="color:#dc2626;">{status_counts['戦力外']}人</div></div>
</div>
<div class="metric-row">
    <div class="metric-box"><div class="m-label">育成落</div><div class="m-val" style="color:#2563eb;">{status_counts['育成移行']}人</div></div>
    <div class="metric-box"><div class="m-label">現ドラ</div><div class="m-val" style="color:#d97706;">{status_counts['現ドラ']}人</div></div>
    <div class="metric-box"><div class="m-label">昇格</div><div class="m-val" style="color:#16a34a;">{promoted_count}人</div></div>
</div>
<hr style="margin: 8px 0 6px 0; border: none; border-top: 1px solid #e2e8f0;"/>
""", unsafe_allow_html=True)

# --- 6. タブ切り替え ---
tab_roster, tab_ikusei, tab_depth, tab_raw = st.tabs(["📋 戦力整理", "🌱 育成昇格", "📊 デプス", "📄 出力"])

# 【タブ1: 戦力整理（完全維持の美しいHTMLグリッド）】
with tab_roster:
    pos_list = ["投手", "捕手", "内野手", "外野手"]
    pos_tabs = st.tabs([f"{p} ({len(target_df[target_df['守備位置'] == p])})" for p in pos_list])

    for p_tab, pos in zip(pos_tabs, pos_list):
        with p_tab:
            p_df = target_df[target_df["守備位置"] == pos].copy()
            
            players_data = []
            for _, r in p_df.iterrows():
                p_no = int(r["No"])
                p_age = int(r["年齢_num"]) if pd.notnull(r["年齢_num"]) else "-"
                is_p = p_no in [int(x) for x in promoted_list]
                players_data.append({
                    "no": p_no,
                    "num": str(r["背番号"]),
                    "name": str(r["選手名"]),
                    "age": str(p_age),
                    "status": current_status.get(p_no, "残留"),
                    "promoted": is_p
                })

            cards_json = json.dumps(players_data, ensure_ascii=False)
            grid_height = max(240, ((len(players_data) + 2) // 3) * 66 + 30)

            # 好評だったデザインCSSは完全にそのまま
            html_code = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
                body {{ background: transparent; padding: 2px; overflow-x: hidden; }}
                
                .grid {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 5px;
                    width: 100%;
                }}

                .card {{
                    height: 58px;
                    border-radius: 6px;
                    padding: 4px 2px;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    align-items: center;
                    cursor: pointer;
                    user-select: none;
                    text-align: center;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
                    transition: transform 0.05s ease;
                }}
                .card:active {{ transform: scale(0.96); }}
                
                .c-name {{
                    font-size: 11.5px;
                    font-weight: bold;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    width: 100%;
                    line-height: 1.2;
                }}
                .c-sub {{
                    font-size: 9.5px;
                    opacity: 0.8;
                    line-height: 1;
                }}
                .c-stat {{
                    font-size: 10px;
                    font-weight: bold;
                    border-radius: 3px;
                    padding: 1px 4px;
                    line-height: 1.1;
                }}

                /* 区分ごとの背景色・文字色・枠線色 */
                .stat-残留 {{ background-color: #ffffff; border: 1.5px solid #cbd5e1; color: #1e293b; }}
                .stat-残留 .c-stat {{ background-color: #f1f5f9; color: #475569; }}

                .stat-戦力外 {{ background-color: #fee2e2; border: 1.5px solid #f87171; color: #991b1b; }}
                .stat-戦力外 .c-stat {{ background-color: #fecaca; color: #991b1b; }}

                .stat-育成移行 {{ background-color: #dbeafe; border: 1.5px solid #60a5fa; color: #1e40af; }}
                .stat-育成移行 .c-stat {{ background-color: #bfdbfe; color: #1e40af; }}

                .stat-現ドラ {{ background-color: #fef3c7; border: 1.5px solid #f59e0b; color: #92400e; }}
                .stat-現ドラ .c-stat {{ background-color: #fde68a; color: #92400e; }}

                .stat-保留 {{ background-color: #f1f5f9; border: 1.5px solid #94a3b8; color: #475569; }}
                .stat-保留 .c-stat {{ background-color: #e2e8f0; color: #334155; }}

                /* モーダルポップアップ */
                .modal-overlay {{
                    display: none;
                    position: fixed;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background: rgba(0,0,0,0.5);
                    justify-content: center;
                    align-items: center;
                    z-index: 999;
                }}
                .modal {{
                    background: white;
                    border-radius: 10px;
                    padding: 14px;
                    width: 82%;
                    max-width: 280px;
                    text-align: center;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                }}
                .modal h4 {{ font-size: 13px; margin-bottom: 10px; color: #111; }}
                .opt-btn {{
                    width: 100%;
                    padding: 9px 0;
                    margin-bottom: 6px;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                    border: 1px solid #ddd;
                    cursor: pointer;
                }}
            </style>
            </head>
            <body>
                <div class="grid" id="playerGrid"></div>

                <!-- 選択肢モーダル -->
                <div class="modal-overlay" id="modalOverlay" onclick="closeModal(event)">
                    <div class="modal" onclick="event.stopPropagation()">
                        <h4 id="modalTitle">選手名</h4>
                        <button class="opt-btn stat-残留" onclick="selectStatus('残留')">残留</button>
                        <button class="opt-btn stat-戦力外" onclick="selectStatus('戦力外')">戦力外</button>
                        <button class="opt-btn stat-育成移行" onclick="selectStatus('育成移行')">育成移行</button>
                        <button class="opt-btn stat-現ドラ" onclick="selectStatus('現ドラ')">現役ドラフト</button>
                        <button class="opt-btn stat-保留" onclick="selectStatus('保留')">保留</button>
                    </div>
                </div>

                <script>
                    const players = {cards_json};
                    const grid = document.getElementById("playerGrid");
                    let activePlayerNo = null;

                    players.forEach(p => {{
                        const card = document.createElement("div");
                        card.className = `card stat-${{p.status}}`;
                        const badge = p.promoted ? "🌱" : "";
                        card.innerHTML = `
                            <div class="c-name">#${{p.num}} ${{p.name}}${{badge}}</div>
                            <div class="c-sub">${{p.age}}歳</div>
                            <div class="c-stat">${{p.status}}</div>
                        `;
                        card.onclick = () => openModal(p.no, `#${{p.num}} ${{p.name}} (${{p.age}}歳)`);
                        grid.appendChild(card);
                    }});

                    function openModal(no, title) {{
                        activePlayerNo = no;
                        document.getElementById("modalTitle").innerText = title;
                        document.getElementById("modalOverlay").style.display = "flex";
                    }}

                    function closeModal(e) {{
                        document.getElementById("modalOverlay").style.display = "none";
                    }}

                    function selectStatus(status) {{
                        document.getElementById("modalOverlay").style.display = "none";
                        // ★ここを安全な通信方式に修正（親画面のクエリパラメータを確実に書き換える）
                        const searchParams = new URLSearchParams(window.top.location.search);
                        searchParams.set("p_no", activePlayerNo);
                        searchParams.set("p_stat", status);
                        window.top.location.search = searchParams.toString();
                    }}
                </script>
            </body>
            </html>
            """
            components.html(html_code, height=grid_height, scrolling=False)

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
                p_no = int(player["No"])
                p_name = player["選手名"]
                p_age = int(player["年齢_num"]) if pd.notnull(player["年齢_num"]) else "-"
                is_checked = p_no in [int(x) for x in promoted_list]
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

# --- 7. 最下部：補強シミュレーション & 枠計算 ---
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
