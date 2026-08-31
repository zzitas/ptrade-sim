# -*- coding: utf-8 -*-
"""模拟行情数据源:确定性随机游走生成日线/分钟线,无需外部数据。"""
import datetime as dt
import math
import random
import zlib

# 模拟的 ETF/股票池(可自行扩充)
DEFAULT_UNIVERSE = [
    "510300.SS", "510500.SS", "588000.SS", "512100.SS", "159915.SZ",
    "512880.SS", "518880.SS", "513100.SS", "512690.SS", "515790.SS",
    "512480.SS", "512660.SS", "516160.SS", "159949.SZ", "512800.SS",
]

SEC_NAMES = {
    "510300.SS": "沪深300ETF", "510500.SS": "中证500ETF", "588000.SS": "科创50ETF",
    "512100.SS": "中证1000ETF", "159915.SZ": "创业板ETF", "512880.SS": "证券ETF",
    "518880.SS": "黄金ETF", "513100.SS": "纳指ETF", "512690.SS": "酒ETF",
    "515790.SS": "光伏ETF", "512480.SS": "半导体ETF", "512660.SS": "军工ETF",
    "516160.SS": "新能源ETF", "159949.SZ": "创业板50ETF", "512800.SS": "银行ETF",
}

# 模拟环境样本 A 股池(get_Ashares 的兜底返回;真实 PTrade 使用交易所全量列表)
DEFAULT_STOCK_POOL = [
    # 沪市主板
    "600519.SS", "601318.SS", "600036.SS", "600900.SS", "600030.SS",
    "601127.SS", "601899.SS", "600438.SS", "601012.SS", "603259.SS",
    "601728.SS", "603986.SS", "601799.SS", "600893.SS", "601633.SS",
    # 深市主板
    "000001.SZ", "000002.SZ", "002594.SZ", "002475.SZ", "002460.SZ",
    "000725.SZ", "002371.SZ", "000625.SZ", "002714.SZ", "002812.SZ",
    # 创业板(±20%)
    "300750.SZ", "300059.SZ", "300474.SZ", "300223.SZ", "300124.SZ",
    "300308.SZ", "300394.SZ", "300274.SZ",
    # 科创板(±20%)
    "688981.SS", "688041.SS", "688111.SS", "688012.SS", "688599.SS",
]

STOCK_NAMES = {
    "600519.SS": "贵州茅台", "601318.SS": "中国平安", "600036.SS": "招商银行",
    "600900.SS": "长江电力", "600030.SS": "中信证券", "601127.SS": "赛力斯",
    "601899.SS": "紫金矿业", "600438.SS": "通威股份", "601012.SS": "隆基绿能",
    "603259.SS": "药明康德", "601728.SS": "中国电信", "603986.SS": "兆易创新",
    "601799.SS": "星宇股份", "600893.SS": "航发动力", "601633.SS": "长城汽车",
    "000001.SZ": "平安银行", "000002.SZ": "万科A", "002594.SZ": "比亚迪",
    "002475.SZ": "立讯精密", "002460.SZ": "赣锋锂业", "000725.SZ": "京东方A",
    "002371.SZ": "北方华创", "000625.SZ": "长安汽车", "002714.SZ": "牧原股份",
    "002812.SZ": "恩捷股份", "300750.SZ": "宁德时代", "300059.SZ": "东方财富",
    "300474.SZ": "景嘉微", "300223.SZ": "北京君正", "300124.SZ": "汇川技术",
    "300308.SZ": "中际旭创", "300394.SZ": "天孚通信", "300274.SZ": "阳光电源",
    "688981.SS": "中芯国际", "688041.SS": "海光信息", "688111.SS": "金山办公",
    "688012.SS": "中微公司", "688599.SS": "天合光能",
}

BASE_PRICE = {code: 1.0 + (i % 10) * 0.35 for i, code in enumerate(DEFAULT_UNIVERSE)}
BASE_VOL = {code: 5_000_000 + i * 800_000 for i, code in enumerate(DEFAULT_UNIVERSE)}

TRADE_TIMES = []  # 9:30-11:30, 13:00-15:00 每 1 分钟一个 bar
_t = dt.time(9, 30)
while _t <= dt.time(11, 30):
    TRADE_TIMES.append(_t)
    _t = (dt.datetime(2000, 1, 1, _t.hour, _t.minute)
          + dt.timedelta(minutes=1)).time()
_t = dt.time(13, 0)
while _t <= dt.time(15, 0):
    TRADE_TIMES.append(_t)
    _t = (dt.datetime(2000, 1, 1, _t.hour, _t.minute)
          + dt.timedelta(minutes=1)).time()


