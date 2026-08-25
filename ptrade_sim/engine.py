# -*- coding: utf-8 -*-
"""PTrade 模拟引擎:事件调度 + 撮合 + 账户结算。"""
import datetime as dt
import importlib.util
import inspect
import io
import os
import sys
import traceback
import zlib

import pandas as pd
from contextlib import redirect_stdout

from . import data as simdata


class Log:
    def __init__(self, engine, verbose=True):
        self.engine = engine
        self.verbose = verbose
        self.file = None        # 本次回测的落盘文件句柄
        self.path = None

    def open_file(self, path):
        """打开本次回测的完整日志文件;失败时静默降级为仅控制台。"""
        try:
            d = os.path.dirname(path)
            if d:
                os.makedirs(d, exist_ok=True)
            self.file = open(path, "a", encoding="utf-8")
            self.path = path
        except Exception:
            self.file = None
            self.path = None
        return self.path

    def close_file(self):
        if self.file:
            try:
                self.file.close()
            except Exception:
                pass
        self.file = None

    def info(self, msg):
        self._write("INFO", msg)

    def warn(self, msg):
        self._write("WARN", msg)

    def warning(self, msg):
        self.warn(msg)

    def set_level(self, *args, **kwargs):
        """兼容聚宽 log.set_level,模拟环境不做分级过滤。"""
        return None

    def error(self, msg):
        self._write("ERROR", msg)

    def debug(self, msg):
        self._write("DEBUG", msg)

    def _write(self, level, msg):
        line = f"[{self.engine.now:%Y-%m-%d %H:%M:%S}] [{level}] {msg}"
        self.engine.logs.append(line)
        if self.file is not None:
            try:
                self.file.write(line + "\n")
                self.file.flush()
            except Exception:
                pass
        if self.verbose:
            print("SIM " + line)

    def __call__(self, msg):
        self.info(msg)


class Position:
    def __init__(self, code):
        self.code = code
        self.amount = 0        # 可用持仓
        self.frozen = 0        # 冻结(今日买入,未交收)
        self.cost = 0.0        # 持仓成本(摊薄)

    @property
    def total_amount(self):
        return self.amount + self.frozen

    @property
    def value(self):
        return self.total_amount * self.engine.get_price(self.code)


class Order:
    def __init__(self, oid, code, side, amount, price, time):
        self.order_id = oid
        self.code = code
        self.side = side          # 'buy' / 'sell'
        self.amount = amount
        self.price = price
        self.time = time
        self.filled = 0
        self.status = "filled"

    def __repr__(self):
        return f"<Order {self.order_id} {self.side} {self.amount} {self.code} @ {self.price} {self.status}>"


class SimBar(dict):
    """事件回调的 data 参数:dict + 属性访问,兼容 data[code] / data.close。"""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


class JQSeries(pd.Series):
    """聚宽兼容 Series:pandas 3.0 移除了 s[-1] 位置回退,这里恢复之。"""
    @property
    def _constructor(self):
        return JQSeries

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except (KeyError, IndexError):
            if isinstance(key, int) and not isinstance(key, bool):
                return self.iloc[key]
            raise


class JQFrame(pd.DataFrame):
    """聚宽兼容 DataFrame:取列得到 JQSeries(支持 s[-1] 等位置写法)。"""
    @property
    def _constructor(self):
        return JQFrame

    def __getitem__(self, key):
        out = super().__getitem__(key)
        if isinstance(out, pd.Series):
            out = JQSeries(out)
        return out


