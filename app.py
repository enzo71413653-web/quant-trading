"""大盘雷达 + 策略回测与参数寻优沙盒。多市场，含摩擦成本、多空方向、买卖点标注、吊灯止损、ATR仓位计算。"""
import sys
import pathlib
import itertools
import datetime as dt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from data import get_price
from theme import inject_css
from indicators import sma, rsi, atr as atr_fn, chandelier_exit
from universe import UNIVERSE

st.set_page_config(page_title="策略回测沙盒", page_icon="📈", layout="wide")
inject_css()

# ============================================================
# 📡 大盘雷达（首页顶部：环境红绿灯 + 自选池信号扫描）
# ============================================================
st.title("📡 大盘雷达")


@st.cache_data(ttl=3600, show_spinner="读取大盘环境…")
def market_regime():
    e = dt.date.today().strftime("%Y%m%d")
    s100 = (dt.date.today() - dt.timedelta(days=100)).strftime("%Y%m%d")
    vix_df, _ = get_price("^VIX", "us", s100, e)
    spy_df, _ = get_price("SPY", "us", s100, e)
    vix_now = vix_df["Close"].iloc[-1]
    spy_close = spy_df["Close"]
    spy_now = spy_close.iloc[-1]
    spy_ma50 = spy_close.rolling(50).mean().iloc[-1]
    risk_off = bool(vix_now > 25 or spy_now < spy_ma50)
    return float(vix_now), float(spy_now), float(spy_ma50), risk_off


@st.cache_data(ttl=3600, show_spinner="扫描自选池信号中（约37个标的，首次约20-40秒）…")
def scan_universe():
    """一次遍历同时算：信号表 + 市场宽度（池内站上50日均线的占比）。避免重复拉取。"""
    end_d = dt.date.today()
    s = (end_d - dt.timedelta(days=300)).strftime("%Y%m%d")
    e = end_d.strftime("%Y%m%d")
    rows = []
    above_ma50 = total = 0
    for u in UNIVERSE:
        try:
            d, _ = get_price(u["symbol"], u["market"], s, e)
            close = d["Close"].dropna()
            if len(close) < 65:
                continue
            total += 1
            s1, s2 = sma(close, 20), sma(close, 60)
            ma50 = sma(close, 50).iloc[-1]
            if close.iloc[-1] > ma50:
                above_ma50 += 1
            golden, death = bool(crossover(s1, s2)), bool(crossover(s2, s1))
            r = rsi(close, 14).iloc[-1]
            chg = close.pct_change().iloc[-1]
            sig = []
            if golden:
                sig.append("🟢金叉")
            if death:
                sig.append("🔴死叉")
            if r >= 70:
                sig.append("⚠️RSI超买")
            if r <= 30:
                sig.append("⚠️RSI超卖")
            if sig:
                rows.append({"标的": u["name"], "赛道": u["sector"], "信号": " ".join(sig),
                            "RSI": round(float(r), 0), "涨跌": f"{chg:+.1%}"})
        except Exception:
            pass
    breadth = above_ma50 / total if total else None
    return pd.DataFrame(rows), breadth


try:
    vix_now, spy_now, spy_ma50, risk_off = market_regime()
    if risk_off:
        st.error(f"🔴 高波动/弱势环境 · VIX={vix_now:.1f} · SPY={spy_now:.0f}（50日均线{spy_ma50:.0f}）"
                 " —— 多头策略建议减仓或观望，仅供参考、非自动执行")
    else:
        st.success(f"🟢 环境正常 · VIX={vix_now:.1f} · SPY={spy_now:.0f}（50日均线{spy_ma50:.0f}）")
except Exception as e:
    st.caption(f"大盘环境读取失败：{e}")

if st.button("🔍 扫描自选池信号（金叉/死叉/RSI超买超卖 + 市场宽度）"):
    st.session_state["scan_res"], st.session_state["breadth"] = scan_universe()
if "scan_res" in st.session_state:
    breadth = st.session_state.get("breadth")
    if breadth is not None:
        st.markdown(f"**自选池内部温度计：{breadth:.0%} 站上各自的50日均线**")
        st.progress(breadth)
        if breadth < 0.35:
            st.caption("⚠️ 池内多数标的已跌破50日均线——即便大盘指数还撑着，内部也可能在走弱（顶背离）。")
    r = st.session_state["scan_res"]
    if r.empty:
        st.caption("今日自选池无触发信号。")
    else:
        st.dataframe(r, use_container_width=True, hide_index=True)
