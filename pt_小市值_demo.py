"""
策略名称：
小市值策略

策略流程：
盘前将中小板综成分股中亏损、st、停牌、退市的股票过滤得到股票池
盘中换仓，始终持有当日流通市值最小的股票（涨停标的不换仓）。
注意事项：
策略中调用的order_target_value接口的使用有场景限制，回测可以正常使用，交易谨慎使用。
回测场景下撮合是引擎计算的，因此成交之后持仓信息的更新是瞬时的，但交易场景下信息的更新依赖于柜台数据
的返回，无法做到瞬时同步，可能造成重复下单。详细原因请看帮助文档。
"""


# 初始化
def initialize(context):
    # 设置基准指数
    set_benchmark("000300.SS")
    # 股票池对应指数代码
    g.index = "399101.SZ"  # 中小板综
    # 持有股票数量
    g.buy_stock_count = 5
    # 筛选股票数量
    g.screen_stock_count = 10
    g.stock_list = []
    g.df = None
    g.pre_position_list = []
    g.sell_submitted = set()
    if not is_trade():
        set_backtest()  # 设置回测条件


# 设置回测条件
def set_backtest():
    set_slippage(0.002)
    set_commission(commission_ratio =0.0003, min_commission=5.0)
    set_limit_mode("UNLIMITED")

# 盘前处理
def before_trading_start(context, data):
    g.pre_position_list = list(get_positions().keys())
    g.sell_submitted = set()
    try:
        g.stock_list = get_index_stocks(g.index)
        if not g.stock_list:
            log.warning("指数成分股为空，今日不交易")
            g.df = None
            return

        # 指数成分股按昨日收盘时的流通市值从小到大排序，先截取前100个以提升回测速度
        df = get_fundamentals(
            g.stock_list,
            "valuation",
            fields=["total_value", "a_floats", "float_value"],
            date=context.previous_date
        )
        if df is None or df.empty:
            log.warning("基本面数据为空，今日不交易")
            g.df = None
            return

        df = df.dropna(subset=["a_floats", "float_value"])
        df = df[df["a_floats"] > 0].sort_values(by="float_value").head(100)
        stock_list_tmp = df.index.tolist()

        # 将ST、停牌、退市三种状态的股票剔除当日的股票池
        stock_list_tmp = filter_stock_by_status(
            stock_list_tmp,
            filter_type=["ST", "HALT", "DELISTING"],
            query_date=None
        )

        # 过滤亏损股：优先使用归母净利润，字段不可用时使用净利润
        stock_list_tmp = filter_non_loss_stocks(stock_list_tmp, context.previous_date)

        # 保留状态筛选后的股票，并取其中流通市值最小的候选股票
        df = df[df.index.isin(stock_list_tmp)]
        g.df = df.head(g.screen_stock_count)
        log.info("盘前候选股票数:%s" % len(g.df))
    except Exception as e:
        log.error("盘前选股失败:%s" % e)
        g.df = None


# 盘中处理
def handle_data(context, data):
    current_time = context.blotter.current_dt.strftime("%H:%M")
    if current_time >= "14:55":
        return

    buy_stocks = get_trade_stocks(context, data)
    log.info("buy_stocks:%s" % buy_stocks)
    if not buy_stocks:
        log.info("今日无可买股票，仅卖出非目标持仓")
    trade(context, buy_stocks)