class SimEngine:
    """PTrade 仿真引擎。date_range: (start_date, end_date),均为 date。"""

    def __init__(self, capital=1_000_000, commission=0.0003,
                 min_commission=5.0, stamp_duty=0.0, verbose=True,
                 data_source=None):
        self.start_capital = capital
        self.cash = capital
        self.commission = commission
        self.buy_commission = commission    # set_commission 可分别设置买卖佣金率
        self.sell_commission = commission
        self.min_commission = min_commission
        self.stamp_duty = stamp_duty
        self.verbose = verbose
        self.ds = data_source if data_source is not None else simdata
        self.now = dt.datetime(2026, 1, 1, 9, 30)
        self.positions = {}
        self.universe = []
        self.orders = []
        self.logs = []
        self.log = Log(self, verbose)
        self.daily_jobs = []       # (time, func)
        self.interval_jobs = []    # (seconds, func, next_run)
        self.params = {}
        self._oid = 0
        self.strategy = None
        self.daily_equity = []     # (date, equity)
        self._g = {}               # g 全局对象
        self.stop_flag = False

    def stop(self):
        """请求停止模拟(由 GUI 调用)。"""
        self.stop_flag = True

    # ---------------- 行情 ----------------
    def get_price(self, code):
        return self.ds.intraday_price(code, self.now.date(), self.now.time())

    # ---------------- 撮合 ----------------
    def _match(self, code, side, amount):
        bar = self.ds.daily_bar(code, self.now.date())
        if bar.get("_paused"):
            self.log.warn(f"{code} 当日停牌,忽略{'买入' if side == 'buy' else '卖出'}")
            return None
        # 对齐 PTrade 回测:成交量不超过当根 bar 的 25%
        cap = int(bar.get("volume", 0) * 0.25)
        if cap > 0 and amount > cap:
            self.log.info(f"{code} 委托 {amount} 股超出当根bar成交量25%,调整为 {cap} 股")
            amount = cap
        px = self.get_price(code)
        rate = self.buy_commission if side == "buy" else self.sell_commission
        fee = max(amount * px * rate, self.min_commission)
        if side == "buy":
            cost = amount * px + fee
            if cost > self.cash:
                amt = int((self.cash - fee) / px)
                if amt <= 0:
                    self.log.warn(f"资金不足,忽略买入 {code}")
                    return None
                amount, cost = amt, amt * px + fee
            self.cash -= cost
            pos = self.positions.setdefault(code, self._new_pos(code))
            pos.frozen += amount
            pos.cost = (pos.cost * pos.total_amount + px * amount) / (pos.total_amount + amount)
        else:
            pos = self.positions.get(code)
            if not pos or pos.amount < amount:
                self.log.warn(f"可卖持仓不足 {code}(可用 {getattr(pos, 'amount', 0)}, 欲卖 {amount})")
                return None
            fee = fee + amount * px * self.stamp_duty
            self.cash += amount * px - fee
            pos.amount -= amount
            pos.cost = 0 if pos.total_amount == 0 else pos.cost
        self._oid += 1
        o = Order(self._oid, code, side, amount, px, self.now)
        o.filled = amount
        self.orders.append(o)
        self.log.info(f"{'买入' if side=='buy' else '卖出'} {code} {amount}股 @ {px} 手续费{fee:.2f}")
        return o

    def _new_pos(self, code):
        p = Position(code)
        p.engine = self
        return p

    # ---------------- 事件循环 ----------------
    def _open_run_log(self, strategy, start, end):
        """为本次回测建立独立日志文件 logs/时间戳_策略名_区间.log。"""
        stem = "strategy"
        src = getattr(strategy, "__file__", "") or ""
        if src:
            stem = os.path.splitext(os.path.basename(src))[0]
        log_dir = os.environ.get("PTRADE_SIM_LOG_DIR") \
            or os.path.join(os.getcwd(), "logs")
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{ts}_{stem}_{start:%Y%m%d}-{end:%Y%m%d}.log"
        path = self.log.open_file(os.path.join(log_dir, name))
        if path:
            self.log.info(
                f"回测开始: 策略={stem} 区间={start}~{end} "
                f"初始资金={self.start_capital:,.0f} "
                f"数据源={type(self.ds).__name__} 日志={path}")

    def run(self, strategy, start, end):
        self.strategy = strategy
        self._open_run_log(strategy, start, end)
        # 注入策略命名空间(策略文件中已定义的同名函数优先,如自定义 set_params/set_backtest)
        inject = build_api(self)
        for k, v in inject.items():
            if k in vars(strategy):
                continue
            setattr(strategy, k, v)
        if not hasattr(strategy, "g"):
            strategy.g = type("G", (), {})()
        if hasattr(strategy, "log") and getattr(strategy.log, "_pt_proxy", False):
            # 移植策略的日志代理: 接到引擎日志后端
            strategy.log._pt_backend = self.log
        elif not hasattr(strategy, "log"):
            strategy.log = self.log

        # 先确定交易日历并定位到首个交易日,再初始化策略(策略初始化可能查询交易日)
        days = list(self.ds.trade_days(start, end))
        if not days:
            self.log.error("区间内无交易日(或数据未覆盖该区间)")
            return self.report()
        self._backtest_start = days[0]
        self.now = dt.datetime.combine(days[0], dt.time(9, 30))
        try:
            self._invoke(strategy.initialize)
        except Exception:
            self.log.error("initialize 异常:\n" + traceback.format_exc())
            return self.report()

        for day in days:
            if self.stop_flag:
                self.log.warn("收到停止指令,模拟中止")
                break
            self._settle_day_start(day)
            self._safe(strategy, "before_trading_start", data=self._make_data(prev_day=True))
            # 处理昨日买入的交收(T+1 可用)
            for p in self.positions.values():
                if p.frozen:
                    p.amount += p.frozen
                    p.frozen = 0
            bar_times = simdata.TRADE_TIMES
            for tm in bar_times:
                if self.stop_flag:
                    break
                self.now = dt.datetime.combine(day, tm)
                self._run_scheduled(tm)
                self._run_intervals()
                self._safe(strategy, "handle_data", data=self._make_data())
                if tm == dt.time(14, 57):
                    self._safe(strategy, "tick_per_second", data=self._make_data())  # 近似
            # 收盘后的调度任务(如 15:05/15:10)按其时间补跑,再进入盘后回调
            for tm in sorted({j["time"] for j in self.daily_jobs
                              if not j.get("every_bar") and j["time"] > dt.time(15, 0)}):
                self.now = dt.datetime.combine(day, tm)
                self._run_scheduled(tm, include_every_bar=False)
            self.now = dt.datetime.combine(day, max(
                [dt.time(15, 0)] + [j["time"] for j in self.daily_jobs
                                    if not j.get("every_bar") and j["time"] > dt.time(15, 0)]))
            self._safe(strategy, "after_trading_end", data=self._make_data())
            self._mark_equity(day)
        return self.report()

    def _settle_day_start(self, day):
        # 重置日内调度为当天
        for job in self.daily_jobs:
            job["ran"] = False
        for job in self.interval_jobs:
            job["last"] = None

    def _fire_job(self, job):
        try:
            self._invoke(job["func"], self._make_data())
        except Exception:
            self.log.error(f"调度任务 {getattr(job['func'], '__name__', job['func'])} 异常:\n"
                           + traceback.format_exc())

    def _run_scheduled(self, tm, include_every_bar=True):
        for job in self.daily_jobs:
            if job.get("every_bar"):
                if include_every_bar:
                    self._fire_job(job)
                continue
            if not job.get("ran") and tm >= job["time"]:
                job["ran"] = True
                self._fire_job(job)

    def _run_intervals(self):
        """近似 PTrade run_interval:盘中每过 seconds 秒触发一次(按 3 分钟 bar 网格取整,
        当日首次触发不早于开盘后 seconds 秒)。"""
        for job in self.interval_jobs:
            last = job.get("last")
            opened = dt.datetime.combine(self.now.date(), simdata.TRADE_TIMES[0])
            elapsed = (self.now - (last or opened)).total_seconds()
            if last is None and elapsed < job["seconds"]:
                continue
            if last is not None and elapsed < job["seconds"]:
                continue
            job["last"] = self.now
            self._fire_job(job)

    def _invoke(self, func, data=None):
        """按函数签名调用:PTrade 事件函数可能是 func() / func(context) / func(context, data)。"""
        try:
            sig = inspect.signature(func)
        except (TypeError, ValueError):
            sig = None
        args = []
        if sig is None:
            args = [self._ctx()]
        else:
            positional = [p for p in sig.parameters.values()
                          if p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                        inspect.Parameter.POSITIONAL_OR_KEYWORD)]
            required = [p for p in positional if p.default is inspect.Parameter.empty]
            has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL
                          for p in sig.parameters.values())
            if required or has_var:
                args.append(self._ctx())
                if len(required) >= 2 or has_var:
                    args.append(data if data is not None else self._make_data())
        func(*args)

    def _make_data(self, prev_day=False):
        day = self.ds.prev_trade_date(self.now.date()) if prev_day else self.now.date()
        d = SimBar()
        codes = self.universe or self.ds.DEFAULT_UNIVERSE
        for code in codes:
            d[code] = self.ds.daily_bar(code, day)
        return d

    def _safe(self, strategy, name, data=None):
        func = getattr(strategy, name, None)
        if not callable(func):
            return
        try:
            self._invoke(func, data)
        except Exception:
            self.log.error(f"{name} 异常:\n" + traceback.format_exc())

    def _ctx(self):
        blotter = type("Blotter", (), {"current_dt": self.now})()
        return type("Context", (), {
            "now": self.now, "current_dt": self.now,
            "previous_date": self.ds.prev_trade_date(self.now.date()),
            "blotter": blotter,
            "portfolio": self._portfolio(),
        })()

    def _portfolio(self):
        pos_val = sum(p.value for p in self.positions.values())
        pf = type("Portfolio", (), {})()
        pf.portfolio_value = self.cash + pos_val
        pf.total_value = pf.portfolio_value      # 聚宽语义别名
        pf.cash = self.cash
        pf.positions_value = pos_val
        pf.returns = pf.portfolio_value / self.start_capital - 1
        pos_wrapper = {}
        for code, p in self.positions.items():
            if p.total_amount > 0:
                pw = type("PW", (), p.__dict__)()
                pw.engine = self
                pw.amount = p.total_amount        # PTrade 语义: 总持仓
                pw.enable_amount = p.amount       # 可用数量(T+1 未交收部分不计入)
                pw.cost_basis = p.cost
                pw.last_sale_price = self.get_price(code)
                pw.avg_cost = p.cost              # 聚宽语义别名
                pw.price = self.get_price(code)
                pw.closeable_amount = p.amount    # 聚宽语义: 可卖数量
                pw.total_amount = p.total_amount
                pw.value = p.value
                pos_wrapper[code] = pw
        pf.positions = pos_wrapper
        return pf

    def _mark_equity(self, day):
        pf = self._portfolio()
        self.daily_equity.append((day, pf.portfolio_value))

    def report(self):
        pf = self._portfolio()
        ret = pf.portfolio_value / self.start_capital - 1
        out = ["========== 模拟结果 ==========",
               f"初始资金: {self.start_capital:,.2f}",
               f"期末资产: {pf.portfolio_value:,.2f} (现金 {self.cash:,.2f})",
               f"总收益率: {ret*100:.2f}%   成交笔数: {len(self.orders)}"]
        if self.daily_equity:
            vals = [v for _, v in self.daily_equity]
            peak = max(vals)
            mdd = (min(v / peak for v, peak in zip(vals, RunningMax(vals))) - 1) * 100
            out.append(f"最大回撤: {mdd:.2f}%")
        for code, p in self.positions.items():
            if p.total_amount:
                out.append(f"  持仓 {code}: {p.total_amount} 股, 市值 {p.value:,.2f}")
        out.append("==============================")
        for ln in out:
            self.log.info(ln)
        if self.log.path:
            self.log.info(f"完整日志已保存: {self.log.path}")
        self.log.close_file()
        return pf


