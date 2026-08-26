#实盘 2026.07.08，
# 修改 07.09 07.10
# 持仓在前三名的ETF判断是否需要卖出
# 增加ETF品种 7.31 
# 增加V型反转动量指标 8.04
# 删除防御ETF 8.14
# 当反转排名为空时，再选动量排名第一且分值>3的标的 8.21

import numpy as np
import math
from datetime import datetime, date, timedelta
import pandas as pd

# ==================== 初始化模块 ====================
def initialize(context):
    """
    初始化函数：设置交易参数、ETF池、核心参数、调度任务
    """
    # ---------- 交易设置 ----------
    log.info("========== 策略初始化开始 ==========")

    g.jiaoyi = False
    if is_trade():
        g.jiaoyi = True   # 是否处于交易模块, False 回测, True 交易 
    else:
        set_limit_mode('UNLIMITED')
        set_volume_ratio(volume_ratio=1.0)
        set_slippage(0.0001)
        # 设置交易成本:ETF交易成本较低
        set_commission(commission_ratio =0.0003, min_commission=5.0)

    # ---------- ETF池(国际)----------
    g.etf_pool_u = [        
        # 国际ETF
        "513100.SS",  # 纳指ETF         
        "159509.SZ",  # 纳指科技ETF
        "513290.SS",  # 纳指生物ETF
        "513500.SS",  # 标普500ETF
        "159529.SZ",  # 标普消费
        "513400.SS",  # 道琼斯ETF
        "513520.SS",  # 日经225ETF
        "513030.SS",  # 德国30ETF
        "513080.SS",  # 法国ETF
    ]
        # 大ETF池
    g.etf_pool  = [
        # 大宗商品ETF
        "518880.SS",  # 黄金ETF
        "159980.SZ",  # 有色ETF（跟踪有色金属板块）
        "159985.SZ",  # 豆粕ETF（跟踪豆粕期货价格）
        "501018.SS",  # 南方原油（投资原油相关资产）    
        '161226.SZ',  # 白银LOF
        "159981.SZ",  # 能源化工ETF

        "513310.SS",  # 中韩半导体ETF
        "513730.SS",  # 东南亚ETF
        
        # 香港ETF
        "159792.SZ",  # 港股互联ETF
        "513130.SS",  # 恒生科技
        "513050.SS",  # 中概互联网ETF
        "159920.SZ",  # 恒生ETF
        "513690.SS",  # 港股红利
        
        # 指数ETF
        "510300.SS",  # 沪深300ETF
        "510500.SS",  # 中证500ETF
        "510050.SS",  # 上证50ETF
        "510210.SS",  # 上证ETF
        "159915.SZ",  # 创业板ETF
        "588080.SS",  # 科创50
        "512100.SS",  # 中证1000ETF
        "563360.SS",  # A500-ETF
        "563300.SS",  # 中证2000ETF
        
        # 风格ETF
        "159967.SZ",  # 创业板成长ETF
        "512040.SS",  # 价值ETF

        # 债券ETF
        "511380.SS",  # 可转债ETF
        "511010.SS",  # 国债ETF
        "511220.SS",  # 城投债ETF
        
        #新增 
        "159995.SZ",  # 芯片ETF
        "588000.SS",  # 科创ETF
        "515880.SS",  # 通信ETF
        "512670.SS",  # 国防ETF
        "562500.SS",  # 机器人ETF华夏
        "588760.SS",  # 科创AIETF广发
        "159638.SZ",  # 高端装备ETF嘉实
        "588170.SS",  # 科创半导体ETF华夏
        "159530.SZ",  # 机器人ETF易方达
        "159518.SZ",  # 标普油气ETF嘉实
        #"513350.SS",  # 标普油气ETF富国
        "588360.SS",  # 科创创业ETF国泰
        
        "159363.SZ",  # 创业版人工智能ETF华宝
        "588200.SS",  # 科创芯片ETF
        "516150.SS",  # 稀土ETF
        "159206.SZ",  # 卫星ETF
        
        "159566.SZ",  # 储能电池ETF易方达
        "159667.SZ",  # 工业母机ETF国泰
        "159713.SZ",  # 稀土ETF富国
        "512880.SS",  # (ZQETF)
        "159993.SZ",  # 证券ETF鹏华 
        "159157.SZ",  # (YSJSETFTH)
        "562800.SS",  # 稀有金属
        #"159062.SZ",  # 稀有金属
        "159133.SZ",  # 化工
        
        "159992.SZ",  #创新药
        "159869.SZ",  #游戏
        "159928.SZ",  #消费
        
        "516510.SS",  #云计算
        "512690.SS",  #酒ETF
        "561580.SS",  #央企红利
        "560080.SS",  #中药
        
        "517520.SS",  #黄金股ETF
        "513120.SS",  #HK创新药
    ]
    
    # ---------- 核心参数 ----------
    g.lookback_days = 25               # 动量计算周期
    g.holdings_num = 1                 # 候选数量
    g.min_money = 500                 # 最小交易金额

    # ---------- 盈利保护参数 ----------
    g.enable_profit_protection = True                      # 盈利保护开关
    g.profit_protection_lookback = 1                       # 盈利保护回看周期（天）
    g.profit_protection_threshold = 0.05                   # 盈利保护回撤阈值（5%）
    g.profit_protection_check_times = ['11:15']            # 盈利保护检查时间点（可添加多个，如['09:45','11:00','13:30']）

    g.loss = 0.97                      # 近3日单日跌幅阈值（排除）

    g.min_score_threshold = 0          # 最低得分
    g.max_score_threshold = 300.0      # 最高得分

    # ---------- 成交量过滤 ----------
    g.enable_volume_check = True
    g.volume_lookback = 5
    g.volume_threshold = 2
    g.volume_return_limit = 1          # 年化收益>100%时启用放量过滤

    # ---------- 短期动量过滤 ----------
    g.use_short_momentum_filter = True
    g.short_lookback_days = 10
    g.short_momentum_threshold = 0.0

    # ---------- 溢价率过滤 ----------
    g.enable_premium_filter = False
    if g.jiaoyi:
        g.enable_premium_filter = True      # 是否启用溢价率过滤
    g.premium_threshold = 0.15          # 溢价率阈值（20%）

    # ---------- 日内趋势判断参数 ----------
    g.trend_lookback_minutes = 30  # 趋势判断回看周期（分钟）
    g.trend_slope_threshold = 0.005  # 趋势判断斜率阈值

    # ---------- 市场状态判断参数 ----------
    g.market_index = '000001.SS'       # 市场代表指数（上证指数）
    g.market_ma_lookback = 250          # 均线周期（250日均线）
    # 市场强：上证指数 >= MA250（用动量打分）；市场弱：上证指数 < MA250（用反转动量打分）

    # ---------- V型反转动量参数 ----------
    g.reversal_lookback = 60           # V型反转回看天数
    g.m2xd_u_shape_center = 0.3        # U型谷底中心值
    g.min_reversal_score = 0.5         # 反转动量最低买入 score
    g.enable_reversal_days_filter = True    # 反弹天数过滤开关
    g.reversal_days_filter_max = 20         # 允许的最大反弹天数
    g.enable_reversal_m2_filter = True      # m2 深度过滤开关
    g.reversal_m2_min = 0.15                # m2 下限
    g.reversal_m2_max = 1.0                 # m2 上限

    # ---------- 运行时变量 ----------
    g.rankings_cache = {'date': None, 'data': None}   # 排名缓存
        
    # ---------- 交易调度 ----------
    if g.jiaoyi:
        run_daily(context,etf_sca_list, time='11:00')
    run_daily(context,etf_sell_trade, time='13:18')
    run_daily(context,etf_buy_trade, time='14:45')

    log.info(f"策略初始化完成：ETF池{len(g.etf_pool)}只，动量周期{g.lookback_days}天，持仓{g.holdings_num}只")
    log.info(f"盈利保护开关：{'开启' if g.enable_profit_protection else '关闭'}，回看周期{g.profit_protection_lookback}天，回撤阈值{g.profit_protection_threshold*100:.0f}%，检查时间点：{g.profit_protection_check_times}")
    if g.enable_premium_filter:
        log.info(f"溢价率过滤已启用，阈值：{g.premium_threshold*100:.0f}%")
    else:
        log.info("溢价率过滤未启用")
    log.info("========== 策略初始化完成 ==========")

