# -*- coding: utf-8 -*-
"""验证垫片 _pt_native 在两种宿主环境下的解析:
A) 真实 PTrade: 先注入原生 API 再 exec 策略源码(快照路径)
B) 模拟器: exec 后再注入原名 + _native_* 别名(命名空间/别名路径)
"""
import datetime
import sys
import traceback

import numpy as np
import pandas as pd

SRC = open(r"D:\xquant\ptrade_七星动态池.py", encoding="utf-8").read()


class FakeLog(object):
    def info(self, m):
        pass

    def warn(self, m):
        pass

    def warning(self, m):
        pass

    def error(self, m):
        pass

    def debug(self, m):
        pass


def make_natives():
    idx_d = pd.date_range("2026-03-02", periods=10, freq="B")
    idx_m = pd.date_range("2026-03-16 09:30", periods=30, freq="min")

    def get_history(count=1, frequency="1d", field="close",
                    security_list=None, fq=None, include=False,
                    is_dict=False, **kw):
        flds = field if isinstance(field, list) else [field]
        idx = idx_m if frequency == "1m" else idx_d
        n = min(int(count), len(idx))
        use = idx[-n:]
        codes_in = [security_list] if isinstance(security_list, str) \
            else list(security_list or [])
        # 模拟恒生端: 含异常代码时抛 reindex 类错误(列表/单只均拦截)
        if any(str(c).startswith("BAD") for c in codes_in):
            raise RuntimeError(
                "Reindexing only valid with uniquely valued Index objects")
        if isinstance(security_list, (list, tuple)):
            if is_dict:
                # 恒生文档 {str: array()} 形态: 二维数组,列序与 fields 一致
                base = np.arange(len(use), dtype=float) + 1
                arr = np.column_stack([base] * len(flds))
                return {c: arr for c in security_list}
            if len(flds) > 1:
                # 多标的 + 多字段(无 is_dict): {代码: DataFrame}
                return {c: pd.DataFrame(
                            {f: np.arange(len(use), dtype=float) + 1
                             for f in flds}, index=use)
                        for c in security_list}
            # 多标的 + 单字段 → DataFrame columns=代码
            return pd.DataFrame({c: np.arange(len(use), dtype=float) + 1
                                 for c in security_list}, index=use)
        return pd.DataFrame({f: np.arange(len(use), dtype=float) + 1
                             for f in flds}, index=use)

    def get_trading_day(day=0):
        return datetime.date(2026, 3, 16)

    def get_price(security, start_date=None, end_date=None, frequency="1d",
                  fields=None, fq=None, count=None, **kw):
        # 恒生真实约束: 日期入参必须是字符串
        assert start_date is None or isinstance(start_date, str), \
            "get_price start_date 必须为字符串: " + repr(start_date)
        assert end_date is None or isinstance(end_date, str), \
            "get_price end_date 必须为字符串: " + repr(end_date)
        flds = fields if isinstance(fields, list) else [fields or "close"]
        idx = idx_m if frequency == "1m" else idx_d

        def _p(v):
            s = str(v).replace("/", "-")
            try:
                return datetime.datetime.strptime(
                    s[:19], "%Y-%m-%d %H:%M:%S").date()
            except ValueError:
                return datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()

        sd = _p(start_date) if start_date is not None else None
        ed = _p(end_date) if end_date is not None else None
        dates = [d.date() if hasattr(d, "date") else d for d in idx]
        mask = np.array([(sd is None or d >= sd) and (ed is None or d <= ed)
                         for d in dates])
        sel = idx[mask]
        if count:
            sel = sel[-int(count):]
        return pd.DataFrame({f: np.arange(len(sel), dtype=float) + 1
                             for f in flds}, index=sel)

    def get_stock_name(c):
        # 恒生真实行为: 无论单个还是列表入参,恒返回 {代码: 名称} 字典
        keys = c if isinstance(c, (list, tuple)) else [c]
        return {k: "测试" + str(k) for k in keys}

    def get_stock_status(codes, f=None):
        keys = codes if isinstance(codes, (list, tuple)) else [codes]
        return {k: False for k in keys}

    def get_trade_days(start_date=None, end_date=None, count=None, **kw):
        days = list(pd.date_range("2026-03-02", "2026-03-16", freq="B").date)
        if start_date:
            days = [d for d in days if d >= start_date]
        if end_date:
            days = [d for d in days if d <= end_date]
        if count:
            days = days[-int(count):]
        return days

    return {"get_history": get_history, "get_price": get_price,
            "get_stock_name": get_stock_name,
            "get_stock_status": get_stock_status,
            "get_trade_days": get_trade_days,
            "get_trading_day": get_trading_day, "log": FakeLog()}


