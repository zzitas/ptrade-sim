# -*- coding: utf-8 -*-
"""聚宽策略 → 真实 PTrade 原生版转换器。

生成策略头部内置"垫片层"(全部用 PTrade 官方 API 实现聚宽功能),
同一文件可在恒生 PTrade 回测与本模拟器中运行。

用法: python jq_to_ptrade.py [输入.py] [输出.py]
"""
import re
import sys

SHIM = '''# ==================== 聚宽→PTrade 兼容垫片(自动生成) ====================
# 用 PTrade 官方 API 实现策略用到的聚宽接口;真实 PTrade 与模拟环境均可运行。
import datetime as _dt
import time as _time
import numpy as _np
import pandas as _pd

# 平台在执行策略代码前把原生 API 注入本模块命名空间;垫片随后的同名定义会覆盖
# 它们,故必须在此刻先快照一份原生函数供 _pt_native 解析。
_PT_API = {k: v for k, v in list(globals().items())
           if callable(v) and not k.startswith("_")}

_PT_TODAY_CACHE = {"ts": 0.0, "val": None, "fn": None}

# 名称永不变化——进程级缓存,避免逐只远程查询
_PT_NAME_CACHE = {}

# HALT 状态按回测日缓存
_PT_STATUS_CACHE = {"day": None, "store": {}}

try:
    import builtins as _builtins
except Exception:
    _builtins = None

_PT_NATIVES = {}

# 垫片自定义的名字:解析原生函数时跳过它们(否则会解析到垫片自身导致递归)
_PT_OWNED = {"set_option", "set_order_cost", "set_slippage", "OrderCost",
             "PriceRelatedSlippage", "FixedSlippage", "get_name",
             "get_current_data", "attribute_history", "get_price",
             "get_extras", "query", "finance", "get_ipo_stocks",
             "ipo_stocks_order", "auto_ipo_subscribe", "get_trade_days",
             "log", "_pt_to_date", "_pt_get_price_fallback",
             "_pt_trade_days_from_history", "_pt_name_of", "_pt_fmt_dt",
             "attribute_history", "pt_batch_history", "pt_batch_hist_multi",
             "_pt_sub_series", "_pt_halted", "pt_warm_snapshot"}


def _pt_native(name):
    """惰性解析 PTrade 原生函数。

    查找顺序: 启动快照 → 模块命名空间 → builtins → _native_* 别名。
    真实 PTrade 与模拟器分别走前两条/末条路径。
    (历史教训: 标准库系统模块会被恒生沙箱拦截,垫片只依赖
     datetime/time/numpy/pandas/builtins)
    """
    fn = _PT_NATIVES.get(name)
    if fn is not None:
        return fn
    fn = _PT_API.get(name)
    if fn is None and name not in _PT_OWNED:
        g = globals().get(name)
        if callable(g):
            fn = g
    if fn is None and _builtins is not None:
        f3 = getattr(_builtins, name, None)
        if callable(f3):
            fn = f3
    if fn is None:
        f4 = globals().get("_native_" + name)
        if callable(f4):
            fn = f4
    if fn is None:
        raise RuntimeError(f"兼容垫片找不到原生函数 {name}")
    _PT_NATIVES[name] = fn
    return fn


class _PTFrame(_pd.DataFrame):
    """位置取值兼容帧: 恢复聚宽时代 df['close'][-1] 等写法。"""
    @property
    def _constructor(self):
        return _PTFrame

    def __getitem__(self, key):
        out = super().__getitem__(key)
        if isinstance(out, _pd.Series):
            out = _PTSeries(out)
        return out


class _PTSeries(_pd.Series):
    @property
    def _constructor(self):
        return _PTSeries

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except (KeyError, IndexError):
            if isinstance(key, int) and not isinstance(key, bool):
                return self.iloc[key]
            raise


def set_option(*_a, **_k):
    return None


def set_order_cost(*_a, **_k):
    log.info("set_order_cost 已忽略(使用 PTrade 佣金默认设置)")
    return None


class OrderCost:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class PriceRelatedSlippage:
    def __init__(self, *a, **k):
        pass


class FixedSlippage:
    def __init__(self, *a, **k):
        pass


def set_slippage(*_a, **_k):
    log.info("set_slippage 已忽略(使用 PTrade 默认滑点)")
    return None


def _pt_name_of(code):
    """原生 get_stock_name 恒返回 {代码: 名称} 字典(官方文档),解包为纯名称。

    名称静态不变,进程级缓存;未命中才发起远程查询。
    """
    if code in _PT_NAME_CACHE:
        return _PT_NAME_CACHE[code]
    out = _pt_native("get_stock_name")(code)
    if isinstance(out, dict):
        for k, v in out.items():
            if v is not None and k not in _PT_NAME_CACHE:
                _PT_NAME_CACHE[k] = str(v)
        val = out.get(code)
        if val is None and len(out) == 1:
            val = next(iter(out.values()))
        out = val
    if out is None:
        name = str(code)
    else:
        name = str(out)
    _PT_NAME_CACHE[code] = name
    return name


def _pt_halted(code):
    """HALT 状态,按回测日缓存(状态盘中不变)。"""
    today = _pt_today()
    if _PT_STATUS_CACHE["day"] != today:
        _PT_STATUS_CACHE["day"] = today
        _PT_STATUS_CACHE["store"] = {}
    st = _PT_STATUS_CACHE["store"]
    if code not in st:
        val = False
        try:
            raw = _pt_native("get_stock_status")([code], "HALT")
            if isinstance(raw, dict):
                val = bool(raw.get(code, False))
            else:
                val = bool(raw)
        except Exception:
            val = False
        st[code] = val
    return st[code]


def get_name(code):
    try:
        return _pt_name_of(code)
    except Exception:
        return str(code)


def _pt_today():
    """当前回测交易日。

    优先引擎时钟 get_trading_day(官方 API,纯日历查询,两端均廉价且随
    回测日精确推进——当日缓存依赖它做跨日失效);不可用时回退
    get_history 探测 + 15 秒墙钟缓存(真机数据查询昂贵)。
    """
    fn = _PT_TODAY_CACHE["fn"]
    if fn is None:
        try:
            fn = _pt_native("get_trading_day")
        except Exception:
            fn = False
        _PT_TODAY_CACHE["fn"] = fn
    if fn:
        try:
            out = fn(0)
            if isinstance(out, _dt.datetime):
                return out.date()
            if isinstance(out, _dt.date):
                return out
            return _dt.datetime.strptime(str(out)[:10].replace("/", "-"),
                                         "%Y-%m-%d").date()
        except Exception:
            pass
    now = _time.time()
    if now - _PT_TODAY_CACHE["ts"] < 15 and _PT_TODAY_CACHE["val"] is not None:
        return _PT_TODAY_CACHE["val"]
    val = None
    try:
        df = _pt_native("get_history")(1, frequency="1d", field=["close"],
                                       include=True, fq="pre")
        if df is not None and len(df):
            ts = df.index[-1]
            val = ts.date() if hasattr(ts, "date") else ts
    except Exception:
        pass
    if val is None:
        val = _dt.date.today()
    _PT_TODAY_CACHE.update(ts=now, val=val)
    return val


class _PTCurDatum:
    def __init__(self, code, name=None, paused=None, last_minute=None):
        self.code = code
        if name is not None:
            name = str(name)
            _PT_NAME_CACHE[code] = name
        self.name = _pt_name_of(code)
        self.paused = bool(paused) if paused is not None else _pt_halted(code)
        self.last_price = 0.0
        self.day_open = 0.0
        try:
            day = _pt_native("get_history")(1, frequency="1d",
                                            field=["open", "close"],
                                            security_list=code, include=True,
                                            fq="pre")
            if day is not None and len(day):
                self.day_open = float(day["open"].iloc[-1])
                self.last_price = float(day["close"].iloc[-1])
        except Exception:
            pass
        if not self.paused:
            if last_minute is not None:
                try:
                    lm = float(last_minute)
                    if lm == lm and lm > 0:
                        self.last_price = lm
                except Exception:
                    pass
            else:
                try:
                    m = _pt_native("get_history")(1, frequency="1m",
                                                  field=["close"],
                                                  security_list=code,
                                                  include=True)
                    if m is not None and len(m) \
                            and float(m["close"].iloc[-1]) > 0:
                        self.last_price = float(m["close"].iloc[-1])
                except Exception:
                    pass
        self.high_limit = round(self.last_price * 1.1, 3)
        self.low_limit = round(self.last_price * 0.9, 3)
        self.is_st = False


def pt_warm_snapshot(codes):
    """一次性批量预热 get_current_data 快照(名称/HALT/最新分钟价)。

    未预热的字段(日线开收)仍按需逐只查询;已预热代码的重复访问零远程调用。
    返回预热条数。"""
    uniq = list(dict.fromkeys(codes))
    today = _pt_today()
    cd = get_current_data()
    todo = [c for c in uniq if (c, today) not in cd._cache]
    if not todo:
        return 0
    names = {}
    try:
        raw = _pt_native("get_stock_name")(todo)
        if isinstance(raw, dict):
            names = {k: v for k, v in raw.items() if v is not None}
    except Exception:
        pass
    halted = {}
    try:
        raw = _pt_native("get_stock_status")(todo, "HALT")
        if isinstance(raw, dict):
            halted = {k: bool(v) for k, v in raw.items()}
    except Exception:
        pass
    minute = None
    try:
        minute = _pt_native("get_history")(1, frequency="1m", field=["close"],
                                           security_list=todo, include=True)

        def _minute_last(fr, c):
            if fr is None:
                return None
            try:
                if isinstance(fr, dict):
                    sub = fr.get(c)
                    if sub is None or not len(sub):
                        return None
                    s = sub["close"] if "close" in getattr(
                        sub, "columns", []) else sub.iloc[:, 0]
                    return float(s.iloc[-1])
                if c in getattr(fr, "columns", []):
                    return float(fr[c].iloc[-1])
            except Exception:
                return None
            return None

        for c in todo:
            cd._cache[(c, today)] = _PTCurDatum(
                c, name=names.get(c), paused=halted.get(c, False),
                last_minute=_minute_last(minute, c))
        return len(todo)
    except Exception:
        return 0


class _PTCurrentData:
    def __init__(self):
        self._cache = {}

    def __getitem__(self, code):
        key = (code, _pt_today())
        if key not in self._cache:
            self._cache[key] = _PTCurDatum(code)
        return self._cache[key]

    def paused(self, code):
        return self[code].paused


def get_current_data():
    return _PTCurrentData()


_PT_AH_CACHE = {"day": None, "store": {}}


def attribute_history(security, count, unit="1d", fields=None,
                      skip_paused=True, df=True, fq="pre"):
    if fields is None:
        fields = ["open", "close", "low", "high", "volume", "money"]
    if isinstance(fields, str):
        fields = [fields]
    daily = str(unit).lower() in ("1d", "d", "day", "daily")
    key = (security, int(count), tuple(fields))
    if daily:
        day = _pt_today()
        if _PT_AH_CACHE["day"] != day:
            _PT_AH_CACHE["day"] = day
            _PT_AH_CACHE["store"] = {}
        else:
            ent = _PT_AH_CACHE["store"].get(key)
            if ent is not None:
                return _PTFrame(ent.copy())
    out = _pt_native("get_history")(int(count), frequency=unit, field=fields,
                                    security_list=security, include=False,
                                    fq=fq or "pre")
    if isinstance(out, _pd.DataFrame):
        if daily:
            _PT_AH_CACHE["store"][key] = out.copy()
        out = _PTFrame(out)
    return out


def _pt_sub_series(sub, flds):
    """从 is_dict 返回的元素中提取 {字段: Series}。

    兼容三种形态: DataFrame(带 columns)、{字段: 数组} 字典、
    二维 numpy 数组(文档 {str: array()} 形态,列序与 fields 一致)。
    """
    out = {}
    if sub is None:
        return out
    cols = getattr(sub, "columns", None)
    if cols is not None:
        for f in flds:
            if f in cols:
                out[f] = sub[f]
        return out
    if isinstance(sub, dict):
        for f in flds:
            v = sub.get(f)
            if v is not None and len(v):
                out[f] = _pd.Series(list(v))
        return out
    try:
        arr = _np.asarray(sub)
    except Exception:
        return out
    if arr.ndim == 2 and arr.shape[1] >= 1:
        for i, f in enumerate(flds[:arr.shape[1]]):
            out[f] = _pd.Series(arr[:, i])
    elif arr.ndim == 1 and len(flds) == 1:
        out[flds[0]] = _pd.Series(arr)
    return out


def pt_batch_hist_multi(codes, count, fields, unit="1d", include=False,
                        chunk=200):
    """一次批量获取多标的多个字段,返回 {字段: DataFrame(index=日期, columns=代码)}。

    降级链: is_dict=True 批量(真机验证形态) → 不带 is_dict 的多标的调用
    → 逐只补取(坏代码剔除、好代码保留)。
    """
    gh = _pt_native("get_history")
    flds = [str(f) for f in fields]
    seen = set()
    uniq = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    per_field = {f: [] for f in flds}
    for i in range(0, len(uniq), int(chunk)):
        part = uniq[i:i + int(chunk)]
        got_any = False
        data = None
        try:
            data = gh(int(count), frequency=unit, field=list(flds),
                      security_list=part, fq="pre",
                      include=bool(include), is_dict=True)
        except Exception:
            data = None
        if isinstance(data, dict) and data:
            collected = {f: {} for f in flds}
            for c, sub in data.items():
                for f, s in _pt_sub_series(sub, flds).items():
                    collected[f][c] = s
            for f in flds:
                if collected[f]:
                    got_any = True
                    per_field[f].append(_pd.DataFrame(collected[f]))
        if not got_any:
            # 形态二: 不带 is_dict 的多标的多字段({代码: DataFrame})
            d2 = None
            try:
                d2 = gh(int(count), frequency=unit, field=list(flds),
                        security_list=part, fq="pre", include=bool(include))
            except Exception:
                d2 = None
            if isinstance(d2, dict) and d2:
                collected = {f: {} for f in flds}
                for c, sub in d2.items():
                    for f, s in _pt_sub_series(sub, flds).items():
                        collected[f][c] = s
                for f in flds:
                    if collected[f]:
                        got_any = True
                        per_field[f].append(_pd.DataFrame(collected[f]))
            elif isinstance(d2, _pd.DataFrame) and len(d2.columns) \
                    and len(flds) == 1:
                per_field[flds[0]].append(d2)
                got_any = True
        if not got_any:
            # 终极回退: 逐只补取
            for c in part:
                try:
                    one = gh(int(count), frequency=unit, field=list(flds),
                             security_list=c, fq="pre", include=bool(include))
                except Exception:
                    continue
                if isinstance(one, _pd.DataFrame) and len(one.columns):
                    for f in flds:
                        if f in one.columns:
                            per_field[f].append(_pd.DataFrame({c: one[f]}))
    out = {}
    for f in flds:
        fs = per_field[f]
        if not fs:
            out[f] = _PTFrame()
        elif len(fs) == 1:
            out[f] = fs[0]
        else:
            try:
                merged = fs[0]
                for extra in fs[1:]:
                    try:
                        merged = _pd.concat([merged, extra], axis=1)
                    except Exception:
                        merged = merged.join(extra, how="outer")
                        merged = merged.loc[:, ~_pd.Index(
                            merged.columns).duplicated()]
                out[f] = merged
            except Exception:
                out[f] = fs[0]
    return out


def pt_batch_history(codes, count, unit="1d", field="close", chunk=200):
    """批量获取多标的同字段历史(PTrade get_history 原生支持代码列表)。

    返回 DataFrame(index=日期, columns=代码)。真机上逐只 attribute_history
    每次都是一次独立远程查询,N 只池子会耗尽数分钟;批量后每字段仅数次调用。
    防御措施: 入参去重;某块批量失败时拆成单只重试(坏代码剔除、好代码保留);
    结果去除重复列/重复索引。
    """
    gh = _pt_native("get_history")
    seen = set()
    uniq = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    frames = []
    for i in range(0, len(uniq), int(chunk)):
        part = uniq[i:i + int(chunk)]
        try:
            dfp = gh(int(count), frequency=unit, field=str(field),
                     security_list=part, include=False, fq="pre")
        except Exception:
            # 整块失败: 拆单只重试,定位并剔除坏代码
            for c in part:
                try:
                    one = gh(int(count), frequency=unit, field=str(field),
                             security_list=[c], include=False, fq="pre")
                except Exception:
                    continue
                if isinstance(one, _pd.DataFrame) and len(one.columns):
                    frames.append(one.rename(columns={one.columns[0]: c}))
            continue
        if isinstance(dfp, _pd.DataFrame) and len(dfp.columns):
            frames.append(dfp)
        elif isinstance(dfp, dict) and dfp:
            frames.append(_pd.DataFrame(dfp))
    if not frames:
        return _PTFrame()
    if len(frames) == 1:
        out = frames[0]
    else:
        try:
            out = _pd.concat(frames, axis=1)
        except Exception:
            try:
                out = _pd.concat([f[~f.index.duplicated()] for f in frames],
                                 axis=1)
            except Exception:
                out = frames[0]
    try:
        if out.columns.has_duplicates:
            out = out.loc[:, ~_pd.Index(out.columns).duplicated()]
        if out.index.has_duplicates:
            out = out[~out.index.duplicated()]
    except Exception:
        pass
    return out


def _pt_fmt_dt(v):
    """恒生数据接口的日期入参必须是字符串:date→'YYYY-MM-DD',
    datetime 保留时刻('YYYY-MM-DD HH:MM:SS')。"""
    if v is None:
        return None
    if isinstance(v, _dt.datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, _dt.date):
        return v.strftime("%Y-%m-%d")
    return str(v)


def get_price(security, start_date=None, end_date=None, frequency="daily",
              fields=None, skip_paused=None, fq=None, count=None,
              panel=None, fill_paused=None, **kw):
    sec = security
    if isinstance(sec, (list, tuple)) and len(sec) == 1:
        sec = sec[0]
    if isinstance(fields, str):
        fields = [fields]
    freq = str(frequency).lower()
    if freq in ("daily", "day"):
        freq = "1d"
    elif freq in ("minute",):
        freq = "1m"
    flds = list(fields) if fields else ["open", "high", "low", "close",
                                        "volume"]
    sd = _pt_to_date(start_date)
    ed = _pt_to_date(end_date)
    # 恒生拒绝 start_date 晚于等于回测日的请求;当日/未来区间直接走模拟路径。
    usable = sd is None or sd < _pt_today()
    out = None
    if usable:
        try:
            gp = _pt_native("get_price")
        except Exception:
            gp = None
        if gp is not None:
            try:
                out = gp(sec, start_date=_pt_fmt_dt(start_date),
                         end_date=_pt_fmt_dt(end_date),
                         frequency=freq, fields=flds, fq=fq or "pre",
                         count=count)
            except Exception as e:
                log.debug(f"原生 get_price 调用失败({e}),改用 get_history 模拟")
                out = None
    if out is None:
        out = _pt_get_price_fallback(sec, sd, ed, freq, flds, count)
    if isinstance(out, _pd.DataFrame):
        out = _PTFrame(out)
    return out


def _pt_to_date(v):
    if v is None:
        return None
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    try:
        return _dt.datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _pt_get_price_fallback(security, sd, ed, freq, fields, count):
    """平台无原生 get_price 时,用 get_history(最近N条) 模拟任意区间。"""
    gh = _pt_native("get_history")
    today = _pt_today()
    per_day = 242 if freq == "1m" else 1
    if sd is not None:
        base = ed if ed is not None else today
        n = max((base - sd).days + 1, 1) * per_day + 15
    else:
        n = int(count or 20) + (10 if freq == "1d" else 250)
    n = int(min(max(n, 5), 6500))
    df = gh(n, frequency=freq, field=list(fields), security_list=security,
            include=True, fq="pre")
    if df is None or len(df) == 0:
        return _PTFrame()
    hi = ed if ed is not None else today
    dates = [i.date() if hasattr(i, "date") else i for i in df.index]
    keep = [(sd is None or d >= sd) and (d <= hi) for d in dates]
    out = df[keep]
    if count:
        out = out.tail(int(count))
    return _PTFrame(out)


def get_extras(extra_name, securities, start_date=None, end_date=None,
               df=True, **k):
    codes = [securities] if isinstance(securities, str) else list(securities)
    sd = start_date or _pt_today()
    ed = end_date or _pt_today()
    if hasattr(sd, "date") and not isinstance(sd, _dt.date):
        sd = sd.date()
    if hasattr(ed, "date") and not isinstance(ed, _dt.date):
        ed = ed.date()
    span = max((ed - sd).days + 1, 1)
    series = {}
    for c in codes:
        dfp = _pt_native("get_history")(span + 10, frequency="1d",
                                        field=["close"], security_list=c,
                                        include=True, fq="pre")
        if dfp is not None and len(dfp):
            s = _PTSeries(dfp["close"])
            s.index = [i.date() if hasattr(i, "date") else i for i in s.index]
            series[c] = s
        else:
            series[c] = _PTSeries([], dtype=float)
    idx = sorted({d for s in series.values() for d in s.index})
    idx = [d for d in idx if sd <= d <= ed]
    out = _PTFrame({c: [float(series[c].get(d, _np.nan)) for d in idx]
                    for c in codes}, index=idx)
    if extra_name != "unit_net_value":
        log.info(f"get_extras({extra_name}) 以收盘价近似净值(垫片近似)")
    return out if df else {c: out[c].to_dict() for c in codes}


class _PTQuery:
    def __init__(self, *a, **k):
        pass

    def filter(self, *a, **k):
        return self

    def orderby(self, *a, **k):
        return self


class _PTFinance:
    class FUND_NET_VALUE:
        code = "code"
        day = "day"
        net_value = "net_value"

    @staticmethod
    def run_query(q):
        return _pd.DataFrame()


def query(*a, **k):
    return _PTQuery()


finance = _PTFinance()


def get_ipo_stocks(*a, **k):
    log.info("打新标的查询在回测中返回空(实盘请接 PTrade 原生接口)")
    return []


def ipo_stocks_order(*a, **k):
    log.info("新股申购在回测中跳过")
    return True


def auto_ipo_subscribe(context):
    log.info("自动打新在回测中跳过")
    return None


def _pt_trade_days_from_history(sd, ed):
    """平台无原生 get_trade_days 时,用基准ETF日线索引推导交易日。"""
    today = _pt_today()
    cands = [x for x in (sd, ed, today) if x is not None]
    lo, hi = min(cands), max(x for x in (ed, today) if x is not None)
    span = int(min(max((hi - lo).days + 20, 40), 800))
    df = _pt_native("get_history")(span, frequency="1d", field=["close"],
                                   security_list="510300.SS", include=True,
                                   fq="pre")
    if df is None or len(df) == 0:
        return []
    ds = [i.date() if hasattr(i, "date") else i for i in df.index]
    if sd is not None:
        ds = [d for d in ds if d >= sd]
    if ed is not None:
        ds = [d for d in ds if d <= ed]
    return sorted(set(ds))


def get_trade_days(start_date=None, end_date=None, count=None, **k):
    try:
        days = _pt_native("get_trade_days")(start_date=start_date,
                                            end_date=end_date)
    except Exception:
        days = _pt_trade_days_from_history(
            _pt_to_date(start_date), _pt_to_date(end_date))
    days = [d.date() if isinstance(d, _dt.datetime) else d for d in days]
    if count:
        days = days[-int(count):]
    return days


class _PTLog:
    _pt_proxy = True

    def __init__(self, backend=None):
        self._pt_backend = backend

    def _emit(self, level, msg):
        b = self._pt_backend
        if b is not None:
            names = ("warning", "warn") if level == "warning" else (level,)
            for nm in names:
                f = getattr(b, nm, None)
                if callable(f):
                    try:
                        f(msg)
                        return
                    except Exception:
                        pass
            print(f"[{level}] {msg}")
        else:
            print(f"[{level}] {msg}")

    def info(self, msg):
        self._emit("info", msg)

    def warn(self, msg):
        self._emit("warn", msg)

    def warning(self, msg):
        self._emit("warning", msg)

    def error(self, msg):
        self._emit("error", msg)

    def debug(self, msg):
        self._emit("debug", msg)

    def set_level(self, *a, **k):
        return None


log = _PTLog(globals().get("log", getattr(_builtins, "log", None)
                           if _builtins else None))
# ==================== 垫片结束 ====================
'''


def convert(src_path, dst_path):
    with open(src_path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    out = []
    for line in lines:
        if line.strip() == "from jqdata import *":
            continue
        out.append(line)
    text = "\n".join(out) + "\n"

    text = text.replace("XSHG", "SS").replace("XSHE", "SZ")
    text = text.replace("context.current_dt", "context.blotter.current_dt")
    text = text.replace(".total_amount", ".amount")
    text = text.replace(".closeable_amount", ".enable_amount")
    text = text.replace(".avg_cost", ".cost_basis")
    text = re.sub(r"\.price\b", ".last_sale_price", text)
    text = text.replace(".total_value", ".portfolio_value")
    text = text.replace("fields='close'", "fields=['close']")
    text = re.sub(r"run_daily\((?!context)", "run_daily(context, ", text)

    text = SHIM + "\n" + text
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(text)
    compile(text, dst_path, "exec")
    print(f"converted: {dst_path} ({len(text.splitlines())} 行, 语法OK)")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else r"D:\xquant\jq_七星动态池.py"
    dst = sys.argv[2] if len(sys.argv) > 2 else r"D:\xquant\ptrade_七星动态池.py"
    convert(src, dst)
