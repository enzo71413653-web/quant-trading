"""策略回测与参数寻优沙盒。多市场，含摩擦成本、多空方向、网格寻优热力图。"""
import sys
import pathlib
import itertools

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import datetime as dt

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from data import get_price
from theme import inject_css

st.set_page_config(page_title="策略回测沙盒", page_icon="📈", layout="wide")
inject_css()
st.title("📈 策略回测与参数寻优沙盒")

PRESETS = {
    "英伟达 NVDA": ("NVDA", "us"), "苹果 AAPL": ("AAPL", "us"), "微软 MSFT": ("MSFT", "us"),
    "台积电 TSM": ("TSM", "us"), "美光 MU": ("MU", "us"), "特斯拉 TSLA": ("TSLA", "us"),
    "标普500 SPY": ("SPY", "us"), "纳指100 QQQ": ("QQQ", "us"), "费城半导体 SOXX": ("SOXX", "us"),
    "三星电子(韩)": ("005930.KS", "kr"), "SK海力士(韩)": ("000660.KS", "kr"),
    "村田(日)": ("6981.T", "jp"),
}
st.sidebar.header("① 标的 / 区间")
choice = st.sidebar.selectbox("常用标的", list(PRESETS))
sym, mkt = PRESETS[choice]
cust = st.sidebar.text_input("或输代码（覆盖）", "").strip()
cust_mkt = st.sidebar.selectbox("市场", ["us", "kr", "jp", "cn_stock", "cn_etf"])
if cust:
    sym, mkt = cust, cust_mkt
d1 = st.sidebar.date_input("起始", dt.date(2019, 1, 1), min_value=dt.date(2000, 1, 1), max_value=dt.date.today())
d2 = st.sidebar.date_input("结束", dt.date.today(), min_value=dt.date(2000, 1, 1), max_value=dt.date.today())
start, end = d1.strftime("%Y%m%d"), d2.strftime("%Y%m%d")

st.sidebar.header("② 摩擦成本")
fee = st.sidebar.slider("手续费率", 0.0, 0.005, 0.0010, 0.0001, format="%.4f")
slip = st.sidebar.slider("滑点比例", 0.0, 0.005, 0.0004, 0.0001, format="%.4f")
commission = fee + slip

st.sidebar.header("③ 持仓方向")
dir_label = st.sidebar.radio("方向", ["仅做多", "仅做空", "多空双向"], horizontal=False)
direction = {"仅做多": "long", "仅做空": "short", "多空双向": "both"}[dir_label]

st.sidebar.header("④ 展示模式")
mode = st.sidebar.radio("模式", ["净值曲线", "参数寻优热力图"])

if st.sidebar.button("🔄 刷新数据"):
    st.cache_data.clear()
    st.rerun()

try:
    df, source = get_price(sym, mkt, start, end)
except Exception as e:
    st.error(f"数据拉取失败：{e}")
    st.stop()
data = df[["Open", "High", "Low", "Close", "Volume"]]
if source == "cache":
    st.caption("⚠️ 用本地缓存（非实时）")


def SMA(s, n):
    return pd.Series(s).rolling(n).mean()


class SmaCross(Strategy):
    n1, n2 = 20, 60
    direction = "both"

    def init(self):
        self.s1 = self.I(SMA, self.data.Close, self.n1)
        self.s2 = self.I(SMA, self.data.Close, self.n2)

    def next(self):
        if crossover(self.s1, self.s2):
            if self.position.is_short:
                self.position.close()
            if self.direction in ("long", "both"):
                self.buy()
        elif crossover(self.s2, self.s1):
            if self.position.is_long:
                self.position.close()
            if self.direction in ("short", "both"):
                self.sell()


st.caption(f"{choice if not cust else sym} · {sym} · 手续费+滑点={commission:.2%} · {dir_label}")