def before_trading_start(context, data):
    """盘前事件：每日开盘前执行持仓检查"""
    check_positions(context)

def etf_sca_list(context):
    """
    每天11:00执行，更新ETF排名
    """
    log.info("========== 上午预计算得分排名 ==========")

    ranked = get_ranked_etfs(context)
    log.info("=== ETF排名前5 ===")
    for i, m in enumerate(ranked[:5]):
        ann = m.get('annualized_returns', m.get('momentum1', 0))
        r2 = m.get('r_squared', m.get('momentum2', 0))
        log.info(f"排名{i+1}: {m['etf']} {m['etf_name']} 得分{m['score']:.4f} 年化{ann*100:.2f}% R²={r2:.4f}")

def handle_data(context, data):
    """
    每分钟执行一次，用于处理需要在特定时间点触发的操作
    替代 run_daily 定时调度，统一在 handle_data 中通过时间判断执行
    """
    current_dt = context.blotter.current_dt
    current_time = current_dt.strftime('%H:%M')

    if g.jiaoyi:
        # 13:20 判断排名第一的ETF是否处于上涨趋势，是则提前买入
        if current_time == '13:20':
            etf_buy_ifup(context)
        
        if current_time == '13:40':
            etf_buy_ifup(context)

        # 14:00 再次判断上涨趋势，进行买入
        if current_time == '14:00':
            etf_buy_ifup(context)

    # 盈利保护检查（按配置的时间点执行）
    if current_time in g.profit_protection_check_times:
        profit_protection_check(context)

# ==================== 盈利保护独立检查函数 ====================
def profit_protection_check(context):
    """
    独立执行的盈利保护检查函数
    遍历所有持仓，若触发盈利保护则卖出
    """
    if not g.enable_profit_protection:
        log.debug("盈利保护模块已关闭，跳过检查")
        return

    log.info("========== 盈利保护独立检查开始 ==========")
    for sec in list(context.portfolio.positions.keys()):
        if sec not in g.etf_pool:
            continue
        pos = context.portfolio.positions[sec]
        if pos.amount > 0:  #amount 总持仓数量
            if check_profit_protection(sec, context):
                if smart_order_target_value(sec, 0, context):
                    log.info(f"🛡️ 盈利保护 {sec} {get_name(sec)} 待继续卖出")
    log.info("========== 盈利保护独立检查完成 ==========")

# ==================== 盈利保护检查函数（核心逻辑） ====================
def check_profit_protection(security, context, lookback=None, threshold=None):
    """
    检查是否触发盈利保护（从最近N日最高点回撤超过阈值）
    参数:
        security: ETF代码
        context: 上下文
        lookback: 回看天数，默认g.profit_protection_lookback
        threshold: 回撤阈值，默认g.profit_protection_threshold
    返回:
        bool: True表示应触发盈利保护（卖出/排除），False表示安全
    """
    # 若开关关闭，直接返回安全（独立检查函数已在外层判断，但保留此判断以防直接调用）
    if not g.enable_profit_protection:
        return False

    lookback = lookback or g.profit_protection_lookback
    threshold = threshold or g.profit_protection_threshold

    # 获取最近N日的最高价（不包括当天）
    hist = get_history(count=lookback+1, frequency='1d',
            field=['high'], security_list=[security],
            fq='pre', include=True
        ) 

    hist = hist[:-1]
    
    if hist.empty or len(hist) < lookback:
        log.debug(f"{security} {get_name(security)} 历史数据不足{lookback}天，无法检查盈利保护")
        return False

    max_high = hist['high'].max()
    current_price = get_current_data([security])[security].last_price

    if current_price <= max_high * (1 - threshold):
        log.info(f"🔻 {security} {get_name(security)} 触发盈利保护：当前价{current_price:.3f}，最近{lookback}日最高{max_high:.3f}，回撤{(1 - current_price/max_high)*100:.2f}% > {threshold*100:.0f}%")
        return True
    else:
        return False

