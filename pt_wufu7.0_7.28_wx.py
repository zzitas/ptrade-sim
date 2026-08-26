import datetime as dt
import json
import numpy as np
import pandas as pd
import math

STRATEGY_NAME = "五福融合-PTrade"


# ===================== 兼容性辅助函数=====================

def get_batch_hist(stock_list, count, fields, freq='1d', include=False):
    """批量历史行情：逐个获取后按 {code: {field: [values...]}} 组装，兼容PTrade接口。
    每批最多200只，避免单次请求过大。"""
    result = {}
    batch_size = 200
    for i in range(0, len(stock_list), batch_size):
        batch = stock_list[i:i + batch_size]
        try:
            for s in batch:
                try:
                    hist = get_history(count, frequency=freq, field=fields,
                                       security_list=s, fq='pre', include=include)
                    if hist is not None and not hist.empty:
                        out = {}
                        for f in fields:
                            if f in hist.columns:
                                out[f] = list(hist[f])
                        result[s] = out
                except Exception:
                    continue
        except Exception:
            pass
    return result


def _get_realtime_price(security):
    """获取证券实时价格：实盘用快照，回测用最近1分钟收盘价"""
    if is_trade():
        snap = get_snapshot(security)  # 快照dict: {code: {last_px, trade_status, up_px, down_px, ...}}
        if snap and snap.get(security):
            px = snap[security].get('last_px', 0)  # last_px: 最新成交价
            if px > 0:
                return px
    hist = get_history(1, frequency='1m', field=['close'],
                       security_list=security, fq='pre', include=True)
    if hist is not None and not hist.empty:
        if 'close' in hist.columns:
            return float(hist['close'].iloc[-1])
        if 'price' in hist.columns:
            return float(hist['price'].iloc[-1])
    return 0


def _get_realtime_paused(security):
    """判断证券是否停牌：实盘用快照状态，回测默认未停牌"""
    if is_trade():
        snap = get_snapshot(security)
        if snap and snap.get(security):
            status = snap[security].get('trade_status', '')  # trade_status: 交易状态(HALT/SUSP/STOPT=停牌)
            return status in ('HALT', 'SUSP', 'STOPT')
    return False


def _get_realtime_high_limit(security):
    """获取证券涨停价：实盘用快照，回测用历史数据"""
    if is_trade():
        snap = get_snapshot(security)
        if snap and snap.get(security):
            return snap[security].get('up_px', float('inf'))  # up_px: 涨停价
    hist = get_history(1, frequency='1d', field=['high_limit'],
                       security_list=security, fq='pre', include=True)
    if hist is not None and not hist.empty and 'high_limit' in hist.columns:
        return float(hist['high_limit'].iloc[-1])
    return float('inf')


def _get_realtime_low_limit(security):
    """获取证券跌停价：实盘用快照，回测用历史数据"""
    if is_trade():
        snap = get_snapshot(security)
        if snap and snap.get(security):
            return snap[security].get('down_px', 0)  # down_px: 跌停价
    hist = get_history(1, frequency='1d', field=['low_limit'],
                       security_list=security, fq='pre', include=True)
    if hist is not None and not hist.empty and 'low_limit' in hist.columns:
        return float(hist['low_limit'].iloc[-1])
    return 0


def get_security_name(security):
    """获取证券名称，优先从缓存取，缓存未命中则调用 get_stock_info 查询"""
    try:
        if hasattr(g, 'etf_names_dict') and g.etf_names_dict.get(security):
            return g.etf_names_dict[security]
        result = get_stock_info(security)
        name = result.get(security, {}).get('stock_name', '') if isinstance(result, dict) else ''
        if name:
            g.etf_names_dict[security] = name
            return name
        return security
    except Exception:
        return security


def _get_all_etf_list():
    """全市场ETF列表：实盘用 get_etf_list；回测用 get_trend_data 键集（无全市场行情时回退到固定池）。"""
    etf_list = []
    try:
        if is_trade():
            etf_list = get_etf_list()
        else:
            seen = set()
            code_list = list(get_trend_data().keys())
            for code in code_list:
                code_upper = str(code).upper()
                bare = code_upper.replace('.XSHG', '').replace('.XSHE', '').replace('.SS', '').replace('.SZ', '').replace('.SH', '').strip()
                if not bare.startswith(('159', '51', '52', '56', '58')):
                    continue
                if bare.startswith(('51', '52', '56', '58')):
                    normalized = bare + '.SS'
                elif bare.startswith('159'):
                    normalized = bare + '.SZ'
                else:
                    continue
                if normalized not in seen:
                    seen.add(normalized)
                    etf_list.append(normalized)
    except Exception:
        etf_list = list(set(g.global_etf_pool + g.china_etf_pool))
    for code in etf_list:
        if code not in g.etf_names_dict:
            try:
                result = get_stock_info(code)
                name = result.get(code, {}).get('stock_name', '') if isinstance(result, dict) else ''
                g.etf_names_dict[code] = name if name else code
            except Exception:
                g.etf_names_dict[code] = code
    return etf_list


def _get_hs300_stocks():
    """沪深300成分股（Regime P0 宽度计算用）。"""
    try:
        return list(get_index_stocks('000300.SS'))
    except Exception:
        try:
            return list(get_index_stocks('000300.XSHG'))
        except Exception:
            return []


def record(**kwargs):
    """PTrade 无原生 record（聚宽为绘图用），此处仅记录日志，不影响交易逻辑。"""
    try:
        log.info("[record] " + json.dumps(kwargs, ensure_ascii=False))
    except Exception:
        pass


# ===================== 参数（对应聚宽 initialize 的全局变量区）=====================

def set_params():
    """初始化全局参数：ETF池、走弱期判断、持仓数量、动量计算、过滤器开关、风控阈值等"""
    g.global_etf_pool = [  # 全球/海外ETF池：黄金、美股、港股、恒生等（走弱期使用）
        '518880.SS', '501018.SS', '161226.SZ', '159985.SZ',
        '159980.SZ', '513310.SS', '159518.SZ', '159509.SZ',
        '513100.SS', '513520.SS', '513500.SS', '159502.SZ',
        '513400.SS', '513030.SS', '513290.SS', '520830.SS',
        '159529.SZ',
    ]
    g.china_etf_pool = [  # 国内ETF池：A股行业ETF（正常期使用）
        '513090.SS', '513120.SS', '513180.SS', '513330.SS',
        '513750.SS', '159892.SZ', '513190.SS', '159605.SZ',
        '513630.SS', '159323.SZ', '510900.SS', '513920.SS',
        '513970.SS', '511380.SS', '512050.SS', '510500.SS',
        '159915.SZ', '510300.SS', '512100.SS', '159949.SZ',
        '588080.SS', '159967.SZ', '588220.SS', '563300.SS',
        '510760.SS', '588200.SS', '515880.SS', '159981.SZ',
        '512880.SS', '513350.SS', '159326.SZ', '159516.SZ',
        '159206.SZ', '512480.SS', '159363.SZ', '159870.SZ',
        '512400.SS', '159755.SZ', '588170.SS', '159992.SZ',
        '159995.SZ', '512890.SS', '515220.SS', '159566.SZ',
        '159819.SZ', '512800.SS', '512690.SS', '515050.SS',
        '562500.SS', '512170.SS', '517520.SS', '159869.SZ',
        '512070.SS', '159611.SZ', '562800.SS', '515120.SS',
        '512010.SS', '510880.SS', '515790.SS', '515980.SS',
        '512660.SS', '159928.SZ', '512710.SS', '560860.SS',
        '515030.SS', '159766.SZ', '159218.SZ', '159852.SZ',
        '516160.SS', '516150.SS', '159227.SZ', '159583.SZ',
        '588790.SS', '159865.SZ', '512980.SS', '159851.SZ',
        '561360.SS', '561980.SS', '562590.SS', '512200.SS',
        '159732.SZ', '159667.SZ', '516510.SS', '159840.SZ',
        '159998.SZ', '159825.SZ', '512670.SS', '159883.SZ',
        '515210.SS', '515400.SS', '159256.SZ', '561330.SS',
        '515170.SS', '159638.SZ', '516520.SS', '513360.SS',
        '516190.SS',
    ]
    g.fixed_etf_pool = g.global_etf_pool + g.china_etf_pool  # 固定池 = 全球池 + 国内池

    # ---- ETF池（动态更新） ----
    g.avg_etf_money_threshold = None  # 流动性门槛（元）：近3日日均总成交额 / 阈值除数
    g.filtered_fixed_pool = []        # 固定池经流动性过滤后的结果
    g.dynamic_etf_pool = []           # 动态池：全市场ETF按行业分组取Top N
    g.merged_etf_pool = []            # 合并池 = 过滤后固定池 ∪ 动态池
    g.ranked_etfs_result = []         # 动量排序后的最终目标ETF列表
    g.filtered_global_pool = []       # 走弱期经流动性过滤后的全球池

    # ---- 走弱期判断 ----
    g.is_a_share_weak = False         # 当前是否处于大A走弱期
    g.weak_period_ma_lookback = 10    # 走弱期判断使用的均线天数
    g.weak_start_date = None          # 走弱期开始日期
    g.weak_days_count = 0             # 走弱期已持续交易日数
    g.max_weak_days = 20              # 走弱期最大持续天数（超过则强制退出）
    g.weak_confirm_days = 1           # 进入/退出走弱期需连续确认的天数
    g.weak_enter_streak = 0           # 连续满足进入条件的天数计数器
    g.weak_exit_streak = 0            # 连续满足退出条件的天数计数器

    # ---- 持仓与交易 ----
    g.holdings_num = 1                # 目标持仓ETF数量
    g.defensive_etf = "511880.SS"     # 防御ETF（货币ETF，无目标时持有）
    g.defensive_etf_backups = [       # 防御ETF备选列表（按优先级）
        "511880.SS", "511990.SS", "511660.SS", "511810.SS",
    ]
    g.min_money = 10                  # 最小交易金额（元）
    g.target_etfs_list = []           # 当日目标持仓ETF列表
    g.pending_buy_etfs = []           # 待买入ETF队列（等待趋势确认）
    g.etf_names_dict = {}             # ETF名称缓存 {code: name}
    g.cache_date = None               # 当前日期（用于缓存失效判断）
    g.yesterday_close_cache = {}      # 昨收价缓存 {code: price}（分钟级止损用）

    # ---- 日内趋势判断 ----
    g.trend_lookback_minutes = 30     # 趋势判断回看分钟数
    g.trend_slope_threshold = 0.001   # 趋势斜率阈值（%/分钟）
    g.trend_r2_threshold = 0.3        # 趋势R²阈值（趋势质量）

    # ---- 动量计算 ----
    g.lookback_days = 25              # 动量计算回看天数（正常期）
    g.min_score_threshold = 0         # 动量得分下限（过滤负收益）
    g.max_score_threshold = 5         # 动量得分上限（过滤过热）
    g.score_threshold_ratio = 0.9     # 候选池得分阈值比例（第N名得分×此比例）

    # ---- 过滤器开关与参数 ----
    g.enable_r2_filter = True         # R²过滤器开关（正常期）
    g.r2_threshold = 0.4              # R²阈值（趋势稳定性）
    g.enable_ma_filter = True         # 均线过滤器开关（走弱期）
    g.ma_lookback = 10                # 均线回看天数
    g.ma_threshold = 1.0              # 均线阈值（价格/MA比例）
    g.enable_volume_check = False     # 成交量过滤器开关
    g.volume_lookback = 5             # 量比回看天数
    g.volume_threshold = 1.8          # 量比上限（过高则剔除）
    g.enable_loss_filter = True       # 短期风控过滤器开关
    g.loss = 0.97                     # 短期风控阈值（近3日跌幅<3%）
    g.enable_premium_filter = False   # 溢价率过滤器开关
    g.max_premium_rate = 30           # 溢价率上限（%）
    g.enable_laplace_filter = False   # 拉普拉斯滤波器开关
    g.laplace_s_param = 0.05          # 拉普拉斯平滑参数
    g.laplace_min_slope = 0.002       # 拉普拉斯斜率下限
    g.dynamic_pool_top_n = 150        # 动态池Top N数量
    g.liquidity_threshold_divisor = 15000  # 流动性阈值除数

    # ---- 回撤监控 ----
    g.max_portfolio_value = 0         # 历史最高净值
    g.drawdown_threshold = 0.03       # 回撤预警阈值（3%）
    g.drawdown_records = []           # 回撤记录列表

    # ---- 分钟级止损 ----
    g.use_fixed_stop_loss = False     # 固定止损开关（成本价×95%）
    g.fixedStopLossThreshold = 0.95   # 固定止损阈值
    g.use_pct_stop_loss = False       # 百分比止损开关（昨收价×95%）
    g.pct_stop_loss_threshold = 0.95  # 百分比止损阈值

    # ---- B型阶梯主线 ----
    g.enable_super_mainline = True    # B型主线评估开关
    g.mainline_score_min = 5.0        # 主线得分下限
    g.mainline_score_max = 20.0       # 主线得分上限（超过则触发持仓延续判断）
    g.mainline_days = 5               # 主线评估连续天数
    g.mainline_min_r2 = 0.85          # 主线当前R²下限
    g.mainline_min_r2_avg = 0.90      # 主线R²均值下限
    g.mainline_min_volume_avg = 1.8   # 主线量比均值下限
    g.mainline_min_score_up_days = 4  # 主线得分抬升天数下限（5天中至少4天抬升）
    g.mainline_min_positive_laplace_days = 5  # 主线拉普拉斯斜率为正的天数下限
    g.mainline_min_score_growth = 2.0 # 主线得分增长倍数下限

    # ---- B型主线持仓延续 ----
    # 已经被 B 型主线买入的 ETF, 若 score 突破 mainline_score_max 而原版又拒绝
    # (score > max_score_threshold=5), 默认会被强制踢出. 持仓延续规则避免这种
    # "主升浪正酣却被迫换仓"的情况.
    g.enable_mainline_retain = True   # 持仓延续开关（得分突破上限但趋势仍好则继续持有）
    g.mainline_retain_min_r2 = 0.85   # 持仓延续R²下限
    g.mainline_retain_min_lap_slope = 0.0  # 持仓延续拉普拉斯斜率下限

    # ---- Regime P0 市场状态分类 ----
    g.enable_regime_p0 = True         # Regime P0开关
    g.regime_breadth_ma = 20          # 宽度计算使用的均线天数
    g.regime_breadth_high = 0.55      # 宽度高阈值（≥此值→NORMAL）
    g.regime_breadth_structural = 0.50  # 宽度结构性阈值（趋势弱+宽度≥此值→STRUCTURAL）
    g.regime_breadth_low = 0.35       # 宽度低阈值（<此值→DEFENSIVE）
    g.regime_liquidity_min_yi = 20000.0  # 流动性下限（亿元），低于则→DEFENSIVE
    g.regime_liquidity_lookback = 20  # 流动性回看天数
    g.regime_p0_log = []              # Regime P0日志记录

    # ---- 震荡市量价背离 ----
    g.enable_choppy_detection = True  # 震荡市检测开关
    g.choppy_lookback = 10            # 震荡市回看天数
    g.choppy_max_ret = 0.010          # 震荡市涨跌幅阈值（1%内视为震荡）
    g.is_choppy = False               # 当前是否处于震荡市
    g.enable_volume_divergence_filter = True  # 量价背离过滤器开关
    g.vd_lookback = 5                 # 量价背离回看天数
    g.vd_price_up_threshold = 0.02    # 价格上涨阈值（2%）
    g.vd_vol_down_threshold = -0.10   # 成交量萎缩阈值（-10%）

    # ---- H72 动态走弱动量窗口 ----
    g.weak_momentum_lookback = 25     # 当前走弱期动量回看天数（动态切换25↔23）
    g.weak_momentum_lookback_base = 25  # 基础回看天数
    g.weak_momentum_lookback_short = 23  # 缩短回看天数（R²高时启用，更灵敏）
    g.enable_dynamic_weak_lookback = True  # 动态窗口开关
    g.r2_lookback_for_signal_quality = 25  # R²信号质量评估回看天数
    g.r2_threshold_for_signal_quality = 0.4  # R²高阈值（连续N天>此值→缩短窗口）
    g.r2_threshold_exit = 0.38        # R²退出阈值（连续N天<此值→恢复窗口）
    g.r2_hysteresis_enter_days = 2    # R²进入滞后天数（需连续N天确认）
    g.r2_hysteresis_exit_days = 2     # R²退出滞后天数
    g.r2_signal_aggregation = "mean"  # R²聚合方式（mean/median）
    g.r2_dynamic_tag = "H72"          # 动态窗口标签（日志用）
    g.r2_high_streak = 0              # R²连续高值天数计数器
    g.r2_low_streak = 0               # R²连续低值天数计数器
    g.r2_dyn_days_23 = 0              # 使用23天窗口的累计天数
    g.r2_dyn_days_25 = 0              # 使用25天窗口的累计天数
    g.r2_dyn_switch_count = 0         # 窗口切换次数计数器

    # ---- H78a 走弱期 R² 过滤 ----
    g.enable_weak_r2_filter = True    # 走弱期R²过滤器开关
    
    g.sold_securities_today = set()   # 今日已卖出证券集合（避免重复卖出）

