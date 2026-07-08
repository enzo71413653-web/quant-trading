"""03 · 回测：用 backtesting.py 跑一个"双均线交叉"策略，体会 想法→验证 的闭环。
ponytail: 双均线是教学玩具，不是能赚钱的策略。目的是学"怎么验证一个想法"，不是照着实盘。
用法：先跑 01，再 python scripts/03_backtest_sma.py
"""
from pathlib import Path
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

ROOT = Path(__file__).resolve().parent.parent
DATA, REP = ROOT / "data", ROOT / "reports"
REP.mkdir(exist_ok=True)
SYMBOL = "510300"

df = pd.read_csv(DATA / f"{SYMBOL}.csv", index_col="Date", parse_dates=True)
df = df[["Open", "High", "Low", "Close", "Volume"]]   # backtesting.py 要这几列


def SMA(series, n):
    return pd.Series(series).rolling(n).mean()


class SmaCross(Strategy):
    n1, n2 = 20, 60          # 短/长均线，自己改着玩
    def init(self):
        self.s1 = self.I(SMA, self.data.Close, self.n1)
        self.s2 = self.I(SMA, self.data.Close, self.n2)
    def next(self):
        if crossover(self.s1, self.s2):      # 短线上穿长线 → 买
            self.buy()
        elif crossover(self.s2, self.s1):    # 短线下穿长线 → 平
            self.position.close()


bt = Backtest(df, SmaCross, cash=100_000, commission=0.001)
stats = bt.run()
print(stats)
out = REP / f"{SYMBOL}_backtest.html"
bt.plot(filename=str(out), open_browser=False)
print(f"[OK] 回测图: {out}")