def exercise(ns, tag):
    ok = True
    ah = ns["attribute_history"]("510300.SS", 5, "1d",
                                 ["close", "high", "low", "open"])
    assert len(ah) == 5 and "close" in ah.columns, tag + " attribute_history"
    assert float(ah["close"][-1]) == 5.0, tag + " attribute_history[-1] 位置取值"

    gp = ns["get_price"]("510300.SS", start_date=datetime.date(2026, 3, 16),
                         end_date=datetime.datetime(2026, 3, 16, 10, 0),
                         frequency="1m", fields=["volume"], skip_paused=False,
                         panel=False)
    assert gp is not None and len(gp) > 0 and "volume" in gp.columns, \
        tag + " get_price 分钟区间"

    gp2 = ns["get_price"]("510300.SS", start_date=datetime.date(2026, 3, 10),
                          end_date=datetime.date(2026, 3, 13),
                          frequency="daily", fields=["close"])
    assert len(gp2) == 4, tag + f" get_price 日线区间过滤(得{len(gp2)}天)"

    gp3 = ns["get_price"]("510300.SS", end_date=datetime.date(2026, 3, 16),
                          count=6, fields="close")
    assert len(gp3) == 6, tag + " get_price count"

    gp4 = ns["get_price"]("510300.SS", start_date=datetime.date(2026, 3, 16),
                          end_date=datetime.date(2026, 3, 16),
                          frequency="daily", fields=["close"])
    assert len(gp4) == 0, \
        tag + f" 同日区间应绕过原生并返回空(得{len(gp4)})"

    gp5 = ns["get_price"]("510300.SS", start_date=datetime.date(2026, 3, 16),
                          end_date=datetime.datetime(2026, 3, 16, 10, 0),
                          frequency="1m", fields=["volume"])
    assert len(gp5) > 0 and "volume" in gp5.columns, tag + " 当日分钟走模拟"

    nm = ns["get_name"]("510300.SS")
    assert isinstance(nm, str) and nm == "测试510300.SS", \
        tag + " get_name 应解包为纯字符串, 实际: " + repr(nm)

    cd = ns["get_current_data"]()
    d = cd["510300.SS"]
    assert d is not None and isinstance(d.name, str), \
        tag + " get_current_data 名称应为纯字符串: " + repr(getattr(d, "name", None))

    td = ns["get_trade_days"](start_date=datetime.date(2026, 3, 12),
                              end_date=datetime.date(2026, 3, 16), count=2)
    assert len(td) == 2 and hasattr(td[0], "year"), tag + " get_trade_days"

    ex = ns["get_extras"]("unit_net_value", "510300.SS",
                          start_date=datetime.date(2026, 3, 12),
                          end_date=datetime.date(2026, 3, 16))
    assert ex is not None and len(ex.columns) == 1, tag + " get_extras"

    bx = ns["pt_batch_history"](["510300.SS", "159915.SZ"], 5, "1d", "close")
    assert list(bx.columns) == ["510300.SS", "159915.SZ"] and len(bx) == 5, \
        tag + " pt_batch_history 批量列"

    bx2 = ns["pt_batch_history"](
        ["510300.SS", "510300.SS", "159915.SZ", "BAD100.SS"], 5, "1d", "close")
    assert bx2.columns.is_unique, tag + " 批量结果列去重"
    assert "BAD100.SS" not in bx2.columns and "510300.SS" in bx2.columns \
        and "159915.SZ" in bx2.columns, \
        tag + f" 坏代码剔除且好代码保留(得{list(bx2.columns)})"

    bm = ns["pt_batch_hist_multi"](
        ["510300.SS", "510300.SS", "159915.SZ", "BAD100.SS"], 5,
        ["close", "high"])
    assert isinstance(bm, dict) and set(bm) >= {"close", "high"}, \
        tag + " multi 返回字段键"
    cb = bm["close"]
    assert cb.columns.is_unique and "BAD100.SS" not in cb.columns \
        and {"510300.SS", "159915.SZ"} <= set(cb.columns) and len(cb) == 5, \
        tag + f" multi 批量容错(得{list(cb.columns)})"
    assert float(cb["510300.SS"].iloc[-1]) == 5.0, tag + " multi 数组值提取"

    nw = ns["pt_warm_snapshot"](["600000.SS", "600001.SS"])
    assert nw == 2, tag + f" 快照预热条数(得{nw})"
    dw = ns["get_current_data"]()["600000.SS"]
    assert isinstance(dw.name, str) and dw.name.startswith("测试"), \
        tag + " 预热后名称: " + repr(dw.name)
    assert not dw.paused and dw.last_price > 0, \
        tag + " 预热后价格: " + repr(dw.last_price)

    ah2 = ns["attribute_history"]("510300.SS", 5, "1d", ["close"])
    assert float(ah2["close"][-1]) == float(ah["close"][-1]), \
        tag + " attribute_history 当日缓存一致性"
    print(f"[{tag}] 全部通过")
    return ok


def run_case(tag, inject_before, aliases=False):
    natives = make_natives()
    ns = {"__name__": "strategy_" + tag}
    if inject_before:
        ns.update(natives)
    try:
        exec(compile(SRC, "<strategy>", "exec"), ns)
    except Exception:
        print(f"[{tag}] exec 失败:")
        traceback.print_exc()
        return False
    if not inject_before:
        # 模拟引擎注入规则: 不覆盖策略/垫片已定义的名字
        for k, v in natives.items():
            if k not in ns:
                ns[k] = v
            if aliases and k != "log":
                ns["_native_" + k] = v
    try:
        exercise(ns, tag)
        return True
    except AssertionError as e:
        print(f"[{tag}] 断言失败: {e}")
        return False
    except Exception:
        print(f"[{tag}] 运行异常:")
        traceback.print_exc()
        return False


results = [
    run_case("A-真实PTrade预注入", inject_before=True),
    run_case("B1-模拟器后注入+别名", inject_before=False, aliases=True),
    run_case("B2-模拟器后注入无别名", inject_before=False, aliases=False),
]
print("=" * 40)
if all(results):
    print("SHIM NS TEST: ALL PASS")
    sys.exit(0)
sys.exit(1)
