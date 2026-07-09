"""共享交易日记数据层：SQLite本地文件。app.py（雷达扫描自动记信号）与 pages/3（手动记录）共用。"""
import sqlite3
import pathlib
import datetime as dt

DB = pathlib.Path(__file__).resolve().parent / "data" / "journal.db"
DB.parent.mkdir(exist_ok=True)


def conn():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, ticker TEXT, signal TEXT, action TEXT, note TEXT,
        source TEXT DEFAULT 'manual', created_at TEXT
    )""")
    try:
        c.execute("ALTER TABLE entries ADD COLUMN source TEXT DEFAULT 'manual'")
    except sqlite3.OperationalError:
        pass  # 列已存在（旧库升级）
    return c


def log_signals(rows):
    """自动记录雷达扫描到的信号。source='系统自动'，仅记录"检测到"，不代表任何执行动作。"""
    if not rows:
        return
    today = dt.date.today().isoformat()
    now = dt.datetime.now().isoformat()
    with conn() as c:
        for r in rows:
            c.execute("INSERT INTO entries (date,ticker,signal,action,note,source,created_at) "
                     "VALUES (?,?,?,?,?,?,?)",
                     (today, r["标的"], r["信号"], "系统检测（未执行）", "", "系统自动", now))
