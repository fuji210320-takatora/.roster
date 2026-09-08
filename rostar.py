import streamlit as st
import pandas as pd
import re

# ★ここを centered に変更！
st.set_page_config(
    page_title="NPB ROSTER LAB",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 余計な横幅を発生させないスリムCSS ---
st.markdown("""
<style>
/* スマホの画面幅（100vw）にピタッと収め、横スクロールを完全に防ぐ */
.block-container {
    max-width: 100% !important;
    padding-left: 6px !important;
    padding-right: 6px !important;
    padding-top: 10px !important;
}

/* 3列カラムの余白を詰める */
div[data-testid="stHorizontalBlock"] {
    gap: 4px !important;
}
div[data-testid="column"] {
    min-width: 0 !important;
}

/* ボタンをカード化（タップで状態切り替え） */
div[data-testid="stButton"] > button {
    width: 100% !important;
    min-height: 44px !important;
    padding: 2px 2px !important;
    border-radius: 6px !important;
}
div[data-testid="stButton"] > button p {
    font-size: 0.70rem !important;
    white-space: pre-line !important;
    line-height: 1.15 !important;
    margin: 0 !important;
}
</style>
""", unsafe_allow_html=True)
