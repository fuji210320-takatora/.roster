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

TEAM_CODE_MAP = {
    "広島東洋カープ": "C", "阪神タイガース": "T", "読売ジャイアンツ": "G",
    "横浜DeNAベイスターズ": "DB", "中日ドラゴンズ": "D", "東京ヤクルトスワローズ": "S",
    "福岡ソフトバンクホークス": "H", "北海道日本ハムファイターズ": "F", "千葉ロッテマリーンズ": "M",
    "東北楽天ゴールデンイーグルス": "E", "オリックス・バファローズ": "B", "埼玉西武ライオンズ": "L",
}

# 退団・除外リスト（球団名: [選手名...]）
RELEASED_PLAYERS = {
    "横浜DeNAベイスターズ": ["コックス", "デュプランティエ", "ビシエド"],
    "東京ヤクルトスワローズ": ["澤野聖悠", "澤野 聖悠"],
    "東北楽天ゴールデンイーグルス": ["ゴンザレス"],
    "オリックス・バファローズ": ["遠藤成", "遠藤 成"],
    "埼玉西武ライオンズ": ["ボー・タカハシ", "ボータカハシ", "タカハシ"]
}

# 手動追加・入団リスト
MANUAL_ADDITIONS = [
    {
        "No": 99901,
        "背番号": "021",
        "選手名": "遠藤 成",
        "守備位置": "内野手",
        "生年月日": "2001/09/19",
        "年齢": "25",
        "年俸": "600万円",
        "コード": "s",
        "球団名": "東京ヤクルトスワローズ",
        "契約区分": "育成"
    }
]

# --- 2. データ読み込み＆学年年齢・年俸整形 ---
SHEET_ID = "1I1JsaaQlYHj1zIsOKkFWkc1yAuoNDnpVdy_pLNW5na8"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

def calc_academic_age(birth_str, target_year=2026):
    try:
        dt = pd.to_datetime(birth_str)
        b_year = dt.year
        b_month = dt.month
        b_day = dt.day

        if (b_month < 4) or (b_month == 4 and b_day == 1):
            school_year_birth = b_year - 1
        else:
            school_year_birth = b_year

        return target_year - school_year_birth
    except Exception:
        return None

def format_salary(salary_val):
    if pd.isna(salary_val):
        return "-"
    s = str(salary_val).replace(" ", "").replace(",", "").replace("推定", "").replace("円", "")
    try:
        if "万" in s:
            num = float(s.replace("万", ""))
            if num >= 10000:
                oku = num / 10000
                return f"{oku:.1f}億".replace(".0億", "億")
            return f"{int(num)}万"
        num = float(s)
        if num >= 10000:
            oku = num / 10000
            return f"{oku:.1f}億".replace(".0億", "億")
        return f"{int(num)}万"
    except Exception:
        return str(salary_val)

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(CSV_URL, dtype={"背番号": str})

    df["球団名"] = df["コード"].map(TEAM_MAP).fillna(df["コード"])

    def check_shihai(no_str):
        s = str(no_str).strip()
        if len(s) >= 3:
            return "育成"
        return "支配下"

    df["契約区分"] = df["背番号"].apply(check_shihai)

    # ★1. 退団選手の除外処理★
    drop_indices = []
    for team, names in RELEASED_PLAYERS.items():
        for name in names:
            # 姓名間の空白を無視して一致判定
            clean_name = name.replace(" ", "").replace(" ", "")
            matches = df[(df["球団名"] == team) & (df["選手名"].str.replace(" ", "").replace(" ", "") == clean_name)].index
            drop_indices.extend(matches.tolist())
    
    if drop_indices:
        df = df.drop(index=list(set(drop_indices)))

    # ★2. 新規入団選手の追加処理★
    add_df = pd.DataFrame(MANUAL_ADDITIONS)
    df = pd.concat([df, add_df], ignore_index=True)

    # 学年年齢計算と年俸整形
    df["学年年齢"] = df["生年月日"].apply(calc_academic_age)
    fallback_age = df["年齢"].astype(str).str.extract(r'(\d+)')[0].astype(float)
    df["学年年齢"] = df["学年年齢"].fillna(fallback_age)

    if "年俸" in df.columns:
        df["年俸_fmt"] = df["年俸"].apply(format_salary)
    else:
        df["年俸_fmt"] = "-"

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