def set_backtest():
    """回测/交易成本与滑点设置。"""
    if not is_trade():
        set_limit_mode('UNLIMITED')
        set_commission(commission_ratio=0.0001, min_commission=5.0)
        set_slippage(0.0001)
# ===================== 初始化与事件入口 =====================

def initialize(context):
    """策略初始化：设置参数、回测配置、初始化全局变量、注册定时任务"""
    # PTrade 日志兼容：确保 log.warning 存在（部分环境仅有 info/error/debug，无 warning 别名）
    if not hasattr(log, 'warning'):
        try:
            log.warning = log.info
        except Exception:
            pass
    set_params()
    set_backtest()
    #g.cache_date = None               # 当前日期（用于缓存失效判断）
    #g.yesterday_close_cache = {}      # 昨收价缓存（分钟级止损用）
    #g.ranked_etfs_result = []         # 动量排序后的ETF结果
    #g.target_etfs_list = []           # 当日目标持仓ETF
    #g.pending_buy_etfs = []           # 待买入ETF队列
    #g.sold_securities_today = set()   # 今日已卖出证券集合（避免重复卖出）
    #g.drawdown_records = []           # 回撤记录
    #g.max_portfolio_value = 0         # 历史最高净值
    #g.etf_names_dict = {}             # ETF名称缓存
    #g.filtered_global_pool = []       # 过滤后的全球ETF池
    #g.filtered_fixed_pool = []        # 过滤后的固定ETF池
    #g.dynamic_etf_pool = []           # 动态ETF池
    #g.merged_etf_pool = []            # 合并ETF池
    #g.regime_p0_log = []              # Regime P0日志
    #g.is_choppy = False               # 是否处于震荡市
    #g.is_a_share_weak = False         # 是否处于大A走弱期
    log.info("【五福融合-PTrade】择时执行 + opt2_v4 + H72/H78a + P-5 5检查点择时 启动！")
    log.info(f"""
【策略参数初始化完成】
=== ETF池配置 ===
- 全球/海外ETF池: {len(g.global_etf_pool)}只
- 国内ETF池: {len(g.china_etf_pool)}只
- 固定池合计: {len(g.fixed_etf_pool)}只
=== 大A走弱期判定 ===
- MA均线周期: {g.weak_period_ma_lookback}日
- 进入条件: 至少3/4指数低于MA{g.weak_period_ma_lookback}
- 退出条件: 至少3/4指数站上MA{g.weak_period_ma_lookback}
- 最长持续: {g.max_weak_days}个交易日
=== 动量得分过滤 ===
- 周期: {g.lookback_days}天
- 得分阈值: [{g.min_score_threshold}, {g.max_score_threshold}]
- 调仓系数: {g.score_threshold_ratio}
=== 过滤条件 ===
- 正常期 R²过滤: {'启用' if g.enable_r2_filter else '禁用'} (阈值>{g.r2_threshold:.1f})
- 走弱期 均线过滤: {'启用' if g.enable_ma_filter else '禁用'} (MA{g.ma_lookback}×{g.ma_threshold})
- 通用 成交量过滤: {'启用' if g.enable_volume_check else '禁用'} (近{g.volume_lookback}日均量比<{g.volume_threshold:.1f})
- 通用 短期风控: {'启用' if g.enable_loss_filter else '禁用'} (近3日单日跌幅<{1-g.loss:.0%})
- 通用 溢价率过滤: {'启用' if g.enable_premium_filter else '禁用'} (阈值≤{g.max_premium_rate}%)
- 通用 拉普拉斯滤波: {'启用' if g.enable_laplace_filter else '禁用'} (s={g.laplace_s_param}, 斜率≥{g.laplace_min_slope})
=== 止损机制 ===
- 分钟级固定比例止损: {'启用' if g.use_fixed_stop_loss else '禁用'} (成本价×{g.fixedStopLossThreshold:.0%})
- 分钟级当日跌幅止损: {'启用' if g.use_pct_stop_loss else '禁用'} (昨收×{g.pct_stop_loss_threshold:.0%})
=== B型阶梯主线 (放宽版) ===
- 启用: {'是' if g.enable_super_mainline else '否'} | score区间({g.mainline_score_min},{g.mainline_score_max}]
- 近{g.mainline_days}日: R²当前≥{g.mainline_min_r2}, R²均值≥{g.mainline_min_r2_avg}, 量比均值≥{g.mainline_min_volume_avg}
- 近{g.mainline_days}日: score抬升天数≥{g.mainline_min_score_up_days}/{g.mainline_days-1}, 拉普拉斯斜率为正天数≥{g.mainline_min_positive_laplace_days}/{g.mainline_days}
- 近{g.mainline_days}日: score增长倍数≥{g.mainline_min_score_growth}
- 第一步打分行后会追加 [主线诊断] 行, 显示每只 score>5 ETF 卡在哪个条件
=== B型主线持仓延续 ===
- 启用: {'是' if getattr(g, 'enable_mainline_retain', False) else '否'} | 触发条件: 当前持仓 + score>{g.mainline_score_max}
- 保留条件: R²≥{g.mainline_retain_min_r2}, 拉普拉斯斜率>{g.mainline_retain_min_lap_slope}, 其余 (loss/premium/弱市MA) 仍生效
=== 其他配置 ===
- 持仓数量: {g.holdings_num}只
- 防御ETF: {g.defensive_etf} (备选: {', '.join(g.defensive_etf_backups[1:])})
- 最小交易额: {g.min_money}元
- 基准: 510300.XSHG
=== v1.2 改造 ===
- S-1: 滑点 0.01%→0.1% | 贴近实盘真实滑点
- S-2: 走弱期延迟确认 {g.weak_confirm_days}天 | 避免单日噪声频繁切换
- S-3: choppy阈值 {g.choppy_max_ret:.3f} | 备选0.015(opt2v3)
- S-4: 日内趋势加成交量验证 | 缩量(量比<0.8)视为假突破不买入
- S-5: 防御ETF备选池 {len(g.defensive_etf_backups)}只 | 主ETF不可用时自动切换
=== v1.7 改造 ===
- P-5: 日内择时增加5检查点(13:40/14:00/14:10/14:30/14:40) | 原3点→5点，降低13:10拥挤
""")
    # 定时任务注册
    run_daily(context, check_weak_period_daily, time='09:40')  # 走弱期判断+池更新
    run_daily(context, compute_regime_p0_daily, time='11:30')  # Regime P0市场状态
    run_daily(context, force_buy_pending, time='14:55')        # 尾盘强制买入
    run_daily(context, reset_daily_flags, time='15:10')        # 收盘重置状态


def before_trading_start(context, data):
    """盘前事件：每日开盘前执行晨间流水线"""
    log.info("【before_trading_start】")
    morning_routine(context)
    log.info("【before_trading_start】 morning_routine 完成")


def handle_data(context, data):
    """每分钟事件：分钟级止损 + 按时间触发下午卖出/买入/趋势复检"""
    # 对应聚宽 run_daily(..., 'every_bar')：分钟级止损
    minute_level_stop_loss(context)
    minute_level_pct_stop_loss(context)

    # 按时间触发下午例行任务（原 run_daily 调度）
    current_time = context.blotter.current_dt.strftime('%H:%M')  # 当前时间 HH:MM
    if current_time == '13:10':
        afternoon_sell_routine(context)  # 13:10 执行卖出
    elif current_time == '13:15':
        afternoon_buy_routine(context)   # 13:15 执行买入（间隔5分钟）
    elif current_time in ('13:40', '14:00', '14:10', '14:30', '14:40'):
        check_pending_buys_trend(context)  # 定时复检待买ETF趋势


def after_trading_end(context, data):
    """盘后事件：每日收盘后执行"""
    log.info("【after_trading_end】")


# ===================== 各流程函数 =====================

def check_weak_period_daily(context):
    """每日09:40执行：判断大A走弱期 + 震荡市检测 + 池更新"""
    check_a_share_weak_period(context)
    if getattr(g, 'enable_choppy_detection', False):
        check_choppy_market(context)
    midday_routine(context)


def check_choppy_market(context):
    """震荡市检测：4大指数近10日涨跌幅绝对值<1%的≥3个则进入震荡模式"""
    if not getattr(g, 'enable_choppy_detection', False):
        return
    indexes = ['000300.SS', '399101.SZ', '399006.SZ', '000510.SS']
    choppy_count = 0
    details = []
    for code in indexes:
        try:
            df = get_history(g.choppy_lookback + 1, frequency='1d', field=['close'],
                             security_list=code, fq='pre', include=False)
            if df is None or len(df) < g.choppy_lookback + 1:
                details.append(f"{code}:数据不足")
                continue
            closes = df['close'].values
            ret_10d = float(closes[-1] / closes[0] - 1)
            details.append(f"{code}:{ret_10d:+.2%}")
            if abs(ret_10d) < g.choppy_max_ret:
                choppy_count += 1
        except Exception:
            details.append(f"{code}:异常")
    was_choppy = bool(getattr(g, 'is_choppy', False))
    g.is_choppy = (choppy_count >= 3)
    if g.is_choppy and not was_choppy:
        log.info(f"🟡 【震荡市检测】{choppy_count}/4 指数近10日涨跌幅<{g.choppy_max_ret:.0%}，进入震荡模式 | {', '.join(details)}")
    elif not g.is_choppy and was_choppy:
        log.info(f"🟢 【震荡市检测】退出震荡模式 | {', '.join(details)}")


def check_volume_price_divergence(hist_closes, hist_volumes, context):
    """量价背离过滤：近N日价格上涨但成交量萎缩则判定为背离，震荡市专用"""
    if not getattr(g, 'enable_volume_divergence_filter', False):
        return True, {'reason': 'disabled'}
    if hist_closes is None or hist_volumes is None:
        return True, {'reason': 'no_data'}
    if len(hist_closes) < g.vd_lookback + 1 or len(hist_volumes) < g.vd_lookback + 1:
        return True, {'reason': 'insufficient_data'}
    try:
        price_change = float(hist_closes[-1] / hist_closes[-g.vd_lookback - 1] - 1)
        recent_vol = float(np.mean(hist_volumes[-3:]))
        earlier_vol = float(np.mean(hist_volumes[-g.vd_lookback - 1:-3]))
        if earlier_vol <= 0:
            return True, {'reason': 'earlier_vol_zero'}
        vol_change = float(recent_vol / earlier_vol - 1)
        is_divergence = (price_change > g.vd_price_up_threshold and vol_change < g.vd_vol_down_threshold)
        return (not is_divergence), {
            'price_change': price_change,
            'vol_change': vol_change,
            'is_divergence': is_divergence,
            'reason': 'divergence' if is_divergence else 'ok'
        }
    except Exception:
        return True, {'reason': 'error'}


def morning_routine(context):
    """盘前例行：持仓检查 → 回撤监控 → 流动性阈值计算"""
    log.info("★" * 80)
    log.info("▶️ 【晨间流水线】启动...")
    log.info("【持仓检查】检查当前持仓状态...")
    check_positions(context)
    log.info("【回撤监控】监控策略回撤...")
    monitor_drawdown(context)
    log.info("【流动性阈值】计算全市场ETF流动性阈值...")
    calculate_global_etf_threshold(context)
    log.info("⏸️ 【晨间流水线】执行完毕！")


