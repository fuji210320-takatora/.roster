import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json

# ページ基本設定
st.set_page_config(
    page_title="NPB ROSTER LAB",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 1. 球団設定 ---
TEAM_MAP = {
    "c": "広島東洋カープ", "t": "阪神タイガース", "g": "読売ジャイアンツ",
    "yb": "横浜DeNAベイスターズ", "d": "中日ドラゴンズ", "s": "東京ヤクルトスワローズ",
    "h": "福岡ソフトバンクホークス", "f": "北海道日本ハムファイターズ", "m": "千葉ロッテマリーンズ",
    "e": "東北楽天ゴールデンイーグルス", "b": "オリックス・バファローズ", "l": "埼玉西武ライオンズ",
}

# --- 2. データ読み込み ---
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

# サイドバー
st.sidebar.title("⚾ 設定")
available_teams = [t for t in TEAM_MAP.values() if t in df_raw["球団名"].values]
if not available_teams:
    available_teams = df_raw["球団名"].unique().tolist()
selected_team = st.sidebar.selectbox("球団を選択", available_teams)

if st.sidebar.button("🔄 データを最新に更新"):
    st.cache_data.clear()
    st.rerun()

# 選手データのJSON化
team_df = df_raw[df_raw["球団名"] == selected_team].copy()
players_list = []
for _, r in team_df.iterrows():
    p_age = int(r["年齢_num"]) if pd.notnull(r["年齢_num"]) else "-"
    players_list.append({
        "no": int(r["No"]),
        "num": str(r["背番号"]),
        "name": str(r["選手名"]),
        "pos": str(r["守備位置"]),
        "age": str(p_age),
        "is_ikusei": r["契約区分"] == "育成",
        "status": "残留"
    })

players_json = json.dumps(players_list, ensure_ascii=False)

# --- 3. アプリ本体（HTML + JavaScript） ---
app_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    body {{ background: transparent; padding: 4px 4px 30px 4px; overflow-x: hidden; }}

    /* タイトルとサマリー */
    .header {{ display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 6px; }}
    .title {{ font-size: 1.25rem; font-weight: 800; color: #111; }}
    .sub {{ font-size: 0.7rem; color: #666; }}

    /* 上部ダッシュボード */
    .metric-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 4px;
        margin-bottom: 8px;
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

    /* タブ切り替え */
    .nav-tabs {{
        display: flex;
        border-bottom: 2px solid #e2e8f0;
        margin-bottom: 8px;
        gap: 8px;
    }}
    .tab-btn {{
        padding: 6px 8px;
        font-size: 0.82rem;
        font-weight: bold;
        color: #64748b;
        background: none;
        border: none;
        cursor: pointer;
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
    }}
    .tab-btn.active {{
        color: #dc2626;
        border-bottom: 2px solid #dc2626;
    }}

    /* ポジションサブタブ */
    .pos-tabs {{
        display: flex;
        gap: 6px;
        margin-bottom: 8px;
        overflow-x: auto;
    }}
    .pos-btn {{
        padding: 4px 8px;
        font-size: 0.75rem;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        background: #fff;
        color: #475569;
        cursor: pointer;
    }}
    .pos-btn.active {{
        background: #334155;
        color: #fff;
        border-color: #334155;
    }}

    /* ★完全な横3列・均等サイズグリッド★ */
    .grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 5px;
        width: 100%;
        margin-bottom: 16px;
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
        transition: transform 0.05s ease, background-color 0.15s ease;
    }}
    .card:active {{ transform: scale(0.95); }}
    
    .c-name {{
        font-size: 11.5px;
        font-weight: bold;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        width: 100%;
        line-height: 1.2;
    }}
    .c-sub {{ font-size: 9.5px; opacity: 0.8; line-height: 1; }}
    .c-stat {{ font-size: 10px; font-weight: bold; border-radius: 3px; padding: 1px 4px; line-height: 1.1; }}

    /* ステータス別の背景色・文字色 */
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

    /* デプステーブル用 */
    .depth-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.72rem;
        margin-bottom: 16px;
        background: #fff;
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid #cbd5e1;
    }}
    .depth-table th, .depth-table td {{
        padding: 5px 4px;
        text-align: center;
        border: 1px solid #e2e8f0;
    }}
    .depth-table th {{ background: #f8fafc; font-weight: bold; color: #475569; }}

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
    .modal h4 {{ font-size: 14px; margin-bottom: 12px; color: #111; }}
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

    /* 補強エリア（最下部） */
    .bottom-section {{
        margin-top: 14px;
        padding-top: 10px;
        border-top: 2px solid #e2e8f0;
    }}
    .input-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 6px;
        margin-bottom: 8px;
    }}
    .input-box {{
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 4px 6px;
    }}
    .input-box label {{ font-size: 0.7rem; color: #475569; display: block; }}
    .input-box input {{ width: 100%; font-size: 0.95rem; font-weight: bold; padding: 2px; border: 1px solid #ccc; border-radius: 4px; }}

    .result-banner {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #f1f5f9;
        border-radius: 8px;
        padding: 8px 10px;
        margin-top: 6px;
    }}
</style>
</head>
<body>

    <!-- ヘッダー -->
    <div class="header">
        <div class="title">{selected_team}</div>
        <div class="sub" id="headerSub"></div>
    </div>

    <!-- 上部ダッシュボード -->
    <div class="metric-grid">
        <div class="metric-box"><div class="m-label">支配下</div><div class="m-val" id="cntShihai">0人</div></div>
        <div class="metric-box"><div class="m-label">残留</div><div class="m-val" id="cntZanryu">0人</div></div>
        <div class="metric-box"><div class="m-label">戦力外</div><div class="m-val" id="cntSenryokugai" style="color:#dc2626;">0人</div></div>
        <div class="metric-box"><div class="m-label">育成落</div><div class="m-val" id="cntIkuseiOchi" style="color:#2563eb;">0人</div></div>
        <div class="metric-box"><div class="m-label">現ドラ</div><div class="m-val" id="cntGendora" style="color:#d97706;">0人</div></div>
        <div class="metric-box"><div class="m-label">昇格</div><div class="m-val" id="cntShokaku" style="color:#16a34a;">0人</div></div>
    </div>

    <!-- タブ -->
    <div class="nav-tabs">
        <button class="tab-btn active" onclick="switchMainTab('roster')">📋 戦力整理</button>
        <button class="tab-btn" onclick="switchMainTab('ikusei')">🌱 育成昇格</button>
        <button class="tab-btn" onclick="switchMainTab('depth')">📊 デプス</button>
    </div>

    <!-- ポジション選択（戦力整理タブ時のみ表示） -->
    <div id="posTabsContainer" class="pos-tabs">
        <button class="pos-btn active" onclick="switchPos('投手')">投手</button>
        <button class="pos-btn" onclick="switchPos('捕手')">捕手</button>
        <button class="pos-btn" onclick="switchPos('内野手')">内野手</button>
        <button class="pos-btn" onclick="switchPos('外野手')">外野手</button>
    </div>

    <!-- 選手カードグリッド -->
    <div class="grid" id="cardGrid"></div>

    <!-- デプステーブル表示領域 -->
    <div id="depthContainer" style="display:none;">
        <table class="depth-table">
            <thead>
                <tr><th>位置</th><th>〜22</th><th>23-25</th><th>26-29</th><th>30-34</th><th>35〜</th><th>計</th></tr>
            </thead>
            <tbody id="depthBody"></tbody>
        </table>
    </div>

    <!-- 最下部：補強シミュレーション -->
    <div class="bottom-section">
        <b style="font-size:0.85rem; color:#334155;">📥 補強シミュレーション</b>
        <div class="input-grid" style="margin-top:4px;">
            <div class="input-box"><label>ドラフト支配下</label><input type="number" id="inDraft" value="5" min="0" max="15" oninput="calcTotals()"></div>
            <div class="input-box"><label>FA・トレード</label><input type="number" id="inFa" value="0" min="0" max="10" oninput="calcTotals()"></div>
            <div class="input-box"><label>新外国人</label><input type="number" id="inForeign" value="1" min="0" max="10" oninput="calcTotals()"></div>
            <div class="input-box"><label>その他新加入</label><input type="number" id="inOther" value="0" min="0" max="10" oninput="calcTotals()"></div>
        </div>

        <div class="result-banner">
            <div>
                <div style="font-size:0.75rem; color:#475569;">翌年予想支配下</div>
                <div style="font-size:1.1rem; font-weight:800; color:#0f172a;" id="nextYearTotal">65人</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.75rem; color:#475569;">70人まで</div>
                <div style="font-size:1.1rem; font-weight:800;" id="remainingSlots">あと 5 枠</div>
            </div>
        </div>
    </div>

    <!-- 区分選択モーダル -->
    <div class="modal-overlay" id="modalOverlay" onclick="closeModal(event)">
        <div class="modal" onclick="event.stopPropagation()">
            <h4 id="modalTitle">選手名</h4>
            <button class="opt-btn stat-残留" onclick="applyStatus('残留')">残留</button>
            <button class="opt-btn stat-戦力外" onclick="applyStatus('戦力外')">戦力外</button>
            <button class="opt-btn stat-育成移行" onclick="applyStatus('育成移行')">育成移行</button>
            <button class="opt-btn stat-現ドラ" onclick="applyStatus('現ドラ')">現役ドラフト</button>
            <button class="opt-btn stat-保留" onclick="applyStatus('保留')">保留</button>
        </div>
    </div>

<script>
    const allPlayers = {players_json};
    let currentMainTab = 'roster';
    let currentPos = '投手';
    let selectedPlayerNo = null;

    render();

    function switchMainTab(tab) {{
        currentMainTab = tab;
        document.querySelectorAll('.tab-btn').forEach((b, i) => {{
            b.classList.toggle('active', 
                (tab === 'roster' && i === 0) || 
                (tab === 'ikusei' && i === 1) ||
                (tab === 'depth' && i === 2)
            );
        }});
        document.getElementById('posTabsContainer').style.display = (tab === 'roster') ? 'flex' : 'none';
        document.getElementById('cardGrid').style.display = (tab === 'depth') ? 'none' : 'grid';
        document.getElementById('depthContainer').style.display = (tab === 'depth') ? 'block' : 'none';
        render();
    }}

    function switchPos(pos) {{
        currentPos = pos;
        document.querySelectorAll('.pos-btn').forEach(b => {{
            b.classList.toggle('active', b.innerText.startsWith(pos));
        }});
        render();
    }}

    function render() {{
        const grid = document.getElementById('cardGrid');
        grid.innerHTML = '';

        // 各ポジションの人数を更新
        ['投手', '捕手', '内野手', '外野手'].forEach((pName, idx) => {{
            const c = allPlayers.filter(p => (!p.is_ikusei || p.promoted) && p.pos === pName).length;
            const btn = document.querySelectorAll('.pos-btn')[idx];
            if (btn) btn.innerText = `${{pName}} (${{c}})`;
        }});

        if (currentMainTab === 'roster') {{
            const target = allPlayers.filter(p => (!p.is_ikusei || p.promoted) && p.pos === currentPos);
            target.forEach(p => {{
                const card = document.createElement('div');
                card.className = `card stat-${{p.status}}`;
                const badge = p.promoted ? '🌱' : '';
                card.innerHTML = `
                    <div class="c-name">#${{p.num}} ${{p.name}}${{badge}}</div>
                    <div class="c-sub">${{p.age}}歳</div>
                    <div class="c-stat">${{p.status}}</div>
                `;
                card.onclick = () => openModal(p.no, `#${{p.num}} ${{p.name}} (${{p.age}}歳)`);
                grid.appendChild(card);
            }});
        }} else if (currentMainTab === 'ikusei') {{
            const target = allPlayers.filter(p => p.is_ikusei);
            target.forEach(p => {{
                const card = document.createElement('div');
                card.className = `card ${{p.promoted ? 'stat-育成移行' : 'stat-残留'}}`;
                card.innerHTML = `
                    <div class="c-name">#${{p.num}} ${{p.name}}</div>
                    <div class="c-sub">${{p.pos}} / ${{p.age}}歳</div>
                    <div class="c-stat">${{p.promoted ? '支配下昇格中' : '育成'}}</div>
                `;
                card.onclick = () => {{
                    p.promoted = !p.promoted;
                    render();
                }};
                grid.appendChild(card);
            }});
        }} else if (currentMainTab === 'depth') {{
            renderDepth();
        }}
        calcTotals();
    }}

    function renderDepth() {{
        const tbody = document.getElementById('depthBody');
        tbody.innerHTML = '';
        const active = allPlayers.filter(p => (!p.is_ikusei || p.promoted) && ['残留', '現ドラ', '保留'].includes(p.status));
        const positions = ['投手', '捕手', '内野手', '外野手'];

        positions.forEach(pos => {{
            const pList = active.filter(p => p.pos === pos);
            const cU22 = pList.filter(p => p.age !== '-' && parseInt(p.age) <= 22).length;
            const c2325 = pList.filter(p => p.age !== '-' && parseInt(p.age) >= 23 && parseInt(p.age) <= 25).length;
            const c2629 = pList.filter(p => p.age !== '-' && parseInt(p.age) >= 26 && parseInt(p.age) <= 29).length;
            const c3034 = pList.filter(p => p.age !== '-' && parseInt(p.age) >= 30 && parseInt(p.age) <= 34).length;
            const c35O = pList.filter(p => p.age !== '-' && parseInt(p.age) >= 35).length;

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight:bold;">${{pos}}</td>
                <td>${{cU22}}</td>
                <td>${{c2325}}</td>
                <td>${{c2629}}</td>
                <td>${{c3034}}</td>
                <td>${{c35O}}</td>
                <td style="font-weight:bold; background:#f8fafc;">${{pList.length}}</td>
            `;
            tbody.appendChild(tr);
        }});
    }}

    function openModal(no, title) {{
        selectedPlayerNo = no;
        document.getElementById('modalTitle').innerText = title;
        document.getElementById('modalOverlay').style.display = 'flex';
    }}

    function closeModal() {{
        document.getElementById('modalOverlay').style.display = 'none';
    }}

    function applyStatus(status) {{
        closeModal();
        const p = allPlayers.find(x => x.no === selectedPlayerNo);
        if (p) {{
            p.status = status;
            render();
        }}
    }}

    function calcTotals() {{
        const shihaiOrigin = allPlayers.filter(p => !p.is_ikusei).length;
        const ikuseiOrigin = allPlayers.filter(p => p.is_ikusei).length;
        document.getElementById('headerSub').innerText = `支配下 ${{shihaiOrigin}}名 / 育成 ${{ikuseiOrigin}}名`;

        const activeShihai = allPlayers.filter(p => !p.is_ikusei || p.promoted);
        const promotedCount = allPlayers.filter(p => p.is_ikusei && p.promoted).length;

        const counts = {{ '残留': 0, '戦力外': 0, '育成移行': 0, '現ドラ': 0, '保留': 0 }};
        activeShihai.forEach(p => {{
            if (counts[p.status] !== undefined) counts[p.status]++;
        }});

        document.getElementById('cntShihai').innerText = `${{shihaiOrigin}}人`;
        document.getElementById('cntZanryu').innerText = `${{counts['残留']}}人`;
        document.getElementById('cntSenryokugai').innerText = `${{counts['戦力外']}}人`;
        document.getElementById('cntIkuseiOchi').innerText = `${{counts['育成移行']}}人`;
        document.getElementById('cntGendora').innerText = `${{counts['現ドラ']}}人`;
        document.getElementById('cntShokaku').innerText = `${{promotedCount}}人`;

        const inDraft = parseInt(document.getElementById('inDraft').value) || 0;
        const inFa = parseInt(document.getElementById('inFa').value) || 0;
        const inForeign = parseInt(document.getElementById('inForeign').value) || 0;
        const inOther = parseInt(document.getElementById('inOther').value) || 0;
        const totalNew = inDraft + inFa + inForeign + inOther;

        const retainedTotal = counts['残留'] + counts['現ドラ'] + counts['保留'];
        const nextTotal = retainedTotal + totalNew;
        const remaining = 70 - nextTotal;

        document.getElementById('nextYearTotal').innerText = `${{nextTotal}}人`;
        const remEl = document.getElementById('remainingSlots');
        if (remaining >= 0) {{
            remEl.innerHTML = `<span style="color:#16a34a;">あと ${{remaining}} 枠</span>`;
        }} else {{
            remEl.innerHTML = `<span style="color:#dc2626;">${{-remaining}}人 超過</span>`;
        }}
    }}
</script>
</body>
</html>
"""

# 投手35名＋補強エリアがすっぽり収まる余裕のある高さを指定し、スクロールを許可
components.html(app_html, height=1050, scrolling=True)
