# PTrade-SIM 使用手册

## 1. 快速开始(图形界面)

1. 启动:`ptrade-gui`(或 `python -m ptrade_sim.gui`)
2. 顶部工具栏依次设置:
   - **策略文件**:下拉自动列出工作目录中的 `.py`,或点"浏览"选择
   - **开始日期 / 结束日期**:`YYYY-MM-DD`
   - **初始资金**:正数
   - **数据源**:
     | 选项 | 说明 |
     |---|---|
     | 通达信终端数据(前复权) | 连接本机通达信终端,真实日线,**推荐** |
     | 真实历史数据-网络(前复权) | 腾讯/东财在线数据 |
     | 模拟行情(合成) | 随机游走合成数据,仅验证逻辑 |
   - **数据加载明细**:勾选后日志逐条显示行情下载进度(默认隐藏)
3. 点 **▶ 运行**,四个页签实时刷新;**■ 停止** 可安全中止;**清空** 重置界面

### 页签说明

| 页签 | 内容 |
|---|---|
| 运行日志 | 引擎与策略输出;ERROR 红 / WARN 黄;超 5000 行自动截断 |
| 资产曲线 | 每日净值曲线、初始资金基准线、收益率/最大回撤实时汇总 |
| 持仓 / 成交 | 持仓明细(总持仓/可用/T+1冻结/成本/现价/市值)+ 最近 300 笔成交(买卖红绿) |
| 统计报告 | 运行结束后生成:区间、现金流拆分、总收益、最大回撤、各持仓浮盈 |

## 2. 命令行工具

```bash
# 回测:策略 开始 结束 初始资金 数据源(tdx|real|sim)
ptrade-run 我的策略.py 2026-06-01 2026-08-21 1000000 tdx

# 冒烟测试(完整引擎日志写入 _selftest_logs.txt;返回码非0表示有异常)
ptrade-selftest 我的策略.py 2026-08-10 2026-08-21 tdx

# 全市场行情预热(一次性,之后回测秒开)
ptrade-prefetch [并行数=6]
```

代码格式与 PTrade 一致:沪 `510300.SS`、深 `159915.SZ`;指数同样支持(如 `000300.SS`)。

## 3. 策略编写要求

策略是一个普通 Python 文件,PTrade 的写法基本可以原样运行:

```python
def initialize(context):
    g.pool = ["510300.SS", "512100.SS"]
    set_universe(g.pool)
    run_daily(context, my_task, time='09:40')   # 官方签名
    run_daily(my_task2, time='14:50')           # 简写亦可

def handle_data(context, data):     # func() / func(context) / func(context, data) 均可
    px = get_snapshot("510300.SS")["510300.SS"]["last_px"]
    if px < g.low_line:
        order("510300.SS", 10000)

def before_trading_start(context, data): ...
def after_trading_end(context, data): ...
```

- 全局对象 `g`、`log`、`set_universe/set_params/set_backtest/set_commission` 由引擎注入;
  **策略文件中自定义的同名函数优先生效**(如自己的 `set_params`)
- `context.blotter.current_dt` 为当前模拟时间;`context.portfolio.positions[code]` 含
  `amount / enable_amount / cost_basis / last_sale_price`
- `data[code]` 支持 dict 与属性两种访问方式

## 4. 已兼容的 PTrade API

**交易**:`order` `order_target` `order_value` `order_target_value` `order_market` `cancel_order`* `get_orders`

**账户**:`get_stock_positions` `get_cash` `get_portfolio`(portfolio_value/cash/positions)

**行情**:`get_snapshot`(last_px/up_px/down_px/trade_status/iopv 等)`get_history` `get_price` `get_gear_price` `get_volume_ratio` `get_stock_blocks`* `get_fundamentals`*

**证券信息**:`get_security_info` `get_security_name` `get_stock_name` `get_stock_info` `get_stock_status` `get_etf_info` `get_index_stocks` `get_etf_list`(全市场上市 ETF)

**日历/状态**:`get_trade_days(start_date,end_date,count)` `get_prev_trade_date` `is_trade`

**调度/设置**:`run_daily` `run_interval` `set_universe` `set_commission` `set_limit_mode`* `set_backtest`* `set_params` `sleep`

带 * 为空实现或简化实现(记录日志,不影响运行)。缺什么在
`ptrade_sim/engine.py → build_api()` 中加一行即可。

### get_history 返回规则(与 PTrade 一致)

| 参数组合 | 返回 |
|---|---|
| 单标的(串或单元素列表) | DataFrame:index=日期,columns=字段 |
| 多标的 + 单字段 | DataFrame:columns=代码 |
| 多标的 + 多字段,或 `is_dict=True` | `{代码: DataFrame}` |

支持字段:`open/high/low/close/preclose/pre_close/volume/amount/money/unit_nav/high_limit/low_limit/is_open`,
分钟频率(`1m` 等)按当日 3 分钟网格近似,volume/amount 按 bar 均摊累计。
参数 `count/frequency/field/security_list/fq/include/is_dict/fill/skip_paused` 均可识别。

