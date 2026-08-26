# 克隆自聚宽文章：https://www.joinquant.com/post/71985
# 标题：向大神致敬！，将烟花三月的五福闹春5.1 完美翻译成P.T
# 作者：庆大祥

# 克隆自聚宽文章：https://www.joinquant.com/post/71413
# 标题：【五福闹新春】v5.1-拟合ETF池最严厉的父亲
# 作者：烟花三月ETF

import datetime as dt
import numpy as np
import pandas as pd
import math


def get_batch_hist(stock_list, count, fields, freq='1d', include=False):
    result = {}
    batch_size = 200
    for i in range(0, len(stock_list), batch_size):
        batch = stock_list[i:i + batch_size]
        try:
            # 逐个获取历史数据，因为这个平台的 get_history 可能不支持批量
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
    if is_trade():
        snap = get_snapshot(security)
        if snap and snap.get(security):
            px = snap[security].get('last_px', 0)
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
    if is_trade():
        snap = get_snapshot(security)
        if snap and snap.get(security):
            status = snap[security].get('trade_status', '')
            return status in ('HALT', 'SUSP', 'STOPT')
    return False


def _get_realtime_high_limit(security):
    if is_trade():
        snap = get_snapshot(security)
        if snap and snap.get(security):
            return snap[security].get('up_px', float('inf'))
    hist = get_history(1, frequency='1d', field=['high_limit'],
                       security_list=security, fq='pre', include=True)
    if hist is not None and not hist.empty and 'high_limit' in hist.columns:
        return float(hist['high_limit'].iloc[-1])
    return float('inf')


def _get_realtime_low_limit(security):
    if is_trade():
        snap = get_snapshot(security)
        if snap and snap.get(security):
            return snap[security].get('down_px', 0)
    hist = get_history(1, frequency='1d', field=['low_limit'],
                       security_list=security, fq='pre', include=True)
    if hist is not None and not hist.empty and 'low_limit' in hist.columns:
        return float(hist['low_limit'].iloc[-1])
    return 0


def initialize(context):
    set_params()
    set_backtest()
    g.cache_date = None
    g.yesterday_close_cache = {}
    g.ranked_etfs_result = []
    g.target_etfs_list = []
    g.drawdown_records = []
    g.all_positions_records = []
    g.max_portfolio_value = 0
    g.etf_names_dict = {}
    if not is_trade():
        g.my_cost_basis = {}
        g.my_shares = {}

    print("【五福闹新春】v5.1-PT 启动！")

    run_daily(context, check_weak_period_daily, time='09:40')
    run_daily(context, afternoon_routine, time='13:10')
    run_daily(context, reset_daily_flags, time='15:10')

def before_trading_start(context, data):
    log.info("【before_trading_start】")
    morning_routine(context)
    log.info("【before_trading_start】 morningmorning_routine")


def handle_data(context, data):
    if not is_trade():
        return
    minute_level_stop_loss(context)
    #log.info("【handle_data】minute_level_stop_loss")
    minute_level_pct_stop_loss(context)
    #log.info("【handle_data】minute_level_pct_stop_loss")

def after_trading_end(context, data):
    log.info("【after_trading_end】")
    record_daily_positions_to_storage(context)
    log.info("【after_trading_end】record_daily_positions_to_storage")
    output_all_positions_summary(context)
    log.info("【after_trading_end】output_all_positions_summary")

