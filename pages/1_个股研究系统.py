"""个股研究系统 —— 选一家公司，出【指标概览 / 对比研究 / 周期行研 / 新闻热点】四大模块。
中/美/韩/日 皆可；每次联网实时拉取，失败回退本地缓存。
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd
import quantstats as qs
import streamlit as st

from data import get_price, get_news
from universe import SECTORS, by_sector

st.set_page_config(page_title="个股研究系统", page_icon="🔬", layout="wide")
st.title("🔬 个股研究系统")

# ---------- 侧栏：选公司 ----------
st.sidebar.header("① 选公司")
sector = st.sidebar.selectbox("赛道", SECTORS)
members = by_sector(sector)
picked = st.sidebar.selectbox("公司", [m["name"] for m in members])
u = next(m for m in members if m["name"] == picked)

st.sidebar.caption("或自定义代码（覆盖上面）")
cust = st.sidebar.text_input("代码", "").strip()
cust_mkt = st.sidebar.selectbox("市场", ["us", "cn_stock", "cn_etf", "kr", "jp"])
if cust:
    u = {"name": cust, "symbol": cust, "market": cust_mkt, "sector": sector}

start = st.sidebar.text_input("起始 (YYYYMMDD)", "20190101")
end = st.sidebar.text_input("结束 (YYYYMMDD)", "20261231")
if st.sidebar.button("🔄 刷新实时数据"):
    st.cache_data.clear()
    st.rerun()

symbol, market = u["symbol"], u["market"]
try:
    df, source = get_price(symbol, market, start, end)
except Exception as e:
    st.error(f"「{u['name']}」数据拉取失败（重试后仍失败，无本地缓存）：{e}\n\n"
             "点侧栏 🔄 重试，或换一个标的。")
    st.stop()

close = df["Close"].dropna()
returns = close.pct_change().dropna()

st.subheader(f"{u['name']} · {symbol} · {market}")
if source == "cache":
    st.caption("⚠️ 联网失败，当前用**本地缓存**（非实时）。点侧栏 🔄 重试联网。")
else:
    st.caption(f"🟢 已联网实时拉取 · 最新 {close.index[-1].date()} 收盘 {close.iloc[-1]:.2f}")

tab1, tab2, tab3, tab4 = st.tabs(["📊 指标概览", "⚖️ 对比研究", "🔄 周期行研", "📰 新闻热点"])

# ---------- Tab1 指标概览 ----------
with tab1:
    chg = returns.iloc[-1] if len(returns) else 0.0
    a, b, c, d = st.columns(4)
    a.metric("最新价", f"{close.iloc[-1]:.2f}", f"{chg:.2%}")
    b.metric("累计收益", f"{(1 + returns).prod() - 1:.1%}")
    c.metric("最大回撤", f"{qs.stats.max_drawdown(returns):.1%}")
    d.metric("夏普", f"{qs.stats.sharpe(returns):.2f}")
    try:
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("年化收益", f"{qs.stats.cagr(returns):.1%}")
        e2.metric("年化波动", f"{qs.stats.volatility(returns):.1%}")
        e3.metric("索提诺", f"{qs.stats.sortino(returns):.2f}")
        e4.metric("卡玛", f"{qs.stats.calmar(returns):.2f}")
    except Exception:
        pass
    st.line_chart(pd.DataFrame({
        "Close": close,
        "MA20": close.rolling(20).mean(),
        "MA60": close.rolling(60).mean(),
    }))
    with st.expander("📋 完整指标表（quantstats 全套）"):
        try:
            st.dataframe(qs.reports.metrics(returns, mode="full", display=False),
                         use_container_width=True)
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
    if len(closes) >= 1:
        price = pd.DataFrame(closes).dropna()
        if not price.empty:
            st.markdown("**归一净值（起点=100，看谁跑得快）**")
            st.line_chart(price / price.iloc[0] * 100)
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
    "半导体": "硅周期叠加 AI 算力需求（GPU/HBM）；关注消费电子复苏、设备与材料国产替代（北方华创）、先进制程产能。费城半导体指数(^SOX)是全行业风向标。",
    "存储": "看 DRAM/NAND 现货价周期与库存去化；三星/海力士/美光的资本开支决定供给，下游手机/PC/服务器/AI 决定需求。价格拐点常领先股价。",
    "MLCC": "消费电子 + 汽车电子景气与库存周期主导；村田/三星电机等日韩龙头掌握定价；国产替代（风华/三环）看份额提升。",
    "CPO": "AI 数据中心资本开支是核心驱动；800G→1.6T 光模块迭代、北美云厂 capex、硅光渗透率决定弹性。",
    "科技大厂": "看盈利增长、AI 变现（云/广告/订阅）、估值(PE)与利率环境；七姐妹权重大，直接左右美股指数。",
    "指数": "宽基指数反映整体市场情绪与流动性；拿个股跟指数比，能看出它是跑赢还是跑输大盘（超额收益 α）。",
}
with tab3:
    st.markdown("**长期价格（多年周期视角）**")
    st.line_chart(close)
    cc1, cc2 = st.columns(2)
    cc1.markdown("**滚动 1 年收益**")
    cc1.line_chart(close.pct_change(252).dropna())
    cc2.markdown("**历史回撤（水下图）**")
    cc2.area_chart(close / close.cummax() - 1)
    st.info(f"**「{sector}」周期驱动要点**\n\n{CYCLE.get(sector, '（待补充）')}")

# ---------- Tab4 新闻热点 ----------
with tab4:
    st.caption("来自全球财经快讯，按公司/赛道关键词过滤（联网实时）。")
    kw = [u["name"].split()[0], sector]
    news = get_news(kw, limit=30)
    if news.empty:
        st.info("暂无匹配到该公司/赛道的快讯（快讯源约 200 条，可能没覆盖）。点侧栏 🔄 刷新或稍后再看。")
    else:
        for _, row in news.iterrows():
            with st.expander(f"🕑 {row['时间']} · {row['标题']}"):
                st.write(row["摘要"] or "（无摘要）")