## 5. 与 PTrade 回测的语义对齐

| 规则 | 本模拟器 |
|---|---|
| 成交价 | 盘中按**日内合成价**(开盘→收盘时间插值+微噪声),15:00 后为收盘价 |
| 成交量限制 | 委托不超过当根 bar 成交量的 **25%**,超出部分自动调整并记日志 |
| 停牌 | 当日无 K 线视为停牌:拒单、快照 `trade_status=HALT`、`is_open=0` |
| 价格口径 | **前复权**(通达信 xdxr 分红记录 / 网络 fqt=1) |
| 交易日历 | 真实 A 股日历(由参考 ETF 实际交易日生成) |
| T+1 | 当日买入冻结,次日可用(`enable_amount`) |
| 手续费 | 默认万分之三、最低 5 元;ETF 免印花税(`stamp_duty=0`) |
| 全市场列表 | 仅含**回测起始日前已上市**的 ETF(避免未来函数),未上市/无效代码自动黑名单 |
| 防未来函数 | 盘中 `include=True` 的当日日线返回**形成中 K 线**(收盘=日内价,量按比例),不泄露当日完整 OHLCV |

### 日内数据的结构性近似(重要)

模拟环境只有日线数据,盘中价格由"开盘→收盘插值 + 微幅确定性噪声"合成。
它保证任意时刻的报价**不等于未来值**(已消除"全天报收盘价"的未来函数),
但路径形态仍由当日开/收决定,与真实分钟走势不同。因此:

- 依赖**截至昨日数据**的信号(动量排名、涨幅计算等):与真机一致,可信;
- 依赖**盘中瞬时价**的信号(网格触发、量比、三连高开等):为近似结果,
  模拟通过不代表真机同样表现,**以真机回测为准**。

## 6. 环境变量开关

| 变量 | 作用 |
|---|---|
| `PTRADE_SIM_DATA_LOG=1` | 日志逐条显示行情下载进度(GUI 中也可勾选"数据加载明细") |
| `PTRADE_SIM_ETF_LIST=cached` | `get_etf_list` 只返回本地已缓存的代码(离线快速验证) |
| `PTRADE_SIM_LOG_DIR=<目录>` | 回测日志保存目录(默认 `<运行目录>/logs`) |

## 7. 回测日志落盘

**每次回测自动把完整日志保存为独立文件**,GUI 与命令行均生效,无需手工重定向:

```
logs/20260825_153725_ptrade_七星动态池_20260727-20260728.log
      └─时间戳        └─策略名         └─回测区间
```

文件内容包括:头部元信息(策略/区间/初始资金/数据源)、全部运行日志
(含 DEBUG 级)、末尾的"模拟结果"块与成交记录。控制台/GUI 窗口只显示
一部分时,打开该文件即可查看全程。

- GUI 工具栏的 **"日志目录"** 按钮可直接打开该目录;
- 日志按时间戳命名,多次回测互不覆盖,请定期清理旧文件。

## 8. 缓存管理

缓存位于包运行目录下 `data_cache/`:

- `<代码>.csv`:日线数据,增量更新;**删除即重新下载**
- `all_etfs.csv`:全市场列表,7 天自动刷新;删除强制重建
- `bad_codes.txt`:无效代码黑名单,可手工编辑(删行即恢复)
- `names.json`:名称映射

预热命令 `ptrade-prefetch` 会把全部上市 ETF 的日线拉齐,首次约 10–60 分钟,
完成后所有回测不再等待网络。

## 9. 常见问题

**Q: 提示 `NameError: name 'xxx'`?**
A: 某个 PTrade API 尚未兼容。到 `engine.py → build_api()` 补一行,例如:
`api["get_margin_data"] = lambda *a, **k: {}`

**Q: 个别 ETF 显示停牌但实际没停?**
A: 其本地缓存尚未刷新到最新交易日。跑一次 `ptrade-prefetch`,或删除该代码的 csv 重建。

**Q: 量比/动量数值和实盘不一致?**
A: 请确认使用通达信或网络数据源(合成行情无意义);分钟级指标为 3 分钟网格近似。

**Q: 结果能直接对照 PTrade 回测吗?**
A: 撮合价、量限、复权、日历已对齐;差异主要来自:分钟粒度近似、撮合不含滑点、
以及东财/通达信与恒生数据的微小出入。适合验证策略逻辑与相对表现。

## 10. 已知限制

- 分钟线以 3 分钟网格近似(引擎调度粒度),非逐笔撮合;无滑点模型
- 涨跌停不拦截成交(仅在快照中提供 limit 价供策略自检);撤单为即时成交模型下的空操作
- 休市法定节假日依赖行情源返回的实际交易日,无需人工维护
- `get_fundamentals`、财务类接口返回空数据
