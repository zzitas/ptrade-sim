# -*- coding: utf-8 -*-
# ==============================================================================
# A股首板打板策略 (PTrade)
# ------------------------------------------------------------------------------
# 思路:
#   1. 盘前用昨日日线初筛候选池: 剔除 ST/退市风险、次新(上市未满 N 天)、
#      近期已有涨停(仅打首板)、仙股/天价股、北交所;
#   2. 盘中按秒级间隔扫描候选池快照(get_snapshot), 捕捉"首次触板"标的:
#      - 当前价 >= 涨停价*(1-容差)          -> 触板
#      - 当日开盘价明显低于涨停价            -> 排除一字板(排板难成交)
#      - 当日成交额达标 + 封单额/封成比达标   -> 过滤烂板
#   3. 命中后以涨停价限价委托打板买入, 单票仓位上限控制, 限制最大持仓数;
#   4. 持仓管理(T+1):
#      - 当日炸板(现价跌破涨停价)            -> 标记次日优先卖出
#      - 次日开盘: 大幅低开直接了结
#      - 盘中: 固定止损 + 冲高回落止盈(跟踪当日高点)
#      - 尾盘 14:50: 未封板的持仓清仓, 封板则继续持有博弈连板
#
# 说明:
#   - 仅使用 PTrade 官方 API(get_snapshot/get_history/get_Ashares/order/
#     run_daily/run_interval 等), 真实环境与本地模拟环境(ptrade_sim)均可运行;
#   - 打板对撮合细节极其敏感(排队/撤单/封单变化), 本地模拟器无排队机制且
#     快照封单字段有限, 回测结果仅验证选股与调度逻辑, 不代表实盘收益;
#   - 实盘请确认券商账户支持创业板/科创板交易权限。
# ==============================================================================


def initialize(context):
    # ---------- 股票池 ----------
    g.pool_mode = "ashares"          # 'ashares'=全市场扫描 / 'custom'=自定义池
    g.custom_pool = [
        "601127.SS",                 # 赛力斯
        "002594.SZ",                 # 比亚迪
        "300474.SZ",                 # 景嘉微
        "300223.SZ",                 # 北京君正
        "688981.SS",                 # 中芯国际
        "600893.SS",                 # 航发动力
        "002371.SZ",                 # 北方华创
        "300308.SZ",                 # 中际旭创
    ]
    # 全市场获取三级回退: get_Ashares() -> get_index_stocks(full_market_index) -> custom_pool
    # (部分券商 PTrade 版本无 get_Ashares 接口, 此时自动改用指数成分)
    g.full_market_index = "000985.SS"  # 中证全指(约4800只沪深A股)
    g.max_scan_codes = 3000            # 全市场扫描数量上限(按代码序截断, 控制初筛耗时)

    # ---------- 选股过滤 ----------
    g.board_lookback = 10            # 首板判定回看交易日数(近N日无涨停)
    g.new_stock_days = 60            # 上市未满天数剔除(次新)
    g.exclude_st = True              # 剔除 ST/*ST
    g.min_price = 3.0                # 均价下限(剔仙股)
    g.max_price = 300.0              # 均价上限
    g.min_turnover = 2.0e8           # 当日成交额下限(元)

    # ---------- 打板条件 ----------
    g.touch_tolerance = 0.002        # 触板容差(现价>=涨停价*(1-容差))
    g.one_word_gap = 0.005           # 开盘价高于涨停价*(1-gap)视为一字板,放弃
    g.min_seal_amount = 2.0e7        # 买一封单金额下限(元);快照无封单数据时跳过该检查
    g.seal_ratio_min = 0.03          # 封单额/当日成交额 下限
    g.max_positions = 3              # 最大同时持仓只数
    g.position_pct = 0.30            # 单票目标仓位(占总资产比例)
    g.buy_start = "09:40"            # 打板时间窗
    g.buy_end = "14:40"
    g.scan_seconds = 15              # 盘中扫描间隔(秒);模拟环境按bar网格取整

    # ---------- 卖出规则 ----------
    g.hold_if_limit_next = True      # 次日再度涨停则持有(博弈连板)
    g.open_dump_sell = -0.02         # 次日开盘较昨收跌幅超过此值 -> 开盘卖出
    g.stop_loss = 0.06               # 固定止损(较成本)
    g.give_back = 0.03               # 冲高回落止盈: 自当日高点回撤超此值且仍有盈利 -> 卖出
    g.force_time = "14:50"           # 尾盘强平检查时刻

    # ---------- 内部状态 ----------
    g.candidates = {}                # code -> 昨收价(盘前初筛结果)
    g.book = {}                      # code -> {"buy_date": date, "buy_px": float}
    g.force_sell = set()             # 当日炸板、次日优先卖出的标的
    g.day_high = {}                  # code -> 当日跟踪最高价
    g.bought_today = []
    g.sold_log = []

    # ---------- 调度 ----------
    run_daily(context, prepare_candidates, time="09:25")
    run_daily(context, morning_exit, time="09:31")
    run_interval(context, scan_and_buy, seconds=g.scan_seconds)
    run_interval(context, manage_holdings, seconds=g.scan_seconds)
    run_daily(context, final_check, time=g.force_time)
    run_daily(context, daily_summary, time="14:57")
    set_universe(g.custom_pool)
    log.info("========== A股首板打板策略初始化完成 ==========")