team_code = TEAM_CODE_MAP.get(selected_team, "NPB")

# 選手データのJSON化
team_df = df_raw[df_raw["球団名"] == selected_team].copy()
players_list = []
for _, r in team_df.iterrows():
    p_age = int(r["学年年齢"]) if pd.notnull(r["学年年齢"]) else "-"
    is_iku = (r["契約区分"] == "育成")
    salary_text = str(r["年俸_fmt"]) if pd.notnull(r["年俸_fmt"]) else "-"
    players_list.append({
        "no": int(r["No"]),
        "num": str(r["背番号"]),
        "name": str(r["選手名"]),
        "pos": str(r["守備位置"]),
        "age": str(p_age),
        "salary": salary_text,
        "is_ikusei": is_iku,
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
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Hiragino Sans", Meiryo, sans-serif; }}
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

    /* メインタブ切り替え */
    .nav-tabs {{
        display: flex;
        border-bottom: 2px solid #e2e8f0;
        margin-bottom: 8px;
        gap: 2px;
        overflow-x: auto;
    }}
    .tab-btn {{
        padding: 4px 5px;
        font-size: 0.64rem;
        font-weight: bold;
        color: #64748b;
        background: none;
        border: none;
        cursor: pointer;
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
        white-space: nowrap;
    }}
    .tab-btn.active {{
        color: #dc2626;
        border-bottom: 2px solid #dc2626;
    }}

    /* ポジションサブタブ */
    .pos-tabs {{
        display: flex;
        gap: 3px;
        margin-bottom: 8px;
        overflow-x: auto;
    }}
    .pos-btn {{
        padding: 2px 5px;
        font-size: 0.62rem;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        background: #fff;
        color: #475569;
        cursor: pointer;
        white-space: nowrap;
    }}
    .pos-btn.active {{
        background: #334155;
        color: #fff;
        border-color: #334155;
    }}

    /* 育成タブ内の見出し */
    .ikusei-sec-title {{
        font-size: 0.75rem;
        font-weight: bold;
        color: #1e293b;
        margin: 10px 0 4px 2px;
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .ikusei-sec-title::after {{
        content: "";
        flex: 1;
        height: 1px;
        background: #e2e8f0;
    }}

    /* カードグリッド（3列） */
    .grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 5px;
        width: 100%;
        margin-bottom: 8px;
    }}

    .card {{
        height: 62px;
        border-radius: 6px;
        padding: 3px 2px;
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
        font-size: 11px;
        font-weight: bold;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        width: 100%;
        line-height: 1.15;
    }}
    .c-sub {{
        font-size: 9px;
        opacity: 0.85;
        line-height: 1;
        display: flex;
        gap: 3px;
        align-items: center;
        justify-content: center;
    }}
    .c-stat {{ font-size: 9.5px; font-weight: bold; border-radius: 3px; padding: 1px 4px; line-height: 1.05; }}

    /* 配色 */
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

    .stat-支配下昇格 {{ background-color: #dcfce7; border: 1.5px solid #22c55e; color: #15803d; }}
    .stat-支配下昇格 .c-stat {{ background-color: #bbf7d0; color: #15803d; }}

    /* デプスチャート */
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

    /* ポップアップメニュー */
    .popover-backdrop {{
        display: none;
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.18);
        z-index: 998;
    }}
    .popover-menu {{
        display: none;
        position: fixed;
        width: 176px;
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
    .pop-btn-stack {{
        display: flex;
        flex-direction: column;
        gap: 5px;
    }}
    .pop-btn {{
        width: 100%;
        padding: 7px 2px;
        border-radius: 5px;
        font-size: 11.5px;
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

    /* 画像出力用スタイル */
    .export-container {{
        width: 100%;
        overflow-x: auto;
        margin-bottom: 12px;
    }}
    .download-bar {{
        display: flex;
        justify-content: center;
        margin: 10px 0 16px 0;
    }}
    .download-btn {{
        background: #0f172a;
        color: #ffffff;
        font-size: 0.85rem;
        font-weight: bold;
        padding: 10px 20px;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .download-btn:active {{ transform: scale(0.97); }}

    #captureArea {{
        width: 460px;
        background: #ffffff;
        padding: 16px 14px;
        margin: 0 auto;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    .exp-top {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 10px;
    }}
    .exp-sub-title {{ font-size: 10px; color: #64748b; font-weight: bold; }}
    .exp-team-badge {{
        background: #091a2b;
        color: #ffffff;
        font-size: 12px;
        font-weight: 900;
        width: 32px;
        height: 22px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .exp-title-area {{ text-align: center; margin-bottom: 12px; }}
    .exp-team-name {{ font-size: 22px; font-weight: 900; color: #0f172a; margin-bottom: 2px; }}
    .exp-year-text {{ font-size: 10.5px; color: #64748b; font-weight: 600; }}

    .exp-summary-row {{
        display: flex;
        justify-content: space-between;
        border-top: 1px solid #f1f5f9;
        border-bottom: 1px solid #f1f5f9;
        padding: 8px 4px;
        margin-bottom: 8px;
        text-align: center;
    }}
    .exp-sum-item {{ flex: 1; }}
    .exp-sum-item:not(:last-child) {{ border-right: 1px solid #f1f5f9; }}
    .exp-sum-label {{ font-size: 10px; color: #475569; }}
    .exp-sum-val {{ font-size: 13px; font-weight: 900; }}

    .exp-legend-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        font-size: 9px;
        color: #64748b;
    }}
    .exp-legends {{ display: flex; gap: 6px; }}
    .exp-leg-item {{ display: flex; align-items: center; gap: 3px; }}
    .exp-leg-box {{ width: 10px; height: 10px; border-radius: 2px; border: 1px solid #cbd5e1; }}

    .exp-pos-sec {{ margin-bottom: 12px; }}
    .exp-pos-header {{
        font-size: 14px;
        font-weight: 900;
        color: #0f172a;
        margin-bottom: 5px;
    }}
    .exp-grid-5 {{
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 2px;
    }}
    .exp-cell {{
        height: 28px;
        font-size: 10.5px;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid #cbd5e1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        padding: 0 1px;
    }}
    .exp-stat-残留 {{ background-color: #f8fafc; color: #0f172a; border-color: #e2e8f0; }}
    .exp-stat-戦力外 {{ background-color: #fecaca; color: #991b1b; border-color: #f87171; }}
    .exp-stat-引退 {{ background-color: #fde68a; color: #92400e; border-color: #f59e0b; }}
    .exp-stat-現ドラ {{ background-color: #e9d5ff; color: #6b21a8; border-color: #c084fc; }}
    .exp-stat-育成移行 {{ background-color: #bfdbfe; color: #1e40af; border-color: #60a5fa; }}
    .exp-stat-保留 {{ background-color: #e2e8f0; color: #334155; border-color: #cbd5e1; }}

    .exp-footer {{
        display: flex;
        justify-content: space-between;
        font-size: 8.5px;
        color: #94a3b8;
        border-top: 1px solid #f1f5f9;
        padding-top: 6px;
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
        <button class="tab-btn" onclick="switchMainTab('ikusei')">🌱 育成</button>
        <button class="tab-btn" onclick="switchMainTab('export')">🖼️ 出力・保存</button>
    </div>

    <!-- ポジション選択 -->
    <div id="posTabsContainer" class="pos-tabs">
        <button class="pos-btn active" onclick="switchPos('投手')">投手</button>
        <button class="pos-btn" onclick="switchPos('捕手')">捕手</button>
        <button class="pos-btn" onclick="switchPos('内野手')">内野手</button>
        <button class="pos-btn" onclick="switchPos('外野手')">外野手</button>
    </div>

    <!-- 選手カードグリッド（戦力整理用） -->
    <div class="grid" id="cardGrid"></div>

    <!-- 育成選手表示領域 -->
    <div id="ikuseiContainer" style="display:none;"></div>

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

    <!-- 画像出力エリア -->
    <div id="exportArea" style="display:none;">
        <div class="download-bar">
            <button class="download-btn" onclick="downloadImage()">
                📥 画像として保存 (PNG)
            </button>
        </div>
        <div class="export-container">
            <div id="captureArea">
                <div class="exp-top">
                    <div class="exp-sub-title">NPB戦力整理シミュレータ</div>
                    <div class="exp-team-badge">{team_code}</div>
                </div>
                <div class="exp-title-area">
                    <div class="exp-team-name">{selected_team}</div>
                    <div class="exp-year-text">2026年 戦力整理予想</div>
                </div>

                <div class="exp-summary-row">
                    <div class="exp-sum-item">
                        <div class="exp-sum-val" style="color:#dc2626;" id="expCntSenryoku">戦力外 0人</div>
                    </div>
                    <div class="exp-sum-item">
                        <div class="exp-sum-val" style="color:#2563eb;" id="expCntIkusei">育成移行 0人</div>
                    </div>
                    <div class="exp-sum-item">
                        <div class="exp-sum-val" style="color:#6b21a8;" id="expCntGendora">現役ドラフト 0人</div>
                    </div>
                    <div class="exp-sum-item">
                        <div class="exp-sum-val" style="color:#15803d;" id="expCntYoso">予想支配下 0人</div>
                    </div>
                </div>

                <div class="exp-legend-row">
                    <div class="exp-legends">
                        <div class="exp-leg-item"><div class="exp-leg-box" style="background:#f8fafc;"></div>残留</div>
                        <div class="exp-leg-item"><div class="exp-leg-box" style="background:#fecaca;"></div>戦力外</div>
                        <div class="exp-leg-item"><div class="exp-leg-box" style="background:#fde68a;"></div>引退</div>
                        <div class="exp-leg-item"><div class="exp-leg-box" style="background:#bfdbfe;"></div>育成移行</div>
                        <div class="exp-leg-item"><div class="exp-leg-box" style="background:#e9d5ff;"></div>現ドラ</div>
                        <div class="exp-leg-item"><div class="exp-leg-box" style="background:#e2e8f0;"></div>保留</div>
                    </div>
                    <div>※個人の予想です</div>
                </div>

                <div id="expGridContainer"></div>

                <div class="exp-footer">
                    <div>roster-npb.streamlit.app</div>
                    <div id="expFooterInfo">補強 +0人  70枠まであと0枠</div>
                </div>
            </div>
        </div>
    </div>

    <!-- 補強シミュレーション -->
    <div class="bottom-section">
        <b style="font-size:0.85rem; color:#334155;">📥 補強シミュレーション</b>
        <div class="input-grid" style="margin-top:4px;">
            <div class="input-box"><label>ドラフト支配下</label><input type="number" inputmode="numeric" id="inDraft" value="0" min="0" max="15" oninput="calcTotals()"></div>
            <div class="input-box"><label>FA・トレード</label><input type="number" inputmode="numeric" id="inFa" value="0" min="0" max="10" oninput="calcTotals()"></div>
            <div class="input-box"><label>新外国人</label><input type="number" inputmode="numeric" id="inForeign" value="0" min="0" max="10" oninput="calcTotals()"></div>
            <div class="input-box"><label>その他新加入</label><input type="number" inputmode="numeric" id="inOther" value="0" min="0" max="10" oninput="calcTotals()"></div>
        </div>

        <div class="result-banner">
            <div>
                <div style="font-size:0.75rem; color:#475569;">翌年予想支配下</div>
                <div style="font-size:1.1rem; font-weight:800; color:#0f172a;" id="nextYearTotal">0人</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.75rem; color:#475569;">70人まで</div>
                <div style="font-size:1.1rem; font-weight:800;" id="remainingSlots">あと 0 枠</div>
            </div>
        </div>
    </div>

    <!-- ポップアップメニュー -->
    <div class="popover-backdrop" id="popoverBackdrop" onclick="closePopover()"></div>
    <div class="popover-menu" id="popoverMenu">
        <div class="pop-header" id="popHeader">選手名</div>
        <div id="popBtnContainer"></div>
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
                (tab === 'ikusei' && i === 2) ||
                (tab === 'export' && i === 3)
            );
        }});
        document.getElementById('posTabsContainer').style.display = (tab === 'roster') ? 'flex' : 'none';
        document.getElementById('cardGrid').style.display = (tab === 'roster') ? 'grid' : 'none';
        document.getElementById('ikuseiContainer').style.display = (tab === 'ikusei') ? 'block' : 'none';
        document.getElementById('depthContainer').style.display = (tab === 'depth') ? 'block' : 'none';
        document.getElementById('exportArea').style.display = (tab === 'export') ? 'block' : 'none';
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
        const ikuContainer = document.getElementById('ikuseiContainer');
        grid.innerHTML = '';
        ikuContainer.innerHTML = '';

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
                const salaryDisp = p.salary !== '-' ? p.salary : '';
                card.innerHTML = `
                    <div class="c-name">#${{p.num}} ${{p.name}}${{badge}}</div>
                    <div class="c-sub"><span>${{p.age}}歳</span>${{salaryDisp ? `<span>/ ${{salaryDisp}}</span>` : ''}}</div>
                    <div class="c-stat">${{p.status}}</div>
                `;
                card.onclick = (e) => openPopover(e.currentTarget, p.no, `#${{p.num}} ${{p.name}} (${{p.age}}歳 / ${{p.salary}})`, false);
                grid.appendChild(card);
            }});
        }} else if (currentMainTab === 'ikusei') {{
            const positions = ['投手', '捕手', '内野手', '外野手'];
            let totalIkusei = 0;

            positions.forEach(pos => {{
                const posPlayers = allPlayers.filter(p => p.is_ikusei && p.pos === pos);
                if (posPlayers.length > 0) {{
                    totalIkusei += posPlayers.length;
                    const secTitle = document.createElement('div');
                    secTitle.className = 'ikusei-sec-title';
                    secTitle.innerText = `${{pos}} (${{posPlayers.length}}名)`;
                    ikuContainer.appendChild(secTitle);

                    const secGrid = document.createElement('div');
                    secGrid.className = 'grid';

                    posPlayers.forEach(p => {{
                        const card = document.createElement('div');
                        let statClass = 'stat-残留';
                        let statLabel = '育成残留';
                        if (p.promoted) {{
                            statClass = 'stat-支配下昇格';
                            statLabel = '支配下昇格';
                        }} else if (p.status === '戦力外') {{
                            statClass = 'stat-戦力外';
                            statLabel = '育成戦力外';
                        }}

                        card.className = `card ${{statClass}}`;
                        const salaryDisp = p.salary !== '-' ? p.salary : '';
                        card.innerHTML = `
                            <div class="c-name">#${{p.num}} ${{p.name}}</div>
                            <div class="c-sub"><span>${{p.age}}歳</span>${{salaryDisp ? `<span>/ ${{salaryDisp}}</span>` : ''}}</div>
                            <div class="c-stat">${{statLabel}}</div>
                        `;
                        card.onclick = (e) => openPopover(e.currentTarget, p.no, `#${{p.num}} ${{p.name}} (育成 / ${{p.salary}})`, true);
                        secGrid.appendChild(card);
                    }});
                    ikuContainer.appendChild(secGrid);
                }}
            }});

            if (totalIkusei === 0) {{
                ikuContainer.innerHTML = '<div style="font-size:0.8rem; color:#666; text-align:center; padding:20px;">育成登録選手はいません</div>';
            }}
        }} else if (currentMainTab === 'depth') {{
            renderDepthChart();
        }} else if (currentMainTab === 'export') {{
            renderExportCanvas();
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
                        <div class="depth-chip stat-${{p.status}}" onclick="openPopover(this, ${{p.no}}, '#${{p.num}} ${{p.name}} (${{p.age}}歳 / ${{p.salary}})', false)">
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

    function renderExportCanvas() {{
        const container = document.getElementById('expGridContainer');
        container.innerHTML = '';

        const activeShihai = allPlayers.filter(p => !p.is_ikusei || p.promoted);
        const positions = ['投手', '捕手', '内野手', '外野手'];

        positions.forEach(pos => {{
            const pList = activeShihai.filter(p => p.pos === pos);
            const totalCount = pList.length;
            const outCount = pList.filter(p => ['戦力外', '引退', '育成移行', '現ドラ'].includes(p.status)).length;

            const sec = document.createElement('div');
            sec.className = 'exp-pos-sec';
            sec.innerHTML = `<div class="exp-pos-header">${{pos}}：${{outCount}} / ${{totalCount}}人</div>`;

            const grid5 = document.createElement('div');
            grid5.className = 'exp-grid-5';

            pList.forEach(p => {{
                const cell = document.createElement('div');
                cell.className = `exp-cell exp-stat-${{p.status}}`;
                const badge = p.promoted ? '🌱' : '';
                cell.innerText = `${{p.name}}${{badge}}`;
                grid5.appendChild(cell);
            }});

            const remainder = pList.length % 5;
            if (remainder !== 0) {{
                for (let i = 0; i < 5 - remainder; i++) {{
                    const emptyCell = document.createElement('div');
                    emptyCell.className = 'exp-cell';
                    emptyCell.style.border = 'none';
                    emptyCell.style.background = 'transparent';
                    grid5.appendChild(emptyCell);
                }}
            }}

            sec.appendChild(grid5);
            container.appendChild(sec);
        }});
    }}

    function downloadImage() {{
        const target = document.getElementById('captureArea');
        html2canvas(target, {{
            scale: 2,
            useCORS: true,
            backgroundColor: '#ffffff'
        }}).then(canvas => {{
            const link = document.createElement('a');
            link.download = `{selected_team}_戦力整理予想2026.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
        }});
    }}

    function openPopover(targetEl, no, title, isIkuseiMode) {{
        selectedPlayerNo = no;
        document.getElementById('popHeader').innerText = title;

        const pop = document.getElementById('popoverMenu');
        const backdrop = document.getElementById('popoverBackdrop');
        const btnContainer = document.getElementById('popBtnContainer');

        if (isIkuseiMode) {{
            btnContainer.innerHTML = `
                <div class="pop-btn-stack">
                    <button class="pop-btn stat-支配下昇格" onclick="applyIkuseiStatus('支配下昇格')">🟢 支配下昇格</button>
                    <button class="pop-btn stat-残留" onclick="applyIkuseiStatus('残留')">⚪ 残留</button>
                    <button class="pop-btn stat-戦力外" onclick="applyIkuseiStatus('戦力外')">🔴 戦力外</button>
                </div>
            `;
        }} else {{
            btnContainer.innerHTML = `
                <div class="pop-btn-grid">
                    <button class="pop-btn stat-残留" onclick="applyStatus('残留')">残留</button>
                    <button class="pop-btn stat-戦力外" onclick="applyStatus('戦力外')">戦力外</button>
                    <button class="pop-btn stat-引退" onclick="applyStatus('引退')">引退</button>
                    <button class="pop-btn stat-現ドラ" onclick="applyStatus('現ドラ')">現役ドラ</button>
                    <button class="pop-btn stat-育成移行" onclick="applyStatus('育成移行')">育成落</button>
                    <button class="pop-btn stat-保留" onclick="applyStatus('保留')">保留</button>
                </div>
            `;
        }}

        const rect = targetEl.getBoundingClientRect();
        const popWidth = 176;
        const popHeight = isIkuseiMode ? 125 : 115;

        let left = rect.left + (rect.width / 2) - (popWidth / 2);
        const maxLeft = window.innerWidth - popWidth - 8;
        if (left < 8) left = 8;
        if (left > maxLeft) left = maxLeft;

        let top = rect.top - popHeight - 6;
        if (rect.top < popHeight + 10) {{
            top = rect.bottom + 6;
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

    function applyIkuseiStatus(action) {{
        closePopover();
        const p = allPlayers.find(x => x.no === selectedPlayerNo);
        if (p) {{
            if (action === '支配下昇格') {{
                p.promoted = true;
                p.status = '残留';
            }} else if (action === '戦力外') {{
                p.promoted = false;
                p.status = '戦力外';
            }} else {{
                p.promoted = false;
                p.status = '残留';
            }}
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

        const taidanTotal = counts['戦力外'] + counts['引退'];

        document.getElementById('cntShihai').innerText = `${{shihaiOrigin}}人`;
        document.getElementById('cntZanryu').innerText = `${{counts['残留']}}人`;
        document.getElementById('cntTaiDan').innerText = `${{taidanTotal}}人`;
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

        const expSenryoku = document.getElementById('expCntSenryoku');
        if (expSenryoku) {{
            expSenryoku.innerText = `戦力外 ${{counts['戦力外'] + counts['引退']}}人`;
            document.getElementById('expCntIkusei').innerText = `育成移行 ${{counts['育成移行']}}人`;
            document.getElementById('expCntGendora').innerText = `現役ドラフト ${{counts['現ドラ']}}人`;
            document.getElementById('expCntYoso').innerText = `予想支配下 ${{nextTotal}}人`;
            document.getElementById('expFooterInfo').innerText = `補強 +${{totalNew}}人  70枠まであと${{remaining >= 0 ? remaining : 0}}枠`;
        }}
    }}
</script>
</body>
</html>
"""

components.html(app_html, height=1450, scrolling=True)