def midday_routine(context):
    """早盘09:40例行：走弱期仅过滤全球池；正常期执行动态池+固定池+合并池"""
    log.info("★" * 80)
    log.info("▶️ 【早盘流水线】启动...")
    if g.is_a_share_weak:
        log.info(f"🔴 【走弱期池更新】仅对全球/海外ETF池进行流动性过滤...")
        filter_global_pool_by_volume(context)
        log.info(f"【走弱期池更新完成】过滤后全球池: {len(g.filtered_global_pool)}只")
    else:
        log.info(f"🟢 【正常期池更新】执行动态池更新、固定池过滤、合并池...")
        log.info("【动态池更新】更新行业ETF动态池（各行业流动性最佳ETF）...")
        update_sector_pool(context)
        log.info("【固定池过滤】过滤固定ETF池流动性...")
        filter_fixed_pool_by_volume(context)
        log.info("【合并池】合并固定池与动态池...")
        daily_merge_etf_pools(context)
        log.info(f"【正常期池更新完成】合并池: {len(g.merged_etf_pool)}只")
    log.info("⏸️ 【早盘流水线】执行完毕！")


def afternoon_sell_routine(context):
    """午盘卖出模块：池更新 + 动量计算 + 卖出"""
    log.info("▶️ 【午盘卖出流水线】启动...")
    if g.is_a_share_weak:
        if hasattr(g, 'filtered_global_pool') and g.filtered_global_pool:
            g.merged_etf_pool = list(set(g.filtered_global_pool))
        else:
            g.merged_etf_pool = list(set(g.global_etf_pool))
        g.merged_etf_pool.sort()
        log.info(f"🔴 【大A走弱期】使用过滤后全球/海外ETF池，共{len(g.merged_etf_pool)}只")
    else:
        log.info(f"🟢 【大A正常期】使用合并池，共{len(g.merged_etf_pool)}只")
    log.info("【动量计算】计算ETF动量得分与排序...")
    calculate_and_log_ranked_etfs(context)
    log.info("【卖出执行】执行卖出操作...")
    execute_sell_trades(context)
    log.info("⏸️ 【午盘卖出流水线】执行完毕！")


def afternoon_buy_routine(context):
    """午盘买入模块：间隔5分钟后执行买入"""
    log.info("▶️ 【午盘买入流水线】启动...")
    log.info("【买入执行】执行买入操作...")
    execute_buy_trades(context)
    log.info("⏸️ 【午盘买入流水线】执行完毕！")


def reset_daily_flags(context):
    """15:10收盘重置：清空缓存、待买队列、防御ETF、已卖记录"""
    # 诊断：打印当日收盘持仓，确认卖出订单是否真正落地（排查「已卖仍持仓」）
    try:
        end_positions = {s: p.amount for s, p in context.portfolio.positions.items() if p.amount > 0}
        log.info(f"【收盘持仓诊断】{end_positions}")
    except Exception:
        pass
    g.cache_date = None
    g.yesterday_close_cache = {}
    g.pending_buy_etfs = []
    g.defensive_etf = "511880.SS"
    g.sold_securities_today = set()
    log.info("🔄 收盘缓存重置完成")


# ===================== R²动态走弱动量窗口 H72 =====================

def adjust_weak_momentum_lookback(context):
    """H72动态窗口：根据全球ETF池R²均值动态切换动量回看窗口（25↔23天）"""
    if not getattr(g, "enable_dynamic_weak_lookback", False):
        return
    try:
        etf_pool = g.global_etf_pool
        if not etf_pool:
            return
        lookback_days = g.r2_lookback_for_signal_quality
        r2_values = []
        for etf in etf_pool:
            try:
                df = get_history(lookback_days + 1, frequency='1d', field=['close'],
                                 security_list=etf, fq='pre', include=False)
                if df is None or df.empty or len(df) < lookback_days + 1:
                    continue
                price_series = df['close'].values
                y = np.log(price_series)
                x = np.arange(len(y))
                weights = np.linspace(1, 2, len(y))
                W = weights ** 2
                W_sum = np.sum(W)
                x_bar = np.sum(W * x) / W_sum
                y_bar = np.sum(W * y) / W_sum
                dx = x - x_bar
                dy = y - y_bar
                variance_x = np.sum(W * dx ** 2)
                if variance_x == 0:
                    continue
                slope = np.sum(W * dx * dy) / variance_x
                intercept = y_bar - slope * x_bar
                y_pred = slope * x + intercept
                ss_res = np.sum(weights * (y - y_pred) ** 2)
                ss_tot = np.sum(weights * (y - np.mean(y)) ** 2)
                r_squared = 1 - ss_res / ss_tot if ss_tot else 0
                r2_values.append(r_squared)
            except Exception:
                continue
        if not r2_values:
            return

        agg = getattr(g, "r2_signal_aggregation", "mean")
        if agg == "median":
            pool_r2 = float(np.median(r2_values))
        else:
            pool_r2 = float(np.mean(r2_values))
        thr_hi = g.r2_threshold_for_signal_quality
        thr_lo = getattr(g, "r2_threshold_exit", 0.38)
        need_enter = int(getattr(g, "r2_hysteresis_enter_days", 2))
        need_exit = int(getattr(g, "r2_hysteresis_exit_days", 2))
        tag = getattr(g, "r2_dynamic_tag", "H72")

        if pool_r2 > thr_hi:
            g.r2_high_streak = getattr(g, "r2_high_streak", 0) + 1
            g.r2_low_streak = 0
        elif pool_r2 < thr_lo:
            g.r2_low_streak = getattr(g, "r2_low_streak", 0) + 1
            g.r2_high_streak = 0
        else:
            g.r2_high_streak = 0
            g.r2_low_streak = 0

        old_lookback = g.weak_momentum_lookback
        new_lookback = old_lookback
        reason = "hold"
        if old_lookback == g.weak_momentum_lookback_base and g.r2_high_streak >= need_enter:
            new_lookback = g.weak_momentum_lookback_short
            reason = "enter_23"
        elif old_lookback == g.weak_momentum_lookback_short and g.r2_low_streak >= need_exit:
            new_lookback = g.weak_momentum_lookback_base
            reason = "exit_23"

        switched = new_lookback != old_lookback
        if switched:
            g.weak_momentum_lookback = new_lookback
            g.r2_dyn_switch_count = getattr(g, "r2_dyn_switch_count", 0) + 1

        if g.weak_momentum_lookback == g.weak_momentum_lookback_short:
            g.r2_dyn_days_23 = getattr(g, "r2_dyn_days_23", 0) + 1
        else:
            g.r2_dyn_days_25 = getattr(g, "r2_dyn_days_25", 0) + 1

        if g.is_a_share_weak or switched:
            log.info(
                f"[R2动态{tag}] date={context.blotter.current_dt.date()} weak={int(g.is_a_share_weak)} "
                f"pool_r2={pool_r2:.4f} agg={agg} hi={g.r2_high_streak}/{need_enter} "
                f"lo={g.r2_low_streak}/{need_exit} reason={reason} "
                f"lb={g.weak_momentum_lookback} switched={int(switched)} "
                f"d23={getattr(g, 'r2_dyn_days_23', 0)} d25={getattr(g, 'r2_dyn_days_25', 0)} "
                f"sw={getattr(g, 'r2_dyn_switch_count', 0)}"
            )
            try:
                record(r2_avg=pool_r2, r2_weak_lb=float(g.weak_momentum_lookback))
            except Exception:
                pass
    except Exception as e:
        log.info(f"[R2动态{tag}] adjust 异常: {e}")


def check_positions(context):
    """盘前持仓检查：打印持仓数量、成本、实时价格，标记停牌标的"""
    for security in context.portfolio.positions:
        position = context.portfolio.positions[security]
        if position.amount > 0:
            security_name = get_security_name(security)
            log.info(f"📊 【持仓检查】{security} {security_name}, 数量: {position.amount}, 成本: {position.cost_basis:.3f}, 当前价: {_get_realtime_price(security):.3f}")
            if _get_realtime_paused(security):
                log.info(f"⚠️ {security} {security_name} 今日停牌")


def monitor_drawdown(context):
    """回撤监控：更新最高净值，回撤超阈值时记录预警"""
    try:
        current_value = context.portfolio.portfolio_value
        if current_value > g.max_portfolio_value:
            g.max_portfolio_value = current_value
        if g.max_portfolio_value > 0:
            current_drawdown = (g.max_portfolio_value - current_value) / g.max_portfolio_value
            if current_drawdown >= g.drawdown_threshold:
                record = {
                    'date': context.blotter.current_dt.strftime('%Y-%m-%d'),
                    'drawdown': current_drawdown,
                    'portfolio_value': current_value,
                    'max_value': g.max_portfolio_value,
                    'is_weak': g.is_a_share_weak
                }
                positions_info = []
                for security in context.portfolio.positions:
                    position = context.portfolio.positions[security]
                    if position.amount > 0:
                        security_name = get_security_name(security)
                        positions_info.append(f"{security_name}:{position.amount}股")
                record['positions'] = positions_info
                g.drawdown_records.append(record)
                log.info(f"【回撤预警】回撤达到 {current_drawdown:.2%} (阈值: {g.drawdown_threshold:.0%})")
                log.info(f"  当前净值: {current_value:,.0f}  |  最高净值: {g.max_portfolio_value:,.0f}")
                log.info(f"  大A状态: {'走弱期' if g.is_a_share_weak else '正常期'}")
                log.info(f"  持仓: {', '.join(positions_info) if positions_info else '空仓'}")
    except Exception as e:
        log.error(f"【回撤监控】计算异常: {e}")


def calculate_global_etf_threshold(context):
    """计算全市场ETF流动性门槛：近3日日均总成交额 / 阈值除数"""
    log.info("【全局阈值更新】开始计算全市场ETF流动性门槛")
    try:
        etf_list = _get_all_etf_list()
        if not etf_list:
            log.warning("未找到任何场内ETF，使用保守阈值1000万")
            g.avg_etf_money_threshold = 10000000
            return
        log.info(f"全市场ETF总数: {len(etf_list)}只")
        hist_data = get_batch_hist(etf_list, 3, ['money'], freq='1d')
        if not hist_data:
            log.warning("无法获取历史成交额数据，使用保守阈值1000万")
            g.avg_etf_money_threshold = 10000000
            return
        daily_totals = {}
        for s, d in hist_data.items():
            money_list = d.get('money', [])
            for i, m in enumerate(money_list):
                if i not in daily_totals:
                    daily_totals[i] = 0.0
                daily_totals[i] += m
        totals = list(daily_totals.values())
        for i, money in daily_totals.items():
            log.info(f"  第{i+1}日 全市场ETF总成交额: {money/1e8:.2f}亿元")
        if len(totals) < 3:
            log.warning(f"仅有{len(totals)}个有效交易日，使用保守阈值1000万")
            g.avg_etf_money_threshold = 10000000
            return
        avg_total_money = sum(totals) / len(totals)
        threshold = avg_total_money / g.liquidity_threshold_divisor
        g.avg_etf_money_threshold = threshold
        log.info(f"【全局阈值更新完成】近{len(totals)}日全市场ETF日均总成交额={avg_total_money/1e8:.2f}亿元，阈值={threshold/1e4:.0f}万元({threshold:,.0f}元)")
    except Exception as e:
        log.warning(f"计算全局阈值异常: {e}，使用保守阈值1000万")
        g.avg_etf_money_threshold = 10000000


def filter_global_pool_by_volume(context):
    """走弱期全球ETF池流动性过滤：剔除近3日日均成交额低于门槛的ETF"""
    log.info("【全球池过滤】开始执行")
    if getattr(g, 'avg_etf_money_threshold', None) is None:
        log.info("【全球池过滤】阈值未初始化，立即计算")
        calculate_global_etf_threshold(context)
    if not g.global_etf_pool:
        log.info("【全球池过滤】全球池为空，跳过过滤")
        g.filtered_global_pool = []
        return
    dynamic_threshold = g.avg_etf_money_threshold
    log.info(f"【全球池过滤】使用流动性门槛=日均{dynamic_threshold/1e4:.0f}万元")
    TRADE_DAYS_COUNT = 3
    try:
        hist_data = get_batch_hist(g.global_etf_pool, TRADE_DAYS_COUNT, ['money'], freq='1d')
        if not hist_data:
            log.warning("【全球池过滤】无法获取成交额数据，使用原始全球池")
            g.filtered_global_pool = g.global_etf_pool[:]
            return
        avg_money_map = {}
        for s, d in hist_data.items():
            money_list = d.get('money', [])
            if len(money_list) >= TRADE_DAYS_COUNT:
                avg_money_map[s] = sum(money_list) / TRADE_DAYS_COUNT
        new_global_pool = [s for s, m in avg_money_map.items() if m > dynamic_threshold]
        removed = set(g.global_etf_pool) - set(new_global_pool)
        if removed:
            removed_info = []
            for code in removed:
                try:
                    name = getattr(g, 'etf_names_dict', {}).get(code, str(code))
                    money = avg_money_map.get(code, 0)
                    removed_info.append(f"{name}({code}) {money/1e8:.2f}亿")
                except Exception:
                    removed_info.append(code)
            log.info(f"【全球池过滤】剔除低流动性ETF({len(removed)}只): {', '.join(removed_info)}")
        g.filtered_global_pool = new_global_pool
        sorted_qualified = sorted(avg_money_map.items(), key=lambda x: x[1], reverse=True)
        log.info(f"【全球池过滤】保留高流动性ETF({len(new_global_pool)}只)")
    except Exception as e:
        log.warning(f"【全球池过滤】异常: {e}")
        g.filtered_global_pool = g.global_etf_pool[:]