def RunningMax(vals):
    m = 0
    for v in vals:
        m = max(m, v)
        yield m


# ---------------- PTrade API 兼容层 ----------------
def build_api(engine):
    api = {}

    api["log"] = engine.log

    # 交易
    def order(code, amount, limit_price=None):
        if amount == 0:
            return None
        return engine._match(code, "buy" if amount > 0 else "sell", abs(int(amount)))

    def order_target(code, target):
        pos = engine.positions.get(code)
        cur = pos.total_amount if pos else 0
        return order(code, target - cur)

    def order_value(code, value):
        return order(code, int(value / engine.get_price(code)))

    def order_target_value(code, value):
        return order_target(code, int(value / engine.get_price(code)))

    def order_market(code, amount, limit_price=None):
        return order(code, amount)

    def cancel_order(*a, **k):
        engine.log.warn("模拟环境: cancel_order 未实现(即时成交,无挂单)")

    def get_orders(*a, **k):
        return {o.order_id: o for o in engine.orders}

    api.update(order=order, order_target=order_target, order_value=order_value,
               order_target_value=order_target_value, order_market=order_market,
               cancel_order=cancel_order, get_orders=get_orders)

    # 账户
    api["get_stock_positions"] = lambda *a, **k: [
        {**{f: getattr(p, f) for f in ("code", "amount", "frozen", "cost")},
         "market_value": p.value} for p in engine.positions.values() if p.total_amount]
    api["get_cash"] = lambda *a, **k: engine.cash
    api["get_portfolio"] = engine._portfolio

    # 行情/数据
    def get_snapshot(codes):
        if isinstance(codes, str):
            codes = [codes]
        ensure = getattr(engine.ds, "ensure", None)
        if ensure:
            ensure(codes)
        out = {}
        for c in codes:
            px = engine.get_price(c)
            bar = engine.ds.daily_bar(c, engine.now.date())
            out[c] = {"last_px": px, "open_px": bar["open"], "high_px": bar["high"],
                      "low_px": bar["low"], "close_px": bar["close"],
                      "preclose_px": bar["pre_close"], "up_px": bar["high_limit"],
                      "down_px": bar["low_limit"],
                      "trade_status": "HALT" if bar.get("_paused") else "TRADE",
                      "iopv": bar.get("unit_nav", bar["close"]),
                      "business_amount": bar["volume"], "business_balance": bar["amount"],
                      "bid_grp": {"bid_price": [round(px * 0.999, 3)] * 5},
                      "offer_grp": {"offer_price": [round(px * 1.001, 3)] * 5}}
        return out

    def _bar_field(code, day, f, tm=None):
        """取某标的某日某字段。tm 不为 None 表示分钟线请求:
        close/price 用日内价,volume/amount 按当根 bar 均摊(PTrade 分钟量累计语义)。

        日线行若恰为"今天"且尚在盘中,返回形成中 K 线(收盘=日内价,
        高低仅含开盘与现价,量按已走 bar 比例)——防止 include=True
        在盘中泄露当日完整 OHLCV(未来函数)。"""
        if tm is not None:
            if f in ("close", "price"):
                return engine.ds.intraday_price(code, day, tm)
            if f in ("volume", "amount", "money"):
                bar = engine.ds.daily_bar(code, day)
                v = bar.get("amount", 0.0) if f == "money" else bar.get("volume", 0)
                return v / len(simdata.TRADE_TIMES)
            if f == "is_open":
                return 1
        bar = engine.ds.daily_bar(code, day)
        now_t = engine.now.time()
        if (day == engine.now.date() and now_t < dt.time(15, 0)
                and not bar.get("_paused")):
            ipx = engine.ds.intraday_price(code, day, now_t)
            elapsed = len([t for t in simdata.TRADE_TIMES if t <= now_t])
            frac = min(max(elapsed / float(len(simdata.TRADE_TIMES)), 0.0), 1.0)
            o = bar.get("open", ipx)
            vals = {"open": o, "close": ipx, "price": ipx,
                    "high": max(o, ipx), "low": min(o, ipx),
                    "volume": (bar.get("volume", 0) or 0) * frac,
                    "amount": (bar.get("amount", 0.0) or 0.0) * frac}
            if f in vals:
                return vals[f]
        if f in bar:
            return bar[f]
        if f in ("unit_nav", "acc_nav", "net_value"):
            return bar["close"]
        if f == "money":
            return bar["amount"]
        if f == "preclose":
            return bar.get("pre_close", bar["close"])
        if f == "is_open":
            return 0 if bar.get("_paused") else 1
        return None

    def _history_days(count, include):
        """截止 include=True 为当日(含),否则为上一交易日(避免未来数据)。"""
        days = []
        d = engine.now.date() if include else engine.ds.prev_trade_date(engine.now.date())
        while len(days) < count:
            days.append(d)
            d = engine.ds.prev_trade_date(d)
        return days[::-1]

    def get_history(count=1, frequency="1d", field="close", security_list=None,
                    fq=None, include=False, is_dict=False, fill=None,
                    skip_paused=False, **kw):
        """返回 pandas DataFrame(与 PTrade 一致):
        单标的: index=日期, columns=字段; 多标的单字段: columns=代码; 多标的多字段: {代码: DataFrame}
        is_dict=True 时强制返回 {代码: DataFrame}。"""
        import pandas as pd
        if isinstance(security_list, str):
            securities = [security_list]
        elif security_list is None:
            securities = list(engine.universe or engine.ds.DEFAULT_UNIVERSE)
        else:
            securities = list(security_list)
        ensure = getattr(engine.ds, "ensure", None)
        if ensure:
            ensure(securities)
        fields = field if isinstance(field, list) else [field]
        freq = (frequency or "1d").lower()

        if freq in ("1m", "m", "minute", "5m", "15m", "30m", "60m"):
            # 分钟线:以当前 bar 往前取 count 个 3 分钟点
            tms = [t for t in simdata.TRADE_TIMES if t <= engine.now.time()]
            day = engine.ds.prev_trade_date(engine.now.date()) if not tms else engine.now.date()
            if not tms:
                tms = list(simdata.TRADE_TIMES)
            idx = [dt.datetime.combine(day, t) for t in tms[-count:]]

            def col(code, f):
                return [_bar_field(code, x.date(), f, tm=x.time()) for x in idx]
        else:
            days = _history_days(count, include)
            idx = days

            def col(code, f):
                return [_bar_field(code, d, f) for d in days]

        def frame(code):
            return JQFrame({f: col(code, f) for f in fields}, index=idx)

        if is_dict:
            return {c: frame(c) for c in securities}
        if len(securities) == 1:
            return frame(securities[0])
        if len(fields) == 1:
            f = fields[0]
            # JQFrame 使取列得到 JQSeries,兼容 pandas 3.0 下的 s[-1] 位置写法
            return JQFrame({c: col(c, f) for c in securities}, index=idx)
        return {c: frame(c) for c in securities}

    api["get_snapshot"] = get_snapshot
    api["get_history"] = get_history
    api["get_price"] = lambda code, *a, **k: engine.get_price(code)
    def get_trade_days(start_date=None, end_date=None, count=None, **kw):
        sd = start_date if start_date is not None else kw.get("start")
        ed = end_date if end_date is not None else kw.get("end")
        if isinstance(sd, str):
            sd = dt.date.fromisoformat(sd)
        if isinstance(ed, str):
            ed = dt.date.fromisoformat(ed)
        # 返回 datetime.date 对象(与聚宽/恒生官方一致,支持日期运算)
        days = list(engine.ds.trade_days(
            sd or dt.date(2018, 1, 1), ed or engine.now.date()))
        if count:
            days = days[-int(count):]
        return days

    api["get_trade_days"] = get_trade_days

    def get_trading_day(day=0):
        """当前回测交易日(官方 API;day=0 取当日,负/正为前/后第 N 个交易日)。"""
        d = engine.now.date()
        n = int(day)
        if n == 0:
            return d
        for _ in range(abs(n)):
            if n > 0:
                nxt = getattr(engine.ds, "next_trade_date", None)
                if nxt is None:
                    raise ValueError("数据源不支持未来交易日查询")
                d = nxt(d)
            else:
                d = engine.ds.prev_trade_date(d)
        return d
    api["get_trading_day"] = get_trading_day
    api["get_prev_trade_date"] = lambda days=1: engine.ds.prev_trade_date(
        engine.now.date() - dt.timedelta(days=days - 1)).isoformat()
    api["get_security_info"] = lambda code: type("SI", (), engine.ds.security_info(code))()
    api["get_security_name"] = lambda code: engine.ds.security_info(code)["display_name"]
    api["get_index_stocks"] = lambda index: list(engine.ds.DEFAULT_UNIVERSE)

    def get_etf_list():
        """全市场 ETF 代码列表(真实数据源: 东财 clist,缓存7天)。
        设环境变量 PTRADE_SIM_ETF_LIST=cached 时仅返回本地已缓存的代码(离线快速验证)。"""
        fn = getattr(engine.ds, "all_etfs", None)
        if fn is None:
            return list(engine.ds.DEFAULT_UNIVERSE)
        lst = [c for c, _ in fn()]
        # 剔除回测起始日之后才有行情的代码(尚未上市,避免未来数据)
        start_day = getattr(engine, "_backtest_start", None)
        fd_fn = getattr(engine.ds, "first_date", None)
        if start_day is not None and fd_fn is not None:
            lim = start_day.isoformat()
            before = len(lst)
            lst = [c for c in lst if (fd_fn(c) or lim) <= lim]
            if before - len(lst):
                engine.log.info(f"get_etf_list: 剔除回测起始日后才上市/无早期数据的 "
                                f"{before - len(lst)} 只")
        if os.environ.get("PTRADE_SIM_ETF_LIST") == "cached":
            have = getattr(engine.ds, "bars", {})
            lst = [c for c in lst if c in have]
            engine.log.info(f"get_etf_list: 仅缓存模式, {len(lst)} 只")
            return lst
        engine.log.info(f"get_etf_list: 全市场 ETF 共 {len(lst)} 只")
        return lst

    api["get_etf_list"] = get_etf_list

    def get_etf_info(*codes):
        """PTrade get_etf_info: {code: {"nav_pre": 前一日单位净值, ...}}。"""
        out = {}
        for code in codes:
            if isinstance(code, list):
                out.update(get_etf_info(*code))
                continue
            code = str(code).strip("[]'\" ")
            try:
                prev = engine.ds.prev_trade_date(engine.now.date())
                nav = engine.ds.daily_bar(code, prev).get("unit_nav") or engine.get_price(code)
            except Exception:
                nav = engine.get_price(code)
            out[code] = {"nav": nav, "nav_pre": nav, "iopv": nav}
        return out

    api["get_etf_info"] = get_etf_info
    api["is_trade"] = lambda day=None: engine.ds.is_trade_date(
        (dt.date.fromisoformat(day) if isinstance(day, str) else day) if day else engine.now.date())
    api["get_stock_status"] = lambda code, query_type="ST", query_date=None: (
        {c: False for c in (code if isinstance(code, (list, tuple)) else [code])})
    api["get_stock_name"] = api["get_security_name"]
    api["get_stock_info"] = api["get_security_info"]
    api["get_volume_ratio"] = lambda code: 1.0 + (zlib.crc32(f"{code}{engine.now.date()}".encode()) % 100) / 100.0
    api["get_stock_blocks"] = lambda code: []
    api["get_fundamentals"] = lambda *a, **k: {}
    api["get_gear_price"] = lambda code: {"bid": engine.get_price(code), "ask": engine.get_price(code)}

    # 调度(兼容 run_daily(func, time) 与 PTrade 官方 run_daily(context, func, time='9:30') 两种写法)
    def _parse_time(tm_raw):
        """解析调度时间;返回 None 表示每个 bar 触发(every_bar)。未知串告警回退到开盘。"""
        if isinstance(tm_raw, dt.time):
            return tm_raw
        if tm_raw is None:
            return dt.time(9, 30)
        s = str(tm_raw).strip().lower()
        specials = {
            "every_bar": None, "everytick": None, "every_tick": None,
            "open": dt.time(9, 30), "market_open": dt.time(9, 30),
            "before_open": dt.time(9, 25),
            "close": dt.time(15, 0), "market_close": dt.time(15, 0),
            "after_end": dt.time(15, 5),
        }
        if s in specials:
            return specials[s]
        try:
            if ":" in s:
                h, m = s.split(":")[:2]
                return dt.time(int(h), int(m))
            return dt.time(int(s), 0)
        except ValueError:
            engine.log.warn(f"run_daily 时间 '{tm_raw}' 无法识别,按 09:30 处理")
            return dt.time(9, 30)

    def _split_sched_args(args, kwargs):
        argv = [a for a in args if callable(a)]
        ctx_args = [a for a in args if not callable(a)]
        func = argv[0] if argv else kwargs.get("func")
        return func, ctx_args

    def run_daily(*args, **kwargs):
        func, ctx_args = _split_sched_args(args, kwargs)
        cand = [a for a in ctx_args if isinstance(a, (str, int, dt.time))]
        tm_raw = kwargs.get("time", cand[-1] if cand else None)
        spec = _parse_time(tm_raw)
        engine.daily_jobs.append({
            "time": spec if spec is not None else dt.time(9, 30),
            "func": func, "ran": False,
            "every_bar": spec is None})

    def run_interval(*args, **kwargs):
        func, ctx_args = _split_sched_args(args, kwargs)
        cand = [a for a in ctx_args if isinstance(a, (int, float))]
        seconds = kwargs.get("seconds", cand[-1] if cand else 60)
        engine.interval_jobs.append({"seconds": seconds, "func": func})

    api["run_daily"] = run_daily
    api["run_interval"] = run_interval

    # 设置类(记录日志,部分生效)
    api["set_universe"] = lambda codes: setattr(engine, "universe",
                                                [codes] if isinstance(codes, str) else list(codes))
    def set_commission(buy_ratio=None, sell_ratio=None, min_commission=None, **kw):
        if buy_ratio is not None:
            engine.buy_commission = buy_ratio
        if sell_ratio is not None:
            engine.sell_commission = sell_ratio
        if min_commission is not None:
            engine.min_commission = min_commission
        engine.commission = engine.sell_commission or engine.buy_commission \
            or engine.commission
        engine.log.info(f"set_commission: 买入={engine.buy_commission} "
                        f"卖出={engine.sell_commission} 最低={engine.min_commission}")
    api["set_commission"] = set_commission
    api["set_limit_mode"] = lambda mode="LIMIT": engine.log.info(f"set_limit_mode({mode}) 已忽略(模拟环境无涨跌停限制)")
    api["set_params"] = lambda **kw: engine.params.update(kw)
    api["set_backtest"] = lambda **kw: engine.log.info(f"set_backtest({kw}) 已忽略")
    api["set_yesterday_position"] = lambda positions="": engine.log.info("set_yesterday_position 已忽略")
    api["set_parameters"] = api["set_params"]
    api["sleep"] = lambda seconds=1: None
    api["has_event"] = lambda: False

    # ================= 聚宽(JoinQuant)风格兼容层 =================
    # 便于移植 JQ 策略;与 PTrade 原生 API 无冲突,原生策略不会触达。
    import pandas as pd

    api["set_option"] = lambda *a, **k: None
    api["set_benchmark"] = lambda bench="": engine.log.info(f"set_benchmark({bench}) 已忽略")
    api["set_slippage"] = lambda *a, **k: engine.log.info("set_slippage 已忽略(模拟环境无滑点)")
    api["set_order_cost"] = lambda *a, **k: engine.log.info("set_order_cost 已忽略(使用引擎佣金设置)")

    class _OrderCostStub:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    api["OrderCost"] = _OrderCostStub
    api["PriceRelatedSlippage"] = lambda *a, **k: None
    api["FixedSlippage"] = lambda *a, **k: None

    def get_name(code):
        try:
            return engine.ds.security_info(code)["display_name"]
        except Exception:
            return str(code)

    api["get_name"] = get_name

    # ---- get_current_data: [code].paused / .last_price / .day_open 等 ----
    class _CurDatum:
        def __init__(self, code):
            self.code = code
            try:
                bar = engine.ds.daily_bar(code, engine.now.date())
            except Exception:
                bar = {}
            self.last_price = engine.get_price(code)
            self.paused = bool(bar.get("_paused"))
            self.day_open = bar.get("open", self.last_price)
            self.high_limit = bar.get("high_limit", round(self.last_price * 1.1, 3))
            self.low_limit = bar.get("low_limit", round(self.last_price * 0.9, 3))
            self.is_st = False
            self.name = get_name(code)

    class CurrentData:
        def __getitem__(self, code):
            return _CurDatum(code)

        def paused(self, code):
            return self[code].paused

    api["get_current_data"] = lambda: CurrentData()

    # ---- 聚宽签名 get_price(start_date/end_date/count/frequency/fields/panel) ----
    def _norm_date(d, default=None):
        if d is None:
            return default
        if isinstance(d, dt.datetime):
            return d.date()
        if isinstance(d, dt.date):
            return d
        return dt.date.fromisoformat(str(d))

    def jq_get_price(security, start_date=None, end_date=None, frequency="daily",
                     fields=None, skip_paused=False, fq="pre", count=None,
                     panel=True, fill_paused=None, **kw):
        codes = [security] if isinstance(security, str) else list(security)
        ensure_fn = getattr(engine.ds, "ensure", None)
        if ensure_fn:
            ensure_fn(codes)
        freq = "1m" if str(frequency).lower() in ("1m", "minute", "m") else "1d"
        if isinstance(fields, str):
            fields = [fields]
        fields = list(fields) if fields else ["open", "close", "high", "low", "volume", "money"]
        end_d = _norm_date(end_date, engine.now.date())

        if freq == "1d":
            start_d = _norm_date(start_date)
            if start_d is not None:
                days = [d.isoformat() for d in engine.ds.trade_days(start_d, end_d)]
                if count is not None:
                    days = days[-int(count):]
            elif count is not None:
                acc, d = [], end_d
                while len(acc) < int(count):
                    acc.append(d)
                    d = engine.ds.prev_trade_date(d)
                days = sorted(d2.isoformat() for d2 in acc)
            else:
                days = []
            # 整数位置索引: 兼容 JQ 时代的 series[-1] 位置取值写法
            idx = pd.RangeIndex(len(days))

            def col(code, f):
                return [_bar_field(code, dt.date.fromisoformat(dd), f) for dd in days]
        else:
            tms = [t for t in simdata.TRADE_TIMES if t <= engine.now.time()]
            if not tms:
                tms = list(simdata.TRADE_TIMES)
            idx = pd.RangeIndex(len(tms))

            def col(code, f):
                return [_bar_field(code, end_d, f, tm=t) for t in tms]

        def frame(code):
            return JQFrame({f: col(code, f) for f in fields}, index=idx)

        if isinstance(security, str):
            return frame(security)
        if panel:
            return {f: JQFrame({c: col(c, f) for c in codes}, index=idx)
                    for f in fields}
        return {c: frame(c) for c in codes}

    api["get_price"] = jq_get_price

    # ---- attribute_history: 截至上一交易日的 count 根 ----
    def attribute_history(security, count, unit="1d", fields=None,
                          skip_paused=True, df=True, fq="pre"):
        import pandas as _pd
        if str(unit).lower() in ("1m", "minute", "m"):
            return jq_get_price(security, end_date=engine.now, frequency="1m",
                                fields=fields, panel=False)
        if fields is None:
            fields = ["open", "close", "low", "high", "volume", "money"]
        if isinstance(fields, str):
            fields = [fields]
        days = _history_days(int(count), include=False)
        idx = _pd.RangeIndex(len(days))
        return JQFrame({f: [_bar_field(security, d, f) for d in days]
                        for f in fields}, index=idx)

    api["attribute_history"] = attribute_history

    # ---- get_extras('unit_net_value', ...) ----
    def get_extras(extra_name, securities, start_date=None, end_date=None,
                   df=True, **k):
        codes = [securities] if isinstance(securities, str) else list(securities)
        sd = _norm_date(start_date, engine.now.date())
        ed = _norm_date(end_date, engine.now.date())
        days = [d.isoformat() for d in engine.ds.trade_days(sd, ed)]
        out = JQFrame({c: [_bar_field(c, dt.date.fromisoformat(dd), "unit_nav")
                           for dd in days] for c in codes},
                      index=pd.to_datetime(days))
        if extra_name != "unit_net_value":
            engine.log.warn(f"get_extras({extra_name}) 未支持,以净值占位返回")
        return out if df else {c: out[c].to_dict() for c in codes}

    api["get_extras"] = get_extras

    # ---- finance.run_query(query(...)): 返回空表(策略侧有 try/except 兜底) ----
    class _JQQuery:
        def __init__(self, *a, **k):
            pass

        def filter(self, *a, **k):
            return self

        def orderby(self, *a, **k):
            return self

    class _JQFinance:
        class FUND_NET_VALUE:
            code = "code"
            day = "day"
            net_value = "net_value"

        @staticmethod
        def run_query(q):
            return pd.DataFrame()

    api["query"] = lambda *a, **k: _JQQuery()
    api["finance"] = _JQFinance

    # ---- 打新 / 逆回购: 模拟环境跳过 ----
    api["get_ipo_stocks"] = lambda *a, **k: []

    def ipo_stocks_order(*a, **k):
        engine.log.info("新股申购在模拟环境跳过")
        return True

    api["ipo_stocks_order"] = ipo_stocks_order
    api["auto_ipo_subscribe"] = lambda *a, **k: engine.log.info("新股自动申购在模拟环境跳过")

    def reverse_repurchase(*a, **k):
        engine.log.info("国债逆回购在模拟环境跳过")
        return None

    api["reverse_repurchase"] = reverse_repurchase

    # 原生别名: 供移植策略的垫片层回溯调用(见 jq_to_ptrade.py 生成的文件)
    api["_native_get_price"] = api["get_price"]
    api["_native_get_history"] = api["get_history"]
    api["_native_get_trade_days"] = api["get_trade_days"]
    api["_native_get_stock_status"] = api["get_stock_status"]
    api["_native_get_stock_name"] = api["get_stock_name"]
    api["_native_get_trading_day"] = api["get_trading_day"]

    return api


