# --- スマホ強制3列化 CSS ---
st.markdown("""
<style>
/* 左右の余白を極小化 */
.block-container {
    padding: 4px 4px 40px 4px !important;
    max-width: 100% !important;
}

/* ヘッダー周り */
.main-title {
    font-size: 1.2rem !important;
    font-weight: bold !important;
    margin: 0 !important;
}
.sub-caption {
    font-size: 0.65rem !important;
    color: #666 !important;
    margin-bottom: 4px !important;
}

/* 上部メトリクス（人数表示）を強制的に3等分 */
div[data-testid="stMetric"] {
    background-color: #f8fafc;
    border-radius: 4px;
    padding: 2px 4px !important;
    border: 1px solid #e2e8f0;
}
div[data-testid="stMetricLabel"] p {
    font-size: 0.62rem !important;
    margin: 0 !important;
}
div[data-testid="stMetricValue"] div {
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    line-height: 1.1 !important;
}

/* ★★★ ここが最重要：スマホの画面幅でも絶対に横3列を維持する指定 ★★★ */
@media (max-width: 768px) {
    /* 水平コンテナの折り返しを強制解除 */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        justify-content: space-between !important;
        gap: 3px !important;
        width: 100% !important;
    }
    /* Streamlitが当てる「min-width: calc(100% - ...)」を完全に上書き */
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 32% !important;
        min-width: 0px !important;
        max-width: 32.5% !important;
        width: 32% !important;
        padding: 0 !important;
        margin: 0 !important;
    }
}

/* PC等の画面でも同様に32%を維持 */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    flex: 1 1 32% !important;
    min-width: 0px !important;
    max-width: 32.5% !important;
    width: 32% !important;
    padding: 0 !important;
}

/* ボタン（選手カード全体）のスタイル */
div[data-testid="stButton"] {
    width: 100% !important;
    margin: 2px 0 !important;
}
div[data-testid="stButton"] > button {
    width: 100% !important;
    min-height: 48px !important;
    height: auto !important;
    padding: 3px 2px !important;
    border-radius: 5px !important;
    border: 1px solid #cbd5e1 !important;
    line-height: 1.15 !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
}

/* ボタン内のテキスト折り返しとサイズ */
div[data-testid="stButton"] > button p {
    font-size: 0.72rem !important;
    white-space: normal !important;
    text-align: center !important;
    margin: 0 !important;
}
</style>
""", unsafe_allow_html=True)