st.caption("扫描按需触发（非自动盘前推送）；结果缓存1小时。")

st.divider()

# ============================================================
# 📈 策略回测与参数寻优
# ============================================================
st.header("📈 策略回测与参数寻优")

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
mode = st.sidebar.radio("模式", ["净值曲线", "参数寻优热力图", "蒙特卡洛压力测试"])

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


class SmaCross(Strategy):
    n1, n2 = 20, 60
    direction = "both"

    def init(self):
        self.s1 = self.I(sma, self.data.Close, self.n1)
        self.s2 = self.I(sma, self.data.Close, self.n2)

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

    # ---- K线 + MA + 吊灯止损 + 买卖点标注（消除黑盒）----
    ce = chandelier_exit(data, 22, 3.0)
    fig_k = go.Figure()
    fig_k.add_trace(go.Candlestick(x=data.index, open=data["Open"], high=data["High"],
                                   low=data["Low"], close=data["Close"], name="K线",
                                   increasing_line_color="#ef5350", decreasing_line_color="#26a69a"))
    fig_k.add_trace(go.Scatter(x=data.index, y=sma(data["Close"], n1), name=f"MA{n1}",
                               line=dict(width=1, color="#f5c518")))
    fig_k.add_trace(go.Scatter(x=data.index, y=sma(data["Close"], n2), name=f"MA{n2}",
                               line=dict(width=1, color="#42a5f5")))
    fig_k.add_trace(go.Scatter(x=data.index, y=ce, name="吊灯止损(22,3×ATR)",
                               line=dict(width=1, color="#ff9800", dash="dot")))
    trades = stats["_trades"]
    if len(trades):
        win = trades["PnL"] > 0
        colors = ["#26a69a" if w else "#ef5350" for w in win]
        fig_k.add_trace(go.Scatter(x=trades["EntryTime"], y=trades["EntryPrice"], mode="markers",
                                   name="开仓", marker=dict(symbol="triangle-up", size=11,
                                   color=colors, line=dict(width=1, color="white"))))
        fig_k.add_trace(go.Scatter(x=trades["ExitTime"], y=trades["ExitPrice"], mode="markers",
                                   name="平仓", marker=dict(symbol="triangle-down", size=11,
                                   color=colors, line=dict(width=1, color="white"))))
    fig_k.update_layout(height=520, template="plotly_dark", hovermode="x unified",
                        xaxis_rangeslider_visible=False, margin=dict(t=20, b=40),
                        legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig_k, use_container_width=True, config={"scrollZoom": True})
    st.caption("三角朝上=开仓、朝下=平仓；绿=该笔盈利、红=该笔亏损。橙色虚线=吊灯止损，跌破视为趋势走坏。")

    eq = stats["_equity_curve"]["Equity"]
    bh = data["Close"] / data["Close"].iloc[0] * eq.iloc[0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bh.index, y=bh, name="基准买入持有", line=dict(color="#42a5f5")))
    fig.add_trace(go.Scatter(x=eq.index, y=eq, name=f"策略（{dir_label}）", line=dict(color="#26a69a")))
    fig.update_layout(height=360, template="plotly_dark", hovermode="x unified",
                      margin=dict(t=20, b=40), legend=dict(orientation="h", y=-0.15),
                      yaxis_title="净值")
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    # ---- ATR 仓位计算器 ----
    with st.expander("🧮 ATR 仓位计算器（买多少，而不是拍脑袋）", expanded=True):
        p1, p2, p3 = st.columns(3)
        account = p1.number_input("账户总资金", min_value=1000, value=100000, step=1000)
        risk_pct = p2.slider("单笔愿承担最大亏损（占总资金%）", 0.1, 5.0, 1.0, 0.1) / 100
        atr_mult = p3.slider("止损距离＝ATR × 倍数", 1.0, 5.0, 2.0, 0.5)
        atr_val = atr_fn(data, 14).iloc[-1]
        stop_dist = atr_val * atr_mult
        risk_amt = account * risk_pct
        shares = int(risk_amt / stop_dist) if stop_dist > 0 else 0
        pos_value = shares * data["Close"].iloc[-1]
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("ATR(14)", f"{atr_val:.2f}")
        q2.metric("止损距离", f"{stop_dist:.2f}")
        q3.metric("建议买入股数", f"{shares:,}")
        q4.metric("占用资金 / 占比", f"{pos_value:,.0f} / {pos_value/account:.1%}")
        st.caption("逻辑：亏到止损距离时，损失恰好等于你设定的'单笔愿承担最大亏损'。波动越大（ATR越高），建议仓位越小。")

        stop_price = data["Close"].iloc[-1] - stop_dist
        order_summary = (f'{{\n  "symbol": "{sym}",\n  "side": "BUY",\n  "qty": {shares},\n'
                         f'  "ref_price": {data["Close"].iloc[-1]:.2f},\n  "stop_loss": {stop_price:.2f}\n}}')
        st.caption("👇 订单摘要（仅供你手动核对后自行在券商下单，本系统不连接任何券商、不自动下单）")
        st.code(order_summary, language="json")

