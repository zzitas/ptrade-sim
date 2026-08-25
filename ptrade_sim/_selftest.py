# -*- coding: utf-8 -*-
"""无头冒烟测试:跑指定策略一小段区间,汇总引擎日志中的异常与缺失 API。

用法: ptrade-selftest [策略文件] [开始] [结束] [tdx|real|sim]
默认使用通达信终端数据;完整引擎日志会写入当前目录 _selftest_logs.txt。
"""
import os
import re
import sys
from datetime import date


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    default_demo = os.path.join(os.path.dirname(__file__), "demo_strategy.py")
    path = os.path.abspath(args[0]) if args else default_demo
    start = date.fromisoformat(args[1]) if len(args) > 1 else date(2026, 7, 1)
    end = date.fromisoformat(args[2]) if len(args) > 2 else date(2026, 8, 21)
    source = args[3].lower() if len(args) > 3 else "tdx"

    from .gui import SimulatorSession

    s = SimulatorSession()
    s.start(path, start, end, 1_000_000, source=source)
    s.thread.join()
    logs = s.engine.logs
    with open("_selftest_logs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(logs))
    errors = [l for l in logs if "[ERROR]" in l]
    missing = sorted(set(re.findall(r"NameError: name '(\w+)'", "\n".join(logs))))
    print(f"data_source: {source}  区间 {start} ~ {end}")
    print("errors:", len(errors), " missing_api:", missing)
    for e in errors[:3]:
        print("---", e[:400])
    trades = [l for l in logs if ("买入" in l or "卖出" in l) and "@ " in l]
    print("trades:", len(trades))
    print("\n".join(trades[-6:]))
    print("\n".join(logs[-8:]))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
