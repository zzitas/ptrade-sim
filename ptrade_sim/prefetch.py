# -*- coding: utf-8 -*-
"""通达信全市场 K 线预热:后台批量下载全部上市 ETF / A 股的日线到本地缓存。

用法:
    python -m ptrade_sim.prefetch [etf|ashare|all] [并行数=6]
可长时间运行;已缓存的代码自动跳过(增量更新)。进度每 50 只打印一次。

- etf    : 仅预热全市场 ETF(默认)
- ashare : 仅预热全市场 A 股
- all    : ETF + A 股
"""
import sys
import time

from .tdxdata import TdxDataSource


class PrefetchLog:
    def info(self, m):
        print("[INFO]", m, flush=True)

    warn = warning = error = debug = info


def _collect_codes(ds, mode):
    codes = []
    if mode in ("etf", "all"):
        codes += [c for c, _ in ds.all_etfs()]
    if mode in ("ashare", "all"):
        codes += [c for c, _ in ds.all_Ashares()]
    return sorted(set(codes))


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "etf").lower()
    if mode not in ("etf", "ashare", "all"):
        print("用法: python -m ptrade_sim.prefetch [etf|ashare|all] [并行数]")
        return
    parallel = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    ds = TdxDataSource()
    ds.log = PrefetchLog()
    codes = _collect_codes(ds, mode)
    print(f"模式={mode} 待预热 {len(codes)} 只, 并行 {parallel}", flush=True)

    done = [0]

    def load(c):
        try:
            ds._load_code(c)
        except Exception as e:
            ds._warn(f"{c} 加载失败: {e}")
        finally:
            done[0] += 1
            if done[0] % 50 == 0:
                print(f"进度 {done[0]}/{len(codes)}", flush=True)

    from concurrent.futures import ThreadPoolExecutor
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=parallel) as ex:
        list(ex.map(load, codes))
    print(f"完成 {done[0]} 只, 用时 {(time.time()-t0)/60:.1f} 分钟", flush=True)


if __name__ == "__main__":
    main()
