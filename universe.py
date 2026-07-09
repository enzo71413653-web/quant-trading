"""标的池：中/美/韩/日 科技供应链代表企业 + 指数，按赛道(sector)分组。
market ∈ {cn_stock, cn_etf, us, kr, jp}；us/kr/jp 的 symbol 直接用 yfinance 代码。
"""
UNIVERSE = [
    # 半导体（美股在前，云上默认可用）
    {"name": "英伟达 NVDA", "symbol": "NVDA", "market": "us", "sector": "半导体"},
    {"name": "AMD", "symbol": "AMD", "market": "us", "sector": "半导体"},
    {"name": "台积电 TSM", "symbol": "TSM", "market": "us", "sector": "半导体"},
    {"name": "博通 AVGO", "symbol": "AVGO", "market": "us", "sector": "半导体"},
    {"name": "应用材料 AMAT", "symbol": "AMAT", "market": "us", "sector": "半导体"},
    {"name": "英特尔 INTC", "symbol": "INTC", "market": "us", "sector": "半导体"},
    {"name": "ASML", "symbol": "ASML", "market": "us", "sector": "半导体"},
    {"name": "费城半导体 SOXX", "symbol": "SOXX", "market": "us", "sector": "半导体"},
    {"name": "中芯国际", "symbol": "688981", "market": "cn_stock", "sector": "半导体"},
    {"name": "北方华创", "symbol": "002371", "market": "cn_stock", "sector": "半导体"},
    {"name": "韦尔股份", "symbol": "603501", "market": "cn_stock", "sector": "半导体"},
    # 存储
    {"name": "美光 MU", "symbol": "MU", "market": "us", "sector": "存储"},
    {"name": "闪迪 SNDK", "symbol": "SNDK", "market": "us", "sector": "存储"},
    {"name": "三星电子", "symbol": "005930.KS", "market": "kr", "sector": "存储"},
    {"name": "SK海力士", "symbol": "000660.KS", "market": "kr", "sector": "存储"},
    {"name": "兆易创新", "symbol": "603986", "market": "cn_stock", "sector": "存储"},
    {"name": "江波龙", "symbol": "301308", "market": "cn_stock", "sector": "存储"},
    # MLCC
    {"name": "村田 6981", "symbol": "6981.T", "market": "jp", "sector": "MLCC"},
    {"name": "三星电机", "symbol": "009150.KS", "market": "kr", "sector": "MLCC"},
    {"name": "风华高科", "symbol": "000636", "market": "cn_stock", "sector": "MLCC"},
    {"name": "三环集团", "symbol": "300408", "market": "cn_stock", "sector": "MLCC"},
    # CPO / 光模块
    {"name": "中际旭创", "symbol": "300308", "market": "cn_stock", "sector": "CPO"},
    {"name": "新易盛", "symbol": "300502", "market": "cn_stock", "sector": "CPO"},
    {"name": "天孚通信", "symbol": "300394", "market": "cn_stock", "sector": "CPO"},
    {"name": "Coherent COHR", "symbol": "COHR", "market": "us", "sector": "CPO"},
    {"name": "Lumentum LITE", "symbol": "LITE", "market": "us", "sector": "CPO"},
    # 科技大厂（含美股七姐妹）
    {"name": "微软 MSFT", "symbol": "MSFT", "market": "us", "sector": "科技大厂"},
    {"name": "苹果 AAPL", "symbol": "AAPL", "market": "us", "sector": "科技大厂"},
    {"name": "谷歌 GOOGL", "symbol": "GOOGL", "market": "us", "sector": "科技大厂"},
    {"name": "亚马逊 AMZN", "symbol": "AMZN", "market": "us", "sector": "科技大厂"},
    {"name": "Meta", "symbol": "META", "market": "us", "sector": "科技大厂"},
    {"name": "特斯拉 TSLA", "symbol": "TSLA", "market": "us", "sector": "科技大厂"},
    {"name": "Palantir PLTR", "symbol": "PLTR", "market": "us", "sector": "科技大厂"},
    {"name": "甲骨文 ORCL", "symbol": "ORCL", "market": "us", "sector": "科技大厂"},
    {"name": "IBM", "symbol": "IBM", "market": "us", "sector": "科技大厂"},
    # 指数
    {"name": "标普500 SPY", "symbol": "SPY", "market": "us", "sector": "指数"},
    {"name": "纳指100 QQQ", "symbol": "QQQ", "market": "us", "sector": "指数"},
    # 贵金属
    {"name": "黄金期货 GC=F", "symbol": "GC=F", "market": "us", "sector": "贵金属"},
    {"name": "黄金ETF GLD", "symbol": "GLD", "market": "us", "sector": "贵金属"},
    {"name": "白银期货 SI=F", "symbol": "SI=F", "market": "us", "sector": "贵金属"},
    {"name": "金矿股ETF GDX", "symbol": "GDX", "market": "us", "sector": "贵金属"},
    {"name": "黄金ETF(A股) 518880", "symbol": "518880", "market": "cn_etf", "sector": "贵金属"},
]

SECTORS = ["半导体", "存储", "MLCC", "CPO", "科技大厂", "指数", "贵金属"]


def by_sector(sector):
    return [u for u in UNIVERSE if u["sector"] == sector]


def find(symbol):
    return next((u for u in UNIVERSE if u["symbol"] == symbol), None)