if mode == "净值曲线":
    n1 = st.sidebar.slider("短均线 n1", 5, 60, 20)
    n2 = st.sidebar.slider("长均线 n2", 20, 250, 60)
    if n1 >= n2:
        st.warning("n1 必须小于 n2")
        st.stop()
    bt = Backtest(data, SmaCross, cash=100_000, commission=commission)
    stats = bt.run(n1=n1, n2=n2, direction=direction)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("累计收益率", f"{stats['Return [%]']:.1f}%")
    c2.metric("最大回撤", f"{stats['Max. Drawdown [%]']:.1f}%")
    c3.metric("夏普比率", f"{stats['Sharpe Ratio']:.2f}")
    n_trades = int(stats["# Trades"])
    win_rate = stats["Win Rate [%]"] if n_trades else 0.0
    c4.metric("交易胜率 / 总次数", f"{win_rate:.1f}% / {n_trades}次")
    c5.metric("基准买入持有", f"{stats['Buy & Hold Return [%]']:.1f}%")

    eq = stats["_equity_curve"]["Equity"]
    bh = data["Close"] / data["Close"].iloc[0] * eq.iloc[0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bh.index, y=bh, name="基准买入持有", line=dict(color="#42a5f5")))
    fig.add_trace(go.Scatter(x=eq.index, y=eq, name=f"策略（{dir_label}）", line=dict(color="#26a69a")))
    fig.update_layout(height=460, template="plotly_dark", hovermode="x unified",
                      margin=dict(t=20, b=40), legend=dict(orientation="h", y=-0.15),
                      yaxis_title="净值")
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

else:
    st.sidebar.header("⑤ 网格范围")
    n1_lo, n1_hi = st.sidebar.slider("短均线范围", 5, 60, (5, 30))
    n2_lo, n2_hi = st.sidebar.slider("长均线范围", 20, 250, (30, 120))
    run = st.sidebar.button("▶ 运行网格寻优", type="primary")

    @st.cache_data(ttl=1800, show_spinner="网格寻优运行中（数十组合，约需十余秒）…")
    def grid_search(sym, mkt, start, end, commission, direction, n1_lo, n1_hi, n2_lo, n2_hi):
        d, _ = get_price(sym, mkt, start, end)
        dd = d[["Open", "High", "Low", "Close", "Volume"]]
        rows = []
        for n1, n2 in itertools.product(range(n1_lo, n1_hi + 1, 2), range(n2_lo, n2_hi + 1, 5)):
            if n1 >= n2:
                continue
            try:
                bt = Backtest(dd, SmaCross, cash=100_000, commission=commission)
                s = bt.run(n1=n1, n2=n2, direction=direction)
                rows.append({"n1": n1, "n2": n2, "sharpe": s["Sharpe Ratio"], "return": s["Return [%]"]})
            except Exception:
                pass
        return pd.DataFrame(rows)

    if run or "grid_res" in st.session_state:
        if run:
            st.session_state["grid_res"] = grid_search(sym, mkt, start, end, commission, direction,
                                                        n1_lo, n1_hi, n2_lo, n2_hi)
        res = st.session_state.get("grid_res")
        if res is None or res.empty:
            st.warning("无有效组合（检查 n1<n2 范围）")
        else:
            piv = res.pivot(index="n2", columns="n1", values="sharpe")
            best = res.loc[res["sharpe"].idxmax()]
            fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index,
                                       colorscale="RdYlGn", colorbar=dict(title="夏普")))
            fig.add_trace(go.Scatter(x=[best.n1], y=[best.n2], mode="markers+text",
                                     marker=dict(symbol="x", size=14, color="white"),
                                     text=["最优"], textposition="top center", showlegend=False))
            fig.update_layout(height=560, template="plotly_dark", margin=dict(t=20, b=20),
                              xaxis_title="短均线 n1", yaxis_title="长均线 n2")
            st.plotly_chart(fig, use_container_width=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("最优组合", f"n1={int(best.n1)}, n2={int(best.n2)}")
            c2.metric("最优夏普", f"{best.sharpe:.2f}")
            c3.metric("对应收益", f"{best['return']:.0f}%")
            st.caption("找一片颜色均匀的高原，而不是孤立的一个深色尖峰——尖峰多半是过拟合。")
    else:
        st.info("设好范围后点「▶ 运行网格寻优」（首次约10-20秒，之后同参数走缓存秒开）。")