def set_params():
    g.global_etf_pool = [
        '518880.SS', '501018.SS', '161226.SZ', '159985.SZ',
        '159980.SZ', '513310.SS', '159518.SZ', '159509.SZ',
        '513100.SS', '513520.SS', '513500.SS', '159502.SZ',
        '513400.SS', '513030.SS', '513290.SS', '520830.SS',
        '159529.SZ',
    ]

    g.china_etf_pool = [
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

    g.fixed_etf_pool = g.global_etf_pool + g.china_etf_pool

    g.avg_etf_money_threshold = None
    g.filtered_fixed_pool = []
    g.filtered_global_pool = []
    g.dynamic_etf_pool = []
    g.merged_etf_pool = []

    g.is_a_share_weak = False
    g.weak_period_ma_lookback = 10
    g.weak_start_date = None
    g.weak_days_count = 0
    g.max_weak_days = 20

    g.holdings_num = 1
    g.defensive_etf = '511880.SS'
    g.min_money = 10000

    g.lookback_days = 25
    g.min_score_threshold = 0
    g.max_score_threshold = 5
    g.score_threshold_ratio = 0.9

    g.enable_r2_filter = True
    g.r2_threshold = 0.4
    g.enable_ma_filter = True
    g.ma_lookback = 10
    g.ma_threshold = 1.0
    g.enable_volume_check = True
    g.volume_lookback = 5
    g.volume_threshold = 1.8
    g.enable_loss_filter = True
    g.loss = 0.97
    g.enable_premium_filter = False
    g.max_premium_rate = 30
    g.enable_laplace_filter = True
    g.laplace_s_param = 0.05
    g.laplace_min_slope = 0.002

    g.max_portfolio_value = 0
    g.drawdown_threshold = 0.03

    g.use_fixed_stop_loss = True
    g.fixedStopLossThreshold = 0.95
    g.use_pct_stop_loss = False
    g.pct_stop_loss_threshold = 0.95


def set_backtest():
    if not is_trade():
        set_limit_mode('UNLIMITED')
        set_commission(commission_ratio=0.0001, min_commission=5.0)


def morning_routine(context):
    check_positions(context)
    monitor_drawdown(context)
    calculate_global_etf_threshold(context)


def check_weak_period_daily(context):
    result = check_a_share_weak_period(context)
    status = "🔴 大A走弱期" if result else "🟢 大A正常期"
    print("【调试】09:40判断 - {}".format(status))
    midday_routine(context)


def midday_routine(context):
    print("【调试】midday_routine 开始执行")
    print("【调试】g.is_a_share_weak: {}".format(g.is_a_share_weak))
    if g.is_a_share_weak:
        filter_global_pool_by_volume(context)
    else:
        update_sector_pool(context)
        filter_fixed_pool_by_volume(context)
        daily_merge_etf_pools(context)
    print("【调试】midday_routine 执行结束")


def afternoon_routine(context):
    print("【调试】afternoon_routine 开始执行")
    print("【调试】g.is_a_share_weak: {}".format(g.is_a_share_weak))
    if g.is_a_share_weak:
        if hasattr(g, 'filtered_global_pool') and g.filtered_global_pool:
            g.merged_etf_pool = list(set(g.filtered_global_pool))
            print("【调试】使用filtered_global_pool, 数量: {}".format(len(g.filtered_global_pool)))
        else:
            g.merged_etf_pool = list(set(g.global_etf_pool))
            print("【调试】使用global_etf_pool, 数量: {}".format(len(g.global_etf_pool)))
        g.merged_etf_pool.sort()
    else:
        if hasattr(g, 'merged_etf_pool'):
            print("【调试】merged_etf_pool 数量: {}".format(len(g.merged_etf_pool)))
    
    calculate_and_log_ranked_etfs(context)
    execute_sell_trades(context)
    execute_buy_trades(context)
    print("【调试】afternoon_routine 执行结束")


def reset_daily_flags(context):
    g.cache_date = None
    g.yesterday_close_cache = {}


def check_positions(context):
    pass


def monitor_drawdown(context):
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
                        positions_info.append("{}:{}股".format(security_name, position.amount))
                record['positions'] = positions_info
                g.drawdown_records.append(record)
    except Exception:
        pass


def _get_all_etf_list():
    etf_list = []
    try:
        if is_trade():
            etf_list = get_etf_list()
        else:
            seen = set()
            code_list = get_trend_data().keys()
            #print("get_trend_data code_list:{}".format(code_list))
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
    return etf_list


def calculate_global_etf_threshold(context):
    try:
        all_etfs = _get_all_etf_list()
        if not all_etfs:
            g.avg_etf_money_threshold = 10000000
            return
        hist_data = get_batch_hist(all_etfs, 3, ['money'], freq='1d')
        if not hist_data:
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
        if len(totals) < 3:
            g.avg_etf_money_threshold = 10000000
            return
        avg_total_money = sum(totals) / len(totals)
        threshold = avg_total_money / 3000
        g.avg_etf_money_threshold = threshold
    except Exception:
        g.avg_etf_money_threshold = 10000000


def filter_global_pool_by_volume(context):
    if getattr(g, 'avg_etf_money_threshold', None) is None:
        calculate_global_etf_threshold(context)
    if not g.global_etf_pool:
        g.filtered_global_pool = []
        return
    dynamic_threshold = g.avg_etf_money_threshold
    TRADE_DAYS_COUNT = 3
    try:
        hist_data = get_batch_hist(g.global_etf_pool, TRADE_DAYS_COUNT, ['money'], freq='1d')
        if not hist_data:
            g.filtered_global_pool = g.global_etf_pool[:]
            return
        avg_money_map = {}
        for s, d in hist_data.items():
            money_list = d.get('money', [])
            if len(money_list) >= TRADE_DAYS_COUNT:
                avg_money_map[s] = sum(money_list) / TRADE_DAYS_COUNT
        g.filtered_global_pool = [s for s, m in avg_money_map.items() if m > dynamic_threshold]
    except Exception:
        g.filtered_global_pool = g.global_etf_pool[:]


def update_sector_pool(context):
    if g.avg_etf_money_threshold is None:
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
        '全指现金', '现金全指', 'ESG', 'MSCI', 'MS', '债', '信用',
    ])), key=len, reverse=True)

    all_etf_codes = _get_all_etf_list()
    if not all_etf_codes:
        all_etf_codes = list(set(g.global_etf_pool + g.china_etf_pool))

    for code in all_etf_codes:
        if code not in g.etf_names_dict:
            try:
                info = get_security_info(code)
                display_name = str(getattr(info, 'display_name', '') or getattr(info, 'name', '') or code)
                g.etf_names_dict[code] = display_name
            except Exception:
                g.etf_names_dict[code] = code

    normal_etfs = []
    special_etfs = []
    special_group_map = {}
    excluded_count = 0

    for code in all_etf_codes:
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

    bond_code_prefixes = ('511', '159001', '159609', '159613', '159650', '159651')
    normal_etfs = [c for c in normal_etfs if not c.startswith(bond_code_prefixes)]
    special_etfs = [c for c in special_etfs if not c.startswith(bond_code_prefixes)]

    dynamic_threshold = g.avg_etf_money_threshold
    TRADE_DAYS_COUNT = 3

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

    if not normal_sorted and not special_sorted:
        g.dynamic_etf_pool = []
        return

    def get_remove_words_for_etf(is_special, matched_group_name):
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
            for word in get_remove_words_for_etf(is_special, matched_group_name):
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
            group_key = "{}_{}".format(matched_group, industry_key)
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
    top_100 = final_pool_info_sorted[:100]
    g.dynamic_etf_pool = [item['code'] for item in top_100]