def get_current_data(stock=None):
    """
    PTrade 兼容聚宽 API：get_current_data()
    实盘使用 get_snapshot，回测使用 get_history

    返回值：一个dict, 其中 key 是股票代码, value 是拥有如下属性的对象
        last_price : 最新价,09:30之前获取返回昨日收盘价
        high_limit: 涨停价
        low_limit: 跌停价
        paused: 是否停牌, 当停牌、未上市或者退市后返回 True
        is_st: 是否是 ST(包括ST, *ST)，是则返回 True，否则返回 False
        day_open: 当天开盘价
        name: 股票现在的名称
    """
    if stock is None:
        security_list = g.etf_pool
    elif isinstance(stock, str):
        security_list = [stock]
    else:
        security_list = list(stock)

    if is_trade():
        return _get_current_data_realtime(security_list)
    else:
        return _get_current_data_backtest(security_list)

def _get_current_data_realtime(security_list):
    """
    实盘：通过 get_snapshot 获取实时行情
    """
    current_data = {}
    try:
        snapshot = get_snapshot(security_list)
    except Exception as e:
        log.warning("get_snapshot 获取失败: %s" % str(e))
        return _get_current_data_backtest(security_list)

    for code in security_list:
        info = snapshot.get(code, {})
        stock_info = {
            'last_price': float(info.get('last_px', 0) or 0),
            'high_limit': float(info.get('up_px', 0) or 0),
            'low_limit': float(info.get('down_px', 0) or 0),
            'day_open': float(info.get('open_px', 0) or 0),
            'paused': info.get('trade_status', 'TRADE') in ('HALT', 'SUSP', 'STOPT', 'SUSPENDED'),
            'is_st': False,
            'name': info.get('name', ''),
        }

        if stock_info['high_limit'] == 0 and stock_info['last_price'] > 0:
            stock_info['high_limit'] = stock_info['last_price'] * 1.1
        if stock_info['low_limit'] == 0 and stock_info['last_price'] > 0:
            stock_info['low_limit'] = stock_info['last_price'] * 0.9

        if 'ST' in stock_info['name'] or '*ST' in stock_info['name'] or '退' in stock_info['name']:
            stock_info['is_st'] = True

        stock_obj = type('StockInfo', (), stock_info)()
        current_data[code] = stock_obj

    return current_data

def _get_current_data_backtest(security_list):
    """
    回测：通过 get_history 获取日线和分钟数据
    """
    current_data = {}

    for code in security_list:
        stock_info = {}

        day_df = get_history(
            count=1,
            frequency='1d',
            field=['close', 'open', 'high', 'low', 'high_limit', 'low_limit', 'is_open', 'preclose'],
            security_list=code,
            fq='pre',
            include=True
        )

        minute_df = get_history(
            count=1,
            frequency='1m',
            field=['price', 'close'],
            security_list=code,
            fq='pre',
            include=False,
            fill='pre'
        )

        if day_df is not None and not day_df.empty:
            row = day_df.iloc[-1]
            stock_info['high_limit'] = float(row.get('high_limit', 0))
            stock_info['low_limit'] = float(row.get('low_limit', 0))
            stock_info['day_open'] = float(row.get('open', 0))
            stock_info['paused'] = (int(row.get('is_open', 1)) == 0)

            if minute_df is not None and not minute_df.empty:
                if 'price' in minute_df.columns:
                    stock_info['last_price'] = float(minute_df['price'].iloc[-1])
                elif 'close' in minute_df.columns:
                    stock_info['last_price'] = float(minute_df['close'].iloc[-1])
                else:
                    stock_info['last_price'] = float(row.get('close', 0))
            else:
                stock_info['last_price'] = float(row.get('close', 0))
        else:
            stock_info['high_limit'] = 0
            stock_info['low_limit'] = 0
            stock_info['day_open'] = 0
            stock_info['last_price'] = 0
            stock_info['paused'] = True

        if stock_info['high_limit'] == 0 and stock_info['last_price'] > 0:
            stock_info['high_limit'] = stock_info['last_price'] * 1.1
        if stock_info['low_limit'] == 0 and stock_info['last_price'] > 0:
            stock_info['low_limit'] = stock_info['last_price'] * 0.9

        stock_info['is_st'] = False
        try:
            info = get_stock_info(code)
            stock_info['name'] = info.get('stock_name', '') if isinstance(info, dict) else ''
        except Exception:
            stock_info['name'] = ''

        if 'ST' in stock_info['name'] or '*ST' in stock_info['name'] or '退' in stock_info['name']:
            stock_info['is_st'] = True

        stock_obj = type('StockInfo', (), stock_info)()
        current_data[code] = stock_obj

    return current_data

# ==================== 溢价率获取函数 ====================
def get_premium_rate(code, max_back_days=5):

    price_data = get_history(count=max_back_days, frequency='1d', field=['close'],
                               security_list=[code], fq='pre', include=True, is_dict=False)
    if price_data.empty:
        log.debug(code + " 无交易价格数据")
        return None, None, None
    price = price_data['close'].iloc[-1]
    nav_df = None
    net_value = None
    if g.jiaoyi:
        try:
            nav_df = get_snapshot(code)
            #log.info(nav_df[code])
            if nav_df is not None:
                net_value = nav_df[code].get('iopv')
                #used_date = nav_df['date'].iloc[-1]
        except Exception:
            net_value = None

        if net_value is None or net_value <= 0:
            try:
                etf_info = get_etf_info(code)
                net_value = etf_info[code]["nav_pre"]   # 前一日净值净值
            except Exception:
                net_value = None

    if net_value is None or net_value<=0:
        log.debug(code + " 无净值数据")
        return None, None, None
    log.info(f"==={code},现价:{price:.4f},净值:{net_value:.4f}===")
    premium_rate = (price - net_value) / net_value
    return premium_rate, price, net_value

# ==================== 核心计算模块 ====================
def get_cached_rankings(context):
    """获取缓存的ETF排名，保证同一交易日内多次调用结果一致"""
    today = context.blotter.current_dt.date()
    if g.rankings_cache['date'] != today:
        log.info("重新计算ETF排名...")
        ranked = get_ranked_etfs(context)
        g.rankings_cache = {'date': today, 'data': ranked}
    else:
        log.debug("使用缓存的ETF排名")
    return g.rankings_cache['data']

