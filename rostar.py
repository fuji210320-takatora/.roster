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

# --- 2. データ読み込み＆学年年齢計算 ---
SHEET_ID = "1I1JsaaQlYHj1zIsOKkFWkc1yAuoNDnpVdy_pLNW5na8"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

def calc_academic_age(birth_str, target_year=2026):
    try:
        dt = pd.to_datetime(birth_str)
        b_year = dt.year
        b_month = dt.month
        b_day = dt.day

        # 4月1日以前（早生まれ）は前年度扱い
        if (b_month < 4) or (b_month == 4 and b_day == 1):
            school_year_birth = b_year - 1
        else:
            school_year_birth = b_year

        return target_year - school_year_birth
    except Exception:
        return None

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(CSV_URL)
    df["学年年齢"] = df["生年月日"].apply(calc_academic_age)
    fallback_age = df["年齢"].astype(str).str.extract(r'(\d+)')[0].astype(float)
    df["学年年齢"] = df["学年年齢"].fillna(fallback_age)
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
    p_age = int(r["学年年齢"]) if pd.notnull(r["学年年齢"]) else "-"
    players_list.append({
        "no": int(r["No"]),
        "num": str(r["背番号"]),
        "name": str(r["選手名"]),
        "pos": str(r["守備位置"]),
        "age": str(p_age),
        "is_ikusei": r["契約区分"] == "育成",
        "status": "残留",
        "promoted": False
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
    body {{ background: transparent; padding: 4px 4px 30px 4px; overflow-x: hidden; position: relative; }}

    /* タイトルとサマリー */
    .header {{ display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 4px; }}
    .title {{ font-size: 1.25rem; font-weight: 800; color: #111; }}
    .sub {{ font-size: 0.7rem; color: #666; }}

    .age-notice {{
        font-size: 0.68rem;
        color: #475569;
        background: #f1f5f9;
        border-left: 3px solid #64748b;
        padding: 3px 6px;
        border-radius: 2px;
        margin-bottom: 6px;
        line-height: 1.3;
    }}

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

    /* 戦力整理グリッド */
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

    /* ★指定配色：残留(白)、戦力外(赤)、引退(黄)、現ドラ(紫)、育成(青)、保留(灰)★ */
    .stat-残留 {{ background-color: #ffffff; border: 1.5px solid #cbd5e1; color: #1e293b; }}
    .stat-残留 .c-stat {{ background-color: #f1f5f9; color: #475569; }}

    .stat-戦力外 {{ background-color: #fee2e2; border: 1.5px solid #f87171; color: #991b1b; }}
    .stat-戦力外 .c-stat {{ background-color: #fecaca; color: #991b1b; }}

    .stat-引退 {{ background-color: #fef3c7; border: 1.5px solid #f59e0b; color: #92400e; }}
    .stat-引退 .c-stat {{ background-color: #fde68a; color: #92400e; }}

    .stat-現ドラ {{ background-color: #f3e8ff; border: 1.5px solid #c084fc; color: #6b21a8; }}
    .stat-現ドラ .c-stat {{ background-color: #e9d5ff; color: #6b21a8; }}

    .stat-育成移行 {{ background-color: #dbeafe; border: 1.5px solid #60a5fa; color: #1e40af; }}
    .stat-育成移行 .c-stat {{ background-color: #bfdbfe; color: #1e40af; }}

    .stat-保留 {{ background-color: #f1f5f9; border: 1.5px solid #94a3b8; color: #475569; }}
    .stat-保留 .c-stat {{ background-color: #e2e8f0; color: #334155; }}

    /* 年齢別デプスチャート */
    .depth-wrapper {{
        width: 100%;
        overflow-x: auto;
        margin-bottom: 16px;
        -webkit-overflow-scrolling: touch;
    }}
    .depth-info {{ font-size: 0.72rem; color: #64748b; margin-bottom: 4px; }}
    .depth-chart-table {{
        width: 100%;
        min-width: 340px;
        border-collapse: collapse;
        font-size: 0.75rem;
        background: #fff;
        border: 1px solid #cbd5e1;
    }}
    .depth-chart-table th, .depth-chart-table td {{
        border: 1px solid #e2e8f0;
        padding: 5px 3px;
        vertical-align: middle;
    }}
    .depth-chart-table th {{
        background: #f1f5f9;
        color: #334155;
        font-weight: bold;
        text-align: center;
        position: sticky;
        top: 0;
    }}
    .depth-age-col {{
        width: 38px;
        min-width: 38px;
        text-align: center;
        font-weight: 800;
        background: #f8fafc;
        color: #1e293b;
        font-size: 0.8rem;
    }}
    .depth-pos-col {{ width: 24%; text-align: center; }}
    .depth-chip {{
        display: inline-block;
        margin: 2px;
        padding: 3px 5px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
        cursor: pointer;
        white-space: nowrap;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        line-height: 1.15;
    }}
    .depth-chip:active {{ transform: scale(0.95); }}

    /* ★タップ位置連動型ポップアップ（絶対配置・吹き出し）★ */
    .popover-backdrop {{
        display: none;
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.15);
        z-index: 998;
    }}
    .popover-menu {{
        display: none;
        position: absolute;
        width: 170px;
        background: #ffffff;
        border-radius: 10px;
        padding: 8px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.25);
        border: 1px solid #cbd5e1;
        z-index: 999;
    }}
    .pop-header {{
        font-size: 11.5px;
        font-weight: bold;
        color: #0f172a;
        text-align: center;
        margin-bottom: 6px;
        padding-bottom: 4px;
        border-bottom: 1px solid #e2e8f0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .pop-btn-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 4px;
    }}
    .pop-btn {{
        width: 100%;
        padding: 6px 2px;
        border-radius: 5px;
        font-size: 11px;
        font-weight: bold;
        border: 1px solid #cbd5e1;
        cursor: pointer;
        text-align: center;
        line-height: 1.1;
    }}
    .pop-btn:active {{ transform: scale(0.96); }}

    /* 補強エリア */
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

    <div class="age-notice">
        📌 <b>年齢の定義：</b>2026年度（2026年4月2日〜2027年4月1日）に迎える学年満年齢で集計しています（同学年で統一）。
    </div>

    <!-- 上部ダッシュボード -->
    <div class="metric-grid">
        <div class="metric-box"><div class="m-label">支配下</div><div class="m-val" id="cntShihai">0人</div></div>
        <div class="metric-box"><div class="m-label">残留</div><div class="m-val" id="cntZanryu">0人</div></div>
        <div class="metric-box"><div class="m-label">戦力外/引退</div><div class="m-val" id="cntTaiDan" style="color:#dc2626;">0人</div></div>
        <div class="metric-box"><div class="m-label">育成落</div><div class="m-val" id="cntIkuseiOchi" style="color:#2563eb;">0人</div></div>
        <div class="metric-box"><div class="m-label">現ドラ</div><div class="m-val" id="cntGendora" style="color:#6b21a8;">0人</div></div>
        <div class="metric-box"><div class="m-label">昇格</div><div class="m-val" id="cntShokaku" style="color:#16a34a;">0人</div></div>
    </div>

    <!-- タブ -->
    <div class="nav-tabs">
        <button class="tab-btn active" onclick="switchMainTab('roster')">📋 戦力整理</button>
        <button class="tab-btn" onclick="switchMainTab('depth')">📊 年齢別デプス</button>
        <button class="tab-btn" onclick="switchMainTab('ikusei')">🌱 育成昇格</button>
    </div>

    <!-- ポジション選択 -->
    <div id="posTabsContainer" class="pos-tabs">
        <button class="pos-btn active" onclick="switchPos('投手')">投手</button>
        <button class="pos-btn" onclick="switchPos('捕手')">捕手</button>
        <button class="pos-btn" onclick="switchPos('内野手')">内野手</button>
        <button class="pos-btn" onclick="switchPos('外野手')">外野手</button>
    </div>

    <!-- 選手カードグリッド -->
    <div class="grid" id="cardGrid"></div>

    <!-- 年齢別デプスチャート -->
    <div id="depthContainer" style="display:none;">
        <div class="depth-info">2026年度学年年齢デプス（横にスクロールできます）</div>
        <div class="depth-wrapper">
            <table class="depth-chart-table">
                <thead>
                    <tr>
                        <th class="depth-age-col">年齢</th>
                        <th class="depth-pos-col">投手</th>
                        <th class="depth-pos-col">捕手</th>
                        <th class="depth-pos-col">内野手</th>
                        <th class="depth-pos-col">外野手</th>
                    </tr>
                </thead>
                <tbody id="depthChartBody"></tbody>
            </table>
        </div>
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

    <!-- ★タップ位置追従型ポップアップメニュー★ -->
    <div class="popover-backdrop" id="popoverBackdrop" onclick="closePopover()"></div>
    <div class="popover-menu" id="popoverMenu">
        <div class="pop-header" id="popHeader">選手名</div>
        <div class="pop-btn-grid">
            <button class="pop-btn stat-残留" onclick="applyStatus('残留')">残留</button>
            <button class="pop-btn stat-戦力外" onclick="applyStatus('戦力外')">戦力外</button>
            <button class="pop-btn stat-引退" onclick="applyStatus('引退')">引退</button>
            <button class="pop-btn stat-現ドラ" onclick="applyStatus('現ドラ')">現役ドラ</button>
            <button class="pop-btn stat-育成移行" onclick="applyStatus('育成移行')">育成落</button>
            <button class="pop-btn stat-保留" onclick="applyStatus('保留')">保留</button>
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
                (tab === 'depth' && i === 1) ||
                (tab === 'ikusei' && i === 2)
            );
        }});
        document.getElementById('posTabsContainer').style.display = (tab === 'roster') ? 'flex' : 'none';
        document.getElementById('cardGrid').style.display = (tab === 'depth') ? 'none' : 'grid';
        document.getElementById('depthContainer').style.display = (tab === 'depth') ? 'block' : 'none';
        closePopover();
        render();
    }}

    function switchPos(pos) {{
        currentPos = pos;
        document.querySelectorAll('.pos-btn').forEach(b => {{
            b.classList.toggle('active', b.innerText.startsWith(pos));
        }});
        closePopover();
        render();
    }}

    function render() {{
        const grid = document.getElementById('cardGrid');
        grid.innerHTML = '';

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
                // タップした要素自身（e.currentTarget）を渡して位置計算
                card.onclick = (e) => openPopover(e.currentTarget, p.no, `#${{p.num}} ${{p.name}} (${{p.age}}歳)`);
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
            renderDepthChart();
        }}
        calcTotals();
    }}

    function renderDepthChart() {{
        const tbody = document.getElementById('depthChartBody');
        tbody.innerHTML = '';

        const activePlayers = allPlayers.filter(p => !p.is_ikusei || p.promoted);
        const validAges = activePlayers.map(p => parseInt(p.age)).filter(a => !isNaN(a));
        const maxAge = validAges.length > 0 ? Math.max(...validAges) : 38;
        const minAge = validAges.length > 0 ? Math.min(...validAges) : 18;
        const positions = ['投手', '捕手', '内野手', '外野手'];

        for (let age = maxAge; age >= minAge; age--) {{
            const tr = document.createElement('tr');
            let rowHtml = `<td class="depth-age-col">${{age}}</td>`;

            positions.forEach(pos => {{
                const playersAtAge = activePlayers.filter(p => parseInt(p.age) === age && p.pos === pos);
                let chipsHtml = '';
                playersAtAge.forEach(p => {{
                    const badge = p.promoted ? '🌱' : '';
                    chipsHtml += `
                        <div class="depth-chip stat-${{p.status}}" onclick="openPopover(this, ${{p.no}}, '#${{p.num}} ${{p.name}} (${{p.age}}歳)')">
                            ${{p.name}}${{badge}}
                        </div>
                    `;
                }});
                rowHtml += `<td class="depth-pos-col">${{chipsHtml}}</td>`;
            }});

            tr.innerHTML = rowHtml;
            tbody.appendChild(tr);
        }}
    }}

    // ★タップした位置のすぐ上にポップアップを表示する計算ロジック★
    function openPopover(targetEl, no, title) {{
        selectedPlayerNo = no;
        document.getElementById('popHeader').innerText = title;

        const pop = document.getElementById('popoverMenu');
        const backdrop = document.getElementById('popoverBackdrop');

        // タップした要素の画面上での座標とスクロール位置を取得
        const rect = targetEl.getBoundingClientRect();
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

        // ポップアップのサイズ
        const popWidth = 170;
        const popHeight = 110;

        // 水平位置：タップ要素の中央に合わせつつ、画面端からはみ出さないように調整
        let left = rect.left + scrollLeft + (rect.width / 2) - (popWidth / 2);
        const maxLeft = document.documentElement.clientWidth - popWidth - 8;
        if (left < 8) left = 8;
        if (left > maxLeft) left = maxLeft;

        // 垂直位置：基本は「カードのすぐ上」。画面最上部付近なら「カードのすぐ下」に出す
        let top = rect.top + scrollTop - popHeight - 6;
        if (rect.top < popHeight + 10) {{
            top = rect.bottom + scrollTop + 6; // 下に出す
        }}

        pop.style.left = `${{left}}px`;
        pop.style.top = `${{top}}px`;

        backdrop.style.display = 'block';
        pop.style.display = 'block';
    }}

    function closePopover() {{
        document.getElementById('popoverBackdrop').style.display = 'none';
        document.getElementById('popoverMenu').style.display = 'none';
    }}

    function applyStatus(status) {{
        closePopover();
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

        const counts = {{ '残留': 0, '戦力外': 0, '引退': 0, '育成移行': 0, '現ドラ': 0, '保留': 0 }};
        activeShihai.forEach(p => {{
            if (counts[p.status] !== undefined) counts[p.status]++;
        }});

        // 退団計（戦力外 ＋ 引退）
        const taidanTotal = counts['戦力外'] + counts['引退'];

        document.getElementById('cntShihai').innerText = `${{shihaiOrigin}}人`;
        document.getElementById('cntZanryu').innerText = `${{counts['残留']}}人`;
        document.getElementById('cntTaiDan').innerText = `${{taidanTotal}}人`;
        document.getElementById('cntIkuseiOchi').innerText = `${{counts['育成移行']}}人`;
        document.getElementById('cntGendora').innerText = `${{counts['現ドラ']}}人`;
        document.getElementById('cntShokaku').innerText = `${{promotedCount}}人`;

        // 翌年支配下計算（残留 ＋ 現ドラ ＋ 保留 ＋ 外部獲得）
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

components.html(app_html, height=1300, scrolling=True)