def filter_fixed_pool_by_volume(context):
    if getattr(g, 'avg_etf_money_threshold', None) is None:
        calculate_global_etf_threshold(context)
    if not g.fixed_etf_pool:
        return
    dynamic_threshold = g.avg_etf_money_threshold
    TRADE_DAYS_COUNT = 3
    try:
        hist_data = get_batch_hist(g.fixed_etf_pool, TRADE_DAYS_COUNT, ['money'], freq='1d')
        if not hist_data:
            g.filtered_fixed_pool = g.fixed_etf_pool[:]
            return
        avg_money_map = {}
        for s, d in hist_data.items():
            money_list = d.get('money', [])
            if len(money_list) >= TRADE_DAYS_COUNT:
                avg_money_map[s] = sum(money_list) / TRADE_DAYS_COUNT
        g.filtered_fixed_pool = [s for s, m in avg_money_map.items() if m > dynamic_threshold]
    except Exception:
        g.filtered_fixed_pool = g.fixed_etf_pool[:]


def daily_merge_etf_pools(context):
    if not hasattr(g, 'filtered_fixed_pool'):
        g.filtered_fixed_pool = g.fixed_etf_pool[:]
    
    fixed_set = set(g.filtered_fixed_pool)
    dynamic_set = set(g.dynamic_etf_pool)
    duplicates = fixed_set & dynamic_set
    
    merged = list(set(g.filtered_fixed_pool + g.dynamic_etf_pool))
    merged.sort()
    g.merged_etf_pool = merged


def calculate_and_log_ranked_etfs(context):
    print("【调试】calculate_and_log_ranked_etfs 开始执行")
    if not hasattr(g, 'merged_etf_pool') or not g.merged_etf_pool:
        print("【调试】merged_etf_pool为空或不存在")
        g.ranked_etfs_result = []
        return
    print("【调试】merged_etf_pool大小: {}".format(len(g.merged_etf_pool)))
    final_list = get_final_ranked_etfs(context)
    print("【调试】get_final_ranked_etfs返回数量: {}".format(len(final_list)))
    g.ranked_etfs_result = final_list