# ==================== 工具函数 ====================
def _limit_pct(code):
    """按板块返回涨跌停幅度: 创业板(30x)/科创板(68x) ±20%, 其余主板 ±10%。"""
    num = code.split(".")[0]
    if num.startswith(("300", "301", "688", "689")):
        return 0.20
    return 0.10


def _name(code):
    try:
        return get_name(code)
    except Exception:
        return ""


def _pos_of(context, code):
    """兼容不同平台的持仓获取。"""
    try:
        pos = context.portfolio.positions.get(code)
        if pos is not None:
            return pos
    except AttributeError:
        pass
    try:
        return context.portfolio.positions[code]
    except (KeyError, IndexError):
        return None


def _total_value(context):
    pf = context.portfolio
    return getattr(pf, "total_value", None) or getattr(pf, "portfolio_value", 0.0)


def _now_time(context):
    cur = getattr(context, "current_dt", None)
    if cur is None:
        cur = getattr(context, "now", None)
    return cur.time() if cur is not None else None


def _hhmm(t):
    return f"{t.hour:02d}:{t.minute:02d}"


def _snap(codes):
    """批量取快照 {code: dict}; 失败的代码跳过。"""
    out = {}
    codes = list(codes)
    for i in range(0, len(codes), 50):
        chunk = codes[i:i + 50]
        try:
            res = get_snapshot(chunk)
        except Exception:
            res = None
        if not res:
            for c in chunk:
                try:
                    one = get_snapshot([c])
                    if one and one.get(c):
                        out[c] = one[c]
                except Exception:
                    continue
            continue
        for c in chunk:
            v = res.get(c) if isinstance(res, dict) else None
            if v:
                out[c] = v
    return out


def _seal_amount(snap):
    """买一封单金额(元); 快照无买一量数据时返回 None。"""
    grp = snap.get("bid_grp") or {}
    vols = grp.get("bid_volume") or grp.get("bid_vol")
    if not vols:
        return None
    try:
        lots = float(vols[0])            # 买一挂量(手)
        px = float((grp.get("bid_price") or [0])[0] or snap.get("last_px", 0))
        return lots * 100 * px
    except (TypeError, ValueError, IndexError):
        return None


def _sell_all(context, code, reason):
    """可用持仓全数卖出(T+1 可用部分)。"""
    pos = _pos_of(context, code)
    if not pos or pos.enable_amount <= 0:
        return False
    o = order(code, -int(pos.enable_amount))
    if o is not None:
        log.info(f"📤 [卖出] {code} {_name(code)} {pos.enable_amount}股 | {reason}")
        g.sold_log.append({"code": code, "reason": reason,
                           "time": str(_now_time(context))})
        g.book.pop(code, None)
        g.force_sell.discard(code)
        g.day_high.pop(code, None)
        return True
    return False


