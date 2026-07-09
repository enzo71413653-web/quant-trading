"""全局 UI 美化：隐藏 Streamlit 默认装饰、收紧边距、指标卡样式。三个页面共用。"""
import streamlit as st


def inject_css():
    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stToolbar"] {visibility: hidden;}
    .stAppDeployButton {display: none;}
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    section[data-testid="stSidebar"] {background-color: #12151c;}
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 12px 16px 8px 16px;
    }
    div[data-testid="stMetricLabel"] { opacity: 0.75; }
    </style>
    """, unsafe_allow_html=True)