# 交易函数
def trade(context, buy_stocks):
    buy_stocks = _unique_list(buy_stocks)
    buy_set = set(buy_stocks)

    # 卖出
    for stock, position in list(context.portfolio.positions.items()):
        if position.amount <= 0:
            continue
        if stock not in buy_stocks:
            if stock in g.sell_submitted:
                log.info("skip sell:%s 已提交卖出委托，等待成交或持仓同步" % stock)
                continue
            enable_amount = getattr(position, "enable_amount", 0)
            if enable_amount <= 0:
                log.info("skip sell:%s 可卖数量为0，可能为当日买入、已挂卖单或柜台持仓未同步" % stock)
                continue
            order_id = order_target_value(stock, 0)
            if order_id:
                g.sell_submitted.add(stock)
                log.info("sell:%s" % stock)
            else:
                log.info("sell failed:%s 委托未成功提交" % stock)

    # 买入
    position_list = [position.sid for position in context.portfolio.positions.values() if position.amount > 0]
    position_count = len(position_list)
    need_count = g.buy_stock_count - position_count
    if need_count <= 0:
        return

    buy_candidates = [stock for stock in buy_stocks if stock not in context.portfolio.positions]
    buy_candidates = buy_candidates[:need_count]
    if not buy_candidates:
        return

    value = context.portfolio.cash / len(buy_candidates)
    if value <= 0:
        log.info("现金不足，不执行买入")
        return

    for stock in buy_candidates:
        if stock not in buy_set:
            continue
        order_target_value(stock, value)
        log.info("buy:%s value:%.2f" % (stock, value))


# 获取买入股票池（涨停股不参与换仓）
def get_trade_stocks(context, data):
    # 获取持仓中涨停的标的
    hold_up_limit_stock = []
    for stock in g.pre_position_list:
        try:
            limit_status = check_limit(stock)
            if limit_status and limit_status.get(stock) == 1:
                hold_up_limit_stock.append(stock)
        except Exception as e:
            log.warning("检查涨停失败:%s %s" % (stock, e))

    if g.df is None or g.df.empty:
        return _unique_list(hold_up_limit_stock)

    df = g.df.copy()
    # 计算当时最新的流通市值（昨日的流通股本*最新价）
    curr_float_values = []
    for stock, row in df.iterrows():
        price = _get_price_from_data(stock, data)
        if price <= 0:
            curr_float_values.append(0)
        else:
            curr_float_values.append(row["a_floats"] * price)
    df["curr_float_value"] = curr_float_values
    df = df[df["curr_float_value"] != 0]
    log.info("候选:%s 有效价格:%s 涨停保留:%s" % (len(g.df), len(df), len(hold_up_limit_stock)))
    # 获取股票标的（按流通市值从小到大排序）        
    stocks = df.sort_values(by="curr_float_value").index.tolist()
    # 计算本次拟买入的数量（最大持仓量-持仓中涨停的数量（因为涨停股不卖））
    count = max(g.buy_stock_count - len(hold_up_limit_stock), 0)
    check_out_lists = stocks[:count]
    check_out_lists = check_out_lists + hold_up_limit_stock
    return _unique_list(check_out_lists)


def filter_non_loss_stocks(stock_list, query_date):
    """过滤亏损股，保留净利润为正的股票。"""
    if not stock_list:
        return []

    try:
        profit_df = get_fundamentals(
            stock_list,
            "income_statement",
            fields=["np_parent_company_owners", "net_profit"],
            date=query_date
        )
        if profit_df is None or profit_df.empty:
            log.warning("利润表数据为空，非亏损过滤后无候选")
            return []

        profit_field = None
        if "np_parent_company_owners" in profit_df.columns:
            profit_field = "np_parent_company_owners"
        elif "net_profit" in profit_df.columns:
            profit_field = "net_profit"

        if profit_field is None:
            log.warning("利润表缺少净利润字段，非亏损过滤后无候选")
            return []

        profit_df = profit_df.dropna(subset=[profit_field])
        profit_df = profit_df[profit_df[profit_field] > 0]
        result = profit_df.index.tolist()
        log.info("非亏损过滤:%s -> %s" % (len(stock_list), len(result)))
        return result
    except Exception as e:
        log.error("非亏损过滤失败:%s" % e)
        return []


def _get_price_from_data(stock, data):
    """安全获取当前价格。"""
    try:
        price = data[stock].price
        if price > 0:
            return price
    except Exception:
        pass

    return 0


def _unique_list(stock_list):
    """按原顺序去重。"""
    result = []
    seen = set()
    for stock in stock_list:
        if stock not in seen:
            seen.add(stock)
            result.append(stock)
    return result