# -*- coding: utf-8 -*-
"""通达信(pytdx)行情数据源。

继承 RealDataSource 的缓存/日历/索引体系,仅覆写取数层:
- K 线:get_security_bars 日线分页拉取,按 xdxr 分红记录做前复权(尽力而为)
- 全市场 ETF 列表:扫描沪深证券列表(51/52/56/58 沪、159 深)
- 优先连接本地通达信终端(127.0.0.1:7709),失败自动切换公共行情主站
"""
import bisect
import socket
import threading
import time

from .redata import RealDataSource


class TdxDataSource(RealDataSource):
    SERVERS = [
        ("127.0.0.1", 17709),        # 本地通达信终端
        ("127.0.0.1", 7709),
        ("180.153.18.170", 7709), ("119.147.212.81", 7709),
        ("114.80.63.12", 7709), ("114.80.63.35", 7709),
        ("180.153.18.171", 7709), ("180.153.39.51", 7709),
        ("202.108.253.130", 7709), ("202.108.253.131", 7709),
        ("115.238.90.165", 7709), ("115.238.90.166", 7709),
        ("60.191.117.167", 7709), ("218.108.98.244", 7709),
        ("218.108.47.69", 7709), ("180.166.55.50", 7709),
        ("101.227.73.130", 7709), ("101.227.77.254", 7709),
        ("122.51.120.217", 7709), ("124.71.187.122", 7709),
        ("111.230.186.52", 7709), ("119.97.185.59", 7709),
    ]
    PAGE = 800  # get_security_bars 单次上限

    _alive_cache = {}   # 类级共享: "ip:port" -> (截止时间, 是否可达)
    _last_good = None   # 类级共享: 最近一次成功连接的主站
    _rr = 0
    _lock = threading.Lock()

    def __init__(self, cache_dir=None, beg="20240101", host=None):
        super().__init__(cache_dir=cache_dir, beg=beg)
        self.host = host
        self._tls = threading.local()   # 每线程独立连接(pytdx 非线程安全)
        self._api = None                # 主连接(列表扫描等单线程场景)
        self._sec_lists = None          # {market: [(code, name), ...]}

    # ---------- 连接 ----------
    def _alive(self, ip, port, ttl=600):
        """2 秒内能否建立 TCP 连接(结果缓存 10 分钟),避免卡在死主站的 SYN_SENT。"""
        key = f"{ip}:{port}"
        now = time.time()
        rec = TdxDataSource._alive_cache.get(key)
        if rec and rec[0] > now:
            return rec[1]
        ok = False
        try:
            s = socket.create_connection((ip, port), timeout=2)
            s.close()
            ok = True
        except OSError:
            ok = False
        TdxDataSource._alive_cache[key] = (now + ttl, ok)
        return ok

    def _conn(self):
        api = getattr(self._tls, "api", None)
        if api is not None:
            meta = getattr(self._tls, "meta", None)
            # 连接复用不超过 5 分钟,且期间主站需保持可达;否则重选(可迁回本地终端)
            if meta and time.time() - meta[2] < 300 and (
                    time.time() - meta[2] < 5 or self._alive(*meta[:2])):
                return api
            self._reset_conn()
        from pytdx.hq import TdxHq_API
        if self.host:
            candidates = [(self.host, 7709)]
        else:
            locals_ = [("127.0.0.1", 17709), ("127.0.0.1", 7709)]
            with self._lock:
                offset = TdxDataSource._rr % max(len(self.SERVERS), 1)
                TdxDataSource._rr += 1
            publics = [c for c in self.SERVERS[offset:] + self.SERVERS[:offset]
                       if c[0] != "127.0.0.1"]
            # 上次成功的主站优先,其次本地终端,再按轮询顺序探活公共主站
            last_good = TdxDataSource._last_good
            ordered = ([last_good] if last_good else []) + locals_ + publics
            seen, candidates = set(), []
            for c in ordered:
                if c not in seen and self._alive(*c):
                    seen.add(c)
                    candidates.append(c)
            if not candidates:
                raise RuntimeError("通达信: 无可达行情服务器(本地终端未开且公共主站不可达)")
        last_err = None
        for ip, port in candidates:
            api = TdxHq_API()
            try:
                if api.connect(ip, port, time_out=4):
                    TdxDataSource._last_good = (ip, port)
                    self._tls.api = api
                    self._tls.meta = (ip, port, time.time())
                    return api
            except Exception as e:
                last_err = e
        raise RuntimeError(f"无法连接通达信行情服务器({last_err})")

    def _reset_conn(self):
        try:
            api = getattr(self._tls, "api", None)
            if api is not None:
                api.disconnect()
        except Exception:
            pass
        self._tls.api = None

    def _call(self, method, *args, retries=2):
        """带断线重连的 pytdx 调用。"""
        for attempt in range(retries + 1):
            api = self._conn()
            try:
                out = getattr(api, method)(*args)
                if out is not None or method == "get_xdxr_info":
                    return out
                raise RuntimeError(f"{method} 返回空")
            except Exception as e:
                last_err = e
                self._reset_conn()
                import time as _t
                _t.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"pytdx {method} 失败: {last_err}")

    @staticmethod
    def _market_of(code):
        return 1 if code.endswith(".SS") else 0

    # ---------- K 线 ----------
    def _fetch(self, code):
        num = code.split(".")[0]
        market = self._market_of(code)
        bulk = getattr(self, "_bulk", False)   # 批量模式: 跳过名称/分红查询(1请求/代码)
        name = self.names.get(code)
        if name is None and not bulk:
            try:
                info = self._call("get_security_info", market, num)
                if info and info.get("name"):
                    name = info["name"]
            except Exception:
                pass

        beg_iso = f"{self.beg[:4]}-{self.beg[4:6]}-{self.beg[6:]}"
        chunks, start = [], 0
        while True:
            part = self._call("get_security_bars", 4, market, num, start, self.PAGE) or []
            if not part:
                break
            chunks = part + chunks
            oldest = str(part[0]["datetime"])[:10]
            if oldest <= beg_iso or len(part) < self.PAGE:
                break
            start += len(part)
        if not chunks:
            self.mark_bad(code)   # 未上市/无数据,永久跳过
            raise RuntimeError(f"{code} 通达信返回空K线")

        factors = {} if bulk else self._qfq_factors(market, num, chunks)
        out = []
        for b in chunks:
            d = str(b["datetime"])[:10]
            f = factors.get(d, 1.0)
            vol = int(float(b.get("vol", 0) or 0))  # 通达信基金日线 vol 已是股
            amt = float(b.get("amount", 0) or 0)
            out.append({"date": d,
                        "open": round(b["open"] * f, 4),
                        "close": round(b["close"] * f, 4),
                        "high": round(b["high"] * f, 4),
                        "low": round(b["low"] * f, 4),
                        "volume": vol, "amount": round(amt, 2)})
        return name, out

    def _qfq_factors(self, market, num, bars):
        """按 xdxr 分红记录计算前复权因子 {date: factor}(现金分红近似)。"""
        try:
            info = self._call("get_xdxr_info", market, num) or []
        except Exception:
            return {}
        closes = {str(b["datetime"])[:10]: float(b["close"]) for b in bars}
        dates_sorted = sorted(closes)
        events = []
        for r in info:
            div = float(r.get("fenhong") or 0)
            if div <= 0:
                continue
            exd = f"{int(r['year']):04d}-{int(r['month']):02d}-{int(r['day']):02d}"
            prev = [x for x in dates_sorted if x < exd]
            if not prev:
                continue
            c0 = closes[max(prev)]
            if c0 > 0:
                events.append((exd, max((c0 - div / 10.0) / c0, 0.05)))
        if not events:
            return {}
        ev_dates = [e[0] for e in events]
        factors = {}
        for d in dates_sorted:
            i = bisect.bisect_right(ev_dates, d)
            f = 1.0
            for _, fe in events[i:]:
                f *= fe
            factors[d] = f
        return factors

    # ---------- 全市场 ETF 列表 ----------
    def _security_lists(self):
        """多服务器轮询扫描证券列表,保留结果最全的一台。"""
        if self._sec_lists is not None:
            return self._sec_lists
        from pytdx.hq import TdxHq_API

        def scan_on(ip, port):
            api = TdxHq_API()
            if not api.connect(ip, port, time_out=6):
                raise RuntimeError("connect False")
            self._api = api
            out = {}
            complete = True
            for market in (1, 0):
                try:
                    count = int(api.get_security_count(market) or 0)
                except Exception:
                    count = 0
                rows, start = [], 0
                while start < count:
                    try:
                        part = api.get_security_list(market, start)
                    except Exception:
                        part = None
                    if not part:
                        complete = False
                        break
                    rows += [(str(x["code"]), x["name"]) for x in part]
                    start += len(part)
                    time.sleep(0.03)
                out[market] = rows
            return out, complete

        candidates = ([(self.host, 7709)] if self.host else self.SERVERS)
        candidates = [c for c in candidates if self._alive(*c)]
        best, best_score, done = {1: [], 0: []}, -1, False
        for ip, port in candidates:
            try:
                res, complete = scan_on(ip, port)
            except Exception as e:
                self._warn(f"通达信 {ip}:{port} 列表扫描失败: {e}")
                continue
            score = sum(len(v) for v in res.values())
            self._info(f"通达信 {ip}:{port} 列表扫描: {score} 条")
            if score > best_score:
                best, best_score = res, score
            if complete and score > 0:
                done = True
                break
        if best_score <= 0:
            self._warn("所有通达信主站的证券列表均不可用,get_etf_list 将回退到策略内置池")
        self._sec_lists = best
        return best

    def _fetch_etf_list(self):
        # 优先用网络列表源(东财 clist / 天天基金代码表,缓存7天)
        pairs = super()._fetch_etf_list()
        if pairs:
            return pairs
        # 兜底:TDX 本机证券列表扫描(部分主站有分页上限,可能不全)
        lists = self._security_lists()
        pairs = []
        seen = set()
        for code, name in lists[1]:
            if code.startswith(("51", "52", "56", "58")):
                c = code + ".SS"
                if c not in seen:
                    seen.add(c)
                    pairs.append((c, name))
        for code, name in lists[0]:
            if code.startswith("159"):
                c = code + ".SZ"
                if c not in seen:
                    seen.add(c)
                    pairs.append((c, name))
        pairs.sort(key=lambda x: x[0])
        return pairs

    def all_Ashares(self, max_age_days=7):
        """全市场 A 股列表: 由通达信证券列表(沪+深)按代码段筛出。

        优先复用东财 clist 全 A(父类),无网络时回退到本机证券列表扫描。"""
        pairs = RealDataSource.all_Ashares(self, max_age_days)
        if pairs:
            return pairs
        lists = self._security_lists()  # {1: [(num, name), ...], 0: [...]}
        items = []
        for mkt in (1, 0):
            for num, name in lists.get(mkt, []):
                suffix = "SS" if mkt == 1 else "SZ"
                items.append((num + "." + suffix, name))
        return self._drop_bad(self._normalize_Ashares(items))
