# -*- coding: utf-8 -*-
"""真实历史行情数据源(东方财富 K 线接口,前复权),带本地磁盘缓存。

对齐 PTrade 回测语义:
- 前复权价格(与 get_history(fq='pre') 一致)
- 真实 A 股交易日历(由参考 ETF 的实际交易日生成)
- 日线回测按当日收盘价撮合(intraday_price 返回当日 close)
- 停牌日无 bar,价格沿用最近交易日收盘(volume=0, _paused=True)

与 simdata(合成行情)暴露相同的函数面,可直接替换引擎数据源。
"""
import bisect
import csv
import datetime as dt
import json
import os
import random
import time
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor

from . import data as simdata

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache")
_REF_CODE = "510300.SS"
_MARKET = {"SS": "1", "SZ": "0"}
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "*/*",
}
# 裸域名偶发拒绝连接,使用编号 CDN 主机轮换
_HOSTS = ["92.push2his.eastmoney.com", "21.push2his.eastmoney.com",
          "48.push2his.eastmoney.com", "64.push2his.eastmoney.com",
          "push2his.eastmoney.com"]


def _secid(code):
    num, mkt = code.split(".")
    return f"{_MARKET[mkt]}.{num}"


def _limit_pct(code, name=""):
    """ETF 涨跌幅:科创/创业板相关 ±20%,其余 ±10%。"""
    num = code.split(".")[0]
    if num.startswith(("588", "689")) or "科创" in name or "创业" in name:
        return 0.20
    return 0.10