def _convert_jq_text(raw):
    """聚宽源码 → PTrade 风格:移除 jqdata 导入,沪深后缀改为 .SS/.SZ。"""
    lines = []
    for line in raw.splitlines():
        if line.strip() == "from jqdata import *":
            lines.append("# [自动转换] from jqdata import * 已由模拟环境兼容层替代")
            continue
        lines.append(line)
    text = "\n".join(lines) + "\n"
    return text.replace("XSHG", "SS").replace("XSHE", "SZ")


def _auto_convert_jq(path, raw):
    """检测到聚宽格式时,生成/更新旁路转换文件并返回其路径。"""
    import os as _os
    d, base = _os.path.split(path)
    out = _os.path.join(d, "ptrade_" + base)
    converted = _convert_jq_text(raw)
    try:
        with open(out, encoding="utf-8") as f:
            if f.read() == converted:
                return out
    except OSError:
        pass
    with open(out, "w", encoding="utf-8") as f:
        f.write(converted)
    return out


def load_strategy(path):
    """加载策略文件为模块对象;供 run_strategy_file 与 GUI 共用。
    自动识别聚宽格式(from jqdata / .XSHG/.XSHE)并即时转换。"""
    raw = None
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except UnicodeDecodeError:
        with open(path, encoding="gbk", errors="replace") as f:
            raw = f.read()
    if raw is not None and ("from jqdata import *" in raw or ".XSHG" in raw
                            or ".XSHE" in raw):
        path = _auto_convert_jq(path, raw)
    spec = importlib.util.spec_from_file_location("user_strategy", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except ModuleNotFoundError as e:
        raise RuntimeError(f"策略依赖不可用模块: {e}") from e
    return mod


def run_strategy_file(path, start="2026-07-01", end="2026-08-21",
                      capital=1_000_000, verbose=True, data_source=None):
    """加载策略文件(含 initialize 的模块)并在模拟环境中运行。

    data_source: 传入 redata.RealDataSource() 即为真实历史行情回测;
    缺省使用合成行情(simdata)。
    """
    mod = load_strategy(path)
    engine = SimEngine(capital=capital, verbose=verbose, data_source=data_source)
    return engine.run(mod, dt.date.fromisoformat(start), dt.date.fromisoformat(end))
