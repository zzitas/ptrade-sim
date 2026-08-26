# PTrade 本地模拟环境

在本地以与 PTrade 一致的事件模型运行策略,无需券商客户端:

- 事件:`initialize` / `before_trading_start` / `handle_data` / `after_trading_end`,以及 `run_daily` / `run_interval` 调度
- API 兼容层:`order` / `order_target` / `order_target_value` / `get_snapshot` / `get_history` / `get_trade_days(start_date, end_date, count)` / `get_stock_positions` / `get_cash` / `get_portfolio` / `set_commission` 等
- 模拟撮合:市价即时成交、T+1 冻结交收、佣金/最低佣金/印花税、资金与持仓管理

## 数据源:真实历史行情(与 PTrade 回测对齐)

`ptrade_sim/redata.py` 提供真实日线数据源(腾讯行情主源 + 东财备用,自动落盘缓存到
`ptrade_sim/data_cache/*.csv`,增量更新,带重试):

- **前复权价格**(与 `get_history(fq='pre')` 一致)
- **真实 A 股交易日历**(由参考 ETF 实际交易日生成,含法定节假日)
- **撮合语义与 PTrade 日线回测一致**:按当日收盘价成交、委托量不超过当根 bar 成交量的 25%、停牌日拒单
- 任意 ETF/指数代码自动按需下载(策略池 114+ 只首次约 1 分钟,之后走缓存)

GUI 顶部"数据源"选择 `真实历史数据(前复权)` 即为真实回测;命令行:

```python
from ptrade_sim import run_strategy_file
from ptrade_sim.redata import RealDataSource
run_strategy_file("pt_wufu5.1.py", "2026-06-01", "2026-08-21",
                  data_source=RealDataSource())
```

无头冒烟测试(默认真实数据):`python -m ptrade_sim._selftest 策略.py 起始 结束 [real|sim]`

## 全市场 A 股日线数据

模拟环境提供"获取全部 A 股日线数据"的能力,用于股票策略的截面选股 / 全市场回测准备:

- **`get_Ashares()`**(PTrade 同名原生接口):真实数据源返回东财全 A 列表(沪 60/68、深 00/30,
  自动剔除 B 股 / 北交所 / 基金债券),本地缓存 7 天;合成数据源回退到内置样本股票池。
- **`get_all_Ashare_daily(stocks=None, start_date, end_date, fields, fq='pre', count=None)`**:
  返回 `{code: DataFrame(index=交易日, columns=字段)}`(结构与聚宽 `get_price` 的 panel 一致)。
  `stocks=None` 时取全部 A 股;也可用 `stocks=[...]` 收敛范围,或 `count=N` 取最近 N 个交易日。

```python
# 引擎 API 直接调用(策略内 / 脚本内)
data = get_all_Ashare_daily(start_date="2026-06-01", end_date="2026-08-21",
                            fields=["close", "volume"])
close_panel = {c: df["close"] for c, df in data.items()}   # 截面收盘价
```

- **离线预热**(真实数据源):`python -m ptrade_sim.prefetch [etf|ashare|all] [并行数]`
  批量下载日线到 `ptrade_sim/data_cache/*.csv`,之后回测 / 取数全程离线、无延迟。
  `ashare` 预热全市场 A 股,`all` 同时预热 ETF + A 股(耗时较长,建议后台运行)。

> 注意:模拟器的全 A 列表、指数成分、基本面均为本地近似,仅保证选股 / 回测逻辑可运行;
> 真实成分股、ST / 退市状态等以真机 PTrade 为准。

## 用法

命令行(合成行情):

```bash
python -m ptrade_sim.run                                # 跑自带示例策略
python -m ptrade_sim.run pt_wufu7.0.py 2026-06-01 2026-08-21 1000000
```

图形界面:

```bash
python -m ptrade_sim.gui
```

界面功能:选择策略文件(下拉列出目录内的 .py)、设置日期区间与初始资金、
选择数据源(真实历史/合成)、后台线程运行并随时"停止";四个页签实时展示
运行日志(WARN/ERROR 着色)、资产曲线(含初始资金基准线、收益与最大回撤)、
持仓与成交明细、期末统计报告。

## 说明与限制

- 行情为合成数据,结果仅用于验证策略逻辑/语法/调度,不代表真实收益
- 任意代码均可生成行情(未知代码按哈希定基准价);日线含 open/high/low/close/pre_close/high_limit/low_limit/unit_nav/volume/amount 字段
- `get_history` 返回 pandas DataFrame(单标的: 列=字段;多标的单字段: 列=代码;多标的多字段: {代码: DataFrame}),支持 1m/5m 等分钟频率(按 3 分钟网格近似)
- `get_snapshot` 含 last_px/trade_status/up_px/down_px 等;`context.blotter.current_dt` 为当前模拟时间
- 事件函数签名自动适配: `func()` / `func(context)` / `func(context, data)` 均可
- `run_daily` 兼容 `run_daily(func, time)` 与 PTrade 官方 `run_daily(context, func, time='9:30')` 两种写法
- 策略文件中自定义的同名函数(如 `set_params`/`set_backtest`)优先于引擎内置实现,不会被覆盖
- 涨跌停、撤单、盘口撮合为简化模型(`set_limit_mode` / `cancel_order` 为空实现)
- 休市日仅排除周末;如需精确交易日历,在 `data.is_trade_date` 中接入
- 无头冒烟测试: `python -m ptrade_sim._selftest 策略文件.py`(输出错误统计与缺失 API)
- 若策略引用了未实现的 PTrade API,会在 `ptrade_sim/engine.py` 的 `build_api` 中补充