class RealDataSource:
    """真实日线数据源。首次访问某代码时自动下载并缓存到 data_cache/*.csv。"""

    DEFAULT_UNIVERSE = simdata.DEFAULT_UNIVERSE

    def __init__(self, cache_dir=None, beg="20240101"):
        self.cache_dir = cache_dir or CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
        self.beg = beg
        # 逐条"数据就绪"日志开关(默认隐藏;环境变量 PTRADE_SIM_DATA_LOG=1 可强制开启)
        self.show_data_logs = os.environ.get("PTRADE_SIM_DATA_LOG") == "1"
        self.bars = {}      # code -> {date_str: bar_dict}
        self.names = dict(simdata.SEC_NAMES)
        self._calendar = None
        self._names_path = os.path.join(self.cache_dir, "names.json")
        try:
            with open(self._names_path, encoding="utf-8") as f:
                self.names.update(json.load(f))
        except (OSError, ValueError):
            pass
        # 确认无行情数据的代码黑名单(未上市/无效),列表构建时排除
        self._bad_path = os.path.join(self.cache_dir, "bad_codes.txt")
        self.bad_codes = set()
        try:
            with open(self._bad_path, encoding="utf-8") as f:
                self.bad_codes = {line.strip() for line in f if line.strip()}
        except OSError:
            pass
        # 进程内"当日增量更新"尝试记录: 失败的代码当天不再反复请求
        self._update_attempted = set()

    def mark_bad(self, code):
        """K 线确认无数据的代码记入黑名单,后续直接跳过。"""
        if code in self.bad_codes:
            return
        self.bad_codes.add(code)
        try:
            with open(self._bad_path, "a", encoding="utf-8") as f:
                f.write(code + "\n")
        except OSError:
            pass

    def first_date(self, code):
        """本地缓存中该代码的首个交易日;未加载返回 None。"""
        m = self.bars.get(code)
        if not m:
            return None
        return min(m.keys())

    # ---------- 下载与缓存 ----------
    def _fetch(self, code):
        """拉取全量日线,返回 (name, [bar, ...])。腾讯为主源,东财为备用。"""
        try:
            return self._fetch_tx(code)
        except Exception:
            return self._fetch_em(code)

    @staticmethod
    def _tx_symbol(code):
        num, mkt = code.split(".")
        return ("sh" if mkt == "SS" else "sz") + num

    def _fetch_tx(self, code):
        """腾讯 ifzq 前复权日线,640 根/页自动向前翻页。"""
        sym = self._tx_symbol(code)
        beg_iso = f"{self.beg[:4]}-{self.beg[4:6]}-{self.beg[6:]}"
        end = dt.date.today().isoformat()
        merged = {}
        name = None
        for _ in range(12):
            url = ("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?"
                   f"param={sym},day,{beg_iso},{end},640,qfq")
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r:
                payload = json.loads(r.read().decode("utf-8"))
            node = (payload.get("data") or {}).get(sym) or {}
            if name is None:
                qt = (node.get("qt") or {}).get(sym)
                if qt and len(qt) > 1:
                    name = qt[1]
            rows = node.get("qfqday") or node.get("day") or []
            if not rows:
                break
            for row in rows:
                merged[row[0]] = row
            oldest = rows[0][0]
            if oldest <= beg_iso or len(rows) < 640:
                break
            end = (dt.date.fromisoformat(oldest) - dt.timedelta(days=1)).isoformat()
        if not merged:
            raise RuntimeError(f"{code} 腾讯接口返回空数据")
        out = []
        for dstr in sorted(merged):
            row = merged[dstr]
            try:
                volume_lot = float(row[5])
            except (ValueError, IndexError):
                continue
            o, c = float(row[1]), float(row[2])
            h, l = float(row[3]), float(row[4])
            vol = int(volume_lot * 100)  # 手 -> 股
            try:
                amount = float(row[6])
            except (ValueError, IndexError):
                amount = round(vol * c, 2)
            out.append({"date": dstr, "open": o, "close": c, "high": h,
                        "low": l, "volume": vol, "amount": amount})
        return name or code, out

    def _fetch_em(self, code):
        """东财备用源,多主机轮换重试。"""
        query = (f"secid={_secid(code)}&fields1=f1,f2,f3,f4,f5,f6"
                 "&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1"
                 f"&beg={self.beg}&end=20991231")
        last_err = None
        payload = None
        for host in _HOSTS:
            url = f"https://{host}/api/qt/stock/kline/get?{query}"
            req = urllib.request.Request(url, headers=_HEADERS)
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    payload = json.loads(r.read().decode("utf-8"))
                break
            except Exception as e:
                last_err = e
                time.sleep(0.5)
        if payload is None:
            raise RuntimeError(f"{code} 东财K线下载失败: {last_err}") from last_err
        data = payload.get("data") or {}
        name = data.get("name") or code
        out = []
        for k in data.get("klines") or []:
            p = k.split(",")
            try:
                out.append({
                    "date": p[0], "open": float(p[1]), "close": float(p[2]),
                    "high": float(p[3]), "low": float(p[4]),
                    "volume": int(float(p[5]) * 100),  # 手 -> 股
                    "amount": float(p[6]),
                })
            except (ValueError, IndexError):
                continue
        return name, out

    def _csv_path(self, code):
        return os.path.join(self.cache_dir, f"{code.replace('.', '_')}.csv")

    def _warn(self, msg):
        if getattr(self, "log", None):
            self.log.warn(msg)

    def _info(self, msg):
        if getattr(self, "log", None):
            self.log.info(msg)

    # ---------- 全市场 ETF 列表 ----------
    def all_etfs(self, max_age_days=7):
        """全市场 ETF 列表 [(code, name), ...]。东财 clist,本地缓存 7 天。"""
        path = os.path.join(self.cache_dir, "all_etfs.csv")
        rows = []
        if os.path.exists(path):
            age = (time.time() - os.path.getmtime(path)) / 86400
            if age < max_age_days:
                with open(path, encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                if rows:
                    return self._drop_bad([(r["code"], r["name"]) for r in rows])
        try:
            pairs = self._fetch_etf_list()
            if pairs:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["code", "name"])
                    w.writerows(pairs)
                for c, n in pairs:          # 名称入缓存,批量下载时可免名称查询
                    self.names.setdefault(c, n)
                self._info(f"全市场 ETF 列表已更新: {len(pairs)} 只")
                return self._drop_bad(pairs)
        except Exception as e:
            self._warn(f"全市场 ETF 列表获取失败: {e}")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if rows:
                self._warn("全市场列表获取失败,使用过期缓存")
                return self._drop_bad([(r["code"], r["name"]) for r in rows])
        return []

    def all_Ashares(self, max_age_days=7):
        """全市场 A 股代码列表 [(code, name), ...]。

        数据来源: 东财 clist 沪深A股板块(全 A),本地缓存 7 天。
        返回的代码经 A 股代码段过滤(沪 60/68、深 00/30),剔除 B 股、北交所、
        基金/债券等。仅用于构造回测股票池;板块成分 / ST 状态等以真机为准。
        """
        path = os.path.join(self.cache_dir, "all_Ashares.csv")
        rows = []
        if os.path.exists(path):
            age = (time.time() - os.path.getmtime(path)) / 86400
            if age < max_age_days:
                with open(path, encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                if rows:
                    return self._drop_bad([(r["code"], r["name"]) for r in rows])
        try:
            pairs = self._fetch_Ashare_list()
            if pairs:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["code", "name"])
                    w.writerows(pairs)
                for c, n in pairs:
                    self.names.setdefault(c, n)
                self._info(f"全市场 A 股列表已更新: {len(pairs)} 只")
                return self._drop_bad(pairs)
        except Exception as e:
            self._warn(f"全市场 A 股列表获取失败: {e}")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if rows:
                self._warn("全市场 A 股列表获取失败,使用过期缓存")
                return self._drop_bad([(r["code"], r["name"]) for r in rows])
        return []

    def _fetch_Ashare_list(self):
        """全市场 A 股列表: 东财 clist 沪深A股(m:0+t:2 沪A, m:1+t:2 深A),
        按代码段筛出 A 股。"""
        items = self._fetch_clist("m:0+t:2,m:1+t:2")
        return self._normalize_Ashares(items)

    def _drop_bad(self, pairs):
        return [(c, n) for c, n in pairs if c not in self.bad_codes]

    def _fetch_etf_list(self):
        """全市场上市 ETF 列表:东财 clist -> 天天基金代码表(两级回退)。"""
        for fn in (self._fetch_etf_list_clist, self._fetch_etf_list_fundjs):
            try:
                pairs = fn()
                if pairs:
                    return pairs
            except Exception as e:
                self._warn(f"{fn.__name__} 失败: {e}")
        return []

    @staticmethod
    def _normalize_etfs(items):
        """按上市 ETF 代码段归一化并去重(沪 51/52/56/58、深 159)。"""
        seen, out = set(), []
        for num, name in items:
            if num.startswith("159"):
                c = num + ".SZ"
            elif num.startswith(("51", "52", "56", "58")):
                c = num + ".SS"
            else:
                continue
            if c not in seen:
                seen.add(c)
                out.append((c, name))
        out.sort(key=lambda x: x[0])
        return out

    def _fetch_etf_list_fundjs(self):
        """天天基金静态代码表(约2MB,含全部场内外基金),按代码段筛出上市 ETF。"""
        import re
        req = urllib.request.Request(
            "https://fund.eastmoney.com/js/fundcode_search.js",
            headers={"User-Agent": _HEADERS["User-Agent"],
                     "Referer": "https://fund.eastmoney.com/"})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8")
        items = re.findall(
            r'\["(\d{6})"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"[^"]*"', body)
        pairs = [(num, full or abbr)
                 for num, abbr, full in items if "ETF" in (full or abbr).upper()]
        pairs = self._normalize_etfs(pairs)
        if len(pairs) < 500:
            raise RuntimeError(f"代码表解析异常, 仅得 {len(pairs)} 只")
        return pairs

    def _fetch_clist(self, fs, max_pages=40, exclude_names=("退", "*")):
        """通用东财 clist 拉取: 分页取字段 f12(代码)/f13(市场)/f14(名称)。

        fs: 板块过滤串(如 "b:MK0021,..." 或 "m:0+t:2,m:1+t:2")。
        返回 [(code, name), ...](已去重;分页中断时返回已得部分)。"""
        pairs, last_err = [], None
        for host in ["push2.eastmoney.com", "92.push2.eastmoney.com",
                     "21.push2.eastmoney.com"]:
            try:
                page = 1
                while page <= max_pages:
                    url = (f"https://{host}/api/qt/clist/get?pn={page}&pz=500"
                           "&po=1&np=1&fltt=2&invt=2&fid=f12"
                           f"&fs={fs}&fields=f12,f14,f13")
                    req = urllib.request.Request(url, headers=_HEADERS)
                    with urllib.request.urlopen(req, timeout=15) as r:
                        d = json.loads(r.read().decode("utf-8"))
                    diff = (d.get("data") or {}).get("diff") or []
                    if not diff:
                        break
                    for x in diff:
                        num = str(x.get("f12", "")).strip()
                        mkt = x.get("f13")
                        name = str(x.get("f14", "")).strip()
                        suffix = "SS" if mkt == 1 else ("SZ" if mkt == 0 else None)
                        if num and suffix and not name.startswith(exclude_names):
                            pairs.append((num + "." + suffix, name))
                    page += 1
                if pairs:
                    break
            except Exception as e:
                last_err = e
                continue
        if not pairs:
            raise RuntimeError(str(last_err) if last_err else "clist 返回空")
        seen, out = set(), []
        for c, n in pairs:
            if c not in seen:
                seen.add(c)
                out.append((c, n))
        return out

    def _normalize_Ashares(self, items):
        """按 A 股代码段归一化(沪 60/68 → .SS,深 00/30 → .SZ),去重并排序。"""
        seen, out = set(), []
        for num, name in items:
            if num.startswith(("60", "68")):
                c = num + ".SS"
            elif num.startswith(("00", "30")):
                c = num + ".SZ"
            else:
                continue
            if c not in seen:
                seen.add(c)
                out.append((c, name))
        out.sort(key=lambda x: x[0])
        return out

    def _fetch_etf_list_clist(self):
        """东财 clist 分页拉取全市场 ETF(沪深)。"""
        pairs = self._fetch_clist("b:MK0021,b:MK0022,b:MK0023,b:MK0024")
        return self._normalize_etfs(pairs)

    def _load_code(self, code):
        """加载单个代码:优先缓存,缺失或过期时增量下载(带重试)。"""
        if code in self.bad_codes:
            raise RuntimeError(f"{code} 已知无行情数据(未上市或无效)")
        if code in getattr(self, "_session_dead", set()):
            raise RuntimeError(f"{code} 本次运行已确认无法加载(网络失败且无本地缓存)")
        path = self._csv_path(code)
        rows = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        last = rows[-1]["date"] if rows else None
        today = dt.date.today().isoformat()
        if last is None or (last < today and code not in self._update_attempted):
            self._update_attempted.add(code)   # 当天只尝试一次,失败则用旧缓存
            name, fetched = None, []
            for attempt in range(3):
                try:
                    name, fetched = self._fetch(code)
                    break
                except Exception:
                    if attempt == 2:
                        if not rows:
                            # 进程内标记为死代码,后续访问立即快速失败,
                            # 避免盘中每根bar重复走完整重试循环
                            if not hasattr(self, "_session_dead"):
                                self._session_dead = set()
                            self._session_dead.add(code)
                            raise RuntimeError(
                                f"{code} 无本地缓存且下载失败(已重试3次),请检查网络后重试") from None
                        self._warn(f"{code} 增量更新失败,使用本地缓存(截至 {last})")
                    else:
                        time.sleep(1.0 + attempt)
            if fetched:
                have = {r["date"] for r in rows}
                rows += [b for b in fetched if b["date"] not in have]
                rows.sort(key=lambda b: b["date"])
                self._save_csv(path, rows)
                if name:
                    self.names[code] = name
                    self._save_names()
        self._index_code(code, rows)
        if getattr(self, "show_data_logs", False) and getattr(self, "log", None):
            self.log.info(f"真实数据就绪: {code} {self.names.get(code, '')} ({len(rows)} 根日线)")

    def _index_code(self, code, rows):
        """把 csv 行转成按日索引的 bar 字典(含 pre_close/涨跌停/unit_nav)。"""
        m = {}
        prev_close = None
        for r in rows:
            close = float(r["close"])
            pre = prev_close if prev_close is not None else close
            pct = _limit_pct(code, self.names.get(code, ""))
            m[r["date"]] = {
                "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": close,
                "pre_close": round(pre, 4),
                "high_limit": round(pre * (1 + pct), 3),
                "low_limit": round(pre * (1 - pct), 3),
                "unit_nav": close,
                "volume": int(r["volume"]), "amount": float(r["amount"]),
                "money": float(r["amount"]),
                "_paused": False,
            }
            prev_close = close
        self.bars[code] = m

    def _save_csv(self, path, rows):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["date", "open", "close", "high",
                                              "low", "volume", "amount"])
            w.writeheader()
            w.writerows(rows)

    def _save_names(self):
        try:
            with open(self._names_path, "w", encoding="utf-8") as f:
                json.dump(self.names, f, ensure_ascii=False)
        except OSError:
            pass

    def ensure(self, codes, parallel=8):
        """批量加载(并行下载缺失代码,单代码失败不影响整体)。"""
        missing = sorted({c for c in codes if c and c not in self.bars})
        if not missing:
            return

        done = [0]

        def safe_load(c):
            try:
                self._load_code(c)
            except Exception as e:
                self._warn(f"{c} 数据加载失败: {e}")
            finally:
                done[0] += 1
                if done[0] % 100 == 0:
                    self._info(f"批量补下载进度 {done[0]}/{len(missing)}")

        if len(missing) == 1:
            safe_load(missing[0])
            return
        self._bulk = True                     # 批量模式(子类可据此精简请求)
        try:
            with ThreadPoolExecutor(max_workers=parallel) as ex:
                list(ex.map(safe_load, missing))
        finally:
            self._bulk = False
        failed = [c for c in missing if c not in self.bars]
        if failed:
            self._warn(f"以下代码数据未能加载: {', '.join(failed[:10])}")

    # ---------- 交易日历 ----------
    def _ensure_calendar(self):
        if self._calendar is None:
            if _REF_CODE not in self.bars:
                self._load_code(_REF_CODE)
            self._calendar = sorted(self.bars[_REF_CODE].keys())
        return self._calendar

    def is_trade_date(self, day):
        d = day.isoformat() if isinstance(day, dt.date) else str(day)
        return d in set(self._ensure_calendar())

    def trade_days(self, start, end):
        cal = self._ensure_calendar()
        lo, hi = start.isoformat(), end.isoformat()
        for d in cal:
            if lo <= d <= hi:
                yield dt.date.fromisoformat(d)

    def prev_trade_date(self, day):
        cal = self._ensure_calendar()
        key = day.isoformat() if isinstance(day, dt.date) else str(day)
        i = bisect.bisect_left(cal, key)
        if i > 0:
            return dt.date.fromisoformat(cal[i - 1])
        return day - dt.timedelta(days=1)

    # ---------- 行情 ----------
    def _last_bar_on_or_before(self, code, key):
        m = self.bars[code]
        dates = self._code_dates(code)
        i = bisect.bisect_right(dates, key)
        if i == 0:
            return m[dates[0]], dates[0]
        d = dates[i - 1]
        return m[d], d

    def _code_dates(self, code):
        if not hasattr(self, "_date_idx"):
            self._date_idx = {}
        if code not in self._date_idx:
            self._date_idx[code] = sorted(self.bars[code].keys())
        return self._date_idx[code]

    def daily_bar(self, code, day):
        if code not in self.bars:
            self.ensure([code])
        if code not in self.bars:
            raise RuntimeError(f"{code} 无行情数据(下载失败或代码无效)")
        key = day.isoformat() if isinstance(day, dt.date) else str(day)
        m = self.bars[code]
        if key in m:
            return m[key]
        # 停牌/无数据:沿用最近交易日收盘
        b, d = self._last_bar_on_or_before(code, key)
        paused = dict(b)
        paused.update({"open": b["close"], "high": b["close"],
                       "low": b["close"], "volume": 0, "amount": 0.0,
                       "_paused": True})
        return paused

    def intraday_price(self, code, day, tm=None):
        """日线合成日内价(确定性): 开盘→收盘按时间插值 + 微幅种子噪声。

        防未来函数: t 时刻报价不再直接等于当日收盘;但路径形态仍由当日
        开/收决定(日线数据的结构性近似),盘中触发的信号为近似结果,
        以真机回测为准。"""
        bar = self.daily_bar(code, day)
        c = float(bar.get("close", 0.0) or 0.0)
        if not c:
            return 0.0
        o = float(bar.get("open", 0.0) or 0.0)
        if tm is None or tm >= dt.time(15, 0) or not o:
            return round(c, 4)
        mins = max((tm.hour - 9) * 60 + tm.minute - 30, 0)
        if tm.hour >= 13:
            mins = 120 + (tm.hour - 13) * 60 + tm.minute
        frac = min(mins / 330.0, 1.0)
        seed = zlib.crc32(f"{code}|{day.isoformat()}".encode("utf-8")) \
            & 0xffffffff
        rng = random.Random(seed)
        drift = rng.uniform(-0.0015, 0.0015)
        px = (o + (c - o) * frac) * (1 + drift * (1 - 0.5 * frac))
        lo, hi = (o, c) if o <= c else (c, o)
        pad = abs(c - o) * 0.02 + c * 0.0005
        px = min(max(px, lo - pad), hi + pad)
        return round(px, 4)

    def is_paused(self, code, day):
        key = day.isoformat() if isinstance(day, dt.date) else str(day)
        return key not in self.bars.get(code, {"__x": 0}) or \
            self.daily_bar(code, day).get("_paused", False)

    def security_info(self, code):
        name = self.names.get(code, code.split(".")[0] + "ETF")
        return {"display_name": name, "name": name, "start_date": "2018-01-01",
                "end_date": "2999-12-31", "type": "etf"}
