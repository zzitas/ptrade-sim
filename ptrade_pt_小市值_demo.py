"""
策略名称：
小市值日线交易策略
运行周期:
日线
策略流程：
盘前将中小板综成分股中st、停牌、退市的股票过滤得到股票池
盘中换仓，始终持有当日流通市值最小的股票（涨停标的不换仓）。
注意事项：
策略中调用的order_target_value接口的使用有场景限制，回测可以正常使用，交易谨慎使用。
回测场景下撮合是引擎计算的，因此成交之后持仓信息的更新是瞬时的，但交易场景下信息的更新依赖于柜台数据
的返回，无法做到瞬时同步，可能造成重复下单。详细原因请看帮助文档。
优化说明：
- 卖出与买入分离，先卖后买，确保资金到位
- 买入前检查可用资金，按剩余资金等分买入
- 增加涨停/跌停状态的卖出保护
- 增加实盘环境下的状态日志
- 增加异常数据防护
"""

import numpy as np


# 兼容垫片: 运行环境未内置 filter_stock_by_status 时使用本地实现
# (HALT 用 get_stock_status 判定;ST/DELISTING 需真实环境数据,默认保留)
try:
    filter_stock_by_status  # noqa: F821
except NameError:
    def filter_stock_by_status(stock_list, filter_type=None,
                               query_date=None, **kw):
        types = filter_type or ["ST", "HALT", "DELISTING"]
        codes = stock_list if isinstance(stock_list, list) else [stock_list]
        kept = []
        for s in codes:
            try:
                if "HALT" in types and get_stock_status([s], "HALT").get(s):
                    continue
            except Exception:
                pass
            kept.append(s)
        return kept


# 初始化
def initialize(context):
    # 设置基准指数
    set_benchmark("000300.SS")
    # 股票池对应指数代码
    g.index = "399101.XBHS"  # 中小板综
    # 持有股票数量
    g.buy_stock_count = 5
    # 筛选股票数量
    g.screen_stock_count = 10
    if not is_trade():
        set_backtest()  # 设置回测条件


# 设置回测条件
def set_backtest():
    set_limit_mode("UNLIMITED")


# 盘前处理
def before_trading_start(context, data):
    g.pre_position_list = list(get_positions().keys())
    g.stock_list = get_index_stocks(g.index)
    # 指数成分股按昨日收盘时的流通市值进行从小到大排序，截取市值最小的100个标的进行股票状态筛选（考虑回测速度）
    df = get_fundamentals(g.stock_list, "valuation", fields=["total_value", "a_floats", "float_value"],
                          date=context.previous_date).sort_values(by="float_value").head(100)
    stock_list_tmp = df.index.tolist()
    # 将ST、停牌、退市三种状态的股票剔除当日的股票池
    stock_list_tmp = filter_stock_by_status(stock_list_tmp, filter_type=["ST", "HALT", "DELISTING"], query_date=None)
    # 保留状态筛选后的股票，并取其中流通市值最小的N个股票
    df = df[df.index.isin(stock_list_tmp)]
    g.df = df.head(g.screen_stock_count)
    log.info("盘前股票池筛选完成，候选股数:%d" % len(g.df))


# 盘中处理
def handle_data(context, data):
    buy_stocks = get_trade_stocks(context, data)
    log.info("目标持仓列表:%s" % buy_stocks)
    # 先卖出不在目标列表中的持仓
    sell_stocks = sell(context, buy_stocks)
    # 卖出完成后再买入（确保资金到位）
    buy(context, buy_stocks, sell_stocks)


# 卖出函数：卖出不在目标列表中的持仓
def sell(context, buy_stocks):
    sell_list = []
    for stock in context.portfolio.positions:
        if stock not in buy_stocks:
            # 跌停不卖（避免无法成交的废单）
            limit_info = check_limit(stock)
            if limit_info[stock] == -1:
                log.info("跌停跳过卖出:%s" % stock)
                continue
            order_target_value(stock, 0)
            log.info("卖出:%s" % stock)
            sell_list.append(stock)
    return sell_list


# 买入函数：按可用资金等分买入
def buy(context, buy_stocks, sell_stocks):
    # 统计当前有效持仓
    position_list = [p.sid for p in context.portfolio.positions.values() if p.amount != 0]
    position_count = len(position_list)
    need_buy_count = g.buy_stock_count - position_count
    if need_buy_count <= 0:
        return

    # 可用资金
    cash = context.portfolio.cash
    if cash <= 0:
        log.info("可用资金不足，跳过买入")
        return

    # 收集需要买入的标的（排除已有持仓的）
    need_buy_list = [s for s in buy_stocks if s not in context.portfolio.positions]
    if not need_buy_list:
        return

    # 按可用资金等分
    per_value = cash / need_buy_count
    for stock in need_buy_list:
        # 再次检查可用资金（实盘中买入后资金会实时变化）
        if context.portfolio.cash < per_value * 0.5:
            log.info("资金不足，停止后续买入")
            break
        # 涨停不买（避免无法成交的废单）
        limit_info = check_limit(stock)
        if limit_info[stock] == 1:
            log.info("涨停跳过买入:%s" % stock)
            continue
        order_target_value(stock, per_value)
        log.info("买入:%s, 目标市值:%.2f" % (stock, per_value))


# 获取买入股票池（涨停股不参与换仓）
def get_trade_stocks(context, data):
    # 获取持仓中涨停的标的
    hold_up_limit_stock = []
    for stock in g.pre_position_list:
        limit_info = check_limit(stock)
        if limit_info[stock] == 1:
            hold_up_limit_stock.append(stock.replace("SS", "SS").replace("SZ", "SZ"))

    df = g.df
    if df.empty:
        return hold_up_limit_stock

    # 向量化计算当前流通市值
    codes = df.index.tolist()
    prices = [data[code].price for code in codes]
    df["curr_float_value"] = df["a_floats"].values * np.array(prices)
    df = df[df["curr_float_value"] != 0]

    if df.empty:
        return hold_up_limit_stock

    # 获取股票标的（按流通市值从小到大排序）
    stocks = df.sort_values(by="curr_float_value").index.tolist()
    # 计算本次拟买入的数量（最大持仓量-持仓中涨停的数量）
    count = g.buy_stock_count - len(hold_up_limit_stock)
    if count <= 0:
        return hold_up_limit_stock
    check_out_lists = stocks[:count]
    check_out_lists = check_out_lists + hold_up_limit_stock
    return check_out_lists
