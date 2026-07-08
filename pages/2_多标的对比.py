"""多标的对比 —— 并排看几个标的的收益/回撤/夏普，价格归一化叠一起看谁跑得快。
这是 Streamlit 的第二个页面：把这个文件放在 pages/ 下，侧栏顶部会自动出现页面导航。
"""
import time
from pathlib import Path

import pandas as pd
import akshare as ak
import quantstats as qs
import streamlit as st

st.set_page_config(page_title="多标的对比", page_icon="📊", layout="wide")
st.title("📊 多标的对比")
st.caption("把几个标的放一起比：谁涨得多、谁跌得狠、谁的性价比（夏普）高。")

DATA = Path(__file__).resolve().parent.parent / "data"   # 页面在 pages/ 里，data 在上一层
DATA.mkdir(exist_ok=True)

PRESETS = {
    "沪深300ETF": ("510300", "etf"), "上证50ETF": ("510050", "etf"),
    "中证500ETF": ("510500", "etf"), "中证1000ETF": ("512100", "etf"),
    "创业板ETF": ("159915", "etf"), "科创50ETF": ("588000", "etf"),
    "红利ETF": ("510880", "etf"), "纳指ETF": ("513100", "etf"),
    "标普500ETF": ("513500", "etf"), "中概互联ETF": ("513050", "etf"),
    "黄金ETF": ("518880", "etf"), "恒生ETF": ("159920", "etf"),
    "贵州茅台": ("600519", "stock"), "宁德时代": ("300750", "stock"),
    "比亚迪": ("002594", "stock"), "招商银行": ("600036", "stock"),
    "五粮液": ("000858", "stock"), "中国平安": ("601318", "stock"),
}

picks = st.sidebar.multiselect("选要对比的标的（2~6 个最清楚）", list(PRESETS),
                               default=["沪深300ETF", "纳指ETF", "红利ETF"])
start = st.sidebar.text_input("起始日期 (YYYYMMDD)", "20190101")
end = st.sidebar.text_input("结束日期 (YYYYMMDD)", "20261231")
if st.sidebar.button("🔄 刷新最新数据"):
    st.cache_data.clear()
    st.rerun()


@st.cache_data(ttl=3600, show_spinner="拉取行情中…")
def load_close(symbol, kind, start, end):
    """只取收盘价；联网重试2次，失败回退本地缓存。"""
    full = DATA / f"{symbol}.csv"            # 主 app 存的完整行情
    cc = DATA / f"{symbol}.close.csv"        # 本页存的收盘价
    last_err = None
    for _ in range(2):
        try:
            if kind == "etf":
                df = ak.fund_etf_hist_em(symbol=symbol, period="daily",
                                         start_date=start, end_date=end, adjust="qfq")
            else:
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                        start_date=start, end_date=end, adjust="qfq")
            df = df.rename(columns={"日期": "Date", "收盘": "Close"})
            df["Date"] = pd.to_datetime(df["Date"])
            s = df.set_index("Date").sort_index()["Close"]
            s.to_frame("Close").to_csv(cc, encoding="utf-8-sig")
            return s
        except Exception as e:
            last_err = e
            time.sleep(1.5)
    if cc.exists():
        return pd.read_csv(cc, index_col="Date", parse_dates=True)["Close"]
    if full.exists():
        return pd.read_csv(full, index_col="Date", parse_dates=True)["Close"]
    raise last_err


if not picks:
    st.info("左边至少选一个标的。")
    st.stop()

closes, errs = {}, []
for name in picks:
    sym, kind = PRESETS[name]
    try:
        closes[name] = load_close(sym, kind, start, end)
    except Exception as e:
        errs.append(f"{name}：{e}")
for e in errs:
    st.warning(f"⚠️ 拉取失败 {e}")
if not closes:
    st.error("一个都没拉到，点侧栏 🔄 重试，或先只选『沪深300ETF』（有本地缓存）。")
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
        rows.append({
            "标的": name,
            "累计收益": f"{(1 + r).prod() - 1:.1%}",
            "年化收益": f"{qs.stats.cagr(r):.1%}",
            "年化波动": f"{qs.stats.volatility(r):.1%}",
            "最大回撤": f"{qs.stats.max_drawdown(r):.1%}",
            "夏普": f"{qs.stats.sharpe(r):.2f}",
            "索提诺": f"{qs.stats.sortino(r):.2f}",
        })
    except Exception as e:
        st.caption(f"{name} 指标计算跳过：{e}")
st.dataframe(pd.DataFrame(rows).set_index("标的"), use_container_width=True)
st.caption("怎么读：夏普/索提诺越高 = 性价比越好；最大回撤越小 = 越扛得住。"
           "收益高但回撤吓人的，不一定适合你。")