# ==================== 盘前初筛 ====================
def prepare_candidates(context):
    """昨日日线初筛候选池: 流动性/价格/ST/次新/首板条件。"""
    g.candidates = {}
    g.bought_today = []
    g.sold_log = []
    g.day_high = {}

    def _valid_stocks(codes):
        # 仅保留沪深A股(排除北交所/三板/基金)
        return [c for c in codes if c.split(".")[0][:1] in ("6", "0")]

    pool, src = [], ""
    if g.pool_mode == "custom":
        pool, src = list(g.custom_pool), "自定义池"
    else:
        # 第一级: PTrade 原生 get_Ashares(部分版本没有该接口)
        fn = globals().get("get_Ashares")
        if callable(fn):
            try:
                pool = _valid_stocks(list(fn()))
                src = "get_Ashares"
            except Exception as e:
                log.warn(f"get_Ashares 调用失败({e})")
        # 第二级: 指数成分替代全市场(get_index_stocks 所有版本都有)
        if not pool:
            idx_fn = globals().get("get_index_stocks")
            idx = getattr(g, "full_market_index", "")
            if callable(idx_fn) and idx:
                try:
                    pool = _valid_stocks(list(idx_fn(idx)))
                    src = f"指数成分{idx}"
                except Exception as e:
                    log.warn(f"get_index_stocks({idx}) 失败({e})")
        # 第三级: 自定义池兜底
        if not pool:
            pool, src = list(g.custom_pool), "自定义池(回退)"
        log.info(f"【股票池】来源={src} 原始数量={len(pool)}")
    trunc = ""
    cap = int(getattr(g, "max_scan_codes", 0) or 0)
    if cap > 0 and len(pool) > cap:
        pool = sorted(pool)[:cap]
        trunc = f", 截断至{cap}"

    st_set = {}
    if g.exclude_st:
        try:
            st_set = get_stock_status(pool, query_type="ST") or {}
        except Exception:
            st_set = {}

    today = context.current_dt.date()
    kept, dropped = 0, 0
    for code in pool:
        try:
            if st_set.get(code):
                dropped += 1
                continue
            info = get_security_info(code)
            start = str(getattr(info, "start_date", "") or "")
            if start and start > str(context.previous_date or ""):
                dropped += 1
                continue                     # 次新股
            if start[:4].isdigit() and (today - _d(start)).days < g.new_stock_days:
                dropped += 1
                continue                     # 上市未满 N 天
            hist = get_history(g.board_lookback + 2, frequency="1d",
                               field=["close"], security_list=[code],
                               include=False)
            closes = hist["close"]
            if closes is None or len(closes) < g.board_lookback + 2:
                dropped += 1
                continue
            pre_close = float(closes.iloc[-1])
            if not (g.min_price <= pre_close <= g.max_price):
                dropped += 1
                continue
            pct = _limit_pct(code)
            touched_recently = False
            arr = [float(x) for x in list(closes.values)]
            for i in range(1, len(arr)):
                prev = arr[i - 1]
                if prev > 0 and arr[i] / prev - 1 >= pct * 0.95:
                    touched_recently = True
                    break
            if touched_recently:
                dropped += 1
                continue                     # 近N日已有涨停, 非首板机会
            g.candidates[code] = pre_close
            kept += 1
        except Exception:
            dropped += 1
            continue
    log.info(f"【盘前初筛】候选 {kept} 只 / 剔除 {dropped} 只 "
             f"(来源={src}{trunc}, 有效池={len(pool)})")


def _d(s):
    import datetime as _dtmod
    return _dtmod.date(int(s[:4]), int(s[5:7]), int(s[8:10]))


# ==================== 盘中打板买入 ====================
def scan_and_buy(context):
    t = _now_time(context)
    if t is None or not ("09:40" <= _hhmm(t) <= "14:40"):
        return
    if not g.candidates:
        return
    held = set(context.portfolio.positions.keys())
    slots = g.max_positions - len(held)
    if slots <= 0:
        return

    snaps = _snap(list(g.candidates.keys()))
    pf = context.portfolio
    total_value = _total_value(context)
    for code, pre_close in list(g.candidates.items()):
        if slots <= 0:
            break
        if code in held or code in g.book:
            continue
        s = snaps.get(code)
        if not s:
            continue
        try:
            last = float(s.get("last_px") or 0)
            up = float(s.get("up_px") or 0)
            opn = float(s.get("open_px") or 0)
            turnover = float(s.get("business_balance") or 0)
        except (TypeError, ValueError):
            continue
        if last <= 0 or up <= 0:
            continue
        if last < up * (1 - g.touch_tolerance):
            continue                          # 未触板
        if turnover < g.min_turnover:
            continue                          # 成交额不足
        if opn > 0 and opn >= up * (1 - g.one_word_gap):
            continue                          # 一字/秒板, 放弃排队
        seal = _seal_amount(s)
        if seal is not None:
            if seal < g.min_seal_amount:
                log.info(f"🚫 [烂板过滤] {code} {_name(code)} 封单{seal/1e8:.2f}亿不足")
                continue
            if turnover > 0 and seal / turnover < g.seal_ratio_min:
                log.info(f"🚫 [烂板过滤] {code} {_name(code)} 封成比{seal/turnover:.3f}不足")
                continue
        # ---- 打板买入 ----
        target_value = min(total_value * g.position_pct, pf.cash * 0.98)
        lots = int(target_value / up / 100) * 100
        if lots < 100:
            continue
        o = order(code, lots, limit_price=up)
        if o is not None:
            g.book[code] = {"buy_date": context.current_dt.date(), "buy_px": up}
            g.bought_today.append(code)
            slots -= 1
            seal_txt = f"{seal/1e8:.2f}亿" if seal is not None else "无数据"
            log.info(f"🎯 [打板买入] {code} {_name(code)} {lots}股 @ {up} "
                     f"| 封单{seal_txt} 成交额{turnover/1e8:.2f}亿")


