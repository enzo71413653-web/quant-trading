"""我的量化学习台 —— Streamlit 交互版
运行：先激活环境，再 `streamlit run app.py`，浏览器会自动打开 localhost:8501。
左边选标的 / 拖滑块调均线，右边图表和指标实时变化。
"""
import time
from pathlib import Path

import pandas as pd
import akshare as ak
import quantstats as qs
import streamlit as st
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

st.set_page_config(page_title="我的量化学习台", page_icon="📈", layout="wide")
st.title("📈 我的量化学习台")
st.caption("纯学习 / 纸面回测，不涉及真实交易。回测赚钱 ≠ 实盘赚钱。")

DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(exist_ok=True)

# ---------------- 侧边栏：参数 ----------------
PRESETS = {
    "沪深300ETF (510300)": ("510300", "etf"),
    "中证500ETF (510500)": ("510500", "etf"),
    "创业板ETF (159915)": ("159915", "etf"),
    "纳指ETF (513100)": ("513100", "etf"),
    "贵州茅台 (600519)": ("600519", "stock"),
    "宁德时代 (300750)": ("300750", "stock"),
}
st.sidebar.header("① 选标的")
choice = st.sidebar.selectbox("常用标的", list(PRESETS))
symbol, kind = PRESETS[choice]
start = st.sidebar.text_input("起始日期 (YYYYMMDD)", "20190101")
end = st.sidebar.text_input("结束日期 (YYYYMMDD)", "20261231")

st.sidebar.header("② 调策略（双均线）")
n1 = st.sidebar.slider("短均线 n1", 5, 60, 20)
n2 = st.sidebar.slider("长均线 n2", 20, 200, 60)


@st.cache_data(ttl=3600, show_spinner="拉取行情中…")
def load(symbol, kind, start, end):
    """先联网拉取（重试2次），失败则回退本地缓存 CSV。"""
    csv = DATA / f"{symbol}.csv"
    last_err = None
    for _ in range(2):
        try:
            if kind == "etf":
                df = ak.fund_etf_hist_em(symbol=symbol, period="daily",
                                         start_date=start, end_date=end, adjust="qfq")
            else:
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                        start_date=start, end_date=end, adjust="qfq")
            df = df.rename(columns={"日期": "Date", "开盘": "Open", "收盘": "Close",
                                    "最高": "High", "最低": "Low", "成交量": "Volume"})
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()[["Open", "High", "Low", "Close", "Volume"]]
            df.to_csv(csv, encoding="utf-8-sig")   # 存本地，下次可兜底
            return df, "online"
        except Exception as e:
            last_err = e
            time.sleep(1.5)
    if csv.exists():   # 联网失败 → 用之前存下的本地数据
        return pd.read_csv(csv, index_col="Date", parse_dates=True), "cache"
    raise last_err


try:
    df, source = load(symbol, kind, start, end)
except Exception as e:
    st.error(f"数据拉取失败（重试后仍失败），且本地没有该标的缓存：\n\n{e}\n\n"
             "多半是数据源（东方财富）临时抽风。按键盘 R 或右上角菜单 Rerun 再试一次；"
             "或先选『沪深300ETF』——它已有本地缓存，一定能打开。")
    st.stop()
if df.empty:
    st.warning("这段时间没有数据，换个日期区间。")
    st.stop()
if source == "cache":
    st.caption("⚠️ 联网失败，当前用的是**本地缓存**数据（可能不是最新）。")

# ---------------- Part 1：体检 ----------------
st.subheader(f"🩺 体检 · {choice}")
returns = df["Close"].pct_change().dropna()
c1, c2, c3, c4 = st.columns(4)
c1.metric("累计收益", f"{(1 + returns).prod() - 1:.1%}")
c2.metric("年化波动", f"{qs.stats.volatility(returns):.1%}")
c3.metric("最大回撤", f"{qs.stats.max_drawdown(returns):.1%}")
c4.metric("夏普比率", f"{qs.stats.sharpe(returns):.2f}")

left, right = st.columns(2)
left.markdown("**价格走势（前复权）**")
left.line_chart(df["Close"])
right.markdown("**回撤 · 水下图（离前高多远）**")
right.area_chart(df["Close"] / df["Close"].cummax() - 1)

# ---------------- Part 2：回测 ----------------
st.subheader(f"🔁 双均线回测 · n1={n1}, n2={n2}")


def SMA(series, n):
    return pd.Series(series).rolling(n).mean()


class SmaCross(Strategy):
    n1, n2 = 20, 60

    def init(self):
        self.s1 = self.I(SMA, self.data.Close, self.n1)
        self.s2 = self.I(SMA, self.data.Close, self.n2)

    def next(self):
        if crossover(self.s1, self.s2):
            self.buy()
        elif crossover(self.s2, self.s1):
            self.position.close()


if n1 >= n2:
    st.warning("短均线要小于长均线（n1 < n2），才是'快线穿慢线'。")
    st.stop()

bt = Backtest(df, SmaCross, cash=100_000, commission=0.001)
stats = bt.run(n1=n1, n2=n2)

b1, b2, b3, b4 = st.columns(4)
b1.metric("策略收益", f"{stats['Return [%]']:.1f}%")
b2.metric("买入持有", f"{stats['Buy & Hold Return [%]']:.1f}%")
b3.metric("策略夏普", f"{stats['Sharpe Ratio']:.2f}")
b4.metric("胜率", f"{stats['Win Rate [%]']:.0f}%")

st.markdown("**价格 + 两条均线（看它们在哪交叉）**")
st.line_chart(pd.DataFrame({
    "Close": df["Close"],
    f"SMA{n1}": SMA(df["Close"], n1),
    f"SMA{n2}": SMA(df["Close"], n2),
}))

st.markdown("**策略权益曲线（10万本金滚到哪）**")
st.line_chart(stats["_equity_curve"]["Equity"])

if stats["Return [%]"] < stats["Buy & Hold Return [%]"]:
    st.info("📉 这套参数下策略跑输了'买入持有'——很正常，多数简单策略都这样。"
            "拖滑块换参数试试，体会'调参很容易骗自己'（这就是过拟合）。")
else:
    st.success("这套参数暂时跑赢买入持有 —— 但别急着当圣杯，换段时间或换标的很可能就翻车。")