def get_ranked_etfs(context):
    """
    根据市场状态选择打分方式：
      市场强（上证指数≥MA60）→ 动量打分
      市场弱（上证指数<MA60）→ V型反转动量打分
    若动量 top1 得分 < 3，则比较动量 top1 与反转 top1 的短期动量，取较高者。
    """
    market_strong = _get_market_strong()
    if market_strong is None:
        log.info("📊 【路径①】市场状态判断失败，默认 market_strong=True，走动量打分")
        market_strong = True  # 数据异常时默认动量打分

    momentum_ranked = _get_ranked_etfs_momentum(context)
    reversal_ranked = get_ranked_etfs_by_reversal(context)

    if market_strong:
        log.info("📊 【路径②】市场强（上证指数 ≥ MA60），使用动量打分，动量top1={} 得分={:.4f}".format(
            momentum_ranked[0]['etf'] + ' ' + momentum_ranked[0]['etf_name'] if momentum_ranked else 'None',
            momentum_ranked[0]['score'] if momentum_ranked else 0))
        top_mom = momentum_ranked[0] if momentum_ranked else None
    else:
        log.info("📊 【路径③】市场弱（上证指数 < MA60），优先使用反转排名")
        if reversal_ranked:
            return reversal_ranked
        # 反转排名为空，回退检查动量 top1 得分 > 3
        top_mom_fb = momentum_ranked[0] if momentum_ranked else None
        if top_mom_fb and top_mom_fb.get('score', 0) > 3:
            log.info(f"🔄 【路径③a】反转排名为空，回退动量排名 top1：{top_mom_fb['etf']} {top_mom_fb['etf_name']} 得分{top_mom_fb['score']:.4f} > 3")
            return momentum_ranked
        log.info("💤 市场弱，反转/动量候选均不可用，保持空仓")
        return []

    # 市场强但动量排名为空（全市场调整日，标的集体触发盈利保护被排除）
    # 回退到反转排名（若有），否则返回空列表触发上层空仓，避免 NoneType 崩溃
    if top_mom is None:
        if reversal_ranked:
            log.info("📊 【路径②b】市场强但动量候选为空，回退使用反转排名")
            return reversal_ranked
        log.info("💤 市场强但动量/反转候选均为空，保持空仓")
        return []
        
    # 市场强且动量 top1 得分 < 3 时，比较短期动量取优
    if top_mom and top_mom.get('score', 0) < 3:
        log.info("⚡ 【路径④】动量top1得分{:.4f}<3，触发对比检查，反转top1={}".format(
            top_mom['score'],
            reversal_ranked[0]['etf'] + ' ' + reversal_ranked[0]['etf_name'] if reversal_ranked else 'None'))
        top_rev = reversal_ranked[0] if reversal_ranked else None
        if top_rev:
            mom_short = top_mom.get('short_annualized', 0)
            rev_short = top_rev.get('short_annualized', 0)
            log.info(f"⚡ 比较短期动量：动量={mom_short*100:.2f}% vs 反转={rev_short*100:.2f}%")
            if rev_short > mom_short:
                log.info(f"🔄 【路径⑤】反转短期动量胜出，最终选用反转排名 top1：{top_rev['etf']} {top_rev['etf_name']}")
                return reversal_ranked
            else:
                log.info(f"📈 【路径⑥】动量短期动量胜出，最终维持动量排名 top1：{top_mom['etf']} {top_mom['etf_name']}")
                return momentum_ranked
        else:
            log.info(f"⚡ 【路径⑦】无反转候选，最终维持动量排名 top1：{top_mom['etf']} {top_mom['etf_name']}")
            return momentum_ranked

    # 动量 top1 得分 >= 3，直接走动量排名
    log.info(f"📈 【路径⑧】动量top1得分{top_mom['score']:.4f}>=3，无需对比，最终使用动量排名 top1：{top_mom['etf']} {top_mom['etf_name']}")
    return momentum_ranked


def _get_ranked_etfs_momentum(context):
    """
    计算所有ETF的动量得分，应用所有过滤条件，返回按得分降序的列表
    """
    etf_metrics = []
    for etf in g.etf_pool:
        # 停牌过滤
        if get_current_data([etf])[etf].paused:
            log.debug(f"{etf} {get_name(etf)} 停牌，跳过")
            continue

        metrics = calculate_momentum_metrics(context, etf)
        if metrics is not None:
            # 得分范围过滤
            if g.min_score_threshold < metrics['score'] < g.max_score_threshold:
                etf_metrics.append(metrics)
            else:
                log.debug(f"{etf} {metrics['etf_name']} 得分{metrics['score']:.2f}超出阈值，过滤")

    etf_metrics.sort(key=lambda x: x['score'], reverse=True)
        # 打印动量排名汇总（便于排查为何无目标ETF）
    if etf_metrics:
        lines = ["──── 动量打分排名（主选）────"]
        lines.append(f"{'排名':<4s} {'代码':<12s} {'名称':<12s} {'得分':>8s} {'年化':>10s} {'R²':>6s} {'短动量':>10s}")
        lines.append("─" * 72)
        for i, m in enumerate(etf_metrics):
            ann = m.get('annualized_returns', 0)
            r2 = m.get('r_squared', 0)
            short = m.get('short_annualized', 0)
            lines.append(f"{i+1:<4d} {m['etf']:<12s} {m['etf_name']:<12s} {m['score']:>8.4f} {ann*100:>9.2f}% {r2:>6.4f} {short*100:>9.2f}%")
        log.info("\n".join(lines))

    return etf_metrics