def update_sector_pool(context):
    """动态池更新：全市场ETF按行业分组，每组取流动性最佳的1只，Top N入池"""
    log.info("【动态池更新】开始执行")
    if g.avg_etf_money_threshold is None:
        log.info("【动态池更新】阈值未初始化，立即计算")
        calculate_global_etf_threshold(context)

    FUND_COMPANIES = sorted(list(set([
        '易方达', '广发', '华夏', '华安', '嘉实', '富国', '招商', '鹏华', '南方', '汇添富', '国泰', '平安',
        '银华', '天弘', '建信', '工银', '华泰柏瑞', '博时', '景顺长城', '景顺', '华宝', '申万菱信', '万家', '中欧',
        '兴证全球', '浙商', '诺安', '前海开源', '泰康', '泰达宏利', '农银汇理', '交银', '东方红', '财通', '华商',
        '国联', '永赢', '金鹰', '德邦', '创金合信', '西部利得', '圆信永丰', '泓德', '汇安', '诺德', '恒生前海',
        '华润元大', '大成', '海富通', '摩根', '华泰', '中信', '中银', '兴全', '国信', '长城', '中金', '浙商证券',
        '东海', '东吴', '浦银安盛', '信达澳亚', '中加', '中航', '中融', '中邮', '中庚', '中信保诚', '中信建投',
        '中银国际', '中银证券', '九泰', '交银施罗德', '光大保德信', '兴银', '农银', '国投瑞银', '国海富兰克林',
        '国联安', '国金', '太平', '方正富邦', '民生加银', '汇丰晋信', '银河', '长信', '长安', '长盛', '长江证券', '鹏扬',
    ])), key=len, reverse=True)

    NOISE_WORDS = sorted(list(set([
        '6666', '8888', '9999', 'A类', 'AH', 'B', 'BS', 'C', 'C类', 'CS', 'DB', 'E', 'E类',
        'ETF', 'ETF基金', 'ETF联接', 'FG', 'G60', 'GF', 'GT', 'HGS', 'LOF', 'LOF基金', 'LOF联接',
        'SG', 'SZ', 'TF', 'TK', 'WJ', 'YH', 'ZS', 'ZZ', '板块', '策略', '产业', '场内', '场外', '低波',
        '基本面', '基金', '精选', '联接', '联接基金', '量化', '龙头', '民企', '民营', '国企', '央企', '智能',
        '全指', '上市开放式', '指基', '指增', '指数', '指数A', '指数C', '指数ETF', '指数基金', '主题', '增强',
        '上海', '黄', '30', '50', '100', '300', '500', '1000', '2000', '大', '新', '四川', '浙江', '湖北',
    ])), key=len, reverse=True)

    SPECIAL_GROUPS = sorted([
        {'name': '香港组', 'keywords': sorted(['恒生', '恒指', '港股', '港股通', 'H股', '香港', '港', 'HKC', 'HK', 'HGS', 'H', '中概', 'HS科技'], key=len, reverse=True),
         'remove_words': sorted(['恒生', '恒指', '港股', '港股通', 'H股', '香港', '港', 'HKC', 'HK', 'HGS', 'H', '中概', 'HS'], key=len, reverse=True)},
        {'name': '科创组', 'keywords': sorted(['科创', '科创板', '科综', 'KC', 'K C', '双创', '科创创业', '创创'], key=len, reverse=True),
         'remove_words': sorted(['科创', '科创板', '科综', 'KC', 'K C', '双创', '科创创业', '创创', '债券', '债汇', '债指', '债沪', '债易', '债基', '债兴', '债摩', '债', 'AAA'], key=len, reverse=True)},
        {'name': '创业组', 'keywords': sorted(['创业板', '创业', '创板', '创成长'], key=len, reverse=True),
         'remove_words': sorted(['创业板', '创业', '创板', '创成长'], key=len, reverse=True)},
        {'name': '美指组', 'keywords': sorted(['标普', '纳指', '纳斯达克'], key=len, reverse=True),
         'remove_words': sorted(['标普', '纳指', '纳斯达克'], key=len, reverse=True)}
    ], key=lambda x: max(len(kw) for kw in x['keywords']), reverse=True)

    exclude_keywords = sorted(list(set([
        '300', '500', '1000', '2000', '800', '30', '50', '100', '180', '200',
        '沪深', '中证', '上证', '深证', '深成', 'A50', 'A100', 'A500', '深100',
        '短融', '可转债', '转债', '双债', '利率债', '国债', '地债', '政金债', '国开债', '基准国债', '新综债',
        '信用债', '企业债', '公司债', '城投债', '城投', '美元债', '沪公司债', '科创债', '科债', '科创AAA',
        '自由现金流', '现金流', '现金流E', '现金流基', '现金流TF', '现金流全', '300现金流', '800现金流',
        '货币', '现金', '快线', '快钱', '中银现金', '500现金', '800现金', '现金800', '现金自由', '现金指数',
        '全指现金', '现金全指', 'ESG', 'MSCI', 'MS', '债',
    ])), key=len, reverse=True)

    try:
        etf_list = _get_all_etf_list()
        g.etf_names_dict = {c: g.etf_names_dict.get(c, c) for c in etf_list}
    except Exception as e:
        log.warning(f"获取全市场ETF列表失败: {e}")
        return

    log.info(f"【动态池更新】全市场ETF总数: {len(etf_list)}只")
    normal_etfs = []
    special_etfs = []
    special_group_map = {}
    excluded_count = 0

    for code in etf_list:
        try:
            name = g.etf_names_dict.get(code, str(code))
            is_special = False
            matched_group = None
            for group in SPECIAL_GROUPS:
                for kw in group['keywords']:
                    if kw in name:
                        is_special = True
                        matched_group = group['name']
                        break
                if is_special:
                    break
            is_excluded = False
            for k in exclude_keywords:
                if k in name:
                    is_excluded = True
                    excluded_count += 1
                    break
            if not is_excluded:
                if is_special:
                    special_etfs.append(code)
                    special_group_map[code] = matched_group
                else:
                    normal_etfs.append(code)
        except Exception:
            continue

    group_counts = {}
    for code in special_etfs:
        group_name = special_group_map.get(code, '未知')
        group_counts[group_name] = group_counts.get(group_name, 0) + 1
    log.info(f"【动态池更新】特别组分布: {group_counts}")
    log.info(f"【动态池更新】进入特别组: {len(special_etfs)}只")
    log.info(f"【动态池更新】进入普通组: {len(normal_etfs)}只")
    log.info(f"【动态池更新】排除ETF: {excluded_count}只")

    TRADE_DAYS_COUNT = 3
    dynamic_threshold = g.avg_etf_money_threshold

    def filter_by_liquidity(etf_codes, group_name):
        if not etf_codes:
            return {}, 0
        try:
            hist_data = get_batch_hist(etf_codes, TRADE_DAYS_COUNT, ['money'], freq='1d')
            if not hist_data:
                return {}, len(etf_codes)
            avg_money_map = {}
            for s, d in hist_data.items():
                money_list = d.get('money', [])
                if len(money_list) >= TRADE_DAYS_COUNT:
                    avg_money_map[s] = sum(money_list) / TRADE_DAYS_COUNT
            qualified = {s: m for s, m in avg_money_map.items() if m > dynamic_threshold}
            filtered_out = len(etf_codes) - len(qualified)
            return qualified, filtered_out
        except Exception:
            return {}, len(etf_codes)

    normal_qualified, normal_filtered_out = filter_by_liquidity(normal_etfs, "普通组")
    special_qualified, special_filtered_out = filter_by_liquidity(special_etfs, "特别组")
    normal_sorted = sorted(normal_qualified.keys(), key=lambda x: normal_qualified[x], reverse=True)
    special_sorted = sorted(special_qualified.keys(), key=lambda x: special_qualified[x], reverse=True)
    log.info(f"【动态池更新】特别组流动性过滤: {len(special_etfs)}→{len(special_sorted)}只")
    log.info(f"【动态池更新】普通组流动性过滤: {len(normal_etfs)}→{len(normal_sorted)}只")

    if not normal_sorted and not special_sorted:
        log.warning("【动态池更新】无ETF通过流动性过滤")
        g.dynamic_etf_pool = []
        return

    def get_remove_words_for_etf(_, is_special, matched_group_name):
        if not is_special:
            return []
        for group in SPECIAL_GROUPS:
            if group['name'] == matched_group_name:
                return group['remove_words']
        return []

    def clean_name(original_name, is_special=False, matched_group_name=None):
        cleaned = original_name
        for company in FUND_COMPANIES:
            cleaned = cleaned.replace(company, '')
        if is_special and matched_group_name:
            for word in get_remove_words_for_etf(original_name, is_special, matched_group_name):
                cleaned = cleaned.replace(word, '')
        for noise in NOISE_WORDS:
            cleaned = cleaned.replace(noise, '')
        return cleaned.strip()

    normal_industry_groups = {}
    for code in normal_sorted:
        try:
            original_name = g.etf_names_dict.get(code, str(code))
            money = normal_qualified[code]
            cleaned = clean_name(original_name, is_special=False)
            if cleaned == '':
                continue
            industry_key = cleaned[:2] if len(cleaned) >= 2 else cleaned
            if industry_key not in normal_industry_groups:
                normal_industry_groups[industry_key] = []
            normal_industry_groups[industry_key].append({
                'code': code, 'original_name': original_name, 'cleaned_name': cleaned,
                'money': money, 'group_type': '普通'
            })
        except Exception:
            continue

    special_industry_groups = {}
    for code in special_sorted:
        try:
            original_name = g.etf_names_dict.get(code, str(code))
            matched_group = special_group_map.get(code, '未知')
            money = special_qualified[code]
            cleaned = clean_name(original_name, is_special=True, matched_group_name=matched_group)
            if cleaned == '':
                continue
            industry_key = cleaned[:2] if len(cleaned) >= 2 else cleaned
            group_key = f"{matched_group}_{industry_key}"
            if group_key not in special_industry_groups:
                special_industry_groups[group_key] = []
            special_industry_groups[group_key].append({
                'code': code, 'original_name': original_name, 'cleaned_name': cleaned,
                'money': money, 'group_type': matched_group, 'display_group': matched_group
            })
        except Exception:
            continue

    final_pool_info = []
    for industry_key, items in normal_industry_groups.items():
        sorted_items = sorted(items, key=lambda x: x['money'], reverse=True)
        final_pool_info.append(sorted_items[0])
    for group_key, items in special_industry_groups.items():
        sorted_items = sorted(items, key=lambda x: x['money'], reverse=True)
        final_pool_info.append(sorted_items[0])

    final_pool_info_sorted = sorted(final_pool_info, key=lambda x: x['money'], reverse=True)
    _top_n = getattr(g, 'dynamic_pool_top_n', 100)
    top_100 = final_pool_info_sorted[:_top_n]
    g.dynamic_etf_pool = [item['code'] for item in top_100]
    log.info(f"【动态池更新完成】动态池共{len(g.dynamic_etf_pool)}只ETF")
    if len(g.dynamic_etf_pool) <= 10:
        for item in top_100[:10]:
            log.info(f"  {item['code']} {item['original_name']} 日均成交额: {item['money']/1e8:.2f}亿")


def filter_fixed_pool_by_volume(context):
    """固定池流动性过滤：剔除近3日日均成交额低于门槛的预设ETF"""
    log.info("【固定池过滤】开始执行")
    if getattr(g, 'avg_etf_money_threshold', None) is None:
        log.info("【固定池过滤】阈值未初始化，立即计算")
        calculate_global_etf_threshold(context)
    if not g.fixed_etf_pool:
        log.info("【固定池过滤】固定池为空，跳过过滤")
        return
    dynamic_threshold = g.avg_etf_money_threshold
    log.info(f"【固定池过滤】使用流动性门槛=日均{dynamic_threshold/1e4:.0f}万元")
    TRADE_DAYS_COUNT = 3
    try:
        hist_data = get_batch_hist(g.fixed_etf_pool, TRADE_DAYS_COUNT, ['money'], freq='1d')
        if not hist_data:
            log.warning("【固定池过滤】无法获取成交额数据，跳过过滤")
            g.filtered_fixed_pool = g.fixed_etf_pool[:]
            return
        avg_money_map = {}
        for s, d in hist_data.items():
            money_list = d.get('money', [])
            if len(money_list) >= TRADE_DAYS_COUNT:
                avg_money_map[s] = sum(money_list) / TRADE_DAYS_COUNT
        new_fixed_pool = [s for s, m in avg_money_map.items() if m > dynamic_threshold]
        removed = set(g.fixed_etf_pool) - set(new_fixed_pool)
        if removed:
            removed_info = []
            for code in removed:
                try:
                    name = getattr(g, 'etf_names_dict', {}).get(code, str(code))
                    money = avg_money_map.get(code, 0)
                    removed_info.append(f"{name}({code}) {money/1e8:.2f}亿")
                except Exception:
                    removed_info.append(code)
            log.info(f"【固定池过滤】剔除低流动性ETF({len(removed)}只): {', '.join(removed_info)}")
        g.filtered_fixed_pool = new_fixed_pool
        log.info(f"【固定池过滤】保留高流动性ETF({len(new_fixed_pool)}只)")
    except Exception as e:
        log.warning(f"【固定池过滤】异常: {e}")
        g.filtered_fixed_pool = g.fixed_etf_pool[:]


def daily_merge_etf_pools(context):
    """合并ETF池：固定池 ∪ 动态池，去重排序"""
    if not hasattr(g, 'filtered_fixed_pool'):
        g.filtered_fixed_pool = g.fixed_etf_pool[:]
    merged = list(set(g.filtered_fixed_pool + g.dynamic_etf_pool))
    merged.sort()
    log.info("【合并ETF池】开始执行")
    log.info(f"【合并池统计】固定池: {len(g.filtered_fixed_pool)}只, 动态池: {len(g.dynamic_etf_pool)}只, 合并后: {len(merged)}只")
    g.merged_etf_pool = merged


def calculate_and_log_ranked_etfs(context):
    """计算合并池内所有ETF的动量得分并排序，结果存入 g.ranked_etfs_result"""
    if not hasattr(g, 'merged_etf_pool') or not g.merged_etf_pool:
        log.warning("【动量计算】合并池为空，无法计算")
        g.ranked_etfs_result = []
        return
    final_list = get_final_ranked_etfs(context)
    g.ranked_etfs_result = final_list


def calculate_momentum_score(price_series, lookback_days):
    """计算动量得分：加权线性回归拟合对数价格，得分 = 年化收益率 × R²"""
    if len(price_series) < lookback_days + 1:
        return None, None, None
    recent_price_series = price_series[-(lookback_days + 1):]  # 取最近lookback_days+1个价格点
    y = np.log(recent_price_series)  # 对数价格
    x = np.arange(len(y))  # 时间序列 [0, 1, 2, ..., n]
    weights = np.linspace(1, 2, len(y))  # 时间权重：从1线性递增到2（近期权重更大）
    W = weights ** 2  # 权重平方
    W_sum = np.sum(W)  # 权重总和
    x_bar = np.sum(W * x) / W_sum  # 加权平均时间
    y_bar = np.sum(W * y) / W_sum  # 加权平均对数价格
    dx = x - x_bar  # 时间偏差
    dy = y - y_bar  # 价格偏差
    variance_x = np.sum(W * dx**2)  # 加权时间方差
    if variance_x == 0:
        return 0, 0, 0
    slope = np.sum(W * dx * dy) / variance_x  # 回归斜率（每日对数收益率）
    intercept = y_bar - slope * x_bar  # 截距
    annualized_returns = math.exp(slope * 250) - 1  # 年化收益率（250个交易日）
    y_pred = slope * x + intercept  # 预测值
    ss_res = np.sum(weights * (y - y_pred) ** 2)  # 残差平方和
    ss_tot = np.sum(weights * (y - np.mean(y)) ** 2)  # 总平方和
    r_squared = 1 - ss_res / ss_tot if ss_tot else 0  # R²（趋势稳定性）
    momentum_score = annualized_returns * r_squared  # 动量得分 = 年化收益 × R²
    return momentum_score, annualized_returns, r_squared


