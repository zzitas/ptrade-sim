# -*- coding: utf-8 -*-
"""验证新增的 A 股日线获取能力(simdata 合成源,无需联网)。

覆盖:
- get_Ashares 在合成源下回退到样本股票池
- get_all_Ashare_daily(stocks=[...], 区间) 返回 {code: DataFrame}
- get_all_Ashare_daily(count=...) 取最近 N 个交易日
- 字段/索引形状正确, 兼容 JQSeries 的位置取值
"""
import datetime as dt

from ptrade_sim.engine import SimEngine, build_api
from ptrade_sim import data as simdata


def main():
    eng = SimEngine(capital=100000, verbose=False, data_source=simdata)
    api = build_api(eng)

    ok = True

    # 1) get_Ashares 回退样本池
    ash = api["get_Ashares"]()
    if not ash or ash != list(simdata.DEFAULT_STOCK_POOL):
        print("FAIL get_Ashares 回退样本池:", ash[:3], "...")
        ok = False
    else:
        print(f"PASS get_Ashares 样本池 {len(ash)} 只, 例: {ash[:3]}")

    # 2) get_all_Ashare_daily 区间版
    codes = ["600519.SS", "000001.SZ", "300750.SZ"]
    start, end = "2026-01-05", "2026-01-16"
    out = api["get_all_Ashare_daily"](stocks=codes, start_date=start,
                                      end_date=end,
                                      fields=["open", "close", "volume"])
    if set(out.keys()) != set(codes):
        print("FAIL 返回代码集不一致:", set(out.keys()))
        ok = False
    else:
        for c in codes:
            df = out[c]
            days = list(simdata.trade_days(dt.date(2026, 1, 5),
                                           dt.date(2026, 1, 16)))
            if list(df.index) != [d for d in days]:
                print(f"FAIL {c} 索引与交易日历不符")
                ok = False
                break
            if list(df.columns) != ["open", "close", "volume"]:
                print(f"FAIL {c} 列不符: {list(df.columns)}")
                ok = False
                break
            # JQSeries 位置取值兼容
            if df["close"][-1] != df["close"].iloc[-1]:
                print(f"FAIL {c} JQSeries 位置取值不兼容")
                ok = False
                break
        else:
            print(f"PASS get_all_Ashare_daily 区间版: {len(codes)} 只 x "
                  f"{len(out['600519.SS'])} 交易日, 列=open/close/volume")

    # 3) get_all_Ashare_daily count 版
    out2 = api["get_all_Ashare_daily"](stocks="600519.SS", end_date="2026-01-16",
                                       count=5, fields="close")
    df2 = out2["600519.SS"]
    if len(df2) != 5:
        print(f"FAIL count 版长度应为5, 实际 {len(df2)}")
        ok = False
    else:
        print(f"PASS get_all_Ashare_daily count=5: 末日 {df2.index[-1]} "
              f"收盘 {df2['close'][-1]}")

    # 4) 单标的单字段: 返回 DataFrame(非 dict)
    single = api["get_all_Ashare_daily"](stocks="600519.SS",
                                         start_date="2026-01-05",
                                         end_date="2026-01-16", fields="close")
    if not isinstance(single, dict) or "600519.SS" not in single:
        print("FAIL 单标的应返回 {code: DataFrame}")
        ok = False
    else:
        print("PASS 单标的返回 {code: DataFrame}")

    print("\n==== 结果:", "ALL PASS" if ok else "HAS FAIL", "====")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
