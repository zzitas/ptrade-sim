# -*- coding: utf-8 -*-
"""命令行运行入口。

用法:
    ptrade-run                                  # 内置示例策略(合成行情)
    ptrade-run 策略.py 2026-06-01 2026-08-21 1000000
"""
import os
import sys


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    default_demo = os.path.join(os.path.dirname(__file__), "demo_strategy.py")
    strategy = os.path.abspath(args[0]) if args else default_demo
    start = args[1] if len(args) > 1 else "2026-07-01"
    end = args[2] if len(args) > 2 else "2026-08-21"
    capital = float(args[3]) if len(args) > 3 else 1_000_000
    source = args[4].lower() if len(args) > 4 else "sim"

    from .engine import run_strategy_file
    ds = None
    if source == "tdx":
        from .tdxdata import TdxDataSource
        ds = TdxDataSource()
    elif source == "real":
        from .redata import RealDataSource
        ds = RealDataSource()
    return run_strategy_file(strategy, start, end, capital=capital,
                             verbose=True, data_source=ds)


if __name__ == "__main__":
    main()