def get_series_ending_at(hist_closes, current_price, offset):
    """构建以当前价格结尾的价格序列，offset表示向前偏移的天数"""
    hist = np.asarray(hist_closes, dtype=float)
    if offset == 0:
        return np.append(hist, float(current_price))
    cut = offset - 1
    if cut == 0:
        return hist
    if len(hist) <= cut:
        return None
    return hist[:-cut]


def get_historical_volume_ratio(hist_volumes, offset, lookback_days):
    """计算历史某日的量比：当日成交量 / 前N日均量"""
    try:
        vols = np.asarray(hist_volumes, dtype=float)
        idx = len(vols) - offset
        if idx <= 0 or idx >= len(vols):
            return None
        start = idx - lookback_days
        if start < 0:
            return None
        base = vols[start:idx]
        if len(base) < lookback_days or np.any(base <= 0) or np.any(np.isnan(base)):
            return None
        avg = np.mean(base)
        return vols[idx] / avg if avg > 0 else None
    except Exception:
        return None


def evaluate_super_mainline(hist_closes, hist_volumes, current_price, current_volume_ratio):
    """B型阶梯主线评估：连续5天动量得分阶梯抬升 + R²>0.85 + 量比>1.8 + 拉普拉斯斜率持续为正"""
    if not getattr(g, 'enable_super_mainline', False):
        return False, {'reason': 'disabled'}
    days = int(getattr(g, 'mainline_days', 5))
    if hist_closes is None or hist_volumes is None:
        return False, {'reason': 'no_hist'}

    scores = []
    r2_values = []
    volume_ratios = []
    laplace_slopes = []

    for offset in range(days - 1, -1, -1):
        series = get_series_ending_at(hist_closes, current_price, offset)
        if series is None or len(series) < int(g.lookback_days * 0.8):
            return False, {'reason': f'series_short@offset{offset}'}
        score, _, r2 = calculate_momentum_score(series, g.lookback_days)
        if score is None or r2 is None or pd.isna(score) or pd.isna(r2):
            return False, {'reason': f'score_nan@offset{offset}'}
        scores.append(score)
        r2_values.append(r2)

        try:
            lap_values = laplace_filter(series, s=g.laplace_s_param)
            lap_slope = lap_values[-1] - lap_values[-2] if len(lap_values) >= 2 else 0
        except Exception:
            lap_slope = 0
        laplace_slopes.append(lap_slope)

        if offset == 0:
            volume_ratios.append(current_volume_ratio)
        else:
            volume_ratios.append(get_historical_volume_ratio(hist_volumes, offset, g.volume_lookback))

    vr_dump = []
    valid_vrs = []
    for v in volume_ratios:
        if v is None:
            vr_dump.append('None')
        elif pd.isna(v):
            vr_dump.append('NaN')
        else:
            vr_dump.append(f'{float(v):.2f}')
            valid_vrs.append(float(v))
    hist_vol_len = len(hist_volumes) if hist_volumes is not None else 0

    has_missing = len(valid_vrs) < len(volume_ratios)
    if has_missing:
        if len(valid_vrs) < 3:
            current_score = scores[-1] if scores else 0
            current_r2 = r2_values[-1] if r2_values else 0
            return False, {
                'reason': 'volume_none',
                'vr_dump': vr_dump,
                'hist_vol_len': hist_vol_len,
                'scores': scores, 'r2_values': r2_values,
                'volume_ratios': [None if v is None or pd.isna(v) else float(v) for v in volume_ratios],
                'laplace_slopes': laplace_slopes,
                'current_score': current_score, 'current_r2': current_r2,
                'r2_avg': float(np.mean(r2_values)) if r2_values else 0,
                'volume_avg': float(np.mean(valid_vrs)) if valid_vrs else 0,
                'score_up_days': sum(1 for i in range(1, len(scores)) if scores[i] >= scores[i - 1]),
                'positive_laplace_days': sum(1 for v in laplace_slopes if v > 0),
            }
        fallback_v = float(np.mean(valid_vrs))
        volume_ratios = [fallback_v if (v is None or pd.isna(v)) else float(v) for v in volume_ratios]

    current_score = scores[-1]
    current_r2 = r2_values[-1]
    r2_avg = float(np.mean(r2_values))
    volume_avg = float(np.mean(volume_ratios))
    score_up_days = sum(1 for i in range(1, len(scores)) if scores[i] >= scores[i - 1])
    positive_laplace_days = sum(1 for v in laplace_slopes if v > 0)
    start_score = scores[0]
    if start_score > 0:
        score_growth = current_score / start_score
    else:
        score_growth = float('inf') if current_score > 0 else 0

    fails = []
    if not (g.mainline_score_min < current_score <= g.mainline_score_max):
        fails.append('score_range')
    if current_r2 < g.mainline_min_r2:
        fails.append('r2_cur')
    if r2_avg < g.mainline_min_r2_avg:
        fails.append('r2_avg')
    if volume_avg < g.mainline_min_volume_avg:
        fails.append('vol_avg')
    if score_up_days < g.mainline_min_score_up_days:
        fails.append('score_up')
    if positive_laplace_days < g.mainline_min_positive_laplace_days:
        fails.append('lap_pos')
    if score_growth < g.mainline_min_score_growth:
        fails.append('score_growth')
    passed = not fails

    reason_str = 'pass' if passed else '+'.join(fails)
    if has_missing and passed:
        reason_str = f'pass(vr_filled@{vr_dump.count("None") + vr_dump.count("NaN")})'

    return passed, {
        'scores': scores,
        'r2_values': r2_values,
        'volume_ratios': volume_ratios,
        'laplace_slopes': laplace_slopes,
        'current_score': current_score,
        'current_r2': current_r2,
        'r2_avg': r2_avg,
        'volume_avg': volume_avg,
        'score_up_days': score_up_days,
        'positive_laplace_days': positive_laplace_days,
        'score_growth': score_growth,
        'vr_dump': vr_dump,
        'hist_vol_len': hist_vol_len,
        'reason': reason_str,
    }


def calculate_all_metrics_for_etf(etf, etf_name, hist_closes, hist_volumes, current_price, today_vol, context):
    """计算ETF的所有指标：动量得分、R²、均线、量比、短期风控、溢价率、拉普拉斯滤波、主线评估、量价背离"""
    try:
        price_series = np.append(hist_closes, current_price)
        mom_lb = g.lookback_days
        if g.is_a_share_weak and getattr(g, "enable_dynamic_weak_lookback", False):
            mom_lb = g.weak_momentum_lookback
        if len(price_series) < mom_lb * 0.8:
            return None
        momentum_score, annualized_returns, r_squared = calculate_momentum_score(price_series, mom_lb)
        if momentum_score is None:
            return None
        passed_momentum = (g.min_score_threshold <= momentum_score <= g.max_score_threshold)
        volume_ratio = get_volume_ratio(hist_volumes, today_vol, context, g.volume_lookback)

        passed_loss_filter = True
        day_ratios = []
        if len(price_series) >= 4:
            day1 = price_series[-1] / price_series[-2]
            day2 = price_series[-2] / price_series[-3]
            day3 = price_series[-3] / price_series[-4]
            day_ratios = [day1, day2, day3]
            if min(day_ratios) < g.loss:
                passed_loss_filter = False

        passed_r2 = r_squared > g.r2_threshold

        passed_ma = True
        ma_value = None
        if len(price_series) >= g.ma_lookback:
            ma_value = np.mean(price_series[-g.ma_lookback:])
            passed_ma = current_price > ma_value * g.ma_threshold
        else:
            passed_ma = False

        premium_rate, passed_premium = calculate_premium_rate(etf, context)

        laplace_value = 0
        laplace_slope = 0
        passed_laplace = False
        if len(price_series) >= 10:
            try:
                laplace_values = laplace_filter(price_series, s=g.laplace_s_param)
                if len(laplace_values) >= 2:
                    laplace_value = laplace_values[-1]
                    laplace_slope = laplace_values[-1] - laplace_values[-2]
                    passed_laplace = (current_price > laplace_values[-1] and laplace_slope > g.laplace_min_slope)
            except Exception:
                pass

        passed_mainline, mainline_info = evaluate_super_mainline(hist_closes, hist_volumes, current_price, volume_ratio)
        passed_volume_divergence, vd_info = check_volume_price_divergence(hist_closes, hist_volumes, context)

        return {
            'etf': etf,
            'etf_name': etf_name,
            'momentum_score': momentum_score,
            'annualized_returns': annualized_returns,
            'r_squared': r_squared,
            'current_price': current_price,
            'volume_ratio': volume_ratio,
            'day_ratios': day_ratios,
            'premium_rate': premium_rate,
            'passed_momentum': passed_momentum,
            'passed_r2': passed_r2,
            'passed_ma': passed_ma,
            'passed_volume': volume_ratio is not None and volume_ratio < g.volume_threshold,
            'passed_loss': passed_loss_filter,
            'passed_premium': passed_premium,
            'ma_value': ma_value,
            'laplace_value': laplace_value,
            'laplace_slope': laplace_slope,
            'passed_laplace': passed_laplace,
            'passed_mainline': passed_mainline,
            'mainline_info': mainline_info,
            'passed_volume_divergence': passed_volume_divergence,
            'vd_info': vd_info,
        }
    except Exception as e:
        log.debug(f"【指标计算】{etf} {etf_name} 计算失败: {e}")
        return None


def get_volume_ratio(hist_volumes, today_vol, context, lookback_days=None):
    """计算量比：当日成交量按已交易时间折算全天预估量 / 近N日均量"""
    if lookback_days is None:
        lookback_days = g.volume_lookback
    try:
        if hist_volumes is None or len(hist_volumes) < lookback_days:
            return None
        past_n_days_vol = hist_volumes[-lookback_days:]
        if np.any(np.isnan(past_n_days_vol)) or np.any(past_n_days_vol == 0):
            return None
        avg_volume = np.mean(past_n_days_vol)
        if avg_volume == 0:
            return None
        now = context.blotter.current_dt
        elapsed_minutes = (now.hour - 9) * 60 + now.minute - 30
        if now.hour >= 13:
            elapsed_minutes -= 90
        elapsed_minutes = max(1, min(elapsed_minutes, 240))
        projected_today_vol = today_vol * (240.0 / elapsed_minutes)
        return projected_today_vol / avg_volume if avg_volume > 0 else 0
    except Exception:
        return None


def calculate_premium_rate(etf, context):
    """计算ETF溢价率：(市价 - 净值) / 净值 × 100%，返回(溢价率, 是否通过过滤)
    实盘优先使用快照中的iopv（实时净值），回退使用get_etf_info获取前一日净值
    """
    try:
        # 获取ETF市价
        etf_price = getattr(g, 'etf_yesterday_close_batch', {}).get(etf)
        if etf_price is None or pd.isna(etf_price):
            hist = get_history(1, frequency='1d', field=['close'], security_list=etf, fq='pre', include=False)
            if hist is None or len(hist) == 0 or 'close' not in hist.columns:
                return None, False
            etf_price = float(hist['close'].values[-1])

        # 获取ETF净值
        net_value = None
        if is_trade():
            # 实盘：优先使用快照中的iopv（实时净值）
            try:
                snap = get_snapshot(etf)
                if snap and snap.get(etf):
                    net_value = snap[etf].get('iopv')  # iopv: 实时参考净值
            except Exception:
                net_value = None

            # 回退：使用get_etf_info获取前一日净值
            if net_value is None or net_value <= 0:
                try:
                    etf_info = get_etf_info(etf)
                    if etf_info and etf_info.get(etf):
                        net_value = etf_info[etf].get('nav_pre')  # nav_pre: 前一日净值
                except Exception:
                    net_value = None
        else:
            # 回测：无法获取净值数据，跳过溢价率过滤
            return None, True

        # 验证净值有效性
        if net_value is None or net_value <= 0 or pd.isna(net_value):
            return None, True  # 无净值数据时不过滤

        # 计算溢价率
        premium_rate = (etf_price - net_value) / net_value * 100
        passed_premium = premium_rate <= g.max_premium_rate
        return premium_rate, passed_premium
    except Exception:
        return None, True


def laplace_filter(price, s=0.05):
    """拉普拉斯滤波：指数平滑滤波器，用于判断价格趋势的稳定性"""
    alpha = 1 - np.exp(-s)
    L = np.zeros(len(price))
    L[0] = price[0]
    for t in range(1, len(price)):
        L[t] = alpha * price[t] + (1 - alpha) * L[t - 1]
    return L


def _compute_hs300_breadth(context):
    """计算沪深300宽度：成分股中价格站上20日均线的比例，用于Regime P0分类"""
    try:
        stocks = _get_hs300_stocks()
        if not stocks:
            return None
        w = int(getattr(g, 'regime_breadth_ma', 20))
        hist_data = get_batch_hist(stocks, w, ['close'], freq='1d')
        if not hist_data:
            return None
        above = 0
        total = 0
        for code in stocks:
            d = hist_data.get(code)
            if not d or 'close' not in d:
                continue
            closes = np.array(d['close'], dtype=float)
            if len(closes) < w:
                continue
            ma = float(np.mean(closes[-w:]))
            px = _get_realtime_price(code)
            if px is None or pd.isna(px) or px <= 0 or ma <= 0:
                continue
            total += 1
            if px > ma:
                above += 1
        if total < 50:
            return None
        return float(above) / float(total)
    except Exception as e:
        log.debug(f"[RegimeP0] breadth error: {e}")
        return None


def _compute_market_liquidity_yi(context):
    """计算市场日均流动性（亿元）：上证+深证成交额均值，用于Regime P0分类"""
    try:
        lb = int(getattr(g, 'regime_liquidity_lookback', 20))
        idx = ['000001.SS', '399001.SZ']
        hist_data = get_batch_hist(idx, lb, ['money'], freq='1d')
        if not hist_data:
            return None
        daily = {}
        for s, d in hist_data.items():
            ml = d.get('money', [])
            for i, m in enumerate(ml):
                daily[i] = daily.get(i, 0.0) + m
        if not daily:
            return None
        vals = list(daily.values())
        return float(np.mean(vals)) / 1e8
    except Exception as e:
        log.debug(f"[RegimeP0] liquidity error: {e}")
        return None