# ==================== 持仓管理 ====================
def morning_exit(context):
    """次日开盘处置: 大幅低开直接了结。"""
    today = context.current_dt.date()
    snaps = _snap(list(g.book.keys()))
    for code in list(g.book.keys()):
        rec = g.book[code]
        if rec["buy_date"] >= today:
            continue                           # 今日买入, T+1 未到期
        s = snaps.get(code)
        if not s:
            continue
        try:
            opn = float(s.get("open_px") or 0)
            pre = float(s.get("preclose_px") or 0)
        except (TypeError, ValueError):
            continue
        if opn > 0 and pre > 0 and opn / pre - 1 <= g.open_dump_sell:
            _sell_all(context, code, f"低开{opn/pre-1:.2%}止损离场")


def manage_holdings(context):
    """盘中持仓风控: 止损 / 冲高回落止盈 / 炸板标记 / 连板持有。"""
    if not g.book:
        return
    today = context.current_dt.date()
    snaps = _snap(list(g.book.keys()))
    for code, rec in list(g.book.items()):
        s = snaps.get(code)
        if not s:
            continue
        try:
            last = float(s.get("last_px") or 0)
            up = float(s.get("up_px") or 0)
            cost = float(rec.get("buy_px") or 0) or None
        except (TypeError, ValueError):
            continue
        if last <= 0:
            continue
        pos = _pos_of(context, code)
        bought_today = rec["buy_date"] >= today
        at_limit = up > 0 and last >= up * (1 - g.touch_tolerance)

        # --- 当日新买入: 仅做炸板标记(T+1 不可卖) ---
        if bought_today:
            if at_limit:
                g.force_sell.discard(code)
            elif code not in g.force_sell:
                g.force_sell.add(code)
                log.info(f"⚠️ [炸板标记] {code} {_name(code)} 现价{last}<涨停{up}, 次日优先卖出")
            continue

        # --- 次日起: 连板持有优先 ---
        if g.hold_if_limit_next and at_limit:
            g.force_sell.discard(code)
            continue
        if code in g.force_sell:
            if _sell_all(context, code, "昨日炸板离场"):
                continue
        # 固定止损
        if cost and last <= cost * (1 - g.stop_loss):
            if _sell_all(context, code, f"止损({-g.stop_loss:.0%})"):
                continue
        # 冲高回落止盈
        hi = max(g.day_high.get(code, last), last)
        g.day_high[code] = hi
        if cost and hi >= cost * 1.02 and last <= hi * (1 - g.give_back) \
                and last > cost and pos and pos.enable_amount > 0:
            _sell_all(context, code,
                      f"冲高回落止盈(高点{hi:.2f}->现价{last:.2f})")


def final_check(context):
    """尾盘决策: 次日及以上持仓未封板的清仓, 封板持有博弈连板。"""
    today = context.current_dt.date()
    snaps = _snap([c for c, r in g.book.items() if r["buy_date"] < today])
    for code, rec in list(g.book.items()):
        if rec["buy_date"] >= today:
            continue
        s = snaps.get(code)
        if not s:
            continue
        try:
            last = float(s.get("last_px") or 0)
            up = float(s.get("up_px") or 0)
        except (TypeError, ValueError):
            continue
        if up > 0 and last >= up * (1 - g.touch_tolerance):
            log.info(f"🔒 [尾盘锁板] {code} {_name(code)} 持有过夜博连板")
        else:
            _sell_all(context, code, "尾盘未封板清仓")


def daily_summary(context):
    if g.bought_today or g.sold_log:
        buys = ", ".join(f"{c}({_name(c)})" for c in g.bought_today) or "无"
        sells = "; ".join(f"{s['code']}:{s['reason']}" for s in g.sold_log) or "无"
        log.info(f"📋 [当日小结] 打板买入: {buys} | 卖出: {sells}")
    log.info(f"📊 [持仓] {len(g.book)} 只 / 现金 {context.portfolio.cash:,.0f}")


def handle_data(context, data):
    pass


def after_trading_end(context):
    pass