def is_trade_date(day: dt.date) -> bool:
    """简化规则:周末休市(不含法定节假日)。"""
    return day.weekday() < 5


def trade_days(start, end):
    d = start
    while d <= end:
        if is_trade_date(d):
            yield d
        d += dt.timedelta(days=1)


def _seed(code, day):
    key = (code, day.isoformat() if day else "")
    return zlib.crc32(repr(key).encode())


def daily_bar(code, day):
    """生成某标的某交易日的日线 bar(close 为当日收盘价)。未知代码按哈希生成基准价。"""
    rng = random.Random(_seed(code, day))
    base = BASE_PRICE.get(code)
    if base is None:
        base = 0.5 + (zlib.crc32(code.encode()) % 500) / 100.0
    vol_base = BASE_VOL.get(code, 3_000_000 + zlib.crc32(code.encode()) % 9_000_000)
    # 锚定价格随机游走(逐日累积),保证同一天结果稳定
    ordinal = day.toordinal()
    vol_seq = 0.0
    r0 = 0.0
    for i in range(ordinal % 60 + 1):
        r = random.Random(_seed(code, day - dt.timedelta(days=i))).gauss(0, 0.018)
        if i == 0:
            r0 = r
        vol_seq += r
    px = base * math.exp(vol_seq)
    pre_close = px / (1 + r0)
    open_ = px * (1 + rng.gauss(0, 0.004))
    high = max(open_, px) * (1 + abs(rng.gauss(0, 0.006)))
    low = min(open_, px) * (1 - abs(rng.gauss(0, 0.006)))
    volume = int(vol_base * (1 + rng.gauss(0, 0.35)))
    return {
        "open": round(open_, 4), "high": round(high, 4),
        "low": round(low, 4), "close": round(px, 4),
        "pre_close": round(pre_close, 4),
        "high_limit": round(pre_close * 1.1, 3),
        "low_limit": round(pre_close * 0.9, 3),
        "unit_nav": round(px, 4),
        "volume": volume, "amount": round(volume * px, 2),
        "money": round(volume * px, 2),
    }


def intraday_price(code, day, tm: dt.time):
    """日内某时刻的模拟价格: 开盘→收盘确定性插值 + 小噪声。

    防未来函数: 盘中报价不再切换为当日收盘价。"""
    bar = daily_bar(code, day)
    rng = random.Random(_seed(code, day) ^ (tm.hour * 100 + tm.minute))
    off = rng.gauss(0, 0.0025)
    o = float(bar.get("open", 0.0) or 0.0)
    c = float(bar["close"])
    if tm >= dt.time(15, 0) or not o:
        return round(c * (1 + off), 4)
    mins = max((tm.hour - 9) * 60 + tm.minute - 30, 0)
    if tm.hour >= 13:
        mins = 120 + (tm.hour - 13) * 60 + tm.minute
    # 全天交易时长 240 分钟(上午120+下午120), 保证 15:00 时插值收敛到收盘价
    frac = min(mins / 240.0, 1.0)
    ref = o + (c - o) * frac
    return round(ref * (1 + off), 4)


def prev_trade_date(day: dt.date) -> dt.date:
    d = day - dt.timedelta(days=1)
    while not is_trade_date(d):
        d -= dt.timedelta(days=1)
    return d


def security_info(code):
    """合成数据源的安全 info: 字段尽量对齐 PTrade。"""
    num = code.split(".")[0]
    is_stock = num.startswith(("600", "601", "603", "605", "000", "001",
                               "002", "003", "300", "301", "688", "689"))
    if code in SEC_NAMES:
        name = SEC_NAMES[code]
        sec_type = "etf"
        listed = "2010-01-01"
    else:
        name = STOCK_NAMES.get(code, num)
        sec_type = "stock" if is_stock else "etf"
        listed = "2015-01-01" if is_stock else "2010-01-01"
    mkt = code.split(".")[-1] if "." in code else "SS"
    exchange = "SSE" if mkt in ("SS", "XSHG", "XBHS") else "SZSE"
    return {
        "code": code, "symbol": code,
        "name": name, "display_name": name,
        "type": sec_type, "exchange": exchange,
        "listed_date": listed, "start_date": listed,
        "de_listed_date": "", "end_date": "2999-12-31",
        "industry_code": "", "industry_name": "",
        "industry": "", "concept": [],
        "status": "N", "is_st": False, "is_halt": False,
    }