def _compute_trend_votes(context):
    """趋势投票：4大指数对比MA10，返回(站上数, 低于数)，用于Regime P0分类"""
    indexes = {'大盘': '000300.SS', '小盘': '399101.SZ', '创业板': '399006.SZ', '中证A500': '000510.SS'}
    above_count = 0
    below_count = 0
    for name, code in indexes.items():
        df = get_history(g.weak_period_ma_lookback + 1, frequency='1d', field=['close'],
                         security_list=code, fq='pre', include=False)
        if df is None or len(df) < g.weak_period_ma_lookback:
            continue
        closes = df['close'].values
        current_price = closes[-1]
        ma_val = np.mean(closes[-g.weak_period_ma_lookback:])
        if current_price > ma_val:
            above_count += 1
        elif current_price < ma_val:
            below_count += 1
    return above_count, below_count


def _classify_regime_p0(above_count, below_count, breadth, liquidity_yi):
    """Regime P0分类：综合趋势投票、宽度、流动性，输出 NORMAL/STRUCTURAL/DEFENSIVE"""
    liq_min = float(getattr(g, 'regime_liquidity_min_yi', 20000.0))
    b_high = float(getattr(g, 'regime_breadth_high', 0.55))
    b_struct = float(getattr(g, 'regime_breadth_structural', 0.50))
    b_low = float(getattr(g, 'regime_breadth_low', 0.35))

    liquidity_ok = liquidity_yi is not None and liquidity_yi >= liq_min
    trend_ok = above_count >= 2
    trend_weak = below_count >= 3

    if breadth is not None and breadth < b_low:
        return 'DEFENSIVE', 2
    if not liquidity_ok:
        return 'DEFENSIVE', 2
    if trend_ok or (breadth is not None and breadth >= b_high):
        return 'NORMAL', 0
    if trend_weak and breadth is not None and breadth >= b_struct:
        return 'STRUCTURAL', 1
    if trend_weak and breadth is not None and breadth < b_low:
        return 'DEFENSIVE', 2
    return 'NORMAL', 0


def compute_regime_p0_daily(context):
    """每日11:30执行：Regime P0 市场状态分类（NORMAL/STRUCTURAL/DEFENSIVE），记录日志供观测"""
    if not getattr(g, 'enable_regime_p0', False):
        return
    above_count, below_count = _compute_trend_votes(context)
    breadth = _compute_hs300_breadth(context)
    liquidity_yi = _compute_market_liquidity_yi(context)
    regime_name, regime_code = _classify_regime_p0(above_count, below_count, breadth, liquidity_yi)
    legacy_weak = bool(getattr(g, 'is_a_share_weak', False))
    mismatch = legacy_weak and regime_name in ('NORMAL', 'STRUCTURAL')

    entry = {
        'date': context.blotter.current_dt.strftime('%Y-%m-%d'),
        'regime': regime_name,
        'regime_code': regime_code,
        'breadth': None if breadth is None else round(breadth, 4),
        'liquidity_yi': None if liquidity_yi is None else round(liquidity_yi, 1),
        'trend_above': above_count,
        'trend_below': below_count,
        'legacy_weak': int(legacy_weak),
        'legacy_mismatch': int(mismatch),
    }
    g.regime_p0_log.append(entry)

    log.info(f"[REGIME_P0] {json.dumps(entry, ensure_ascii=False)}")
    log.info(
        f"📊 【RegimeP0】{regime_name} | 宽度={entry['breadth']} 流动性={entry['liquidity_yi']}亿 "
        f"| 趋势 上/下={above_count}/{below_count} | 原走弱期={legacy_weak} "
        f"| 错配={'是' if mismatch else '否'}"
    )
    record(
        regime_p0=regime_code,
        breadth_p0=0.0 if breadth is None else float(breadth),
        liquidity_p0=0.0 if liquidity_yi is None else float(liquidity_yi),
        trend_below_p0=float(below_count),
        legacy_weak_p0=1.0 if legacy_weak else 0.0,
        regime_mismatch_p0=1.0 if mismatch else 0.0,
    )


def check_a_share_weak_period(context):
    """大A走弱期判断：4大指数对比MA10，≥3个低于则进入走弱期，切换至全球ETF池"""
    today = context.blotter.current_dt.date()
    indexes = {'大盘': '000300.SS', '小盘': '399101.SZ', '创业板': '399006.SZ', '中证A500': '000510.SS'}

    above_count = 0
    below_count = 0
    for name, code in indexes.items():
        df = get_history(g.weak_period_ma_lookback + 1, frequency='1d', field=['close'],
                         security_list=code, fq='pre', include=False)
        if df is None or len(df) < g.weak_period_ma_lookback:
            log.warning(f"📊 【走弱期判断】{name}({code})数据不足，跳过该指数")
            continue
        closes = df['close'].values
        current_price = closes[-1]
        ma_val = np.mean(closes[-g.weak_period_ma_lookback:])
        is_above = current_price > ma_val
        is_below = current_price < ma_val
        if is_above:
            above_count += 1
        if is_below:
            below_count += 1
        status_emoji = "⬆️站上" if is_above else ("⬇️低于" if is_below else "➡️持平")
        log.info(f"📊 【走弱期判断】{name}({code}): 收盘{current_price:.2f} / MA{g.weak_period_ma_lookback} {ma_val:.2f} → {status_emoji}")

    weak_condition_met = (below_count >= 3)
    exit_condition_met = (above_count >= 3)
    log.info(f"📊 【走弱期判断】低于MA{g.weak_period_ma_lookback}: {below_count}/4, 站上MA{g.weak_period_ma_lookback}: {above_count}/4")

    if g.is_a_share_weak and g.weak_start_date is not None:
        try:
            count = 0
            for i in range(g.max_weak_days + 1):
                td = get_trading_day(-i)
                if td < g.weak_start_date:
                    break
                count += 1
            g.weak_days_count = count
        except Exception:
            g.weak_days_count = 0
    else:
        g.weak_days_count = 0
    max_days_exceeded = (g.weak_days_count >= g.max_weak_days)

    cd = int(getattr(g, 'weak_confirm_days', 2))
    if weak_condition_met:
        g.weak_enter_streak = getattr(g, 'weak_enter_streak', 0) + 1
    else:
        g.weak_enter_streak = 0
    if exit_condition_met:
        g.weak_exit_streak = getattr(g, 'weak_exit_streak', 0) + 1
    else:
        g.weak_exit_streak = 0

    if g.is_a_share_weak:
        if max_days_exceeded:
            log.info(f"🔔 【走弱期退出】已达到最大持续天数{g.max_weak_days}个交易日，强制退出")
            g.is_a_share_weak = False
            g.weak_start_date = None
            g.weak_days_count = 0
            g.weak_exit_streak = 0
        elif g.weak_exit_streak >= cd:
            log.info(f"🟢 【走弱期退出】连续{g.weak_exit_streak}天满足退出条件(需≥{cd})，退出走弱期")
            g.is_a_share_weak = False
            g.weak_start_date = None
            g.weak_days_count = 0
            g.weak_exit_streak = 0
        elif weak_condition_met:
            g.weak_start_date = today
            g.weak_days_count = 0
            log.info(f"🟡 【走弱期中】再次触发进入条件(连续{g.weak_enter_streak}天)，重置计数器")
        elif g.weak_exit_streak > 0:
            log.info(f"🔴 【走弱期中】退出条件已触发{g.weak_exit_streak}/{cd}天，需连续{cd}天确认 | 已持续{g.weak_days_count}/{g.max_weak_days}天")
        else:
            log.info(f"🔴 【走弱期中】已持续{g.weak_days_count}/{g.max_weak_days}个交易日")
    else:
        if g.weak_enter_streak >= cd:
            log.info(f"🔴 【走弱期进入】连续{g.weak_enter_streak}天满足进入条件(需≥{cd})，进入大A走弱期")
            g.is_a_share_weak = True
            g.weak_start_date = today
            g.weak_days_count = 0
            g.weak_enter_streak = 0
        elif g.weak_enter_streak > 0:
            log.info(f"🟡 【正常期中】进入条件已触发{g.weak_enter_streak}/{cd}天，需连续{cd}天确认")
        else:
            log.info(f"🟢 【正常期中】未满足进入条件")

    status_emoji = "🔴" if g.is_a_share_weak else "🟢"
    status_str = f"{status_emoji} 最终状态: 走弱期={g.is_a_share_weak}"
    if g.is_a_share_weak:
        status_str += f" (已持续{g.weak_days_count}/{g.max_weak_days}个交易日)"
        record(走弱期状态=1)
    else:
        record(走弱期状态=0)
    log.info(f"📊 【走弱期判断】{status_str}")
    if getattr(g, "enable_dynamic_weak_lookback", False):
        adjust_weak_momentum_lookback(context)
    return g.is_a_share_weak


def apply_filters(metrics_list):
    """多层过滤器：动量得分→R²→均线→成交量→短期风控→溢价率→拉普拉斯→量价背离，按序剔除不达标ETF"""
    steps = [
        ('动量得分', lambda m: m['passed_momentum'], True),
        ('R²', lambda m: m['passed_r2'],
         (g.enable_r2_filter and not g.is_a_share_weak)
         or (getattr(g, 'enable_weak_r2_filter', False) and g.is_a_share_weak)),
        ('均线', lambda m: m['passed_ma'],
         g.enable_ma_filter and g.is_a_share_weak),
        ('成交量', lambda m: m['passed_volume'], g.enable_volume_check),
        ('短期风控', lambda m: m['passed_loss'], g.enable_loss_filter),
        ('溢价率', lambda m: m['passed_premium'], g.enable_premium_filter),
        ('拉普拉斯滤波', lambda m: m['passed_laplace'], g.enable_laplace_filter),
        ('量价背离', lambda m: m.get('passed_volume_divergence', True), g.enable_volume_divergence_filter and g.is_choppy),
    ]
    filtered = metrics_list[:]
    for name, condition, is_enabled in steps:
        if is_enabled and (name == '动量得分' or name == 'R²' or not g.is_a_share_weak):
            filtered = [m for m in filtered if condition(m)]
    return filtered


