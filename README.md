# 量化学习系统（初学版）

一套"只为学习、不投真钱"的最小量化环境。定位：**A股 · 初学 · 先补认知 · 只回测/纸面**。

## 你要下载什么（3 类，全在 `requirements.txt`）
1. **数据**：`akshare` —— 免费拉 A股/ETF/基金，中文文档
2. **回测**：`backtesting` —— 极简，几十行跑通一个策略
3. **体检**：`quantstats` —— 收益/回撤/夏普，给你现有仓位做体检

（+ `pandas`/`numpy`/`matplotlib` 基础；可选 `jupyterlab` 边学边试）

> 刻意**不装** TA-Lib 这类要编译的重货——初学用不上，还容易卡在安装。

## 安装（建个隔离环境，别污染系统）
```powershell
cd "C:\Users\70476928\Desktop\Claude-Hub\04-代码项目\量化学习系统"
python3.14 -m venv .venv
.venv\Scripts\Activate.ps1        # PowerShell；cmd 用 .venv\Scripts\activate.bat
pip install -r requirements.txt
```
> 你的 Python 是 3.14（很新）。若某个包没有 3.14 轮子装报错，把 `quantstats` 换成 `quantstats-lumi`，或直接找我帮你处理兼容。

## 目录结构
```
量化学习系统/
├─ README.md            ← 本文件：学习体系总纲
├─ requirements.txt     ← 下载清单
├─ scripts/
│  ├─ 01_get_data.py           取数（akshare）
│  ├─ 02_portfolio_checkup.py  体检（quantstats）
│  └─ 03_backtest_sma.py       回测（backtesting.py 双均线）
├─ data/       ← 脚本自动生成，存行情
├─ reports/    ← 体检/回测的 HTML 报告
├─ strategies/ ← 以后你自己的策略
└─ notes/      ← 学习笔记（对着 quant-wiki / ML4T 记）
```

## 学习体系：三层

**第 1 层 · 认知（读，先别写代码）**
- [LLMQuant/quant-wiki](https://github.com/LLMQuant/quant-wiki)（中文知识库）通读一遍建框架
- [ML4T](https://github.com/stefan-jansen/machine-learning-for-trading) 挑 2–3 章看概念
- 目标：听得懂 收益率 / 波动 / 回撤 / 夏普 / 因子 这些词

**第 2 层 · 数据与工具（动手，不花钱）**
- `01_get_data.py`：用 [akshare](https://github.com/akfamily/akshare) 把你持有的标的历史拉下来
- `02_portfolio_checkup.py`：用 [quantstats](https://github.com/ranaroussi/quantstats) 出体检报告 ← 先搞清你现在"乱/亏"在哪
- 目标：能自己拿数据、能看懂一张绩效报告

**第 3 层 · 实践（回测，只在纸面）**
- `03_backtest_sma.py`：跑一个双均线策略，改参数看结果怎么变
- 把你自己的想法写进 `strategies/`，用 [backtesting.py](https://github.com/kernc/backtesting.py) 验证
- 目标：养成"任何想法先回测验证，再谈钱"的习惯

## 三步走（把上面串起来）
1. 装好环境 → 2. 跑 `01` 再跑 `02`，先给你现在的仓做体检 → 3. 跑 `03` 体会回测

## 进阶（基础稳了再上，别现在碰）
- [microsoft/qlib](https://github.com/microsoft/qlib)：AI 因子 / 机器学习选股
- [vnpy](https://github.com/vnpy/vnpy)：完整实盘平台（接券商/期货）——真要实盘前，先在纸上练很久
- [TradingAgents](https://github.com/TauricResearch/TradingAgents) / [Kronos](https://github.com/shiyu-coder/Kronos) / [FinRL](https://github.com/AI4Finance-Foundation/FinRL)：AI 智能体/大模型，当兴趣项目玩

## 一句话
工具是拿来学的。**回测赚钱 ≠ 实盘赚钱**；这套系统全程不投一分真钱，先把认知和习惯练出来。
