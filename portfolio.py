"""持仓组合数据层：本地SQLite记录你的真实持仓（标的/份额/成本价）。"""
import sqlite3
import pathlib

import pandas as pd

DB = pathlib.Path(__file__).resolve().parent / "data" / "portfolio.db"
DB.parent.mkdir(exist_ok=True)


def conn():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS holdings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, market TEXT, shares REAL, cost_basis REAL, note TEXT
    )""")
    return c


def add_holding(symbol, market, shares, cost_basis, note=""):
    with conn() as c:
        c.execute("INSERT INTO holdings (symbol,market,shares,cost_basis,note) VALUES (?,?,?,?,?)",
                 (symbol.strip().upper(), market, shares, cost_basis, note.strip()))


def list_holdings():
    with conn() as c:
        return pd.read_sql("SELECT * FROM holdings ORDER BY id", c)


def delete_holding(id_):
    with conn() as c:
        c.execute("DELETE FROM holdings WHERE id=?", (id_,))
