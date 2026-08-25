# -*- coding: utf-8 -*-
"""演示策略:在 PTrade 模拟环境中运行的 ETF 网格/轮动示例。"""


def initialize(context):
    log.info("策略初始化")
    g.codes = ["510300.SS", "512100.SS", "518880.SS", "512880.SS"]
    g.etf = g.codes[0]
    g.grid_step = 0.02          # 网格间距 2%
    g.last_price = None
    set_universe(g.codes)
    run_daily(rebalance, "9:35")
    run_daily(check_grid, "14:50")


def before_trading_start(context):
    snap = get_snapshot(g.codes)
    g.open_prices = {c: snap[c]["open_px"] for c in g.codes}


def rebalance(context):
    hist = get_history(5, "1d", "close", g.codes)
    # 简单动量:买入 5 日涨幅最高者(get_history 返回 DataFrame,列为代码)
    momentum = {c: hist[c].iloc[-1] / hist[c].iloc[0] - 1 for c in hist.columns}
    target = max(momentum, key=momentum.get)
    log.info(f"动量排名 {sorted(momentum.items(), key=lambda x: -x[1])}")
    for c in g.codes:
        pos = [p for p in get_stock_positions() if p["code"] == c]
        if pos:
            order_target_value(c, 0)
    order_target_value(target, context.portfolio.cash * 0.95)
    g.etf = target


def check_grid(context):
    px = get_snapshot(g.etf)[g.etf]["last_px"]
    if g.last_price and px < g.last_price * (1 - g.grid_step):
        log.info(f"网格触发: {g.last_price} -> {px}, 补仓")
        order(g.etf, 10000)
    g.last_price = px


def after_trading_end(context):
    pf = get_portfolio()
    log.info(f"收盘 总资产 {pf.portfolio_value:,.0f} 收益 {pf.returns*100:.2f}%")
