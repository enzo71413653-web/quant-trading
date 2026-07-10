"""黄金专属研究页 —— 驱动逻辑和股票不同：核心看美元强弱(反向)、实际利率(反向)、避险情绪(正向)，
不是看盈利增长。这里是通用个股模板给不了的宏观驱动关系仪表盘。
"""
import sys
import pathlib
import datetime as dt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd
import quantstats as qs
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data import get_price, get_quote
from theme import inject_css
from indicators import sma
import western_news

st.set_page_config(page_title="黄金", page_icon="🥇", layout="wide")
inject_css()
st.title("🥇 黄金 · 贵金属研究")
st.caption("黄金不是靠盈利定价的资产——它对美元、实际利率、避险情绪的反应，比对'公司基本面'更直接。")

start = st.sidebar.date_input("起始", dt.date(2021, 1, 1)).strftime("%Y%m%d")
end = dt.date.today().strftime("%Y%m%d")
if st.sidebar.button("🔄 刷新数据"):
    st.cache_data.clear()
    st.rerun()

try:
    gold, src = get_price("GC=F", "us", start, end)
    dxy, _ = get_price("DX-Y.NYB", "us", start, end)
    tnx, _ = get_price("^TNX", "us", start, end)
    vix, _ = get_price("^VIX", "us", start, end)
    silver, _ = get_price("SI=F", "us", start, end)
    gdx, _ = get_price("GDX", "us", start, end)
except Exception as e:
    st.error(f"数据拉取失败：{e}")
    st.stop()

g_close = gold["Close"].dropna()
g_ret = g_close.pct_change().dropna()

# ---------- 体检（实时价格条：每30秒自动重跑，不用你点任何东西） ----------
st.subheader("🩺 黄金现价 · GC=F")


@st.fragment(run_every="10s")
def _live_gold_ticker():
    g, src2 = get_price("GC=F", "us", start, end)
    close = g["Close"].dropna()
    ret = close.pct_change().dropna()
    c1, c2, c3, c4 = st.columns(4)
    try:
        last, chg = get_quote("GC=F")
        c1.metric("最新价（近实时）", f"{last:.1f}", f"{chg:+.2%}", delta_color="inverse")
        quote_ok = True
    except Exception:
        c1.metric("最新价（日线收盘）", f"{close.iloc[-1]:.1f}", f"{ret.iloc[-1]:+.2%}", delta_color="inverse")
        quote_ok = False
    c2.metric("累计收益", f"{(1+ret).prod()-1:.1%}")
    c3.metric("最大回撤", f"{qs.stats.max_drawdown(ret):.1%}")
    c4.metric("夏普比率", f"{qs.stats.sharpe(ret):.2f}")
    src_tag = "🟢 近实时报价(约15分钟延迟)" if quote_ok else "⚠️ 报价接口不可用，回退日线收盘价"
    st.caption(f"{src_tag} · 每30秒自动检查一次 · 最后检查 {dt.datetime.now().strftime('%H:%M:%S')}")


_live_gold_ticker()

fig_k = go.Figure(go.Candlestick(x=gold.index, open=gold["Open"], high=gold["High"],
                                 low=gold["Low"], close=gold["Close"], name="黄金",
                                 increasing_line_color="#ffca28", decreasing_line_color="#78909c"))
fig_k.add_trace(go.Scatter(x=gold.index, y=sma(g_close,20), name="MA20", line=dict(width=1,color="#42a5f5")))
fig_k.add_trace(go.Scatter(x=gold.index, y=sma(g_close,60), name="MA60", line=dict(width=1,color="#ef5350")))
fig_k.update_layout(height=420, template="plotly_dark", xaxis_rangeslider_visible=False,
                    margin=dict(t=20,b=40), legend=dict(orientation="h", y=-0.15))
st.plotly_chart(fig_k, use_container_width=True, config={"scrollZoom": True})

st.divider()

# ---------- 宏观驱动仪表盘 ----------
st.subheader("🧭 宏观驱动仪表盘（黄金的真正定价逻辑）")


def rolling_corr(a, b, window=60):
    ra, rb = a.align(b, join="inner")
    return ra.pct_change().rolling(window).corr(rb.pct_change())