def get_final_ranked_etfs(context):
    """动量排序主流程：获取历史数据→计算所有ETF指标→多层过滤→B型主线补充→持仓延续→结合当前持仓确定最终目标"""
    all_metrics = []
    etf_set = list(g.merged_etf_pool)
    if not etf_set:
        g.ranked_etfs_result = []
        return []
    mom_lb = g.weak_momentum_lookback if (
        g.is_a_share_weak and getattr(g, "enable_dynamic_weak_lookback", False)
    ) else g.lookback_days
    lookback = max(mom_lb, g.volume_lookback, g.ma_lookback) + 20
    safe_lookback = lookback + 20
    now = context.blotter.current_dt
    today = now.date()
    log.info(f"【动量得分计算】使用合并池，合计{len(etf_set)}只ETF")
    log.info(f"【当前状态】{'🔴 大A走弱期' if g.is_a_share_weak else '🟢 大A正常期'}")

    hist_data = get_batch_hist(etf_set, safe_lookback, ['close', 'volume'], freq='1d')
    if not hist_data:
        log.warning("【动量计算】无法获取历史价格数据")
        return []

    g.etf_yesterday_close_batch = {}
    g.etf_yesterday_nav_batch = {}
    try:
        for etf in etf_set:
            d = hist_data.get(etf)
            if d and d.get('close'):
                g.etf_yesterday_close_batch[etf] = d['close'][-1]
        nav_data = get_batch_hist(etf_set, 1, ['unit_nav'], freq='1d')
        for etf, d in nav_data.items():
            nl = d.get('unit_nav', [])
            if nl:
                g.etf_yesterday_nav_batch[etf] = nl[-1]
    except Exception as e:
        log.warning(f"【动量计算】批量获取溢价率数据异常: {e}")

    elapsed_minutes = (now.hour - 9) * 60 + now.minute - 30
    if now.hour >= 13:
        elapsed_minutes -= 90
    elapsed_minutes = max(1, min(elapsed_minutes, 240))
    today_vol_data = get_batch_hist(etf_set, elapsed_minutes, ['volume'], freq='1m', include=True)
    today_vols = {s: (sum(d.get('volume', [])) if d.get('volume') else 0) for s, d in today_vol_data.items()}

    for etf in etf_set:
        if _get_realtime_paused(etf):
            continue
        d = hist_data.get(etf)
        if not d or 'close' not in d or 'volume' not in d:
            continue
        raw_closes = np.array(d['close'], dtype=float)
        raw_volumes = np.array(d['volume'], dtype=float)
        valid_mask = (~np.isnan(raw_volumes)) & (raw_volumes > 0)
        hist_closes = raw_closes[valid_mask]
        hist_volumes = raw_volumes[valid_mask]
        hist_closes = hist_closes[-lookback:]
        hist_volumes = hist_volumes[-lookback:]
        if len(hist_closes) < g.lookback_days:
            continue
        etf_name = get_security_name(etf)
        current_price = _get_realtime_price(etf)
        if current_price <= 0:
            continue
        today_vol = today_vols.get(etf, 0)
        metrics = calculate_all_metrics_for_etf(etf, etf_name, hist_closes, hist_volumes, current_price, today_vol, context)
        if metrics:
            if metrics['etf'] in {m['etf'] for m in all_metrics}:
                continue
            all_metrics.append(metrics)

    for item in all_metrics:
        score = item.get('momentum_score')
        if pd.isna(score) or (isinstance(score, float) and np.isnan(score)):
            item['momentum_score'] = float('-inf')
    all_metrics.sort(key=lambda x: x.get('momentum_score', float('-inf')), reverse=True)

    log_buffer = []
    log_buffer.append("")
    log_buffer.append(">>> 第一步：所有ETF按动量得分从大到小排序 <<<")
    for m in all_metrics[:100]:
        def fmt_status(value_str, passed):
            return f"{value_str} {'✅' if passed else '❌'}"
        score_str = f"{m['momentum_score']:.4f}" if m['momentum_score'] != float('-inf') else "nan"
        r2_str = f"{m['r_squared']:.3f}" if not pd.isna(m['r_squared']) else "nan"
        vol_val = f"{m['volume_ratio']:.2f}" if m['volume_ratio'] is not None else "N/A"
        min_ratio = min(m['day_ratios']) if m['day_ratios'] else 'N/A'
        loss_val = f"{min_ratio:.4f}" if isinstance(min_ratio, float) and not pd.isna(min_ratio) else str(min_ratio)
        premium_str = f"{m['premium_rate']:.2f}%" if m['premium_rate'] is not None else "N/A"
        ma_str = f"MA{g.ma_lookback}: {m['ma_value']:.2f}" if m['ma_value'] is not None else "MA:N/A"
        line = (
            f"{m['etf']} {m['etf_name']}: "
            f"动量得分: {fmt_status(score_str, m['passed_momentum'])}，"
            f"R²: {fmt_status(r2_str, m['passed_r2'])}，"
            f"均线: {fmt_status(ma_str, m['passed_ma'])}，"
            f"成交量比值: {fmt_status(vol_val, m['passed_volume'])}，"
            f"短期风控: {fmt_status(loss_val, m['passed_loss'])}，"
            f"溢价率: {fmt_status(premium_str, m['passed_premium'])}，"
            f"拉普拉斯斜率: {m['laplace_slope']:.4f} {fmt_status('', m['passed_laplace'])}，"
            f"B型主线: {'✅' if m.get('passed_mainline') else '❌'}，"
            f"量价背离: {'✅' if m.get('passed_volume_divergence', True) else '❌'}"
        )
        log_buffer.append(line)
        if getattr(g, 'enable_super_mainline', False) and m.get('momentum_score', 0) > g.mainline_score_min:
            info = m.get('mainline_info', {}) or {}
            if info:
                line_d = (
                    f"    [主线诊断 {m['etf']}] reason={info.get('reason', 'n/a')} | "
                    f"score_cur={info.get('current_score', 0):.2f} "
                    f"r2_cur={info.get('current_r2', 0):.3f} "
                    f"r2_avg={info.get('r2_avg', 0):.3f} "
                    f"vol_avg={info.get('volume_avg', 0):.2f} "
                    f"up={info.get('score_up_days', 0)}/{g.mainline_days-1} "
                    f"lap+={info.get('positive_laplace_days', 0)}/{g.mainline_days} "
                    f"score_growth={info.get('score_growth', 0):.2f}"
                )
                vr_dump = info.get('vr_dump')
                if vr_dump:
                    line_d += f" | vr_list=[{', '.join(vr_dump)}] hist_vol_len={info.get('hist_vol_len', '?')}"
                log_buffer.append(line_d)
            else:
                log_buffer.append(f"    [主线诊断 {m['etf']}] info 为空 (评估提前返回)")

    filtered_list = apply_filters(all_metrics)
    if getattr(g, 'enable_super_mainline', False):
        normal_codes = {m['etf'] for m in filtered_list}
        mainline_list = [
            m for m in all_metrics
            if m.get('passed_mainline')
            and m['etf'] not in normal_codes
            and (not g.enable_loss_filter or m['passed_loss'])
            and (not g.enable_premium_filter or m['passed_premium'])
            and (not (g.enable_ma_filter and g.is_a_share_weak) or m['passed_ma'])
        ]
        filtered_list = filtered_list + mainline_list
        log_buffer.append("")
        log_buffer.append(
            f">>> B型阶梯主线：score在({g.mainline_score_min},{g.mainline_score_max}]且满足阶梯主线条件的ETF {len(mainline_list)}只 <<<"
        )
        for m in mainline_list[:15]:
            info = m.get('mainline_info', {})
            log_buffer.append(
                f"  {m['etf']} {m['etf_name']}: score={m['momentum_score']:.4f}, "
                f"R²当前={info.get('current_r2', 0):.3f}, R²均值={info.get('r2_avg', 0):.3f}, "
                f"量比均值={info.get('volume_avg', 0):.2f}, "
                f"score抬升={info.get('score_up_days', 0)}/{g.mainline_days-1}, "
                f"拉普拉斯正={info.get('positive_laplace_days', 0)}/{g.mainline_days}, "
                f"score增长={info.get('score_growth', 0):.2f}倍"
            )

        retain_list = []
        if getattr(g, 'enable_mainline_retain', True):
            held_codes_set = {sec for sec, pos in context.portfolio.positions.items() if pos.amount > 0}
            already_codes = {m['etf'] for m in filtered_list}
            for m in all_metrics:
                if m['etf'] not in held_codes_set:
                    continue
                if m['etf'] in already_codes:
                    continue
                score_val = m.get('momentum_score', 0)
                if score_val is None or pd.isna(score_val):
                    continue
                if score_val <= g.mainline_score_max:
                    continue
                r2_val = m.get('r_squared')
                lap_slope = m.get('laplace_slope', 0)
                if r2_val is None or pd.isna(r2_val) or r2_val < g.mainline_retain_min_r2:
                    continue
                if lap_slope is None or pd.isna(lap_slope) or lap_slope <= g.mainline_retain_min_lap_slope:
                    continue
                if g.enable_loss_filter and not m['passed_loss']:
                    continue
                if g.enable_premium_filter and not m['passed_premium']:
                    continue
                if g.enable_ma_filter and g.is_a_share_weak and not m['passed_ma']:
                    continue
                retain_list.append(m)
            if retain_list:
                for m in retain_list:
                    m['mainline_retained'] = True
                filtered_list = filtered_list + retain_list
                log_buffer.append("")
                log_buffer.append(
                    f">>> B型主线持仓延续：当前持仓中 score 已突破{g.mainline_score_max}但趋势品质仍达标的ETF {len(retain_list)}只 <<<"
                )
                for m in retain_list:
                    log_buffer.append(
                        f"  {m['etf']} {m['etf_name']}: score={m['momentum_score']:.4f}, "
                        f"R²={m['r_squared']:.3f}, 拉普拉斯斜率={m['laplace_slope']:.4f} "
                        f"→ 持仓延续保留"
                    )

    filtered_list.sort(key=lambda x: x.get('momentum_score', float('-inf')), reverse=True)
    top_10 = filtered_list[:10]
    log_buffer.append("")
    log_buffer.append(">>> 第二步：符合全部过滤条件的ETF按动量得分从大到小排序(前10名) <<<")
    if top_10:
        for m in top_10:
            def fmt_status(value_str, passed):
                return f"{value_str} {'✅' if passed else '❌'}"
            score_str = f"{m['momentum_score']:.4f}" if m['momentum_score'] != float('-inf') else "nan"
            r2_str = f"{m['r_squared']:.3f}" if not pd.isna(m['r_squared']) else "nan"
            vol_val = f"{m['volume_ratio']:.2f}" if m['volume_ratio'] is not None else "N/A"
            min_ratio = min(m['day_ratios']) if m['day_ratios'] else 'N/A'
            loss_val = f"{min_ratio:.4f}" if isinstance(min_ratio, float) and not pd.isna(min_ratio) else str(min_ratio)
            premium_str = f"{m['premium_rate']:.2f}%" if m['premium_rate'] is not None else "N/A"
            ma_str = f"MA{g.ma_lookback}: {m['ma_value']:.2f}" if m['ma_value'] is not None else "MA:N/A"
            line = (
                f"{m['etf']} {m['etf_name']}: "
                f"动量得分: {fmt_status(score_str, m['passed_momentum'])}，"
                f"R²: {fmt_status(r2_str, m['passed_r2'])}，"
                f"均线: {fmt_status(ma_str, m['passed_ma'])}，"
                f"成交量比值: {fmt_status(vol_val, m['passed_volume'])}，"
                f"短期风控: {fmt_status(loss_val, m['passed_loss'])}，"
                f"溢价率: {fmt_status(premium_str, m['passed_premium'])}，"
                f"拉普拉斯斜率: {m['laplace_slope']:.4f} {fmt_status('', m['passed_laplace'])}，"
                f"B型主线: {'✅' if m.get('passed_mainline') else '❌'}，"
                f"量价背离: {'✅' if m.get('passed_volume_divergence', True) else '❌'}"
            )
            log_buffer.append(line)
    else:
        log_buffer.append("（无符合条件的ETF）")
        log.info("\n".join(log_buffer))
        return []

    score_key = 'momentum_score'
    if len(top_10) >= g.holdings_num:
        reference_score = top_10[g.holdings_num - 1].get(score_key, float('-inf'))
        ratio = g.score_threshold_ratio if not g.is_a_share_weak else 1.0
        score_threshold = reference_score * ratio
        log_buffer.append("")
        log_buffer.append(f">>> 第三步：选取动量得分≥第{g.holdings_num}名({top_10[g.holdings_num - 1]['etf_name']})得分{reference_score:.4f}×{g.score_threshold_ratio}={score_threshold:.4f}的ETF <<<")
        candidate_pool = [item for item in top_10 if item.get(score_key, float('-inf')) >= score_threshold]
    else:
        log_buffer.append("")
        log_buffer.append(f">>> 第三步：前10名不足{g.holdings_num}只，全部作为候选池 <<<")
        candidate_pool = top_10[:]
    log_buffer.append(f"【候选池】共{len(candidate_pool)}只ETF（按动量得分排序）：")
    for i, item in enumerate(candidate_pool):
        if item.get('mainline_retained'):
            tag = " [主线延续]"
        elif item.get('passed_mainline'):
            tag = " [B型主线]"
        else:
            tag = ""
        log_buffer.append(f"  {i+1}. {item['etf_name']}({item['etf']}) {score_key}: {item.get(score_key, 0):.4f}{tag}")
    log_buffer.append("")
    log_buffer.append(">>> 第四步：结合当前持仓进行调整 <<<")
    current_holdings = [sec for sec, pos in context.portfolio.positions.items() if pos.amount > 0]
    log_buffer.append(f"当前持仓ETF：{current_holdings}")
    candidate_dict = {item['etf']: item for item in candidate_pool}
    retained = [candidate_dict[etf] for etf in current_holdings if etf in candidate_dict]
    log_buffer.append(f"其中存在于候选池中的持仓ETF：{[item['etf'] for item in retained]}")
    if len(retained) >= g.holdings_num:
        retained_sorted = sorted(retained, key=lambda x: x.get(score_key, float('-inf')), reverse=True)
        final_result = retained_sorted[:g.holdings_num]
        log_buffer.append(f"保留的持仓ETF数量({len(retained)})超过目标持仓数({g.holdings_num})，将从保留的ETF中按动量得分取前{g.holdings_num}只作为最终目标。")
    else:
        need = g.holdings_num - len(retained)
        remaining_pool = [item for item in candidate_pool if item['etf'] not in {r['etf'] for r in retained}]
        additional = remaining_pool[:need]
        final_result = retained + additional
        log_buffer.append(f"保留持仓ETF {len(retained)}只，还需补充{need}只。")
        if retained:
            log_buffer.append("保留的ETF（按原有顺序）：")
            for item in retained:
                log_buffer.append(f"  {item['etf_name']}({item['etf']})")
        if additional:
            log_buffer.append("补充的ETF（按动量得分排序）：")
            for i, item in enumerate(additional):
                if item.get('mainline_retained'):
                    tag = " [主线延续]"
                elif item.get('passed_mainline'):
                    tag = " [B型主线]"
                else:
                    tag = ""
                log_buffer.append(f"  {i+1}. {item['etf_name']}({item['etf']}) {score_key}: {item.get(score_key, 0):.4f}{tag}")
    log_buffer.append(f"【最终目标】共{len(final_result)}只ETF：")
    for i, item in enumerate(final_result):
        if item.get('mainline_retained'):
            tag = " [主线延续]"
        elif item.get('passed_mainline'):
            tag = " [B型主线]"
        else:
            tag = ""
        log_buffer.append(f"  {i+1}. {item['etf_name']}({item['etf']}){tag}")
    log_buffer.append("==================================================")
    log.info("\n".join(log_buffer))
    return final_result


def execute_sell_trades(context):
    """执行卖出：持仓不在目标列表中则全部卖出"""
    log.info("========== 卖出操作开始 ==========")
    ranked_etfs = getattr(g, 'ranked_etfs_result', [])
    target_etfs = []

    if ranked_etfs:
        for metrics in ranked_etfs[:g.holdings_num]:
            target_etfs.append(metrics['etf'])
            log.info(f"确定最终目标: {metrics['etf']} {metrics['etf_name']}")
    else:
        if check_defensive_etf_available(context):
            target_etfs = [g.defensive_etf]
            etf_name = get_security_name(g.defensive_etf)
            log.info(f"🛡️ 确定最终目标(防御模式): {g.defensive_etf} {etf_name}")
        else:
            log.info("💤 无最终目标(空仓模式)")
            target_etfs = []

    g.target_etfs_list = target_etfs
    current_positions = list(context.portfolio.positions.keys())
    log.info(f"【卖出前持仓】{[ (s, context.portfolio.positions[s].amount) for s in current_positions ]}")
    target_set = set(target_etfs)
    sell_count = 0

    for security in current_positions:
        position = context.portfolio.positions[security]
        if position.amount > 0 and security not in target_set:
            security_name = get_security_name(security)
            success = smart_order_target_value(security, 0, context)
            if success:
                sell_count += 1
                log.info(f"✅ 已成功卖出: {security} {security_name}")

    log.info(f"本次共计划卖出{sell_count}只ETF。")
    log.info("========== 卖出操作完成 ==========")


def execute_buy_trades(context):
    """执行买入：计算有效持仓→确定待买ETF→日内趋势判断→挂起未通过的待后续复检"""
    log.info("========== 买入操作开始（择时趋势判断）==========")
    g.pending_buy_etfs = []
    target_etfs = g.target_etfs_list

    if not target_etfs:
        log.info("根据计算的结果，今日无目标ETF，保持空仓")
        log.info("========== 买入操作完成 ==========")
        return

    current_positions = set(context.portfolio.positions.keys())
    etfs_to_buy = [etf for etf in target_etfs if etf not in current_positions]
    actual_holding_count = len(current_positions)
    # 同一Bar内先卖后买：若卖出订单尚未撮合落地，持仓计数仍含已卖标的。
    # 用「有效持仓」= 实际持仓 - 本Bar已下单卖出且仍在持仓中的标的，避免目标ETF被错误跳过。
    sold_set = getattr(g, 'sold_securities_today', set())
    sold_still_held = [s for s in sold_set if s in current_positions]
    effective_holding_count = actual_holding_count - len(sold_still_held)
    max_buy_count = max(0, g.holdings_num - effective_holding_count)
    num_etfs_to_buy = min(len(etfs_to_buy), max_buy_count)

    if num_etfs_to_buy <= 0:
        if sold_still_held:
            # 本Bar已卖出，成交落地后持仓将减少；将目标ETF挂起，待后续Bar（13:40+）复检买入
            g.pending_buy_etfs = list(etfs_to_buy)
            log.info(f"当前实际持仓({actual_holding_count})含本Bar已卖出{sold_still_held}，有效持仓{effective_holding_count}；"
                     f"目标ETF {g.pending_buy_etfs} 挂起，待成交落地后由13:40+复检买入")
        else:
            log.info(f"当前实际持仓数量({actual_holding_count})已达到或超过目标({g.holdings_num})，无需买入")
        log.info("========== 买入操作完成 ==========")
        return

    etfs_to_buy = etfs_to_buy[:num_etfs_to_buy]
    log.info(f"当前实际持仓: {actual_holding_count}只, 目标持仓: {g.holdings_num}只, 本次计划买入: {num_etfs_to_buy}只")

    g.pending_buy_etfs = list(etfs_to_buy)
    log.info(f"计划买入ETF: {g.pending_buy_etfs}，先进行13:10趋势判断；若不满足，将在13:40/14:00/14:10/14:30/14:40复检，14:55强制买入")
    execute_buy_with_trend(context, force=False)

    if g.pending_buy_etfs:
        log.info(f"⏳ 等待趋势确认的ETF: {g.pending_buy_etfs}")

    log.info("========== 买入操作完成（择时趋势判断）==========")


