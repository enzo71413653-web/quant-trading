"""02 · 体检：用 quantstats 给一只标的/你的持仓算 收益、最大回撤、夏普，出 HTML 报告。
学习点：先看清风险（回撤/波动），再谈收益。正好用来体检你现在"乱/亏"的仓位。
用法：先跑 01 拿到 data/510300.csv，再 python scripts/02_portfolio_checkup.py
"""
from pathlib import Path
import pandas as pd
import quantstats as qs

ROOT = Path(__file__).resolve().parent.parent
DATA, REP = ROOT / "data", ROOT / "reports"
REP.mkdir(exist_ok=True)

SYMBOL = "510300"
px = pd.read_csv(DATA / f"{SYMBOL}.csv", index_col="Date", parse_dates=True)
returns = px["Close"].pct_change().dropna()      # 日收益率
returns.name = SYMBOL

# 命令行速览关键指标
print("累计收益: {:.1%}".format((1 + returns).prod() - 1))
print("年化波动: {:.1%}".format(qs.stats.volatility(returns)))
print("最大回撤: {:.1%}".format(qs.stats.max_drawdown(returns)))
print("夏普比率: {:.2f}".format(qs.stats.sharpe(returns)))

# 完整可视化报告
out = REP / f"{SYMBOL}_report.html"
qs.reports.html(returns, output=str(out), title=f"{SYMBOL} 体检报告")
print(f"[OK] 完整报告: {out}")