def dual_axis(name_a, series_a, name_b, series_b, color_a, color_b):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=series_a.index, y=series_a, name=name_a, line=dict(color=color_a)),
                 secondary_y=False)
    fig.add_trace(go.Scatter(x=series_b.index, y=series_b, name=name_b, line=dict(color=color_b)),
                 secondary_y=True)
    fig.update_layout(height=320, template="plotly_dark", margin=dict(t=20,b=30),
                      legend=dict(orientation="h", y=-0.2))
    return fig


t1, t2, t3 = st.columns(3)
corr_dxy = rolling_corr(g_close, dxy["Close"]).dropna()
corr_tnx = rolling_corr(g_close, tnx["Close"]).dropna()
corr_vix = rolling_corr(g_close, vix["Close"]).dropna()
t1.metric("金价 vs 美元指数 · 60日相关性", f"{corr_dxy.iloc[-1]:.2f}",
         help="理论上应为负：美元走强，黄金（以美元计价）通常承压。")
t2.metric("金价 vs 10Y美债收益率 · 60日相关性", f"{corr_tnx.iloc[-1]:.2f}",
         help="理论上应为负：黄金零息，利率越高，持有黄金的机会成本越大。")
t3.metric("金价 vs VIX恐慌指数 · 60日相关性", f"{corr_vix.iloc[-1]:.2f}",
         help="理论上应为正：市场恐慌时避险资金流入黄金。")

st.markdown("**金价 vs 美元指数（DXY）**")
st.plotly_chart(dual_axis("黄金", g_close, "美元指数DXY", dxy["Close"], "#ffca28", "#42a5f5"),
                use_container_width=True)
st.markdown("**金价 vs 10年期美债收益率**")
st.plotly_chart(dual_axis("黄金", g_close, "10Y收益率%", tnx["Close"], "#ffca28", "#ef5350"),
                use_container_width=True)

st.divider()

# ---------- 金银比 / 金矿股相对强弱 ----------
st.subheader("⚖️ 贵金属内部结构")
cc1, cc2 = st.columns(2)
with cc1:
    ratio = (g_close / silver["Close"]).dropna()
    pct = (ratio.iloc[-1] > ratio).mean()
    st.markdown(f"**金银比（Gold/Silver Ratio）：当前 {ratio.iloc[-1]:.1f}，历史分位 {pct:.0%}**")
    fig_r = go.Figure(go.Scatter(x=ratio.index, y=ratio, line=dict(color="#ffca28")))
    fig_r.update_layout(height=280, template="plotly_dark", margin=dict(t=10,b=20))
    st.plotly_chart(fig_r, use_container_width=True)
    st.caption("比值越高＝金相对银越贵；历史上金银比有均值回归倾向，但不保证一定回归。")
with cc2:
    gm, gl = gdx["Close"].align(g_close, join="inner")
    rel = (gm/gm.iloc[0]) / (gl/gl.iloc[0]) * 100
    st.markdown(f"**金矿股相对强弱（GDX ÷ 金价，归一至100）：当前 {rel.iloc[-1]:.0f}**")
    fig_gdx = go.Figure(go.Scatter(x=rel.index, y=rel, line=dict(color="#ab47bc")))
    fig_gdx.add_hline(y=100, line=dict(dash="dot", color="#666"))
    fig_gdx.update_layout(height=280, template="plotly_dark", margin=dict(t=10,b=20))
    st.plotly_chart(fig_gdx, use_container_width=True)
    st.caption(">100＝矿业股跑赢金价本身（杠杆化看多情绪强）；<100＝矿业股跑输，即便金价在涨，市场信心也可能不足。")

st.divider()

# ---------- 新闻 ----------
st.subheader("📰 黄金相关资讯")
n1, n2 = st.tabs(["🌐 Google News", "🟣 Yahoo Finance"])
with n1:
    try:
        gn = western_news.google_news("gold price central bank reserves", limit=15)
        for _, row in gn.iterrows():
            st.markdown(f"🕑 {row['时间'][:16]} · [{row['标题']}]({row['链接']}) · *{row['来源']}*")
    except Exception as e:
        st.caption(f"暂不可用：{e}")
with n2:
    try:
        yn = western_news.yf_news("GLD", limit=10)
        for _, row in yn.iterrows():
            with st.expander(f"🕑 {row['时间']} · {row['标题'][:70]}"):
                st.caption(f"来源：{row['来源']}")
                st.write(row["摘要"] or "（无摘要）")
    except Exception as e:
        st.caption(f"暂不可用：{e}")