def calculate_momentum_score(price_series, lookback_days):
    if len(price_series) < lookback_days + 1:
        return None, None, None
    recent_price_series = price_series[-(lookback_days + 1):]
    y = np.log(recent_price_series)
    x = np.arange(len(y))
    weights = np.linspace(1, 2, len(y))
    W = weights ** 2
    W_sum = np.sum(W)
    x_bar = np.sum(W * x) / W_sum
    y_bar = np.sum(W * y) / W_sum
    dx = x - x_bar
    dy = y - y_bar
    variance_x = np.sum(W * dx**2)
    if variance_x == 0:
        return 0, 0, 0
    slope = np.sum(W * dx * dy) / variance_x
    intercept = y_bar - slope * x_bar
    annualized_returns = math.exp(slope * 250) - 1
    y_pred = slope * x + intercept
    ss_res = np.sum(weights * (y - y_pred) ** 2)
    ss_tot = np.sum(weights * (y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot else 0
    momentum_score = annualized_returns * r_squared
    return momentum_score, annualized_returns, r_squared


def get_volume_ratio(hist_volumes, today_vol, context, lookback_days=None):
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
    try:
        current_price = _get_realtime_price(etf)
        if current_price <= 0:
            return None, True
        nav_data = get_history(5, frequency='1d', field=['unit_nav'], security_list=etf, fq='pre', include=False)
        if nav_data is not None and len(nav_data) > 0 and 'unit_nav' in nav_data.columns:
            nav_values = nav_data['unit_nav'].values
            valid_nav = nav_values[~np.isnan(nav_values)]
            if len(valid_nav) > 0:
                nav = valid_nav[-1]
                if nav > 0:
                    premium_rate = (current_price / nav - 1) * 100
                    passed = abs(premium_rate) <= g.max_premium_rate
                    return premium_rate, passed
    except Exception:
        pass
    return None, True


def laplace_filter(price, s=0.05):
    alpha = 1 - np.exp(-s)
    L = np.zeros(len(price))
    L[0] = price[0]
    for t in range(1, len(price)):
        L[t] = alpha * price[t] + (1 - alpha) * L[t - 1]
    return L


def check_a_share_weak_period(context):
    today = context.blotter.current_dt.date()
    indexes = {
        '大盘': '000300.SS',
        '小盘': '399101.SZ',
        '创业板': '399006.SZ',
        '中证A500': '000510.SS'
    }

    above_count = 0
    below_count = 0
    index_details = []
    for name, code in indexes.items():
        try:
            hist_data = get_history(g.weak_period_ma_lookback + 1, frequency='1d', field=['close'], security_list=code, fq='pre', include=False)
            if hist_data is None or len(hist_data) < g.weak_period_ma_lookback:
                data_len = len(hist_data) if hist_data is not None else 0
                index_details.append("{}({}): 数据不足({})".format(name, code, data_len))
                continue
            closes = hist_data['close'].values
            current_price = closes[-1]
            ma_val = np.mean(closes[-g.weak_period_ma_lookback:])
            is_above = current_price > ma_val
            is_below = current_price < ma_val
            status = "↑线上" if is_above else ("↓线下" if is_below else "=持平")
            ma_len = len(closes[-g.weak_period_ma_lookback:])
            index_details.append("{}({}): 价格={:.3f} MA{}={:.3f} {}".format(name, code, current_price, ma_len, ma_val, status))
            if is_above:
                above_count += 1
            if is_below:
                below_count += 1
        except Exception as e:
            index_details.append("{}({}): 异常={}".format(name, code, e))
            continue

    weak_condition_met = (below_count >= 3)
    exit_condition_met = (above_count >= 3)

    if g.is_a_share_weak and g.weak_start_date is not None:
        trade_days = get_trade_days(start_date=g.weak_start_date, end_date=today)
        g.weak_days_count = len(trade_days) if trade_days is not None and len(trade_days) > 0 else 0
    else:
        g.weak_days_count = 0
    max_days_exceeded = (g.weak_days_count >= g.max_weak_days)

    if g.is_a_share_weak:
        if max_days_exceeded:
            g.is_a_share_weak = False
            g.weak_start_date = None
            g.weak_days_count = 0
        elif exit_condition_met:
            g.is_a_share_weak = False
            g.weak_start_date = None
            g.weak_days_count = 0
        elif weak_condition_met:
            g.weak_start_date = today
            g.weak_days_count = 0
    else:
        if weak_condition_met:
            g.is_a_share_weak = True
            g.weak_start_date = today
            g.weak_days_count = 0

    g.weak_index_details = index_details
    prev_weak = getattr(g, '_prev_is_a_share_weak', False)
    status_text = '走弱' if g.is_a_share_weak else '正常'
    #print("【调试】  状态机: prev_weak={} above={} below={} exit={} weak={} days={} max_exceeded={} → {}".format(prev_weak, above_count, below_count, exit_condition_met, weak_condition_met, g.weak_days_count, max_days_exceeded, status_text))
    g._prev_is_a_share_weak = g.is_a_share_weak
    return g.is_a_share_weak


def apply_filters(metrics_list):
    steps = [
        ('动量得分', lambda m: m['passed_momentum'], True),
        ('R²', lambda m: m['passed_r2'], g.enable_r2_filter and not g.is_a_share_weak),
        ('均线', lambda m: m['passed_ma'], g.enable_ma_filter and g.is_a_share_weak),
        ('成交量', lambda m: m['passed_volume'], g.enable_volume_check),
        ('短期风控', lambda m: m['passed_loss'], g.enable_loss_filter),
        ('溢价率', lambda m: m['passed_premium'], g.enable_premium_filter),
        ('拉普拉斯滤波', lambda m: m['passed_laplace'], g.enable_laplace_filter),
    ]
    filtered = metrics_list[:]
    for name, condition, is_enabled in steps:
        if is_enabled:
            filtered = [m for m in filtered if condition(m)]
    return filtered


def calculate_all_metrics_for_etf(etf, etf_name, hist_closes, hist_volumes, current_price, today_vol, context):
    try:
        price_series = np.append(hist_closes, current_price)
        if len(price_series) < g.lookback_days * 0.8:
            return None
        momentum_score, annualized_returns, r_squared = calculate_momentum_score(price_series, g.lookback_days)
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
        }
    except Exception:
        return None


def get_final_ranked_etfs(context):
    print("【调试】get_final_ranked_etfs 开始执行")
    all_metrics = []
    etf_set = list(g.merged_etf_pool)
    print("【调试】etf_set大小: {}".format(len(etf_set)))

    lookback = max(g.lookback_days, g.volume_lookback, g.ma_lookback) + 20
    safe_lookback = lookback + 20
    print("【调试】lookback: {}, safe_lookback: {}".format(lookback, safe_lookback))

    # 尝试多个不同的lookback天数
    hist_data = None
    #print("【调试】etf_set：{}".format(etf_set))
    for try_days in [safe_lookback, lookback, 20, 10, 5]:
        hist_data = get_batch_hist(etf_set, try_days, ['close', 'volume'], freq='1d')
        if hist_data and len(hist_data) > 0:
            print("【调试】使用{}天数据，hist_data大小: {}".format(try_days, len(hist_data)))
            # 如果使用了较短的lookback，相应调整后续逻辑中需要的天数
            if try_days < lookback:
                lookback = try_days
            break
    if not hist_data or len(hist_data) == 0:
        print("【调试】所有尝试都失败，hist_data为空")
        return []

    now = context.blotter.current_dt
    elapsed_minutes = (now.hour - 9) * 60 + now.minute - 30
    if now.hour >= 13:
        elapsed_minutes -= 90
    elapsed_minutes = max(1, min(elapsed_minutes, 240))
    
    today_vol_data = get_batch_hist(etf_set, elapsed_minutes, ['volume'], freq='1m')
    today_vols = {}
    for s, d in today_vol_data.items():
        vol_list = d.get('volume', [])
        today_vols[s] = sum(vol_list) if vol_list else 0

    for etf in etf_set:
        try:
            if _get_realtime_paused(etf):
                continue
            if etf not in hist_data:
                continue

            d = hist_data[etf]
            closes = d.get('close', [])
            volumes = d.get('volume', [])
            if len(closes) < lookback:
                continue

            valid_mask = (~np.isnan(volumes)) & (np.array(volumes) > 0)
            if not any(valid_mask):
                continue

            valid_indices = np.where(valid_mask)[0]
            hist_closes = np.array(closes)[valid_indices][-lookback:]
            hist_volumes = np.array(volumes)[valid_indices][-lookback:]

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
        except Exception:
            continue

    for item in all_metrics:
        score = item.get('momentum_score')
        if score is None or (isinstance(score, float) and np.isnan(score)):
            item['momentum_score'] = float('-inf')

    all_metrics.sort(key=lambda x: x.get('momentum_score', float('-inf')), reverse=True)

    print("【调试】第一步-排名前5（过滤前）:")
    for idx, m in enumerate(all_metrics[:5]):
        print("【调试】  {}. {} {} 动量得分={:.4f} r2={:.4f} MA={} 量比={} 拉普拉斯={}".format(idx+1, m['etf'], m['etf_name'], m['momentum_score'], m['r_squared'], m['passed_ma'], m['volume_ratio'], m['passed_laplace']))

    filtered_list = apply_filters(all_metrics)
    filtered_list.sort(key=lambda x: x.get('momentum_score', float('-inf')), reverse=True)

    print("【调试】第二步-排名前3（过滤后）:")
    for idx, m in enumerate(filtered_list[:3]):
        print("【调试】  {}. {} {} 动量得分={:.4f} r2={:.4f} MA={} 量比={} 拉普拉斯={}".format(idx+1, m['etf'], m['etf_name'], m['momentum_score'], m['r_squared'], m['passed_ma'], m['volume_ratio'], m['passed_laplace']))

    top_10 = filtered_list[:10]
    if not top_10:
        return []

    score_key = 'momentum_score'
    if len(top_10) >= g.holdings_num:
        reference_score = top_10[g.holdings_num - 1].get(score_key, float('-inf'))
        ratio = g.score_threshold_ratio if not g.is_a_share_weak else 1.0
        score_threshold = reference_score * ratio
        candidate_pool = [item for item in top_10 if item.get(score_key, float('-inf')) >= score_threshold]
    else:
        candidate_pool = top_10[:]

    current_holdings = [sec for sec, pos in context.portfolio.positions.items() if pos.amount > 0]
    print("【调试】当前持仓: {}".format(current_holdings))
    candidate_dict = {item['etf']: item for item in candidate_pool}
    print("【调试】候选池大小: {}".format(len(candidate_pool)))
    retained = [candidate_dict[etf] for etf in current_holdings if etf in candidate_dict]
    print("【调试】保留的持仓数量: {}".format(len(retained)))

    if len(retained) >= g.holdings_num:
        retained_sorted = sorted(retained, key=lambda x: x.get(score_key, float('-inf')), reverse=True)
        final_result = retained_sorted[:g.holdings_num]
        print("【调试】从保留持仓中选取，数量: {}".format(len(final_result)))
    else:
        need = g.holdings_num - len(retained)
        remaining_pool = [item for item in candidate_pool if item['etf'] not in {r['etf'] for r in retained}]
        additional = remaining_pool[:need]
        final_result = retained + additional
        print("【调试】保留{}，新增{}，总共{}".format(len(retained), len(additional), len(final_result)))

    print("【调试】get_final_ranked_etfs 返回结果: {}".format([x['etf'] for x in final_result]))
    return final_result


def get_security_name(security):
    try:
        if hasattr(g, 'etf_names_dict') and security in g.etf_names_dict:
            return g.etf_names_dict[security]
        info = get_security_info(security)
        name = getattr(info, 'display_name', '') or getattr(info, 'name', '')
        return str(name) if name else security
    except Exception:
        return security


def check_defensive_etf_available(context):
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


def execute_sell_trades(context):
    print("【调试】execute_sell_trades 开始执行")
    ranked_etfs = getattr(g, 'ranked_etfs_result', [])
    print("【调试】ranked_etfs_result数量: {}".format(len(ranked_etfs)))
    target_etfs = []

    if ranked_etfs:
        for metrics in ranked_etfs[:g.holdings_num]:
            target_etfs.append(metrics['etf'])
        print("【调试】从排名中选取的目标ETF: {}".format(target_etfs))
    else:
        if check_defensive_etf_available(context):
            target_etfs = [g.defensive_etf]
            print("【调试】使用防御性ETF: {}".format(g.defensive_etf))
        else:
            target_etfs = []
            print("【调试】防御性ETF不可用，无目标ETF")

    g.target_etfs_list = target_etfs
    current_positions = list(context.portfolio.positions.keys())
    print("【调试】当前持仓: {}".format(current_positions))
    target_set = set(target_etfs)

    sold = False
    for security in current_positions:
        position = context.portfolio.positions[security]
        if position.amount > 0 and security not in target_set:
            print("【调试】准备卖出: {}, 数量: {}".format(security, position.amount))
            smart_order_target_value(security, 0, context)
            sold = True
    
    if not sold:
        print("【调试】没有需要卖出的持仓")


def execute_buy_trades(context):
    print("【调试】execute_buy_trades 开始执行")
    target_etfs = g.target_etfs_list
    print("【调试】目标ETF列表: {}".format(target_etfs))
    if not target_etfs:
        print("【调试】无目标ETF，返回")
        return

    current_positions = set(context.portfolio.positions.keys())
    print("【调试】当前持仓集合: {}".format(current_positions))
    etfs_to_buy = [etf for etf in target_etfs if etf not in current_positions]
    print("【调试】需要买入的ETF: {}".format(etfs_to_buy))
    
    actual_holding_count = len([s for s in context.portfolio.positions.keys() if context.portfolio.positions[s].amount > 0])
    print("【调试】实际持仓数量: {}".format(actual_holding_count))
    print("【调试】g.holdings_num: {}".format(g.holdings_num))
    max_buy_count = max(0, g.holdings_num - actual_holding_count)
    print("【调试】最大可买入数量: {}".format(max_buy_count))
    num_etfs_to_buy = min(len(etfs_to_buy), max_buy_count)
    print("【调试】实际将买入数量: {}".format(num_etfs_to_buy))
    if num_etfs_to_buy <= 0:
        print("【调试】无需买入，返回")
        return

    etfs_to_buy = etfs_to_buy[:num_etfs_to_buy]
    for i, etf in enumerate(etfs_to_buy):
        remaining_cash = context.portfolio.cash
        print("【调试】买入{}: 剩余现金{}".format(etf, remaining_cash))
        if remaining_cash < g.min_money:
            print("【调试】现金不足{}，停止买入".format(g.min_money))
            break
        remaining_to_buy = len(etfs_to_buy) - i
        target_value_for_this_etf = remaining_cash // remaining_to_buy
        if target_value_for_this_etf < g.min_money and remaining_cash >= g.min_money:
            target_value_for_this_etf = remaining_cash
        print("【调试】为{}分配资金: {}".format(etf, target_value_for_this_etf))
        smart_order_target_value(etf, target_value_for_this_etf, context)


def _get_etf_type(security):
    if hasattr(g, 'global_etf_pool') and security in g.global_etf_pool:
        return 'overseas'
    etf_name = g.etf_names_dict.get(security, '')
    commodity_keywords = ['黄金', '白银', '原油', '豆粕', '有色', '金', '银', '铜']
    commodity_codes = ('518880', '501018', '161226', '159985', '159980')
    if security.startswith(commodity_codes) or (security in g.global_etf_pool and any(kw in etf_name for kw in commodity_keywords)):
        return 'commodity'
    hk_prefixes = ('5130', '5131', '5133', '5137', '5139', '1598', '1599')
    if security.startswith(hk_prefixes):
        hk_keywords = ['恒生', '港股', 'HK', 'H股', '香港', '中概', '消费']
        if any(kw in etf_name for kw in hk_keywords):
            return 'hk'
    return 'a_share'


def smart_order_target_value(security, target_value, context):
    security_name = get_security_name(security)
    etf_type = _get_etf_type(security)

    # ========== 1. 买入资金检查 ==========
    if target_value > 0:
        available_cash = context.portfolio.cash
        if target_value > available_cash:
            target_value = available_cash
        if target_value < g.min_money:
            return False

    # ========== 2. 交易限制 ==========
    if _get_realtime_paused(security):
        return False

    if etf_type == 'a_share':
        high_limit = _get_realtime_high_limit(security)
        low_limit = _get_realtime_low_limit(security)
        current_price = _get_realtime_price(security)
        if current_price <= 0:
            return False
        if high_limit != float('inf') and current_price >= high_limit:
            return False
        if low_limit > 0 and current_price <= low_limit:
            return False
    else:
        current_price = _get_realtime_price(security)
        if current_price <= 0:
            return False

    if current_price <= 0:
        return False

    # ========== 3. 买入股数计算（整百） ==========
    estimated_price = current_price * (1 + 0.0001 + 0.0001)

    if target_value > 0:
        target_amount = int(target_value / estimated_price)
        target_amount = (target_amount // 100) * 100
        if target_amount <= 0:
            target_amount = 100
        max_shares = int(context.portfolio.cash / current_price)
        max_shares = (max_shares // 100) * 100
        if max_shares < target_amount:
            target_amount = max_shares
        if target_amount <= 0:
            return False
    else:
        target_amount = 0

    # ========== 4. 获取当前持仓 ==========
    current_position = context.portfolio.positions.get(security, None)
    current_amount = current_position.amount if current_position else 0
    amount_diff = target_amount - current_amount
    trade_value = abs(amount_diff) * current_price

    if 0 < trade_value < g.min_money:
        return False

    if amount_diff < 0:
        if etf_type == 'a_share':
            closeable_amount = current_position.enable_amount if current_position else 0
        else:
            closeable_amount = current_position.amount if current_position else 0
        if closeable_amount == 0:
            return False
        amount_diff = -min(abs(amount_diff), closeable_amount)

    # ========== 5. 执行下单 ==========
    if amount_diff != 0:
        order_result = order(security, amount_diff)
        if order_result:
            if amount_diff > 0:
                if not is_trade():
                    g.my_cost_basis[security] = g.my_cost_basis.get(security, 0) + amount_diff * current_price
                    new_pos = context.portfolio.positions.get(security)
                    g.my_shares[security] = new_pos.amount if new_pos else 0
                print("买入{} {} 数量:{} 价格:{:.3f}".format(security, security_name, amount_diff, current_price))
            else:
                sell_qty = abs(amount_diff)
                if not is_trade():
                    my_old_shares = g.my_shares.get(security, 0)
                    my_old_cost = g.my_cost_basis.get(security, 0)
                    new_pos = context.portfolio.positions.get(security)
                    new_amount = new_pos.amount if new_pos else 0
                    if my_old_shares > 0 and new_amount <= 0:
                        profit_pct = (current_price / (my_old_cost / my_old_shares) - 1) * 100
                        g.my_shares.pop(security, None)
                        g.my_cost_basis.pop(security, None)
                    elif my_old_shares > 0 and new_amount > 0:
                        ratio = sell_qty / my_old_shares
                        g.my_cost_basis[security] = my_old_cost * (1 - ratio)
                        g.my_shares[security] = new_amount
                        profit_pct = (current_price / (my_old_cost / my_old_shares) - 1) * 100
                    else:
                        profit_pct = 0
                else:
                    cost_basis = current_position.cost_basis if current_position else 0
                    profit_pct = (current_price / cost_basis - 1) * 100 if cost_basis > 0 else 0
                print("卖出{} {} 数量:{} 价格:{:.3f} 盈亏:{:+.2f}%".format(security, security_name, sell_qty, current_price, profit_pct))
            return True
        else:
            return False
    return False


def minute_level_stop_loss(context):
    if not g.use_fixed_stop_loss:
        return

    current_time = context.blotter.current_dt.strftime('%H:%M')
    if not (('09:30' < current_time < '11:30') or ('13:00' < current_time < '14:57')):
        return

    for security in list(context.portfolio.positions.keys()):
        position = context.portfolio.positions[security]
        if position.amount <= 0:
            continue

        etf_type = _get_etf_type(security)
        if etf_type == 'a_share':
            if position.enable_amount <= 0:
                continue
        else:
            if position.amount <= 0:
                continue

        current_price = _get_realtime_price(security)
        if current_price <= 0:
            continue

        my_shares = g.my_shares.get(security, 0) if not is_trade() else 0
        if not is_trade():
            if my_shares <= 0:
                continue
            my_cost = g.my_cost_basis.get(security, 0) / my_shares
            if my_cost <= 0:
                my_cost = position.cost_basis
        else:
            my_cost = position.cost_basis
        if my_cost <= 0:
            continue

        loss_ratio = current_price / my_cost
        if loss_ratio <= g.fixedStopLossThreshold:
            security_name = get_security_name(security)
            loss_percent = (1 - loss_ratio) * 100
            print("【分钟级固定止损】{} {} 触发止损，亏损: {:.2f}%".format(security, security_name, loss_percent))
            smart_order_target_value(security, 0, context)


def minute_level_pct_stop_loss(context):
    if not g.use_pct_stop_loss:
        return

    current_time = context.blotter.current_dt.strftime('%H:%M')
    if not (('09:30' < current_time < '11:30') or ('13:00' < current_time < '14:57')):
        return

    current_date = context.blotter.current_dt.date()

    if not hasattr(g, 'cache_date') or g.cache_date != current_date:
        g.yesterday_close_cache = {}
        g.cache_date = current_date

    for security in list(context.portfolio.positions.keys()):
        position = context.portfolio.positions[security]
        if position.amount <= 0:
            continue

        etf_type = _get_etf_type(security)
        if etf_type == 'a_share':
            if position.enable_amount <= 0:
                continue
        else:
            if position.amount <= 0:
                continue

        yesterday_close = getattr(g, 'yesterday_close_cache', {}).get(security)
        if yesterday_close is None:
            try:
                hist_data = get_history(1, frequency='1d', field=['close'], security_list=security, fq='pre', include=False)
                if hist_data is None or hist_data.empty or 'close' not in hist_data.columns:
                    continue
                yesterday_close = float(hist_data['close'].iloc[-1])
                if yesterday_close <= 0:
                    continue
                g.yesterday_close_cache[security] = yesterday_close
            except Exception:
                continue

        current_price = _get_realtime_price(security)
        if current_price <= 0:
            continue

        stop_price = yesterday_close * g.pct_stop_loss_threshold
        if current_price <= stop_price:
            security_name = get_security_name(security)
            daily_loss = (current_price / yesterday_close - 1) * 100
            print("【分钟级跌幅止损】{} {} 触发止损，当日跌幅: {:.2f}%".format(security, security_name, daily_loss))
            smart_order_target_value(security, 0, context)


def record_daily_positions_to_storage(context):
    current_date = context.blotter.current_dt.strftime('%Y-%m-%d')
    if not hasattr(g, 'all_positions_records'):
        g.all_positions_records = []

    holdings = [sec for sec, pos in context.portfolio.positions.items() if pos.amount > 0]
    if not holdings:
        g.all_positions_records.append({'date': current_date, 'turnover': '无持仓', 'code': '', 'name': ''})
        return

    try:
        today_data = get_batch_hist(holdings, 1, ['money'], freq='1d')
        for sec in holdings:
            turnover = 0
            if sec in today_data:
                money_list = today_data[sec].get('money', [])
                turnover = sum(money_list) if money_list else 0
            etf_name = get_security_name(sec)
            turnover_yi = turnover / 100000000
            turnover_str = "{:.2f}亿".format(turnover_yi)
            g.all_positions_records.append({'date': current_date, 'turnover': turnover_str, 'code': sec, 'name': etf_name})
    except Exception:
        pass


def output_all_positions_summary(context):
    pass

