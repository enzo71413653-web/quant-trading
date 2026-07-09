"""共享技术指标：SMA / RSI / MACD / ATR / 吊灯止损(Chandelier Exit)。app.py 与各页面共用。"""
import pandas as pd


def sma(s, n):
    return pd.Series(s).rolling(n).mean()


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean().replace(0, 1e-9)
    return 100 - 100 / (1 + up / dn)


def macd(s, f=12, sl=26, sig=9):
    dif = s.ewm(span=f).mean() - s.ewm(span=sl).mean()
    dea = dif.ewm(span=sig).mean()
    return dif, dea, (dif - dea) * 2


def atr(df, n=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def chandelier_exit(df, n=22, mult=3.0):
    """吊灯止损（多头）：N日最高价 - mult×ATR。价格跌破此线，趋势判定走坏。"""
    highest = df["High"].rolling(n).max()
    return highest - atr(df, n) * mult