def check_intraday_trend(security, context):
    """日内趋势判断：30分钟加权回归斜率>0 + R²>0.3 + 量比≥0.8，确认上涨趋势"""
    try:
        minute_data = get_history(
            g.trend_lookback_minutes, frequency='1m', field=['close', 'volume'],
            security_list=security, fq='pre', include=True
        )
        if minute_data is None or minute_data.empty:
            log.info(f"【趋势判断】{security} 无分钟数据，默认上涨趋势")
            return True

        closes = minute_data['close'].values
        closes = closes[closes > 0]
        if len(closes) < 5:
            log.info(f"【趋势判断】{security} 有效分钟数据不足({len(closes)}根)，默认没有上涨趋势")
            return False

        n = len(closes)
        x = np.arange(n)
        weights = np.linspace(0.5, 2.0, n)
        w = weights / weights.sum()
        x_bar = np.sum(w * x)
        y_bar = np.sum(w * closes)
        dx = x - x_bar
        dy = closes - y_bar
        variance_x = np.sum(w * dx**2)
        if variance_x == 0:
            slope = 0
        else:
            slope = np.sum(w * dx * dy) / variance_x

        mean_price = y_bar if y_bar > 0 else closes.mean()
        slope_pct = slope / mean_price * 100 if mean_price > 0 else 0

        y_pred = slope * x + (y_bar - slope * x_bar)
        ss_res = np.sum(w * (closes - y_pred)**2)
        ss_tot = np.sum(w * (closes - y_bar)**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        passed_slope = slope_pct > g.trend_slope_threshold
        passed_r2 = r2 > g.trend_r2_threshold

        vol_ok = True
        vol_desc = ""
        if 'volume' in minute_data.columns:
            volumes = minute_data['volume'].values
            if len(volumes) >= 15:
                split = len(volumes) * 2 // 3
                recent_vol = np.mean(volumes[split:])
                earlier_vol = np.mean(volumes[:split])
                if earlier_vol > 0:
                    vol_ratio = recent_vol / earlier_vol
                    vol_ok = vol_ratio >= 0.8
                    vol_desc = f"量比={vol_ratio:.2f}(阈值≥0.8){'✓' if vol_ok else '✗'}"
        if not vol_desc:
            vol_desc = "量数据不足"

        is_uptrend = passed_slope and passed_r2 and vol_ok

        if not is_uptrend:
            if not passed_slope:
                trend_desc = "斜率不足"
            elif not passed_r2:
                trend_desc = "趋势质量差(R²过低)"
            elif not vol_ok:
                trend_desc = "成交量萎缩(疑似假突破)"
            else:
                trend_desc = "未知"
        else:
            trend_desc = "上涨趋势确认"
        log.info(
            f"【趋势判断】{security} 最近{n}分钟 | "
            f"斜率={slope_pct:.6f}%/min(阈值{g.trend_slope_threshold}){'✓' if passed_slope else '✗'} | "
            f"R²={r2:.3f}(阈值{g.trend_r2_threshold}){'✓' if passed_r2 else '✗'} | "
            f"{vol_desc} | "
            f"判定: {trend_desc}"
        )
        return is_uptrend

    except Exception as e:
        log.info(f"【趋势判断】{security} 异常: {e}，默认上涨趋势")
        return True


def execute_buy_with_trend(context, force=False):
    """执行买入（带趋势判断）：force=True时跳过趋势判断直接买入，否则逐只检查趋势"""
    if not g.pending_buy_etfs:
        return

    current_positions = set(context.portfolio.positions.keys())
    g.pending_buy_etfs = [etf for etf in g.pending_buy_etfs if etf not in current_positions]

    if not g.pending_buy_etfs:
        return

    current_time = context.blotter.current_dt.strftime('%H:%M')
    mode_desc = "强制买入" if force else "趋势判断"
    log.info(f"========== 买入操作开始（{mode_desc} {current_time}）==========")

    etfs_to_buy_now = []
    still_pending = []

    for etf in g.pending_buy_etfs:
        etf_name = get_security_name(etf)
        if force:
            etfs_to_buy_now.append(etf)
            log.info(f"⏰ {current_time} 强制买入 {etf} {etf_name}")
        else:
            if check_intraday_trend(etf, context):
                etfs_to_buy_now.append(etf)
                log.info(f"📈 {current_time} {etf} {etf_name} 趋势上涨，立即买入")
            else:
                still_pending.append(etf)
                log.info(f"📉 {current_time} {etf} {etf_name} 趋势未确认，等待下次判断")

    total_count = len(etfs_to_buy_now) + len(still_pending)
    for i, etf in enumerate(etfs_to_buy_now):
        remaining_cash = context.portfolio.cash
        if remaining_cash < g.min_money:
            log.info(f"可用现金 {remaining_cash:.2f} 不足最小交易额 {g.min_money:.2f}，停止买入")
            break

        remaining_to_buy = total_count - i
        target_value_for_this_etf = remaining_cash // remaining_to_buy

        if target_value_for_this_etf < g.min_money and remaining_cash >= g.min_money:
            target_value_for_this_etf = remaining_cash

        etf_name = get_security_name(etf)
        log.info(f"为 {etf} {etf_name} 分配目标金额: {target_value_for_this_etf:.2f} 元 (剩余现金 {remaining_cash:.2f}, 总待买 {remaining_to_buy})")

        success = smart_order_target_value(etf, target_value_for_this_etf, context)
        if success:
            log.info(f"✅ ETF {etf} 下单成功")
        else:
            log.info(f"❌ ETF {etf} 下单失败")

    g.pending_buy_etfs = still_pending

    if still_pending:
        log.info(f"⏳ 仍待趋势确认的ETF: {still_pending}")
    else:
        log.info("✅ 所有待买ETF已处理完毕")

    log.info(f"========== 买入操作完成（{mode_desc}）==========")


def check_pending_buys_trend(context):
    """13:40/14:00/14:10/14:30/14:40定时复检：对挂起的待买ETF重新做趋势判断"""
    if not g.pending_buy_etfs:
        return
    log.info("★" * 80)
    log.info("▶️ 【趋势复检】检查待买ETF趋势...")
    execute_buy_with_trend(context, force=False)
    if g.pending_buy_etfs:
        log.info(f"⏳ 仍在等待的ETF: {g.pending_buy_etfs}")
    log.info("⏸️ 【趋势复检】执行完毕！")


def force_buy_pending(context):
    """14:55尾盘强制买入：跳过趋势判断，买入所有剩余待买ETF"""
    if not g.pending_buy_etfs:
        return
    log.info("★" * 80)
    log.info("▶️ 【14:55强制买入】强制买入所有待买ETF...")
    execute_buy_with_trend(context, force=True)
    log.info("⏸️ 【14:55强制买入】执行完毕！")


def check_defensive_etf_available(context):
    """检查防御ETF是否可交易：未停牌、未涨跌停、价格有效"""
    defensive_etf = g.defensive_etf
    if _get_realtime_paused(defensive_etf):
        return False
    high_limit = _get_realtime_high_limit(defensive_etf)
    low_limit = _get_realtime_low_limit(defensive_etf)
    last_price = _get_realtime_price(defensive_etf)
    if last_price <= 0:
        return False
    if high_limit != float('inf') and last_price >= high_limit:
        return False
    if low_limit > 0 and last_price <= low_limit:
        return False
    return True


def smart_order_target_value(security, target_value, context):
    """智能下单：按目标金额下单，自动处理涨跌停、停牌、最小交易额、100股整数倍等限制"""
    security_name = get_security_name(security)

    if target_value > 0:
        available_cash = context.portfolio.cash  # 可用现金
        if target_value > available_cash:
            target_value = available_cash  # 目标金额不超过可用现金
        if target_value < g.min_money:
            log.info(f"{security} {security_name}: 目标金额{target_value:.2f}小于最小交易额{g.min_money}，跳过")
            return False

    if _get_realtime_paused(security):
        log.info(f"{security} {security_name}: 今日停牌，跳过交易")
        return False
    current_price = _get_realtime_price(security)  # 实时价格
    high_limit = _get_realtime_high_limit(security)  # 涨停价
    low_limit = _get_realtime_low_limit(security)  # 跌停价
    if current_price <= 0:
        log.info(f"{security} {security_name}: 当前价格为0，跳过交易")
        return False
    if high_limit != float('inf') and current_price >= high_limit:
        log.info(f"{security} {security_name}: 当前涨停，跳过交易")
        return False
    if low_limit > 0 and current_price <= low_limit:
        log.info(f"{security} {security_name}: 当前跌停，跳过交易")
        return False

    buy_commission_rate = 0.0001  # 买入佣金率（万分之一）
    slippage_rate = 0.0001  # 滑点率（万分之一）
    estimated_price = current_price * (1 + buy_commission_rate + slippage_rate)  # 预估含成本价格

    if target_value > 0:
        target_amount = int(target_value / estimated_price)  # 目标股数（按预估价格计算）
        target_amount = (target_amount // 100) * 100  # 取100股整数倍
        if target_amount <= 0 and target_value > 0:
            target_amount = 100  # 至少买100股
        max_shares = int(context.portfolio.cash / current_price)  # 现金可买最大股数
        max_shares = (max_shares // 100) * 100  # 取100股整数倍
        if max_shares < target_amount:
            log.info(f"{security} {security_name}: 现金可买{max_shares}股，原计划{target_amount}股，已调低")
            target_amount = max_shares
        if target_amount <= 0:
            log.info(f"{security} {security_name}: 现金不足买100股，跳过")
            return False
    else:
        target_amount = 0  # 目标为0表示清仓

    current_position = context.portfolio.positions.get(security, None)  # 当前持仓
    current_amount = current_position.amount if current_position else 0  # 当前持仓股数
    amount_diff = target_amount - current_amount  # 买卖差额（正=买入，负=卖出）
    trade_value = abs(amount_diff) * current_price  # 交易金额

    if 0 < trade_value < g.min_money:
        log.info(f"{security} {security_name}: 交易金额{trade_value:.2f}小于最小交易额{g.min_money}，跳过")
        return False

    if amount_diff < 0:
        closeable_amount = current_position.enable_amount if current_position else 0  # 可卖出股数（T+1限制）
        if closeable_amount == 0:
            log.info(f"{security} {security_name}: 当天买入不可卖出(T+1)")
            return False
        amount_diff = -min(abs(amount_diff), closeable_amount)  # 实际卖出数量不超过可卖数量

    if amount_diff != 0:
        order_result = order(security, amount_diff)  # 下单（正=买入，负=卖出）
        if order_result:
            if amount_diff > 0:
                log.info(f"📦 买入{security} {security_name}，数量: {amount_diff}，价格: {current_price:.3f} (预估含成本价: {estimated_price:.3f})")
            else:
                log.info(f"📤 卖出{security} {security_name}，数量: {abs(amount_diff)}，价格: {current_price:.3f}")
                try:
                    g.sold_securities_today.add(security)  # 记录今日已卖出
                except Exception:
                    pass
            # 诊断：打印 order 返回，确认订单是否被平台接受/拒单
            log.info(f"[诊断] order({security}, {amount_diff}) 返回: {order_result}")
            return True
        else:
            log.warning(f"下单失败: {security} {security_name}，数量: {amount_diff}")
            return False
    return False


def minute_level_stop_loss(context):
    """分钟级固定止损：价格跌破成本×95%立即卖出（默认关闭）"""
    if not g.use_fixed_stop_loss:
        return

    current_time = context.blotter.current_dt.strftime('%H:%M')
    if not (('09:25' < current_time < '11:30') or ('13:00' < current_time < '14:57')):
        return

    for security in list(context.portfolio.positions.keys()):
        position = context.portfolio.positions[security]
        if position.amount <= 0 or position.enable_amount <= 0:
            continue

        current_price = _get_realtime_price(security)
        if current_price <= 0:
            continue

        cost_price = position.cost_basis
        if cost_price <= 0:
            continue

        if current_price <= cost_price * g.fixedStopLossThreshold:
            security_name = get_security_name(security)
            loss_percent = (current_price / cost_price - 1) * 100
            log.info(f"🚨 【分钟级固定止损】{security} {security_name} 触发止损，亏损: {loss_percent:.2f}%")
            smart_order_target_value(security, 0, context)


def minute_level_pct_stop_loss(context):
    if not g.use_pct_stop_loss:
        return

    current_time = context.blotter.current_dt.strftime('%H:%M')
    if not (('09:25' < current_time < '11:30') or ('13:00' < current_time < '14:57')):
        return

    current_date = context.blotter.current_dt.date()

    if not hasattr(g, 'cache_date') or g.cache_date != current_date:
        g.yesterday_close_cache = {}
        g.cache_date = current_date

    for security in list(context.portfolio.positions.keys()):
        position = context.portfolio.positions[security]
        if position.amount <= 0 or position.enable_amount <= 0:
            continue

        yesterday_close = getattr(g, 'yesterday_close_cache', {}).get(security)
        if yesterday_close is None:
            try:
                close_series = get_history(1, frequency='1d', field=['close'],
                                           security_list=security, fq='pre', include=False)
                if close_series is None or len(close_series) == 0 or 'close' not in close_series.columns:
                    continue
                yesterday_close = float(close_series['close'].values[-1])
                if yesterday_close <= 0:
                    continue
                g.yesterday_close_cache[security] = yesterday_close
            except Exception:
                continue
