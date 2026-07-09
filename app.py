"""我的量化学习台（首页）—— 单标的：体检 + 双均线回测。多市场，默认美股。
纯学习 / 纸面回测，不涉及真实交易。回测赚钱 ≠ 实盘赚钱。
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import pandas as pd
import quantstats as qs
import streamlit as st
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from data import get_price

st.set_page_config(page_title="我的量化学习台", page_icon="📈", layout="wide")
st.title("📈 我的量化学习台")
st.caption("纯学习 / 纸面回测，不涉及真实交易。回测赚钱 ≠ 实盘赚钱。")

PRESETS = {
    "英伟达 NVDA": ("NVDA", "us"), "苹果 AAPL": ("AAPL", "us"), "微软 MSFT": ("MSFT", "us"),
    "台积电 TSM": ("TSM", "us"), "美光 MU": ("MU", "us"), "特斯拉 TSLA": ("TSLA", "us"),
    "标普500 SPY": ("SPY", "us"), "纳指100 QQQ": ("QQQ", "us"), "费城半导体 SOXX": ("SOXX", "us"),
    "三星电子(韩)": ("005930.KS", "kr"), "SK海力士(韩)": ("000660.KS", "kr"),
    "村田(日)": ("6981.T", "jp"),
}
st.sidebar.header("① 选标的")
choice = st.sidebar.selectbox("常用标的", list(PRESETS))
sym, mkt = PRESETS[choice]
cust = st.sidebar.text_input("或输代码（覆盖）", "").strip()
cust_mkt = st.sidebar.selectbox("市场", ["us", "kr", "jp", "cn_stock", "cn_etf"])
if cust:
    sym, mkt = cust, cust_mkt
start = st.sidebar.text_input("起始 (YYYYMMDD)", "20190101")
end = st.sidebar.text_input("结束 (YYYYMMDD)", "20261231")
st.sidebar.header("② 双均线")
n1 = st.sidebar.slider("短均线 n1", 5, 60, 20)
n2 = st.sidebar.slider("长均线 n2", 20, 200, 60)
if st.sidebar.button("🔄 刷新"):
    st.cache_data.clear()
    st.rerun()

try:
    df, source = get_price(sym, mkt, start, end)
except Exception as e:
    st.error(f"数据拉取失败：{e}（点侧栏 🔄 重试，或换标的）")
    st.stop()
close = df["Close"].dropna()
returns = close.pct_change().dropna()

st.subheader(f"🩺 体检 · {cust if cust else choice}")
a, b, c, d = st.columns(4)
a.metric("最新价", f"{close.iloc[-1]:.2f}")
b.metric("累计收益", f"{(1 + returns).prod() - 1:.1%}")
c.metric("最大回撤", f"{qs.stats.max_drawdown(returns):.1%}")
d.metric("夏普", f"{qs.stats.sharpe(returns):.2f}")
st.line_chart(df["Close"])

st.subheader(f"🔁 双均线回测 · n1={n1}, n2={n2}")
if n1 >= n2:
    st.warning("短均线要小于长均线（n1 < n2）。")
    st.stop()


def SMA(s, n):
    return pd.Series(s).rolling(n).mean()


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


try:
    bt = Backtest(df[["Open", "High", "Low", "Close", "Volume"]], SmaCross,
                  cash=100_000, commission=0.001)
    stats = bt.run(n1=n1, n2=n2)
    e, f, g, h = st.columns(4)
    e.metric("策略收益", f"{stats['Return [%]']:.1f}%")
    f.metric("买入持有", f"{stats['Buy & Hold Return [%]']:.1f}%")
    g.metric("策略夏普", f"{stats['Sharpe Ratio']:.2f}")
    h.metric("胜率", f"{stats['Win Rate [%]']:.0f}%")
    st.line_chart(stats["_equity_curve"]["Equity"])
    if stats["Return [%]"] < stats["Buy & Hold Return [%]"]:
        st.info("📉 这套参数跑输了'买入持有'——多数简单策略如此。拖滑块试试，体会'调参很容易骗自己'（过拟合）。")
    else:
        st.success("这套参数暂时跑赢买入持有 —— 别当圣杯，换标的/时段很可能翻车。")
except Exception as ex:
    st.warning(f"回测暂不可用：{ex}")
