"""我的持仓 —— 真实持仓聚合视图：市值/权重/浮动盈亏 + 组合层面回撤/夏普 + 相关性矩阵。
本地SQLite存储，不连接任何券商，你自己录入真实数字。
"""
import sys
import pathlib
import datetime as dt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd
import quantstats as qs
import streamlit as st
import plotly.graph_objects as go

from data import get_price
from theme import inject_css
import portfolio as pf

st.set_page_config(page_title="我的持仓", page_icon="💼", layout="wide")
inject_css()
st.title("💼 我的持仓")
st.caption("录入你真实持有的标的，看聚合后的真实风险敞口——不是假设研究，是你自己的钱。")

with st.form("add_holding", clear_on_submit=True):
    c1, c2, c3, c4 = st.columns(4)
    symbol = c1.text_input("代码（如 NVDA / 600519 / 005930.KS）")
    market = c2.selectbox("市场", ["us", "cn_stock", "cn_etf", "kr", "jp"])
    shares = c3.number_input("持有份额（股）", min_value=0.0, value=0.0, step=1.0)
    cost = c4.number_input("平均成本价", min_value=0.0, value=0.0, step=0.01)
    note = st.text_input("备注（可选）")
    if st.form_submit_button("➕ 加入持仓"):
        if symbol.strip() and shares > 0:
            pf.add_holding(symbol, market, shares, cost, note)
            st.success(f"已加入 {symbol.upper()}")
        else:
            st.warning("代码和份额必填。")

holdings = pf.list_holdings()
st.divider()

if holdings.empty:
    st.info("还没有持仓记录，上面填一条开始。")
    st.stop()

if st.button("🗑️ 管理持仓（删除）"):
    st.session_state["show_del"] = True
if st.session_state.get("show_del"):
    for _, row in holdings.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.write(f"{row['symbol']} · {row['shares']}股 · 成本{row['cost_basis']}")
        if c2.button("删除", key=f"del{row['id']}"):
            pf.delete_holding(int(row["id"]))
            st.rerun()

# ---------- 拉取现价，聚合计算 ----------
today = dt.date.today().strftime("%Y%m%d")
start2y = (dt.date.today() - dt.timedelta(days=730)).strftime("%Y%m%d")
rows, closes = [], {}
for _, h in holdings.iterrows():
    try:
        d, _ = get_price(h["symbol"], h["market"], start2y, today)
        close = d["Close"].dropna()
        last = close.iloc[-1]
        mv = h["shares"] * last
        cost_total = h["shares"] * h["cost_basis"]
        pnl = mv - cost_total
        rows.append({"标的": h["symbol"], "份额": h["shares"], "现价": last, "市值": mv,
                    "成本": cost_total, "浮动盈亏": pnl,
                    "盈亏%": (pnl / cost_total * 100) if cost_total else 0.0})
        closes[h["symbol"]] = close
    except Exception as e:
        st.warning(f"{h['symbol']} 拉取失败：{e}")

if not rows:
    st.error("所有持仓都拉取失败，稍后重试。")
    st.stop()

df = pd.DataFrame(rows)
total_mv, total_cost = df["市值"].sum(), df["成本"].sum()
total_pnl = total_mv - total_cost

st.subheader("📊 组合概览")
c1, c2, c3, c4 = st.columns(4)
c1.metric("总市值", f"{total_mv:,.0f}")
c2.metric("总成本", f"{total_cost:,.0f}")
c3.metric("浮动盈亏", f"{total_pnl:,.0f}", f"{total_pnl/total_cost*100:+.1f}%" if total_cost else None,
         delta_color="inverse")
c4.metric("持仓数", f"{len(df)} 只")

df["权重"] = df["市值"] / total_mv
disp = df.copy()
for col in ["现价", "市值", "成本", "浮动盈亏"]:
    disp[col] = disp[col].round(2)
disp["盈亏%"] = disp["盈亏%"].round(1)
disp["权重"] = (disp["权重"] * 100).round(1)
st.dataframe(disp, use_container_width=True, hide_index=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("**持仓权重**")
    fig_pie = go.Figure(go.Pie(labels=df["标的"], values=df["市值"], hole=0.4))
    fig_pie.update_layout(height=360, template="plotly_dark", margin=dict(t=10, b=10))
    st.plotly_chart(fig_pie, use_container_width=True)

# ---------- 组合层面回撤/夏普（按市值加权真实日收益率）----------
ret_df = pd.DataFrame({k: v.pct_change() for k, v in closes.items()}).dropna()
if not ret_df.empty and len(ret_df.columns) == len(closes):
    weights = df.set_index("标的")["市值"] / total_mv
    weights = weights.reindex(ret_df.columns).fillna(0)
    port_ret = (ret_df * weights).sum(axis=1)

    with c2:
        st.markdown("**持仓相关性矩阵**")
        corr = ret_df.corr()
        fig_corr = go.Figure(go.Heatmap(z=corr.values, x=corr.columns, y=corr.columns,
                                        colorscale="RdBu_r", zmin=-1, zmax=1, zmid=0))
        fig_corr.update_layout(height=360, template="plotly_dark", margin=dict(t=10, b=10))
        st.plotly_chart(fig_corr, use_container_width=True)
        high_corr = [(a, b, corr.loc[a, b]) for a in corr.columns for b in corr.columns
                    if a < b and corr.loc[a, b] > 0.8]
        if high_corr:
            pairs = "，".join(f"{a}-{b}({v:.2f})" for a, b, v in high_corr)
            st.caption(f"⚠️ 相关性>0.8：{pairs} —— 看着是分散，实际risk高度集中。")

    st.subheader("📉 组合层面风险指标（按当前市值加权，非单只股票）")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("组合年化波动", f"{qs.stats.volatility(port_ret):.1%}")
    q2.metric("组合最大回撤", f"{qs.stats.max_drawdown(port_ret):.1%}")
    q3.metric("组合夏普", f"{qs.stats.sharpe(port_ret):.2f}")
    q4.metric("组合索提诺", f"{qs.stats.sortino(port_ret):.2f}")

    st.markdown("**组合水下回撤图**")
    dd = (1 + port_ret).cumprod()
    dd = dd / dd.cummax() - 1
    fig_dd = go.Figure(go.Scatter(x=dd.index, y=dd, fill="tozeroy", line=dict(color="#ef5350"),
                                  fillcolor="rgba(239,83,80,0.3)"))
    fig_dd.update_layout(height=260, template="plotly_dark", margin=dict(t=10, b=10), yaxis_tickformat=".0%")
    st.plotly_chart(fig_dd, use_container_width=True)
    st.caption("按现价权重回溯近2年计算，权重会随时间实际变化而漂移——这是近似值，不是精确的历史归因。")
else:
    st.caption("持仓不足2只或数据未对齐，暂不计算组合层面指标。")
