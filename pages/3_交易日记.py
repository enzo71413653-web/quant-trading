"""交易日记 —— 记录你对系统信号的主观决策，积累后对比"系统原始信号 vs 你的实际选择"。
纯标准库 sqlite3，本地文件 data/journal.db，不依赖任何外部服务。
"""
import sys
import pathlib
import sqlite3
import datetime as dt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from theme import inject_css

st.set_page_config(page_title="交易日记", page_icon="📓", layout="wide")
inject_css()
st.title("📓 交易日记")
st.caption("记录你对系统信号的主观取舍。攒够数据后，才能诚实回答：你的主观判断是在帮你，还是在拖后腿。")

DB = pathlib.Path(__file__).resolve().parent.parent / "data" / "journal.db"
DB.parent.mkdir(exist_ok=True)


def _conn():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, ticker TEXT, signal TEXT, action TEXT, note TEXT, created_at TEXT
    )""")
    return c


with st.form("add_entry", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    date = c1.date_input("日期", dt.date.today())
    ticker = c2.text_input("标的（如 NVDA）")
    signal = c3.selectbox("触发信号", ["🟢金叉", "🔴死叉", "⚠️RSI超买", "⚠️RSI超卖", "无系统信号/纯主观", "其他"])
    action = st.radio("你的实际决策", ["严格执行", "跳过", "部分执行（减仓/延迟）"], horizontal=True)
    note = st.text_area("备注（为什么？例如：财报将近，主观放弃）", height=70)
    if st.form_submit_button("➕ 记录"):
        if ticker.strip():
            with _conn() as c:
                c.execute("INSERT INTO entries (date,ticker,signal,action,note,created_at) VALUES (?,?,?,?,?,?)",
                         (date.isoformat(), ticker.strip().upper(), signal, action, note.strip(),
                          dt.datetime.now().isoformat()))
            st.success("已记录。")
        else:
            st.warning("标的不能为空。")

with _conn() as c:
    df = pd.read_sql("SELECT date, ticker, signal, action, note FROM entries ORDER BY date DESC, id DESC", c)

st.divider()
if df.empty:
    st.info("还没有记录。日记攒够几十条之前，任何'系统 vs 主观'的对比结论都没有统计意义——先老老实实记。")
else:
    n = len(df)
    skipped = (df["action"] == "跳过").sum()
    executed = (df["action"] == "严格执行").sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("累计记录", f"{n} 条")
    c2.metric("严格执行", f"{executed} 条（{executed/n:.0%}）")
    c3.metric("主观跳过", f"{skipped} 条（{skipped/n:.0%}）")
    if n < 20:
        st.caption(f"⚠️ 样本仅 {n} 条，'系统 vs 主观哪个更赚'这类归因分析现在做没有意义，继续记，攒到至少几十条再看。")
    st.dataframe(df, use_container_width=True, hide_index=True)
