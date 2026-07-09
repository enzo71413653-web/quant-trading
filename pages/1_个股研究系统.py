"""个股研究系统 —— 指标概览 / 对比研究 / 周期行研 / 新闻热点。
中/美/韩/日 皆可；联网实时拉取，失败回退本地缓存。富可视化用 Plotly（可缩放/悬浮/开关副图）。
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import datetime as dt

import pandas as pd
import quantstats as qs
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data import get_price, get_news
from universe import SECTORS, by_sector

st.set_page_config(page_title="个股研究系统", page_icon="🔬", layout="wide")
st.title("🔬 个股研究系统")

# ---------- 侧栏 ----------
st.sidebar.header("① 选公司")
sector = st.sidebar.selectbox("赛道", SECTORS)
members = by_sector(sector)
picked = st.sidebar.selectbox("公司", [m["name"] for m in members])
u = next(m for m in members if m["name"] == picked)
cust = st.sidebar.text_input("或自定义代码（覆盖上面）", "").strip()
cust_mkt = st.sidebar.selectbox("市场", ["us", "cn_stock", "cn_etf", "kr", "jp"])
if cust:
    u = {"name": cust, "symbol": cust, "market": cust_mkt, "sector": sector}

st.sidebar.header("② 时间范围")
d1 = st.sidebar.date_input("起始", dt.date(2019, 1, 1),
                           min_value=dt.date(2000, 1, 1), max_value=dt.date.today())
d2 = st.sidebar.date_input("结束", dt.date.today(),
                           min_value=dt.date(2000, 1, 1), max_value=dt.date.today())
start, end = d1.strftime("%Y%m%d"), d2.strftime("%Y%m%d")

st.sidebar.header("③ 技术指标参数")
n_short = st.sidebar.slider("短均线", 5, 60, 20)
n_long = st.sidebar.slider("长均线", 30, 250, 60)
rsi_n = st.sidebar.slider("RSI 周期", 6, 30, 14)

st.sidebar.header("④ 副图开关")
show_vol = st.sidebar.checkbox("成交量", True)
show_rsi = st.sidebar.checkbox("RSI", True)
show_macd = st.sidebar.checkbox("MACD", True)

if st.sidebar.button("🔄 刷新实时数据"):
    st.cache_data.clear()
    st.rerun()

symbol, market = u["symbol"], u["market"]
try:
    df, source = get_price(symbol, market, start, end)
except Exception as e:
    st.error(f"「{u['name']}」数据拉取失败：{e}（点侧栏 🔄 重试或换标的）")
    st.stop()
close = df["Close"].dropna()
returns = close.pct_change().dropna()


def _rsi(s, n):
    d = s.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean().replace(0, 1e-9)
    return 100 - 100 / (1 + up / dn)


def _macd(s, f=12, sl=26, sig=9):
    dif = s.ewm(span=f).mean() - s.ewm(span=sl).mean()
    dea = dif.ewm(span=sig).mean()
    return dif, dea, (dif - dea) * 2


st.subheader(f"{u['name']} · {symbol} · {market}")
if source == "cache":
    st.caption("⚠️ 联网失败，当前用本地缓存（非实时）。点侧栏 🔄 重试。")
else:
    st.caption(f"🟢 联网实时 · 最新 {close.index[-1].date()} 收盘 {close.iloc[-1]:.2f}")

tab1, tab2, tab3, tab4 = st.tabs(["📊 指标概览", "⚖️ 对比研究", "🔄 周期行研", "📰 新闻热点"])

# ---------- Tab1 指标概览 ----------
with tab1:
    day = returns.iloc[-1] if len(returns) else 0.0
    r1 = st.columns(4)
    r1[0].metric("最新价", f"{close.iloc[-1]:.2f}", f"{day:+.2%}", delta_color="inverse",
                 help="最新收盘价；下方为当日涨跌幅（红涨绿跌）")
    cum = (1 + returns).prod() - 1
    r1[1].metric("累计收益", f"{cum:+.1%}", f"{cum:+.1%}", delta_color="inverse",
                 help="区间内买入持有的总回报")
    mdd = qs.stats.max_drawdown(returns)
    r1[2].metric("最大回撤", f"{mdd:.1%}", f"{mdd:.1%}", delta_color="inverse",
                 help="从历史最高点回落的最大幅度；越接近 0 越抗跌。你能扛住这个跌幅吗？")
    r1[3].metric("夏普比率", f"{qs.stats.sharpe(returns):.2f}",
                 help="每单位总波动换来的超额收益；>1 较好，0.5 左右一般，<0 别碰")
    try:
        r2 = st.columns(4)
        cagr = qs.stats.cagr(returns)
        r2[0].metric("年化收益", f"{cagr:+.1%}", f"{cagr:+.1%}", delta_color="inverse",
                     help="几何年化收益率（CAGR）")
        r2[1].metric("年化波动", f"{qs.stats.volatility(returns):.1%}",
                     help="收益的年化标准差；越大越颠簸")
        r2[2].metric("索提诺", f"{qs.stats.sortino(returns):.2f}",
                     help="类似夏普，但只惩罚下跌波动，更贴近'亏钱'的痛感")
        r2[3].metric("卡玛", f"{qs.stats.calmar(returns):.2f}",
                     help="卡玛比率 = 年化收益率 / 最大回撤，衡量每单位回撤换来的收益")
        r3 = st.columns(4)
        hi52 = close.iloc[-252:].max() if len(close) >= 252 else close.max()
        m1 = (close.iloc[-1] / close.iloc[-21] - 1) if len(close) > 21 else 0.0
        r3[0].metric("当前 RSI", f"{_rsi(close, rsi_n).iloc[-1]:.0f}",
                     help=f"相对强弱指标（{rsi_n} 日）；>70 超买、<30 超卖")
        r3[1].metric("距52周高", f"{close.iloc[-1] / hi52 - 1:.1%}",
                     help="现价相对近一年最高价的距离")
        r3[2].metric("近1月", f"{m1:+.1%}", f"{m1:+.1%}", delta_color="inverse",
                     help="最近约 21 个交易日的涨跌")
        r3[3].metric("日胜率", f"{qs.stats.win_rate(returns):.1%}",
                     help="上涨交易日占比")
    except Exception:
        pass

    # 动态 Plotly：主图 + 可开关的副图
    rows = [("💹 K线 + 均线", 0.46)]
    if show_vol:
        rows.append(("成交量", 0.16))
    if show_rsi:
        rows.append((f"RSI({rsi_n})", 0.19))
    if show_macd:
        rows.append(("MACD", 0.19))
    tot = sum(h for _, h in rows)
    fig = make_subplots(rows=len(rows), cols=1, shared_xaxes=True,
                        row_heights=[h / tot for _, h in rows], vertical_spacing=0.045,
                        subplot_titles=[t for t, _ in rows])
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"],
                                 close=df["Close"], name="K线",
                                 increasing_line_color="#ef5350", decreasing_line_color="#26a69a"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=close.rolling(n_short).mean(), name=f"MA{n_short}",
                             line=dict(width=1, color="#f5c518")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=close.rolling(n_long).mean(), name=f"MA{n_long}",
                             line=dict(width=1, color="#42a5f5")), row=1, col=1)
    r = 1
    if show_vol:
        r += 1
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="成交量", marker_color="#888"), row=r, col=1)
    if show_rsi:
        r += 1
        fig.add_trace(go.Scatter(x=df.index, y=_rsi(close, rsi_n), name="RSI",
                                 line=dict(color="#ab47bc")), row=r, col=1)
        fig.add_hline(y=70, row=r, col=1, line=dict(dash="dot", color="#ef5350"))
        fig.add_hline(y=30, row=r, col=1, line=dict(dash="dot", color="#26a69a"))
    if show_macd:
        r += 1
        dif, dea, hist = _macd(close)
        fig.add_trace(go.Bar(x=df.index, y=hist, name="MACD柱",
                             marker_color=["#ef5350" if v >= 0 else "#26a69a" for v in hist]), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=dif, name="DIF", line=dict(color="#f5c518", width=1)), row=r, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=dea, name="DEA", line=dict(color="#42a5f5", width=1)), row=r, col=1)
    fig.update_layout(height=780, template="plotly_dark", hovermode="x unified",
                      xaxis_rangeslider_visible=False, margin=dict(t=40, b=60, l=10, r=10),
                      legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5))
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    with st.expander("📄 查看 / 下载历史数据（OHLCV）"):
        show = df.copy()
        show.index = show.index.date
        st.dataframe(show, use_container_width=True)
        st.download_button("⬇️ 下载 CSV", df.to_csv().encode("utf-8-sig"),
                           file_name=f"{symbol}_{start}_{end}.csv", mime="text/csv")
    with st.expander("📋 完整指标表（quantstats 全套几十个指标）"):
        try:
            st.dataframe(qs.reports.metrics(returns, mode="full", display=False), use_container_width=True)
        except Exception as ex:
            st.caption(f"完整指标表暂不可用：{ex}")

# ---------- Tab2 对比研究 ----------
with tab2:
    st.caption(f"与同赛道（{sector}）同行并排对比")
    closes = {}
    for p in by_sector(sector):
        try:
            pdf, _ = get_price(p["symbol"], p["market"], start, end)
            closes[p["name"]] = pdf["Close"]
        except Exception:
            pass
    if closes:
        price = pd.DataFrame(closes).dropna()
        if not price.empty:
            norm = price / price.iloc[0] * 100
            f2 = go.Figure()
            for cn in norm.columns:
                f2.add_trace(go.Scatter(x=norm.index, y=norm[cn], name=cn, mode="lines"))
            f2.update_layout(height=440, template="plotly_dark", hovermode="x unified",
                             title="归一净值（起点=100，看谁跑得快）", margin=dict(t=40, b=40),
                             legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(f2, use_container_width=True, config={"scrollZoom": True})
        rows = []
        for nm, s in closes.items():
            r = s.pct_change().dropna()
            try:
                rows.append({"标的": nm, "累计": f"{(1 + r).prod() - 1:.0%}",
                             "年化": f"{qs.stats.cagr(r):.0%}", "波动": f"{qs.stats.volatility(r):.0%}",
                             "最大回撤": f"{qs.stats.max_drawdown(r):.0%}", "夏普": f"{qs.stats.sharpe(r):.2f}"})
            except Exception:
                pass
        if rows:
            st.dataframe(pd.DataFrame(rows).set_index("标的"), use_container_width=True)
    else:
        st.info("同行数据未拉到，点侧栏 🔄 重试。")

# ---------- Tab3 周期行研 ----------
CYCLE = {
    "半导体": "硅周期叠加 AI 算力需求（GPU/HBM）；关注消费电子复苏、设备与材料国产替代（北方华创）、先进制程产能。费城半导体是全行业风向标。",
    "存储": "看 DRAM/NAND 现货价周期与库存去化；三星/海力士/美光的资本开支决定供给，下游手机/PC/服务器/AI 决定需求。价格拐点常领先股价。",
    "MLCC": "消费电子 + 汽车电子景气与库存周期主导；村田/三星电机等日韩龙头掌握定价；国产替代（风华/三环）看份额提升。",
    "CPO": "AI 数据中心资本开支是核心驱动；800G→1.6T 光模块迭代、北美云厂 capex、硅光渗透率决定弹性。",
    "科技大厂": "看盈利增长、AI 变现（云/广告/订阅）、估值(PE)与利率环境；七姐妹权重大，直接左右美股指数。",
    "指数": "宽基指数反映整体市场情绪与流动性；拿个股跟指数比，能看出它跑赢还是跑输大盘（超额收益 α）。",
}
with tab3:
    st.markdown("**长期价格（多年周期视角）**")
    st.line_chart(close)
    cc = st.columns(2)
    cc[0].markdown("**滚动 1 年收益**")
    cc[0].line_chart(close.pct_change(252).dropna())
    cc[1].markdown("**历史回撤（水下图）**")
    cc[1].area_chart(close / close.cummax() - 1)
    st.info(f"**「{sector}」周期驱动要点**\n\n{CYCLE.get(sector, '（待补充）')}")

# ---------- Tab4 新闻热点 ----------
with tab4:
    st.caption("多源快讯（东财 + 同花顺 + 新浪）按公司/赛道关键词过滤，联网实时。")
    news = get_news([u["name"].split()[0], sector], limit=40)
    if news.empty:
        st.info("暂无快讯，点侧栏 🔄 刷新。")
    else:
        for _, row in news.iterrows():
            with st.expander(f"🕑 {row['时间']} · {str(row['标题'])[:60]}"):
                st.write(row["摘要"] or "（无摘要）")
