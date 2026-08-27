# ptrade-sim

本地 PTrade 模拟/回测环境 —— 无需恒生 PTrade 终端,在本地用 Python 复现
PTrade 回测引擎的事件模型与撮合语义,并内置**聚宽 → PTrade 策略转换器**
(生成可在真实恒生 PTrade 上直接运行的策略文件)。

> 免责声明:本项目仅用于学习与研究,不构成任何投资建议。回测结果不代表
> 未来表现;盘中信号基于日线数据的合成近似(见下文"已知限制")。

## 特性

- **事件模型对齐 PTrade**:`initialize / before_trading_start / handle_data /
  after_trading_end`、`run_daily` 定时任务、`context.blotter.current_dt`
- **撮合语义对齐**:当日成交量 25% 限制、T+1 冻结交收(`enable_amount`)、
  停牌拒单、真实 A 股交易日历、前复权价格
- **防未来函数**:盘中 `include=True` 的当日日线返回形成中 K 线;
  盘中报价为开→收插值,不泄露当日收盘(详见 `docs/MANUAL.md`)
- **三种数据源**:通达信本地终端(pytdx)、网络行情(腾讯主源+东财备用)、
  合成行情(离线演示)
- **图形界面**(Tkinter,零第三方 GUI 依赖):选策略/区间/资金/数据源,
  实时日志、持仓/成交/净值曲线,每次回测自动落盘完整日志
- **全市场 ETF 列表**:自动获取并过滤上市日期(只含回测起点前已上市的代码)
- **聚宽兼容垫片**:`attribute_history / get_price / get_extras /
  get_current_data / finance.run_query / 打新` 等聚宽 API 均可用

## 安装

```bash
pip install .            # 或使用发行包 wheels/
```

要求:Python 3.9+(开发环境为 3.11)。通达信数据源需要本机运行通达信
(默认端口 7709;若为 17709 等自定义端口会自动探测)。

## 快速开始

```bash
# 图形界面
ptrade-gui                       # 等价于 python -m ptrade_sim.gui

# 命令行回测: 策略 开始 结束 初始资金 数据源(tdx|real|sim)
ptrade-run demo_strategy.py 2026-07-01 2026-08-01 1000000 tdx

# 全市场行情预热(一次性,之后回测秒开)
ptrade-prefetch

# 自检
ptrade-selftest
```

每次回测的完整日志自动保存到 `logs/时间戳_策略名_区间.log`。

## 聚宽策略转 PTrade

```bash
python jq_to_ptrade.py jq_我的策略.py ptrade_我的策略.py
```

生成的文件头部自带自包含垫片层:

- 在本模拟器与真实恒生 PTrade 回测端均可直接运行;
- 自动处理两端差异:`get_stock_name` 返回字典解包、原生 `get_price`
  要求字符串日期且拒绝 `start_date≥回测日`(自动改走模拟路径)、
  `set_option/set_order_cost/set_slippage` 桩、pandas 3.0 序列位置取值等;
- 内置性能优化:`is_dict=True` 批量行情(200 只分块+坏代码剔除)、
  名称/停牌状态缓存、快照批量预热——真机上全池扫描从数分钟降到秒级。

## 项目结构

```
ptrade_sim/          模拟引擎、数据源、GUI、CLI 入口
jq_to_ptrade.py      聚宽→PTrade 转换器(生成自包含垫片)
test_shim_ns.py      垫片多宿主环境解析测试
test_lookahead.py    防未来函数回归测试
docs/                安装说明与使用手册
```

## 已知限制

- 只有日线数据:盘中价格由开盘→收盘插值合成。依赖截至昨日数据的信号
  (动量排名等)可信;依赖盘中瞬时价的信号(网格、量比)为近似,
  以真实 PTrade 回测为准。
- 打新、逆回购等非 ETF 业务为桩函数。

详细语义对照表见 [docs/MANUAL.md](docs/MANUAL.md)。

## License

[MIT](LICENSE)