elif mode == "参数寻优热力图":
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

else:  # 蒙特卡洛压力测试
    st.caption("⚠️ 这不是预测未来价格。做法：把本策略【历史上真实发生过的每笔交易收益率】重新随机洗牌1000次，"
               "看同样这批交易换个先后顺序会得到多惨/多好的结果——用来量化'运气/顺序'对回测表现的影响。")
    n1 = st.sidebar.slider("短均线 n1", 5, 60, 20)
    n2 = st.sidebar.slider("长均线 n2", 20, 250, 60)
    n_sims = st.sidebar.slider("模拟次数", 200, 3000, 1000, 200)
    if n1 >= n2:
        st.warning("n1 必须小于 n2")
        st.stop()

    bt = Backtest(data, SmaCross, cash=100_000, commission=commission)
    stats = bt.run(n1=n1, n2=n2, direction=direction)
    trades = stats["_trades"]
    n_trades = len(trades)

    if n_trades < 5:
        st.warning(f"该参数组合只产生 {n_trades} 笔交易，样本太少，重新洗牌没有统计意义。换参数或拉长回测区间。")
    else:
        if n_trades < 15:
            st.caption(f"⚠️ 样本仅 {n_trades} 笔交易，bootstrap 结果的置信度有限，仅供粗略参考。")
        rets = trades["ReturnPct"].values
        rng = np.random.default_rng(42)
        paths = np.empty((n_sims, n_trades + 1))
        paths[:, 0] = 100_000.0
        for i in range(n_sims):
            sample = rng.choice(rets, size=n_trades, replace=True)
            paths[i, 1:] = 100_000.0 * np.cumprod(1 + sample)
        p5, p50, p95 = (np.percentile(paths, q, axis=0) for q in (5, 50, 95))
        running_max = np.maximum.accumulate(paths, axis=1)
        worst_dd = ((paths - running_max) / running_max).min(axis=1)

        x = list(range(n_trades + 1))
        fig_mc = go.Figure()
        fig_mc.add_trace(go.Scatter(x=x, y=p95, line=dict(width=0), showlegend=False))
        fig_mc.add_trace(go.Scatter(x=x, y=p5, fill="tonexty", fillcolor="rgba(66,165,245,0.2)",
                                    line=dict(width=0), name="5%~95% 区间"))
        fig_mc.add_trace(go.Scatter(x=x, y=p50, line=dict(color="#42a5f5", width=2), name="中位数路径"))
        fig_mc.update_layout(height=440, template="plotly_dark", margin=dict(t=20, b=40),
                             xaxis_title="第几笔交易之后", yaxis_title="模拟净值",
                             legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig_mc, use_container_width=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("原始回测收益", f"{stats['Return [%]']:.0f}%", help="固定这一种交易顺序的结果")
        c2.metric(f"{n_sims}次重排·中位数收益", f"{(p50[-1]/100_000-1)*100:.0f}%")
        c3.metric("最差5%情景·最终净值", f"{p5[-1]:,.0f}", help="1000次重排里最差的5%落在这以下")
        c4.metric("最差5%情景·回撤", f"{np.percentile(worst_dd,5):.1%}", help="比单次回测显示的最大回撤更接近'真实可能发生的最坏情况'")
        st.caption("如果'最差5%回撤'远比单次回测的最大回撤更吓人，说明这个策略的表现高度依赖交易顺序/运气，不够稳健。")
