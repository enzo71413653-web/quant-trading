"""多标的对比 —— 并排看几个标的的收益/回撤/夏普。用统一 data.py 适配器(新浪优先，更稳)。"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd
import quantstats as qs
import streamlit as st

from data import get_price

st.set_page_config(page_title="多标的对比", page_icon="📊", layout="wide")
st.title("📊 多标的对比")
st.caption("把几个标的放一起比：谁涨得多、谁跌得狠、谁的性价比（夏普）高。")

PRESETS = {
    "沪深300ETF": ("510300", "cn_etf"), "上证50ETF": ("510050", "cn_etf"),
    "中证500ETF": ("510500", "cn_etf"), "中证1000ETF": ("512100", "cn_etf"),
    "创业板ETF": ("159915", "cn_etf"), "科创50ETF": ("588000", "cn_etf"),
    "红利ETF": ("510880", "cn_etf"), "纳指ETF": ("513100", "cn_etf"),
    "标普500ETF": ("513500", "cn_etf"), "中概互联ETF": ("513050", "cn_etf"),
    "黄金ETF": ("518880", "cn_etf"), "恒生ETF": ("159920", "cn_etf"),
    "贵州茅台": ("600519", "cn_stock"), "宁德时代": ("300750", "cn_stock"),
    "比亚迪": ("002594", "cn_stock"), "招商银行": ("600036", "cn_stock"),
    "五粮液": ("000858", "cn_stock"), "中国平安": ("601318", "cn_stock"),
    "英伟达 NVDA": ("NVDA", "us"), "台积电 TSM": ("TSM", "us"), "苹果 AAPL": ("AAPL", "us"),
}

picks = st.sidebar.multiselect("选要对比的标的（2~6 个最清楚）", list(PRESETS),
                               default=["沪深300ETF", "纳指ETF", "红利ETF"])
start = st.sidebar.text_input("起始日期 (YYYYMMDD)", "20190101")
end = st.sidebar.text_input("结束日期 (YYYYMMDD)", "20261231")
if st.sidebar.button("🔄 刷新最新数据"):
    st.cache_data.clear()
    st.rerun()

if not picks:
    st.info("左边至少选一个标的。")
    st.stop()

closes, errs = {}, []
for name in picks:
    sym, mkt = PRESETS[name]
    try:
        df, _ = get_price(sym, mkt, start, end)
        closes[name] = df["Close"]
    except Exception as e:
        errs.append(f"{name}（{type(e).__name__}）")
for e in errs:
    st.warning(f"⚠️ 拉取失败 {e}，点侧栏 🔄 重试")
if not closes:
    st.error("一个都没拉到，点侧栏 🔄 重试。")
    st.stop()

price = pd.DataFrame(closes).dropna()
if price.empty:
    st.warning("这些标的没有公共的重叠时间段，缩短区间或换一批标的。")
    st.stop()

st.subheader("📈 净值对比（起点都归一到 100，看谁跑得快）")
st.line_chart(price / price.iloc[0] * 100)

st.subheader("💧 回撤对比（越靠下越惨）")
st.line_chart(price / price.cummax() - 1)

st.subheader("📋 关键指标对比")
rows = []
for name, s in closes.items():
    r = s.pct_change().dropna()
    try:
        rows.append({"标的": name, "累计收益": f"{(1 + r).prod() - 1:.1%}",
                     "年化收益": f"{qs.stats.cagr(r):.1%}", "年化波动": f"{qs.stats.volatility(r):.1%}",
                     "最大回撤": f"{qs.stats.max_drawdown(r):.1%}", "夏普": f"{qs.stats.sharpe(r):.2f}",
                     "索提诺": f"{qs.stats.sortino(r):.2f}"})
    except Exception:
        pass
st.dataframe(pd.DataFrame(rows).set_index("标的"), use_container_width=True)
st.caption("夏普/索提诺越高 = 性价比越好；最大回撤越小 = 越扛得住。")