def calculate_momentum_metrics(context, etf_code):
    """
    计算单只ETF的动量指标，应用所有过滤条件
    返回字典：etf, etf_name, annualized_returns, r_squared, score, current_price, short_annualized
    """
    try:
        name = get_name(etf_code)
        # 获取足够历史数据
        lookback = max(g.lookback_days, g.short_lookback_days) + 20
        prices = get_history(count=lookback + 1, frequency='1d',
            field=['close', 'high'], security_list=[etf_code], 
            fq='pre', include=True )
        prices = prices[:-1]

        current_price = get_current_data([etf_code])[etf_code].last_price
        price_series = np.append(prices["close"].values, current_price)
        
        # ===== 1. 盈利保护检查（排除） =====
        if check_profit_protection(etf_code, context):
            log.info("🚫 " + str(etf_code) + " " + str(name) + " 触发盈利保护，从排名中排除")
            return None
        # ===== 2. 溢价率过滤（提前至排名阶段，获取失败则跳过过滤）=====
        if g.enable_premium_filter:
            premium, _, _ = get_premium_rate(etf_code)
            if premium is not None:
                if premium > g.premium_threshold:
                    log.info("🚫 " + str(etf_code) + " " + str(name) + " 溢价率" + str(premium*100) + "% > " + str(g.premium_threshold*100) + "%，从排名中排除")
                    return None
            else:
                log.debug(str(etf_code) + " " + str(name) + " 无法获取溢价率，跳过溢价率过滤")
        
        # ===== 3. 成交量过滤（排除） =====
        if g.enable_volume_check:
            vol_ratio = get_volume_ratio(context, etf_code)
            if vol_ratio is not None:
                annualized = get_annualized_returns(price_series, g.lookback_days)
                if annualized > g.volume_return_limit:
                    log.info("📉 " + str(etf_code) + " " + str(name) + " 成交量放量" + str(vol_ratio) + "倍，且年化" + str(annualized*100) + "% > 阈值" + str(g.volume_return_limit*100) + "%，过滤")
                    return None

        # ===== 4. 短期动量过滤（排除） =====
        if len(price_series) >= g.short_lookback_days + 1:
            short_return = price_series[-1] / price_series[-(g.short_lookback_days + 1)] - 1
            short_annualized = (1 + short_return) ** (250 / g.short_lookback_days) - 1
        else:
            short_annualized = 0

        if g.use_short_momentum_filter and short_annualized < g.short_momentum_threshold:
            log.debug(str(etf_code) + " " + str(name) + " 短期动量" + str(short_annualized*100) + "% < 阈值" + str(g.short_momentum_threshold*100) + "%，过滤")
            return None

        # ===== 5. 长期动量计算（得分） =====
        recent = price_series[-(g.lookback_days + 1):]
        y = np.log(recent)
        x = np.arange(len(y))
        weights = np.linspace(1, 2, len(y))
        slope, intercept = np.polyfit(x, y, 1, w=weights)
        annualized_returns = math.exp(slope * 250) - 1

         # R²（趋势稳定性）
        ss_res = np.sum(weights * (y - (slope * x + intercept)) ** 2)
        ss_tot = np.sum(weights * (y - np.mean(y)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot != 0 else 0

        score = annualized_returns * (r_squared + 1)/2
        
        # ===== 6. 近3日单日跌幅过滤（排除） =====
        if len(price_series) >= 4:
            day1 = price_series[-1] / price_series[-2]
            day2 = price_series[-2] / price_series[-3]
            day3 = price_series[-3] / price_series[-4]
            if min(day1, day2, day3) < g.loss:
                log.info("⚠️ " + str(etf_code) + " " + str(name) + " 近3日有单日跌幅超" + str((1-g.loss)*100) + "%，直接排除")
                return None

        return {
            'etf': etf_code,
            'etf_name': name,
            'annualized_returns': annualized_returns,
            'r_squared': r_squared,
            'score': score,
            'current_price': current_price,
            'short_annualized': short_annualized,
        }

    except Exception as e:
        log.warning("计算ETF动量指标时出错: " + str(e))
        return None

def get_annualized_returns(price_series, lookback_days):
    """计算加权年化收益率"""
    recent = price_series[-(lookback_days + 1):]
    y = np.log(recent)
    x = np.arange(len(y))
    weights = np.linspace(1, 2, len(y))
    slope, _ = np.polyfit(x, y, 1, w=weights)
    return math.exp(slope * 250) - 1


# ============================================================
# 市场状态判断
# ============================================================
def _get_market_strong():
    """判断市场强弱：上证指数是否在60日均线上方。
    返回 True（市场强，用动量打分）或 False（市场弱，用反转动量打分）。
    """
    try:
        df = get_history(
            count=g.market_ma_lookback + 1,
            frequency='1d',
            field=['close'],
            security_list=[g.market_index],
            fq='pre',
            include=True
        )
        if df is None or df.empty:
            return None
        closes = list(df['close'])
        if len(closes) < g.market_ma_lookback + 1:
            return None
        current_price = closes[-1]
        ma60 = np.mean(closes[:-1])  # 前60日均线（不含今日）
        if ma60 <= 0:
            return None
        return current_price >= ma60
    except Exception as e:
        log.warning(f"市场状态判断异常: {e}")
        return None


# ============================================================
# V型反转动量评分（市场弱时的备选方案）
# ============================================================
def calculate_reversal_momentum(security, prices):
    """计算V型反转动量指标。
    返回 (momentum1, momentum2, days_since_min, days_max_to_min, score) 或 None。
    """
    try:
        if prices is None or len(prices) < 10:
            return None

        close_prices = np.array(prices, dtype=float)
        close_prices = close_prices[close_prices > 0]
        if len(close_prices) < 10:
            return None

        current_price = close_prices[-1]
        if current_price <= 0:
            return None

        # 找最低点（谷底）
        min_idx = np.argmin(close_prices)
        dmin = close_prices[min_idx]

        if dmin <= 0 or min_idx >= len(close_prices) - 1:
            return None

        # 反弹动量
        momentum1 = (current_price - dmin) / dmin

        # 找最低点之前的最高点（下跌起点）
        if min_idx > 0:
            dmax = np.max(close_prices[:min_idx])
            dmax_idx = np.argmax(close_prices[:min_idx])
        else:
            dmax = close_prices[0]
            dmax_idx = 0

        if dmax <= 0:
            return None

        # 下跌深度
        momentum2 = (dmax - dmin) / dmax

        # 反弹天数
        days_since_min = len(close_prices) - 1 - min_idx
        # 下跌天数
        days_max_to_min = min_idx - dmax_idx

        # 评分
        momentum2_x_days = momentum2 * days_max_to_min
        score = (momentum2_x_days - g.m2xd_u_shape_center) ** 2

        # 短期动量
        short_ret = prices[-1] / prices[-(g.short_lookback_days + 1)] - 1 if len(prices) >= g.short_lookback_days + 1 else 0
        short_annualized = (1 + short_ret) ** (250 / g.short_lookback_days) - 1

        return (momentum1, momentum2, days_since_min, days_max_to_min, score, short_annualized)

    except Exception as e:
        log.info(f"【V型反转】{security} 计算异常: {e}")
        return None


def get_ranked_etfs_by_reversal(context):
    """
    使用V型反转动量评分计算ETF排名，应用反转过滤条件。
    返回按得分降序的列表，每项含 etf, etf_name, score, momentum1, momentum2, days_since_min, current_price
    """
    etf_metrics = []
    for etf in g.etf_pool:
        if get_current_data([etf])[etf].paused:
            log.debug(f"{etf} {get_name(etf)} 停牌，跳过")
            continue

        # 获取历史数据（60日）
        df = get_history(
            count=g.reversal_lookback + 1,
            frequency='1d',
            field=['close'],
            security_list=[etf],
            fq='pre',
            include=True
        )
        if df is None or df.empty:
            continue
        df = df[:-1]

        prices = list(df["close"].values)
        current_price = get_current_data([etf])[etf].last_price
        if current_price > 0:
            if not prices or prices[-1] != current_price:
                prices = prices + [current_price]

        if len(prices) < 10:
            continue

        # 近3日跌幅过滤
        if len(prices) >= 4:
            skip = False
            for i in range(1, 4):
                if prices[-i - 1] > 0:
                    daily_ret = prices[-i] / prices[-i - 1]
                    if daily_ret < g.loss:
                        skip = True
                        break
            if skip:
                continue

        result = calculate_reversal_momentum(etf, prices)
        if result is None:
            continue
        momentum1, momentum2, days_since_min, days_max_to_min, score, short_annualized = result

        # 反弹天数过滤
        if g.enable_reversal_days_filter and days_since_min > g.reversal_days_filter_max:
            continue

        # m2深度过滤
        if g.enable_reversal_m2_filter and (momentum2 < g.reversal_m2_min or momentum2 > g.reversal_m2_max):
            continue

        # score 最低阈值
        if score < g.min_reversal_score:
            continue

        etf_metrics.append({
            'etf': etf,
            'etf_name': get_name(etf),
            'score': score,
            'momentum1': momentum1,
            'momentum2': momentum2,
            'days_since_min': days_since_min,
            'days_max_to_min': days_max_to_min,
            'current_price': current_price,
            'short_annualized': short_annualized,
        })

    etf_metrics.sort(key=lambda x: x['score'], reverse=True)

    if etf_metrics:
        lines = ["──── V型反转动量排名（备选）────"]
        lines.append(f"{'排名':<4s} {'代码':<12s} {'名称':<12s} {'得分':>8s} {'m1':>8s} {'m2':>8s} {'反弹天':>6s}")
        lines.append("─" * 66)
        for i, m in enumerate(etf_metrics):
            lines.append(f"{i+1:<4d} {m['etf']:<12s} {m['etf_name']:<12s} {m['score']:>8.4f} {m['momentum1']:>7.2f} {m['momentum2']:>7.2f} {m['days_since_min']:>4d}")
        log.info("\n".join(lines))

    return etf_metrics

def get_today_finished_k_count(current_dt):
    """
    计算 今天 09:30 到 当前时间 已走完的 1分钟K线数量
    :param current_dt: context.blotter.current_dt
    :return: 已走完的K线数量
    """
    today = current_dt.date()
    morning_start = datetime.combine(today, datetime.strptime("09:30", "%H:%M").time())
    morning_end = datetime.combine(today, datetime.strptime("11:30", "%H:%M").time())
    afternoon_start = datetime.combine(today, datetime.strptime("13:00", "%H:%M").time())
    afternoon_end = datetime.combine(today, datetime.strptime("15:00", "%H:%M").time())

    # 当前时间减去1分钟（只算已闭合K线）
    current_dt = current_dt - timedelta(minutes=1)

    if current_dt <= morning_start:
        return 0
    elif morning_start < current_dt <= morning_end:
        return int((current_dt - morning_start).total_seconds() / 60)
    elif morning_end < current_dt <= afternoon_start:
        return 120
    elif afternoon_start < current_dt <= afternoon_end:
        return 120 + int((current_dt - afternoon_start).total_seconds() / 60)
    else:
        return 240

def get_volume_ratio(context, security, lookback=None, threshold=None):
    """计算当日成交量与过去N日均量的比值，若超过阈值则返回比值，否则None"""
    lookback = lookback or g.volume_lookback
    threshold = threshold or g.volume_threshold
    try:
        name = get_name(security)
        hist = get_history(
            count=lookback, frequency='1d',
            field=['volume'], security_list=[security],
            fq='pre', include=False
        ) 
        avg_vol = hist['volume'].mean()

        # 获取当日分钟成交量累计
        current_dt = context.blotter.current_dt

        # 自动计算今天已经走了多少根1分钟K线
        k_count = get_today_finished_k_count(current_dt)
        #log.info(f"【今天已走完的1分钟K线数量】: {k_count}")

        # 直接获取这些K线（完美对应 09:30 ~ 当前-1分钟）
        df_vol = get_history(
            count=k_count,        # 自动算出来的数量
            frequency='1m',
            field=['volume'],
            security_list=[security],
            fq='pre', include=False
        )

        if df_vol is None or df_vol.empty:
            return None
        current_vol = df_vol['volume'].sum()
        ratio = current_vol / avg_vol if avg_vol > 0 else 0
        if ratio > threshold:
            log.debug(f"{security} {name} 成交量比{ratio:.2f} > {threshold}")
            return ratio
        return None
    except Exception as e:
        log.warning(f"成交量计算失败 {security}: {e}")
        return None

# ==================== 卖出模块 ====================
def check_positions(context):
    """每日开盘检查持仓状态，仅用于日志"""
    for sec in context.portfolio.positions:
        pos = context.portfolio.positions[sec]
        if pos.amount > 0:
            log.info(f"📊 持仓：{sec} {get_name(sec)} 数量{pos.amount} 成本{pos.cost_basis:.3f} 现价{pos.last_sale_price:.3f}")

def etf_sell_trade(context):
    """卖出不符合条件的持仓（排名变化、溢价率过高）"""
    log.info("========== 卖出操作开始 ==========")

    ranked = get_cached_rankings(context)
    log.info("=== ETF排名前5 ===")
    for i, m in enumerate(ranked[:5]):
        ann = m.get('annualized_returns', m.get('momentum1', 0))
        r2 = m.get('r_squared', m.get('momentum2', 0))
        log.info(f"排名{i+1}: {m['etf']} {m['etf_name']} 得分{m['score']:.4f} 年化{ann*100:.2f}% R²={r2:.4f}")

    # 确定目标ETF列表（得分前N名且满足得分阈值）
    target_etfs = []
    for m in ranked[:g.holdings_num]:
        if m['score'] >= g.min_score_threshold:
            target_etfs.append(m['etf'])
    # 若没有目标ETF则空仓
    if not target_etfs:
        log.info("💤 无目标ETF，保持空仓")
        return

    target_set = set(target_etfs)

    # 检查是否有持仓需要先卖出（不在目标列表的持仓）
    current_etf_pos = [s for s in context.portfolio.positions if s in g.etf_pool]

    # --- 计算排名第一的ETF今日涨幅 ---
    rank1_today_return = None
    if ranked:
        rank1_etf = ranked[0]['etf']
        rank1_hist = get_history(count=2, frequency='1d', field=['close'],
                                security_list=[rank1_etf], fq='pre', include=True)
        if rank1_hist is not None and len(rank1_hist) >= 2:
            rank1_today_close = get_current_data([rank1_etf])[rank1_etf].last_price
            rank1_yesterday_close = float(rank1_hist['close'].iloc[-2])
            if rank1_yesterday_close > 0:
                rank1_today_return = rank1_today_close / rank1_yesterday_close - 1
                log.info(f"📈 排名第一 {rank1_etf} {get_name(rank1_etf)} 今日涨幅: {rank1_today_return*100:.2f}%")

    # --- 计算持仓股今日涨幅 ---
    held_today_return = {}
    for sec in context.portfolio.positions:
        if sec not in g.etf_pool:
            continue
        pos = context.portfolio.positions[sec]
        if pos.amount <= 0:
            continue
        sec_hist = get_history(count=2, frequency='1d', field=['close'],
                              security_list=[sec], fq='pre', include=True)
        if sec_hist is not None and len(sec_hist) >= 2:
            sec_today_close = get_current_data([sec])[sec].last_price
            sec_yesterday_close = float(sec_hist['close'].iloc[-2])
            if sec_yesterday_close > 0:
                held_today_return[sec] = sec_today_close / sec_yesterday_close - 1

    # 构建排名前3的ETF集合（用于快速查找）
    top3_set = set(m['etf'] for m in ranked[:3])

    # 卖出不在目标列表的持仓（排除满足保留条件的）
    for sec in list(context.portfolio.positions.keys()):
        if sec not in g.etf_pool:
            continue
        if sec not in target_set:
            pos = context.portfolio.positions[sec]
            if pos.amount > 0:
                # 保留条件：排名前3 且 今日涨幅>3% 且 不低于第一名涨幅一个点
                keep = False
                if sec in top3_set and sec in held_today_return and rank1_today_return is not None:
                    sec_ret = held_today_return[sec]
                    if sec_ret > 0.03 and sec_ret >= rank1_today_return - 0.01:
                        keep = True
                        log.info(f"🔒 保留持仓：{sec} {get_name(sec)} 排名前3，今日涨幅{sec_ret*100:.2f}% > 3%，"
                                 f"不低于第一名{rank1_today_return*100:.2f}%一个点")
                if not keep:
                    if smart_order_target_value(sec, 0, context):
                        log.info(f"📤 卖出不在目标的持仓：{sec} {get_name(sec)}")

    log.info("========== 卖出操作完成 ==========")

def etf_buy_ifup(context):
    log.info("==========判断是否尽快买入 ==========")
    ranked = get_cached_rankings(context)
    if not ranked:
        log.info("无ETF排名结果，不执行买入")
        return

    target_etf = ranked[0]['etf']
    if check_intraday_trend(target_etf, context):
        log.info(f"{target_etf} {get_name(target_etf)} 处于上涨趋势，执行买入")
        etf_buy_trade(context)
    else:
        log.info(f"{target_etf} {get_name(target_etf)} 未处于上涨趋势，暂不买入")

# ==================== 买入模块 ====================
def etf_buy_trade(context):
    """买入符合条件的ETF，等权分配，按排名顺序逐个尝试直到凑够持仓数量"""
    log.info("========== 买入操作开始 ==========")

    ranked = get_ranked_etfs(context)
    # 打印排名前5的指标（调试用）
    log.info("=== ETF排名前5 ===")
    for i, m in enumerate(ranked[:5]):
        ann = m.get('annualized_returns', m.get('momentum1', 0))
        r2 = m.get('r_squared', m.get('momentum2', 0))
        log.info(f"排名{i+1}: {m['etf']} {m['etf_name']} 得分{m['score']:.4f} 年化{ann*100:.2f}% R²={r2:.4f}")

    # ---------- 确定目标ETF列表：依次尝试排名靠前的ETF ----------
    target_etfs = []

    for m in ranked:   # 按得分从高到低遍历所有ETF
        if len(target_etfs) >= g.holdings_num:
            break   # 已凑够目标持仓数量
        etf = m['etf']

        # 通过所有检查，加入目标列表
        target_etfs.append(etf)
        log.info(f"🎯 目标ETF {len(target_etfs)}: {etf} {m['etf_name']} 得分{m['score']:.4f}")

    # 检查是否有持仓需要先卖出（不在目标列表的持仓）
    current_etf_pos = [s for s in context.portfolio.positions if s in g.etf_pool]
    to_sell = [s for s in current_etf_pos if s not in target_etfs and context.portfolio.positions[s].amount > 0]
    if to_sell:
        to_sell_names = [get_name(s) for s in to_sell]
        log.info(f"尚有持仓需要卖出：{list(zip(to_sell, to_sell_names))}，等待卖出完成再买入")
        return
        
    # 若没有目标ETF则保持空仓（防止除零错误，与 etf_sell_trade 逻辑对齐）
    # 触发场景：市场弱走反转路径，但反转排名为空（门槛筛光所有标的，熊市常见）
    if not target_etfs:
        log.info("💤 无目标ETF，保持空仓")
        return


    # 等权分配（基于总市值而非现金）
    total_val = context.portfolio.portfolio_value -100 # 容错
    target_per_etf = total_val / len(target_etfs)
    current_price = get_current_data([target_etfs[0]])[target_etfs[0]].last_price if target_etfs else 0
    log.debug(f"【资金分配】总市值={total_val:.2f}, 目标ETF数={len(target_etfs)}, 每份目标={target_per_etf:.2f}, 当前价={current_price:.3f}, 可买股数={int(target_per_etf/current_price)//100*100 if current_price > 0 else 0}")

    for etf in target_etfs:
        current_val = 0
        if etf in context.portfolio.positions:
            pos = context.portfolio.positions[etf]
            if pos.amount > 0:
                current_val = pos.amount * pos.last_sale_price
        if current_val > 0:
            diff_val = current_val - target_per_etf
            if diff_val > target_per_etf * 0.05:
                if smart_order_target_value(etf, target_per_etf, context):
                    log.info(f"📦 调仓卖出：{etf} {get_name(etf)} 卖出后目标金额{target_per_etf:.2f}")
                    continue

        if current_val < target_per_etf * 0.95:
            if smart_order_target_value(etf, target_per_etf, context):
                log.info(f"📦 买入：{etf} {get_name(etf)} 目标金额{target_per_etf:.2f}")

    log.info("========== 买入操作完成 ==========")


# ==================== 辅助函数 ====================
def get_name(security):
    """获取证券名称，带异常处理"""
    try:
        result = get_stock_name(security)
        if isinstance(result, dict):
            return result.get(security, security)
        return result
    except Exception:
        return security

def smart_order_target_value(security, target_value, context):
    """
    智能下单：根据目标市值调整持仓，处理停牌、涨跌停、最小交易金额、T+1
    """
    
    name = get_name(security)
    data = get_current_data([security])
    
    if data[security].paused:
        log.info(f"{security} {name} 停牌，跳过")
        return False

    price = data[security].last_price
    if price == 0:
        log.info(f"{security} {name} 当前价格0，跳过")
        return False
    if math.isnan(price) or math.isinf(price):
        log.info(f"{security} {name} 当前价格{price}无效，跳过")
        return False

    target_amount = int(target_value / price)
    # 按100股整数倍调整
    target_amount = (target_amount // 100) * 100
    if target_amount <= 0 and target_value > 0:
        target_amount = 100

    cur_pos = context.portfolio.positions.get(security, None)
    cur_amount = cur_pos.amount if cur_pos else 0
    diff = target_amount - cur_amount

    # 根据交易方向检查涨跌停
    if diff > 0:  # 买入
        if data[security].last_price >= data[security].high_limit:
            log.info(f"{security} {name} 涨停，跳过买入")
            return False
    elif diff < 0:  # 卖出
        if data[security].last_price <= data[security].low_limit:
            log.info(f"{security} {name} 跌停，跳过卖出")
            return False

    # 最小交易金额检查
    trade_val = abs(diff) * price
    if 0 < trade_val < g.min_money:
        log.info(f"{security} {name} 交易金额{trade_val:.2f} < {g.min_money}，提醒")
        #return False

    # T+1处理
    if diff < 0:
        closeable = cur_pos.enable_amount if cur_pos else 0
        if closeable == 0:
            log.info(f"{security} {name} 当天买入不可卖出")
            return False
        diff = -min(abs(diff), closeable)

    if diff != 0:
        order_result = order(security, diff)
        if order_result:
            log.info(f"{'📥 买入' if diff>0 else '📤 卖出'} {security} {name} 数量{abs(diff)} 价格{price:.3f}")
            return True
        else:
            log.warning(f"下单失败: {security} {name} 数量{diff}")
            return False
    return False

def check_intraday_trend(security, context):
    """
    判断ETF盘中短期趋势
    基于最近N分钟分钟线收盘价的线性回归斜率（归一化处理）
    返回True表示上涨趋势，False表示下跌趋势
    """
    try:
        minute_data = get_history(
            count=g.trend_lookback_minutes,
            frequency='1m',
            field=['close'],
            security_list=[security],
            fq='pre',
            include=False
        )
        if minute_data is None or minute_data.empty:
            log.info(f"【趋势判断】{security} 无分钟数据，默认上涨趋势")
            return True

        closes = minute_data['close'].values
        # 过滤掉价格为0的无效数据（停牌时段）
        closes = closes[closes > 0]
        if len(closes) < 5:
            log.info(f"【趋势判断】{security} 有效分钟数据不足({len(closes)}根)，默认没有上涨趋势")
            return False

        # 线性回归斜率判断趋势方向
        x = np.arange(len(closes))
        slope = np.polyfit(x, closes, 1)[0]

        # 斜率归一化：转为每分钟涨跌幅(%)，消除价格量纲影响，便于跨标的比较
        mean_price = closes.mean()
        slope_pct = slope / mean_price * 100 if mean_price > 0 else 0

        # 归一化斜率 > 阈值 才判定为上涨趋势
        is_uptrend = slope_pct > g.trend_slope_threshold
        trend_desc = "上涨" if is_uptrend else "下跌"
        log.info(f"【趋势判断】{security} 最近{len(closes)}分钟归一化斜率={slope_pct:.6f}%/min (阈值{g.trend_slope_threshold})，判定为{trend_desc}趋势")
        return is_uptrend
    except Exception as e:
        log.info(f"【趋势判断】{security} 异常: {e}，默认上涨趋势")
        return True