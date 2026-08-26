# 克隆自聚宽文章：https://www.joinquant.com/post/76560
# 标题：（目前最强七星：今年487%）PT自动打新和逆回购
# 作者：开心etf

# 克隆自聚宽文章：https://www.joinquant.com/post/76366
# 标题：动量反写邪恶七星日志加强版（可用）
# 作者：偷鸡万岁


# ==================== 📦 导入模块 ====================
import numpy as np
import math
import datetime
import time
import pandas as pd
from jqdata import *
from functools import wraps

# ==================== 🌟 全局 ETF 池配置 ====================
MASTER_ETF_POOL = [
        # 行业板块 (后视镜)
        "515880.XSHG",  # 通信ETF
        "159516.XSHE",  # 半导体设备
        "159530.XSHE",  # 机器人
        "159206.XSHE",  # 卫星ETF永赢
        "560390.XSHG",  # 电网设备ETF
        "561910.XSHG",  # 电池ETF
        "159381.XSHE",  # 创业板人工智能ETF
        "159153.XSHE",  # 消费电子ETF鹏华
        "159783.XSHE",  # 科创创业50ETF
        "588710.XSHG",  # 科半导体
        "588220.XSHG",  # 科创100F
        # 大宗商品ETF
        "518880.XSHG",  # 黄金ETF
        "159980.XSHE",  # 有色ETF
        "159985.XSHE",  # 豆粕ETF
        "501018.XSHG",  # 南方原油
        '161226.XSHE',  # 白银LOF
        "159981.XSHE",  # 能源化工ETF
        # 国际ETF
        "513100.XSHG",  # 纳指ETF
        "159509.XSHE",  # 纳指科技ETF
        "513290.XSHG",  # 纳指生物ETF
        "513500.XSHG",  # 标普500ETF
        "159529.XSHE",  # 标普消费
        "513400.XSHG",  # 道琼斯ETF
        "513520.XSHG",  # 日经225ETF
        "513030.XSHG",  # 德国30ETF
        "513080.XSHG",  # 法国ETF
        "513310.XSHG",  # 中韩半导体ETF
        "513730.XSHG",  # 东南亚ETF
        # 香港ETF
        "159792.XSHE",  # 港股互联ETF
        "513130.XSHG",  # 恒生科技
        "513050.XSHG",  # 中概互联网ETF
        "159920.XSHE",  # 恒生ETF
        "513690.XSHG",  # 港股红利
        # 指数ETF
        "510300.XSHG",  # 沪深300ETF
        "510500.XSHG",  # 中证500ETF
        "510050.XSHG",  # 上证50ETF
        "510210.XSHG",  # 上证ETF
        "159915.XSHE",  # 创业板ETF
        "588080.XSHG",  # 科创50
        "512100.XSHG",  # 中证1000ETF
        "563360.XSHG",  # A500-ETF
        "563300.XSHG",  # 中证2000ETF
        # 风格ETF
        "512890.XSHG",  # 红利低波ETF
        "159967.XSHE",  # 创业板成长ETF
        "512040.XSHG",  # 价值ETF
        "159201.XSHE",  # 自由现金流ETF
        # 债券ETF
        "511380.XSHG",  # 可转债ETF
        "511010.XSHG",  # 国债ETF
        "511220.XSHG",  # 城投债ETF
    ]

# ==================== 🌟 行业ETF池（约421只，仅供播报） ====================
INDUSTRY_ETF_POOL = [
    # ==================== 芯片半导体 ====================
    "513310.XSHG",   # 中韩半导体ETF华泰柏瑞
    "588260.XSHG",   # 科创信息ETF华安
    "159801.XSHE",   # 芯片ETF广发
    "588200.XSHG",   # 科创芯片ETF嘉实
    "588170.XSHG",   # 科创半导体ETF华夏
    "159516.XSHE",   # 半导体设备ETF国泰
    "159995.XSHE",   # 芯片ETF华夏
    "512480.XSHG",   # 半导体ETF国联安
    "159558.XSHE",   # 半导体设备ETF易方达
    "512760.XSHG",   # 芯片ETF国泰
    "562590.XSHG",   # 半导体设备ETF华夏
    "588290.XSHG",   # 科创芯片ETF华安
    "159813.XSHE",   # 半导体ETF鹏华
    "588790.XSHG",   # 科创AIETF博时
    "588710.XSHG",   # 科创半导体设备ETF华泰柏瑞
    "560780.XSHG",   # 半导体设备ETF广发
    "588750.XSHG",   # 科创芯片ETF汇添富
    "561980.XSHG",   # 半导体设备ETF招商
    "589020.XSHG",   # 科创半导体设备ETF鹏华
    "588780.XSHG",   # 科创芯片设计ETF国联安
    "588890.XSHG",   # 科创芯片ETF南方
    "159325.XSHE",   # 半导体ETF南方
    "159327.XSHE",   # 半导体设备ETF万家
    "588810.XSHG",   # 科创芯片ETF富国
    "588990.XSHG",   # 科创芯片ETF博时
    "159546.XSHE",   # 集成电路ETF国泰
    "159665.XSHE",   # 半导体龙头ETF工银
    "159582.XSHE",   # 半导体ETF博时
    "562820.XSHG",   # 集成电路ETF嘉实
    "159560.XSHE",   # 芯片ETF景顺
    "159310.XSHE",   # 芯片ETF天弘
    "516350.XSHG",   # 芯片ETF易方达
    "159599.XSHE",   # 芯片ETF东财
    "516640.XSHG",   # 芯片ETF富国
    "516920.XSHG",   # 芯片ETF汇添富
    "589100.XSHG",   # 科创芯片ETF国泰
    "588920.XSHG",   # 科创芯片ETF鹏华
    "588100.XSHG",   # 科创信息ETF嘉实
    "588770.XSHG",   # 科创信息ETF摩根
    "512330.XSHG",   # 信息科技ETF南方
    "159939.XSHE",   # 信息技术ETF广发
    "159997.XSHE",   # 电子ETF天弘
    "515260.XSHG",   # 电子ETF华宝
    "515320.XSHG",   # 电子50ETF华安
    
    # ==================== 通信 ====================
    "560690.XSHG",   # 电信ETF鹏华
    "560300.XSHG",   # 电信ETF汇添富
    "515880.XSHG",   # 通信ETF国泰
    "515050.XSHG",   # 通信ETF华夏
    "159583.XSHE",   # 通信ETF富国
    "159994.XSHE",   # 通信ETF银华
    "159695.XSHE",   # 通信ETF嘉实
    "159507.XSHE",   # 通信ETF广发
    "159511.XSHE",   # 通信ETF南方
    "159811.XSHE",   # 5GETF博时
    "563010.XSHG",   # 电信ETF易方达
    
    # ==================== 证券/券商 ====================
    "513090.XSHG",   # 香港证券ETF易方达
    "516730.XSHG",   # 证券ETF浦银
    "159848.XSHE",   # 证券ETF国联安
    "510200.XSHG",   # 上证券商ETF汇安
    "516980.XSHG",   # 证券先锋ETF华富
    "562870.XSHG",   # 证券ETF嘉实
    "516200.XSHG",   # 证券ETF华安
    "512880.XSHG",   # 证券ETF国泰
    "512000.XSHG",   # 券商ETF华宝
    "159842.XSHE",   # 券商ETF银华
    "159841.XSHE",   # 证券ETF天弘
    "512570.XSHG",   # 证券ETF易方达
    "560090.XSHG",   # 证券ETF汇添富
    "515010.XSHG",   # 证券ETF华夏
    "159993.XSHE",   # 证券ETF鹏华
    "159692.XSHE",   # 证券ETF东财
    "512900.XSHG",   # 证券ETF南方
    "515850.XSHG",   # 证券ETF富国
    "515560.XSHG",   # 证券ETF建信
    "512070.XSHG",   # 证券保险ETF易方达
    "515630.XSHG",   # 证券保险ETF鹏华
    
    # ==================== 银行 ====================
    "512800.XSHG",   # 银行ETF华宝
    "516310.XSHG",   # 银行ETF易方达
    "515020.XSHG",   # 银行ETF华夏
    "159887.XSHE",   # 银行ETF富国
    "512820.XSHG",   # 银行ETF汇添富
    "512700.XSHG",   # 银行ETF南方
    "515290.XSHG",   # 银行ETF天弘
    "512730.XSHG",   # 银行ETF鹏华
    "516210.XSHG",   # 银行ETF华安
    "517900.XSHG",   # 银行AH优选ETF招商
    # ==================== 金融/金融科技 ====================
    "159933.XSHE",   # 金融地产ETF国投瑞银
    "563670.XSHG",   # 金融科技ETF鹏华
    "515720.XSHG",   # 金融科技ETF富国
    "159103.XSHE",   # 金融科技ETF汇添富
    "510650.XSHG",   # 金融地产ETF华夏
    "510230.XSHG",   # 金融ETF国泰
    "159931.XSHE",   # 金融地产ETF汇添富
    "513750.XSHG",   # 港股通非银ETF广发
    "159940.XSHE",   # 金融地产ETF广发
    "512640.XSHG",   # 金融地产ETF嘉实
    
    # ==================== 电力/公用事业 ====================
    "560620.XSHG",   # 公用事业ETF万家
    "560190.XSHG",   # 公用事业ETF鹏华
    "159669.XSHE",   # 绿色电力ETF国泰
    "512580.XSHG",   # 环保ETF广发
    "159611.XSHE",   # 电力ETF广发
    "561560.XSHG",   # 电力ETF华泰柏瑞
    "562550.XSHG",   # 绿电ETF华夏
    "562960.XSHG",   # 绿色电力ETF易方达
    "561170.XSHG",   # 绿色电力ETF富国
    "159625.XSHE",   # 绿色电力ETF嘉实
    "562350.XSHG",   # 电力ETF银华
    "561700.XSHG",   # 电力ETF博时
    "560580.XSHG",   # 电力ETF南方
    "159301.XSHE",   # 公用事业ETF华夏
    "159320.XSHE",   # 电网设备ETF广发
    "561380.XSHG",   # 电网设备ETF国泰
    "159326.XSHE",   # 电网设备ETF华夏
    
    # ==================== 红利 ====================
    "159336.XSHE",   # 央企红利ETF融通
    "159332.XSHE",   # 央企红利ETF富国
    "512390.XSHG",   # 中国低波ETF平安
    "562060.XSHG",   # 标普A股红利ETF华宝
    "561680.XSHG",   # A500红利低波ETF平安
    "560700.XSHG",   # 央企红利ETF广发
    "512530.XSHG",   # 沪深300红利ETF建信
    "159296.XSHE",   # A500红利低波ETF华宝
    "159228.XSHE",   # 红利低波ETF长城
    "560520.XSHG",   # 红利低波100ETF大成
    "560070.XSHG",   # 央企红利ETF汇添富
    "159515.XSHE",   # 国企红利ETF鹏扬
    "159333.XSHE",   # 港股央企红利ETF万家
    "159355.XSHE",   # 800红利低波ETF华宝
    "560150.XSHG",   # 红利低波ETF泰康
    "563690.XSHG",   # 红利低波ETF永赢
    "563890.XSHG",   # 国企红利ETF创金合信
    "159589.XSHE",   # 红利ETF广发
    "563700.XSHG",   # XD红利价值ETF易方达
    "512890.XSHG",   # 红利低波ETF华泰柏瑞
    "510880.XSHG",   # 红利ETF华泰柏瑞
    "515180.XSHG",   # 红利ETF易方达
    "515080.XSHG",   # 中证红利ETF招商
    "515450.XSHG",   # 红利低波50ETF南方
    "515100.XSHG",   # 红利低波100ETF景顺
    "159307.XSHE",   # 红利低波100ETF博时
    "515300.XSHG",   # 300红利低波ETF嘉实
    "159549.XSHE",   # 红利低波ETF天弘
    "159525.XSHE",   # 红利低波ETF富国
    "510720.XSHG",   # 红利国企ETF国泰
    "530880.XSHG",   # 红利国企ETF银河
    "561580.XSHG",   # 央企红利ETF华泰柏瑞
    "159905.XSHE",   # 红利ETF工银
    "515890.XSHG",   # 红利ETF博时
    "159581.XSHE",   # 红利ETF万家
    "560570.XSHG",   # A500红利ETF国联安
    "561060.XSHG",   # 国企红利ETF华安
    "159209.XSHE",   # 红利质量ETF招商
    "159758.XSHE",   # 红利质量ETF华夏
    "159708.XSHE",   # 红利ETF西部利得
    
    # ==================== 消费/食品饮料 ====================
    "159725.XSHE",   # 线上消费ETF工银
    "159672.XSHE",   # 消费ETF博时
    "560680.XSHG",   # 消费ETF广发
    "159728.XSHE",   # 在线消费ETF南方
    "516900.XSHG",   # 食品饮料ETF华安
    "159689.XSHE",   # 消费ETF南方
    "512600.XSHG",   # 消费ETF嘉实
    "159843.XSHE",   # 食品饮料ETF招商
    "159793.XSHE",   # 线上消费ETF平安
    "159520.XSHE",   # 消费龙头ETF工银
    "517550.XSHG",   # 沪港深消费龙头ETF招商
    "159862.XSHE",   # 食品饮料ETF银华
    "159730.XSHE",   # 家电ETF博时
    "159936.XSHE",   # 可选消费ETF广发
    "562580.XSHG",   # 可选消费ETF华夏
    "159670.XSHE",   # 消费50ETF国联安
    "516600.XSHG",   # 消费服务ETF工银
    "159699.XSHE",   # 恒生消费ETF广发
    "561120.XSHG",   # 家电ETF富国
    "517880.XSHG",   # 品牌消费ETF华泰柏瑞
    "159328.XSHE",   # 家电ETF易方达
    "159529.XSHE",   # 标普消费ETF景顺
    "515920.XSHG",   # 智能消费ETF博时
    "512690.XSHG",   # 酒ETF鹏华
    "159928.XSHE",   # 消费ETF汇添富
    "515170.XSHG",   # 食品饮料ETF华夏
    "515710.XSHG",   # 食品饮料ETF华宝
    "159736.XSHE",   # 食品饮料ETF天弘
    "515650.XSHG",   # 消费50ETF富国
    "510630.XSHG",   # 消费ETF华夏
    "510150.XSHG",   # 消费ETF招商
    "159798.XSHE",   # 消费ETF易方达
    "561130.XSHG",   # 国货ETF富国
    "516130.XSHG",   # 消费龙头ETF华宝
    "159732.XSHE",   # 消费电子ETF华夏
    "562950.XSHG",   # 消费电子ETF易方达
    "561100.XSHG",   # 消费电子ETF富国
    "561600.XSHG",   # 消费电子ETF平安
    "159779.XSHE",   # 消费电子ETF招商
    "561310.XSHG",   # 消电ETF国泰
    "159996.XSHE",   # 家电ETF国泰
    "560880.XSHG",   # 家电ETF广发
    
    # ==================== 医药/医疗 ====================
    "159643.XSHE",   # 疫苗ETF国泰
    "159567.XSHE",   # 港股创新药ETF银华
    "159657.XSHE",   # 疫苗ETF鹏华
    "159508.XSHE",   # 生物医药ETF华安
    "562860.XSHG",   # 疫苗ETF嘉实
    "159506.XSHE",   # 港股通创新药医疗ETF富国
    "159645.XSHE",   # 疫苗ETF富国
    "513120.XSHG",   # 港股创新药ETF广发
    "561920.XSHG",   # 疫苗ETF招商
    "520700.XSHG",   # 港股通创新药ETF万家
    "159366.XSHE",   # 港股医疗ETF永赢
    "560900.XSHG",   # 创新药ETF摩根
    "517120.XSHG",   # 创新药ETF华泰柏瑞
    "159849.XSHE",   # 生物科技ETF招商
    "516930.XSHG",   # 生物科技ETF民生加银
    "560260.XSHG",   # 医疗ETF广发
    "517990.XSHG",   # 沪港深医药ETF招商
    "588250.XSHG",   # 科创医药ETF鹏华
    "515950.XSHG",   # 医药50ETF富国
    "159891.XSHE",   # 医疗ETF建信
    "159760.XSHE",   # 医疗健康ETF泰康
    "159797.XSHE",   # 医疗器械ETF汇添富
    "515960.XSHG",   # 医药ETF嘉实
    "561510.XSHG",   # 中药ETF华泰柏瑞
    "159873.XSHE",   # 医疗设备ETF天弘
    "562390.XSHG",   # 中药ETF银华
    "159877.XSHE",   # 医疗ETF南方
    "516790.XSHG",   # 医疗ETF华泰柏瑞
    "516610.XSHG",   # 医疗设备ETF大成
    "159838.XSHE",   # 医药50ETF博时
    "513290.XSHG",   # 纳指生物科技ETF汇添富
    "512170.XSHG",   # 医疗ETF华宝
    "512010.XSHG",   # 医药ETF易方达
    "159992.XSHE",   # 创新药ETF银华
    "515120.XSHG",   # 创新药ETF广发
    "159859.XSHE",   # 生物医药ETF天弘
    "512290.XSHG",   # 生物医药ETF国泰
    "159839.XSHE",   # 生物医药ETF汇添富
    "159929.XSHE",   # 医药ETF汇添富
    "159938.XSHE",   # 医药ETF广发
    "512120.XSHG",   # 医药ETF华安
    "510660.XSHG",   # 医药ETF华夏
    "159837.XSHE",   # 生物科技ETF易方达
    "516500.XSHG",   # 生物科技ETF华夏
    "159883.XSHE",   # 医疗器械ETF永赢
    "562600.XSHG",   # 医疗器械ETF华夏
    "159898.XSHE",   # 医疗器械ETF招商
    "159828.XSHE",   # 医疗ETF国泰
    "159847.XSHE",   # 医疗ETF易方达
    "516820.XSHG",   # 医疗创新ETF平安
    "159622.XSHE",   # 创新药ETF东财
    "159748.XSHE",   # 创新药ETF富国
    "159858.XSHE",   # 创新药ETF南方
    "159835.XSHE",   # 创新药ETF建信
    "517380.XSHG",   # 创新药ETF天弘
    "516080.XSHG",   # 创新药ETF易方达
    "517110.XSHG",   # 创新药ETF国泰
    "516060.XSHG",   # 创新药ETF工银
    "589720.XSHG",   # 科创创新药ETF国泰
    "589120.XSHG",   # 科创创新药ETF汇添富
    "560080.XSHG",   # 中药ETF汇添富
    "159647.XSHE",   # 中药ETF鹏华
    "588700.XSHG",   # 科创医药ETF嘉实
    "588130.XSHG",   # 科创医药ETF华夏
    "588860.XSHG",   # 科创医药ETF工银
    "159377.XSHE",   # 创业板医药ETF国泰
    "562050.XSHG",   # 药ETF华宝
    
    # ==================== 新能源/光伏/电池 ====================
    "159872.XSHE",   # 智能网联汽车ETF鹏华
    "159618.XSHE",   # 光伏ETF华安
    "159795.XSHE",   # 智能汽车ETF汇添富
    "159889.XSHE",   # 智能汽车ETF国泰
    "159863.XSHE",   # 光伏ETF鹏华
    "159609.XSHE",   # 光伏ETF浦银
    "516180.XSHG",   # 光伏ETF平安
    "159637.XSHE",   # 新能源车ETF东财
    "516390.XSHG",   # 新能源车ETF汇添富
    "159767.XSHE",   # 电池龙头ETF兴银
    "516590.XSHG",   # 智能汽车ETF易方达
    "159824.XSHE",   # 新能源车ETF博时
    "516660.XSHG",   # 新能源车ETF华安
    "516380.XSHG",   # 智能电动车ETF华宝
    "516580.XSHG",   # 新能源ETF博时
    "159752.XSHE",   # 新能源ETF申万菱信
    "159261.XSHE",   # 创业板新能源ETF鹏华
    "515790.XSHG",   # 光伏ETF华泰柏瑞
    "159857.XSHE",   # 光伏ETF天弘
    "159864.XSHE",   # 光伏ETF国泰
    "516880.XSHG",   # 光伏ETF银华
    "516290.XSHG",   # 光伏ETF汇添富
    "562970.XSHG",   # 光伏ETF易方达
    "560980.XSHG",   # 光伏龙头ETF广发
    "515030.XSHG",   # 新能源车ETF华夏
    "515700.XSHG",   # 新能源车ETF平安
    "159806.XSHE",   # 新能源车ETF国泰
    "159755.XSHE",   # 电池ETF广发
    "159796.XSHE",   # 电池ETF汇添富
    "562880.XSHG",   # 电池ETF嘉实
    "561910.XSHG",   # 电池ETF招商
    "561160.XSHG",   # 电池ETF富国
    "159775.XSHE",   # 电池ETF建信
    "159757.XSHE",   # 电池ETF景顺
    "159566.XSHE",   # 储能电池ETF易方达
    "159305.XSHE",   # 储能电池ETF广发
    "159840.XSHE",   # 锂电池ETF工银
    "159790.XSHE",   # 碳中和ETF华夏
    "516160.XSHG",   # 新能源ETF南方
    "516270.XSHG",   # 新能源ETF华安
    "159875.XSHE",   # 新能源ETF嘉实
    "516850.XSHG",   # 新能源ETF华夏
    "516090.XSHG",   # 新能源ETF易方达
    "159387.XSHE",   # 创业板新能源ETF国泰
    "159368.XSHE",   # 创业板新能源ETF华夏
    "588830.XSHG",   # 科创新能源ETF鹏华
    "588960.XSHG",   # 科创新能源ETF富国
    "589960.XSHG",   # 科创新能源ETF易方达
    # ==================== 汽车/汽车零部件/智能驾驶 ====================
    "159306.XSHE",   # 汽车零部件ETF平安
    "159720.XSHE",   # 智能车ETF泰康
    "159512.XSHE",   # 汽车ETF广发
    "516110.XSHG",   # 汽车ETF国泰
    "159565.XSHE",   # 汽车零部件ETF易方达
    "562700.XSHG",   # 汽车零部件ETF华夏
    "516520.XSHG",   # 智能驾驶ETF华泰柏瑞
    "159888.XSHE",   # 智能汽车ETF华夏
    "515250.XSHG",   # 智能汽车ETF富国
    
    # ==================== 有色/稀土/稀有金属 ====================
    "561330.XSHG",   # 矿业ETF国泰
    "512400.XSHG",   # 有色金属ETF南方
    "159652.XSHE",   # 有色ETF汇添富
    "159876.XSHE",   # 有色ETF华宝
    "159880.XSHE",   # 有色ETF鹏华
    "159871.XSHE",   # 有色ETF银华
    "159881.XSHE",   # 有色金属ETF国泰
    "516650.XSHG",   # 有色金属ETF华夏
    "562800.XSHG",   # 稀有金属ETF嘉实
    "159608.XSHE",   # 稀有金属ETF广发
    "159671.XSHE",   # 稀有金属ETF工银
    "561800.XSHG",   # 稀有金属ETF华富
    "516150.XSHG",   # 稀土ETF嘉实
    "159715.XSHE",   # 稀土ETF易方达
    "159713.XSHE",   # 稀土ETF富国
    "516780.XSHG",   # 稀土ETF华泰柏瑞
    "159690.XSHE",   # 有色矿业ETF招商
    "560860.XSHG",   # 工业有色ETF万家
    # ==================== 钢铁/材料 ====================
    "515210.XSHG",   # 钢铁ETF国泰
    "159944.XSHE",   # 材料ETF广发
    "516710.XSHG",   # 新材料ETF华夏
    "159763.XSHE",   # 新材料ETF建信
    "516890.XSHG",   # 新材料ETF平安
    "516360.XSHG",   # 新材料ETF华宝
    "159703.XSHE",   # 新材料ETF天弘
    "159761.XSHE",   # 新材料ETF国泰
    
    # ==================== 化工 ====================
    "159870.XSHE",   # 化工ETF鹏华
    "516020.XSHG",   # 化工ETF华宝
    "516120.XSHG",   # 化工ETF富国
    "516220.XSHG",   # 化工ETF国泰
    "516570.XSHG",   # 化工行业ETF易方达
    
    # ==================== 人工智能/云计算/软件 ====================
    "159613.XSHE",   # 信息安全ETF嘉实
    "516700.XSHG",   # 大数据ETF华宝
    "560360.XSHG",   # 软件ETF万家
    "562920.XSHG",   # 信息安全ETF易方达
    "517390.XSHG",   # 云计算ETF天弘
    "159311.XSHE",   # 数字经济ETF易方达
    "159248.XSHE",   # 人工智能ETF万家
    "589380.XSHG",   # 科创人工智能ETF富国
    "561220.XSHG",   # 数字经济ETF工银
    "159363.XSHE",   # 创业板人工智能ETF华宝
    "159819.XSHE",   # 人工智能ETF易方达
    "159381.XSHE",   # 创业板人工智能ETF华夏
    "515980.XSHG",   # 人工智能ETF华富
    "515070.XSHG",   # 人工智能ETF华夏
    "159246.XSHE",   # 创业板人工智能ETF富国
    "159382.XSHE",   # 创业板人工智能ETF南方
    "588760.XSHG",   # 科创人工智能ETF广发
    "588730.XSHG",   # 科创人工智能ETF易方达
    "159242.XSHE",   # 创业板人工智能ETF大成
    "159388.XSHE",   # 创业板人工智能ETF国泰
    "159279.XSHE",   # 创业板人工智能ETF华安
    "589010.XSHG",   # 科创人工智能ETF华夏
    "588930.XSHG",   # 科创人工智能ETF银华
    "589520.XSHG",   # 科创人工智能ETF华宝
    "589560.XSHG",   # 科创人工智能ETF汇添富
    "589110.XSHG",   # 科创人工智能ETF国泰
    "589090.XSHG",   # 科创AIETF鹏华
    "512930.XSHG",   # AI人工智能ETF平安
    "515000.XSHG",   # 科技ETF华宝
    "159807.XSHE",   # 科技ETF易方达
    "515750.XSHG",   # 科技50ETF富国
    "516050.XSHG",   # 科技龙头ETF工银
    "517800.XSHG",   # 人工智能50ETF方正富邦
    "512220.XSHG",   # TMTETF景顺
    "515580.XSHG",   # 科技100ETF华泰柏瑞
    "159852.XSHE",   # 软件ETF嘉实
    "515230.XSHG",   # 软件ETF国泰
    "159899.XSHE",   # 软件ETF招商
    "562930.XSHG",   # 软件ETF易方达
    "561010.XSHG",   # 软件ETF华安
    "159590.XSHE",   # 软件ETF汇添富
    "516510.XSHG",   # 云计算ETF易方达
    "516630.XSHG",   # 云计算ETF华夏
    "159739.XSHE",   # 云计算ETF鹏华
    "159273.XSHE",   # 云计算ETF汇添富
    "159738.XSHE",   # 云计算ETF华泰柏瑞
    "159890.XSHE",   # 云计算ETF招商
    "159527.XSHE",   # 云计算ETF广发
    "560660.XSHG",   # 云计算50ETF新华
    "515400.XSHG",   # 大数据ETF富国
    "516000.XSHG",   # 大数据ETF华夏
    "159998.XSHE",   # 计算机ETF天弘
    "512720.XSHG",   # 计算机ETF国泰
    "159851.XSHE",   # 金融科技ETF华宝
    "516860.XSHG",   # 金融科技ETF博时
    "516100.XSHG",   # 金融科技ETF华夏
    "159299.XSHE",   # 金融科技ETF易方达
    "562570.XSHG",   # 信创ETF华夏
    "159538.XSHE",   # 信创ETF富国
    "159539.XSHE",   # 信创ETF广发
    "159537.XSHE",   # 信创ETF国泰
    "562030.XSHG",   # 信创ETF华宝
    "560850.XSHG",   # 信创ETF汇添富
    "159540.XSHE",   # 信创ETF易方达
    "560800.XSHG",   # 数字经济ETF鹏扬
    "159385.XSHE",   # 数字经济ETF富国
    "159658.XSHE",   # 数字经济ETF华安
    "159389.XSHE",   # 数字经济ETF嘉实
    "159256.XSHE",   # 创业板软件ETF华夏
    "159107.XSHE",   # 创业板软件ETF富国
    "563210.XSHG",   # 专精特新ETF国富
    # ==================== 科技/计算机/互联网/物联网 ====================
    "159586.XSHE",   # 计算机ETF南方
    "517360.XSHG",   # 沪港深科技ETF华安
    "517350.XSHG",   # 沪港深科技ETF广发
    "515860.XSHG",   # 科技ETF嘉实
    "159723.XSHE",   # 科技龙头ETF汇添富
    "159777.XSHE",   # 创科技ETF国联安
    "159773.XSHE",   # 创业板科技ETF华泰柏瑞
    "560990.XSHG",   # 科技先锋ETF中金
    "562560.XSHG",   # 信息技术ETF华夏
    "159729.XSHE",   # 互联网ETF汇添富
    "159550.XSHE",   # 互联网ETF东财
    "517050.XSHG",   # 互联网ETF华泰柏瑞
    "517200.XSHG",   # 互联网ETF嘉实
    "159856.XSHE",   # 互联网龙头ETF工银
    "159778.XSHE",   # 工业互联网ETF鹏华
    "159709.XSHE",   # 物联网ETF工银
    "517660.XSHG",   # 物联网ETF天弘
    "159895.XSHE",   # 物联网ETF易方达
    "159896.XSHE",   # 物联网ETF南方
    "159701.XSHE",   # 物联网ETF招商
    "516330.XSHG",   # 物联网ETF华泰柏瑞
    "516260.XSHG",   # 物联网ETF华夏
    "159909.XSHE",   # TMT50ETF招商
   
    # ==================== 机器人/智能制造 ====================
    "159542.XSHE",   # 工程机械ETF大成
    "159886.XSHE",   # 机械ETF富国
    "516960.XSHG",   # 机械ETF国泰
    "159530.XSHE",   # 机器人ETF易方达
    "562500.XSHG",   # 机器人ETF华夏
    "159770.XSHE",   # 机器人ETF天弘
    "159272.XSHE",   # 机器人ETF富国
    "159559.XSHE",   # 机器人ETF景顺
    "159278.XSHE",   # 机器人ETF鹏华
    "159526.XSHE",   # 机器人ETF嘉实
    "560770.XSHG",   # 机器人ETF招商
    "159213.XSHE",   # 机器人ETF汇添富
    "159551.XSHE",   # 机器人ETF国泰
    "159258.XSHE",   # 机器人ETF南方
    "562360.XSHG",   # 机器人ETF银华
    "560630.XSHG",   # 机器人ETF万家
    "159667.XSHE",   # 工业母机ETF国泰
    "159663.XSHE",   # 机床ETF华夏
    "516800.XSHG",   # 智能制造ETF华宝
    "562910.XSHG",   # 高端制造ETF易方达
    
    # ==================== 军工/航空航天 ====================
    "159267.XSHE",   # 航天ETF华安
    "159257.XSHE",   # 航空ETF汇添富
    "159231.XSHE",   # 通用航空ETF华宝
    "159392.XSHE",   # 航空ETF富国
    "159255.XSHE",   # 通用航空ETF易方达
    "516320.XSHG",   # 高端装备ETF华夏
    "512710.XSHG",   # 军工龙头ETF富国
    "512660.XSHG",   # 军工ETF国泰
    "512560.XSHG",   # 军工ETF易方达
    "512680.XSHG",   # 军工ETF广发
    "512810.XSHG",   # 军工ETF华宝
    "512670.XSHG",   # 国防ETF鹏华
    "159227.XSHE",   # 航空航天ETF华夏
    "159241.XSHE",   # 航空航天ETF天弘
    "159208.XSHE",   # 航空航天ETF万家
    "159638.XSHE",   # 高端装备ETF嘉实
    "159378.XSHE",   # 通用航空ETF永赢
    "159230.XSHE",   # 通用航空ETF华夏
    "159283.XSHE",   # 通用航空ETF南方
    "563320.XSHG",   # 通用航空ETF华泰柏瑞
    "159206.XSHE",   # 卫星ETF永赢
    "563230.XSHG",   # 卫星ETF富国
    "159218.XSHE",   # 卫星ETF招商
    
    # ==================== 游戏/传媒 ====================
    "159855.XSHE",   # 影视ETF银华
    "517770.XSHG",   # 游戏传媒ETF浦银
    "159869.XSHE",   # 游戏ETF华夏
    "516010.XSHG",   # 游戏ETF国泰
    "516770.XSHG",   # 游戏ETF华泰柏瑞
    "512980.XSHG",   # 传媒ETF广发
    "516190.XSHG",   # 传媒ETF华夏
    "159805.XSHE",   # 传媒ETF鹏华
    "516620.XSHG",   # 影视ETF国泰
    "159786.XSHE",   # VRETF银华
    
    # ==================== 房地产/基建 ====================
    "159787.XSHE",   # 建材ETF易方达
    "516750.XSHG",   # 建材ETF富国
    "159619.XSHE",   # 基建ETF国泰
    "512200.XSHG",   # 房地产ETF南方
    "515060.XSHG",   # 房地产ETF华夏
    "159707.XSHE",   # 地产ETF华宝
    "159768.XSHE",   # 房地产ETF银华
    "516950.XSHG",   # 基建ETF银华
    "516970.XSHG",   # 基建ETF广发
    "159635.XSHE",   # 基建ETF华夏
    "159745.XSHE",   # 建材ETF国泰
    "560280.XSHG",   # 工程机械ETF广发
    
    # ==================== 石油/能源/煤炭 ====================
    "561260.XSHG",   # 能源ETF工银
    "561790.XSHG",   # 央企能源ETF博时
    "563150.XSHG",   # 油气ETF银华
    "159731.XSHE",   # 石化ETF华夏
    "562010.XSHG",   # 绿色能源ETF华宝
    "561360.XSHG",   # 石油ETF国泰
    "159697.XSHE",   # 石油ETF鹏华
    "159588.XSHE",   # 石油ETF景顺
    "159148.XSHE",   # 石油ETF富国
    "561570.XSHG",   # 油气ETF华泰柏瑞
    "561760.XSHG",   # 油气ETF博时
    "159309.XSHE",   # 油气ETF汇添富
    "159930.XSHE",   # 能源ETF汇添富
    "159945.XSHE",   # 能源ETF广发
    "515220.XSHG",   # 煤炭ETF国泰
    "510170.XSHG",   # 大宗商品ETF国联安
    "510410.XSHG",   # 资源ETF博时
    
    # ==================== 黄金/黄金股 ====================
    "159322.XSHE",   # 黄金股ETF平安
    "517520.XSHG",   # 黄金股ETF永赢
    "159562.XSHE",   # 黄金股ETF华夏
    "517400.XSHG",   # 黄金股ETF国泰
    "159315.XSHE",   # 黄金股ETF工银
    "159321.XSHE",   # 黄金股ETF华安
    
    # ==================== 旅游 ====================
    "159766.XSHE",   # 旅游ETF富国
    "562510.XSHG",   # 旅游ETF华夏
    
    # ==================== 农业/养殖 ====================
    "159275.XSHE",   # 农牧渔ETF华宝
    "562900.XSHG",   # 农业ETF易方达
    "516760.XSHG",   # 养殖ETF平安
    "159827.XSHE",   # 农业ETF银华
    "159616.XSHE",   # 农牧ETF建信
    "516550.XSHG",   # 农业ETF嘉实
    "516810.XSHG",   # 农业ETF华夏
    "159825.XSHE",   # 农业ETF富国
    "516670.XSHG",   # 畜牧养殖ETF招商
    "159698.XSHE",   # 粮食ETF鹏华
    "159587.XSHE",   # 粮食ETF广发
    
    # ==================== 物流/运输 ====================
    "159662.XSHE",   # 交运ETF南方
    "561320.XSHG",   # 交运ETF国泰
    "516530.XSHG",   # 物流ETF银华
    "516910.XSHG",   # 物流ETF富国
    "159666.XSHE",   # 交通运输ETF华夏
    
    # ==================== 教育 ====================
    "513360.XSHG",   # 教育ETF博时
    
    # ==================== 风格ETF（价值/成长/质量/基本面） ====================
    "159391.XSHE",   # 大盘价值ETF博时
    "510030.XSHG",   # 价值ETF华宝
    "159263.XSHE",   # 价值ETF易方达
    "512040.XSHG",   # 价值100ETF富国
    "159617.XSHE",   # 中证500价值ETF华夏
    "159203.XSHE",   # 大盘成长ETF博时
    "159259.XSHE",   # 成长ETF易方达
    "159906.XSHE",   # 深成长ETF大成
    "515910.XSHG",   # 质量ETF中金
    "512750.XSHG",   # 基本面50ETF嘉实
    "159910.XSHE",   # 基本面120ETF嘉实
    "561500.XSHG",   # 漂亮50ETF华泰柏瑞
    
    # ==================== 高股息/红利 ====================
    "159207.XSHE",   # 高股息ETF广发
    "563180.XSHG",   # 高股息ETF银华
    
    # ==================== 现金流/自由现金流 ====================
    "561870.XSHG",   # 现金流全指ETF华富
    "563770.XSHG",   # 全指现金流ETF招商
    "159236.XSHE",   # 自由现金流ETF工银
    "563830.XSHG",   # 全指现金流ETF博时
    "563680.XSHG",   # 800现金流ETF汇添富
    "512130.XSHG",   # 全指现金流ETF鹏华
    "561080.XSHG",   # 全指现金流ETF华安
    "563620.XSHG",   # 全指现金流ETF兴业
    "159399.XSHE",   # 现金流ETF国泰
    "159232.XSHE",   # 自由现金流ETF南方
    "159201.XSHE",   # 自由现金流ETF华夏
    "159222.XSHE",   # 自由现金流ETF易方达
    "159233.XSHE",   # 自由现金流ETF平安
    "159229.XSHE",   # 自由现金流ETF广发
    "159223.XSHE",   # 现金流ETF永赢
    "159225.XSHE",   # 现金流ETF银华
    "159221.XSHE",   # 现金流ETF嘉实
    "159276.XSHE",   # 现金流ETF汇添富
    "563760.XSHG",   # 全指现金流ETF中银
    "563390.XSHG",   # 全指现金流ETF华泰柏瑞
    "563580.XSHG",   # 自由现金流800ETF万家
    "563780.XSHG",   # 现金流全指ETF方正富邦
    "563900.XSHG",   # 300自由现金流ETF摩根
    "562080.XSHG",   # 300现金流ETF华宝
    "563990.XSHG",   # 800现金流ETF富国
    "560120.XSHG",   # 中证500现金流ETF华夏
    "516460.XSHG",   # 现金流ETF800鹏华
    "159235.XSHE",   # 中证现金流ETF大成
    
    # ==================== MSCI系列 ====================
    "515770.XSHG",   # MSCI中国A股ETF摩根
    "512180.XSHG",   # MSCIA股ETF建信
    "512360.XSHG",   # MSCIA股ETF平安
    "512380.XSHG",   # MSCI中国ETF银华
    "512160.XSHG",   # MSCI中国A股ETF南方
    "512520.XSHG",   # MSCI中国ETF华泰柏瑞
    "515160.XSHG",   # MSCI中国ETF招商
    "512090.XSHG",   # MSCIA股ETF易方达
    "512990.XSHG",   # MSCIA股ETF华夏
    
    # ==================== A50/A500系列 ====================
    "563600.XSHG",   # A500增强ETF易方达
    "512370.XSHG",   # A500增强ETF华夏
    "563630.XSHG",   # A500增强ETF国联安
    "563280.XSHG",   # A50增强ETF富国
    "159240.XSHE",   # A500增强ETF天弘
    "561750.XSHG",   # A50ETF博时
    "512030.XSHG",   # 中证A50增强ETF易方达
    "512150.XSHG",   # 富时A50ETF汇安
    "512550.XSHG",   # 富时A50ETF嘉实
    "159601.XSHE",   # A50ETF华夏
    "563000.XSHG",   # 中国A50ETF易方达
    "159602.XSHE",   # 中国A50ETF南方
    "560050.XSHG",   # 中国A50ETF汇添富
    "561090.XSHG",   # A500增强ETF华安
    "159226.XSHE",   # 中证A500增强ETF国泰
    "159249.XSHE",   # A500增强ETF工银
    
    # ==================== 央企/国企 ====================
    "560810.XSHG",   # 央企ESGETF融通
    "563060.XSHG",   # 央企50ETF易方达
    "510060.XSHG",   # 央企ETF工银
    "561960.XSHG",   # 央企回报ETF招商
    "517090.XSHG",   # 央企共赢ETF国泰
    "515900.XSHG",   # 央企创新ETF博时
    "515680.XSHG",   # 央企创新ETF嘉实
    "515600.XSHG",   # 央企创新ETF广发
    "159974.XSHE",   # 央企创新ETF富国
    "512960.XSHG",   # 央企结构调整ETF博时
    "159959.XSHE",   # 央企ETF银华
    "562380.XSHG",   # 央企科技ETF银华
    "563050.XSHG",   # 央企科技ETF易方达
    "517180.XSHG",   # 中国国企ETF南方
    "159719.XSHE",   # 国企ETF平安
    "510810.XSHG",   # 上海国企ETF汇添富
    "510270.XSHG",   # 国企ETF中银
    "159528.XSHE",   # 国企改革ETF富国
    "159335.XSHE",   # 央企科创ETF融通
    "560170.XSHG",   # 央企科技ETF南方
    "512950.XSHG",   # 央企改革ETF华夏
    "562850.XSHG",   # 央企能源ETF嘉实
    "515760.XSHG",   # 浙江国资ETF华夏
    
    # ==================== 科创系列 ====================
    "589580.XSHG",   # 科创综指ETF兴银
    "589050.XSHG",   # 科创综指ETF兴业
    "589550.XSHG",   # 科创价值ETF华夏
    "589200.XSHG",   # 科创200ETF工银
    "588520.XSHG",   # 科创增强ETF永赢
    "589820.XSHG",   # 科创200ETF建信
    "589780.XSHG",   # 科创200ETF富国
    "589060.XSHG",   # 科创综指ETF东财
    "588690.XSHG",   # 科创增强ETF银华
    "588680.XSHG",   # 科创100增强ETF广发
    "588880.XSHG",   # 科创100ETF华泰柏瑞
    "588550.XSHG",   # 科创综指增强ETF易方达
    "588980.XSHG",   # 科创100ETF广发
    "589980.XSHG",   # 科创100ETF汇添富
    "589950.XSHG",   # 科创100ETF富国
    "589890.XSHG",   # 科创综指ETF景顺
    "588670.XSHG",   # 科创综指增强ETF嘉实
    "589700.XSHG",   # 科创成长ETF南方
    "588070.XSHG",   # 科创成长ETF万家
    "588800.XSHG",   # 科创100ETF华夏
    "588210.XSHG",   # 科创100ETF易方达
    "588020.XSHG",   # 科创成长ETF易方达
    "588110.XSHG",   # 科创成长ETF广发
    "588010.XSHG",   # 科创新材料ETF博时
    "588160.XSHG",   # 科创新材料ETF南方
    "589180.XSHG",   # 科创新材料ETF汇添富
    "588230.XSHG",   # 科创200ETF华泰柏瑞
    "588240.XSHG",   # 科创200ETF鹏华
    "588820.XSHG",   # 科创200ETF华夏
    "588270.XSHG",   # 科创200ETF易方达
    "588140.XSHG",   # 科创200ETF广发
    "588850.XSHG",   # 科创机械ETF嘉实
    "588910.XSHG",   # 科创价值ETF建信
    "589500.XSHG",   # 科创综指ETF工银
    "589600.XSHG",   # 科创综指ETF富国
    "589900.XSHG",   # 科创综指ETF博时
    
    # ==================== ESG/碳中和 ====================
    "510990.XSHG",   # 180ESGETF工银
    "159653.XSHE",   # ESG300ETF国联安
    "159621.XSHE",   # ESGETF国泰
    "159717.XSHE",   # ESGETF鹏华
    "516720.XSHG",   # ESGETF浦银
    "560180.XSHG",   # 沪深300ESGETF南方
    "561190.XSHG",   # 碳中和ETF富国
    "560550.XSHG",   # 碳中和ETF广发
    "159639.XSHE",   # 碳中和ETF南方
    "159640.XSHE",   # 碳中和龙头ETF工银
    "560060.XSHG",   # 碳中和ETF汇添富
    "159641.XSHE",   # 碳中和ETF招商
    "562990.XSHG",   # 碳中和ETF易方达
    "159642.XSHE",   # 碳中和ETF大成
    "159861.XSHE",   # 碳中和50ETF国泰
    "562300.XSHG",   # 碳中和ETF银华
    "159885.XSHE",   # 碳中和ETF鹏华
    "560560.XSHG",   # 碳中和ETF泰康
    "515090.XSHG",   # 可持续发展ETF博时
    "516070.XSHG",   # 低碳ETF易方达
    
    # ==================== 区域主题 ====================
    "512870.XSHG",   # 杭州湾区ETF南华
    "159743.XSHE",   # 湖北ETF博时
    "517330.XSHG",   # 长江保护ETF易方达
    "512190.XSHG",   # 浙商之江凤凰ETF
    "159976.XSHE",   # 湾创ETF工银
    "512970.XSHG",   # 大湾区ETF平安
    "517160.XSHG",   # 长江保护ETF南方
    "512650.XSHG",   # 长三角ETF汇添富
    "510770.XSHG",   # G60创新ETF申万菱信
    "517850.XSHG",   # 张江ETF汇添富
    "159623.XSHE",   # 成渝经济圈ETF博时
    
    # ==================== 指数/策略ETF ====================
    "510010.XSHG",   # 180治理ETF交银
    "510090.XSHG",   # 责任ETF建信
    "159965.XSHE",   # 央视50ETF国联
    "159578.XSHE",   # 深证主板50ETF南方
    "563330.XSHG",   # A股ETF华泰柏瑞
    "530530.XSHG",   # 上证580ETF华夏
    "159290.XSHE",   # 创业板综指增强ETF东财
    "159291.XSHE",   # 创业板综增强ETF招商
    "159287.XSHE",   # 创业板综ETF博时
    "159288.XSHE",   # 创业板综ETF银华
    "159289.XSHE",   # 创业板综指ETF鹏华
    "515200.XSHG",   # 创新100ETF申万菱信
    "512770.XSHG",   # 战略新兴ETF华夏
    "159966.XSHE",   # 创业板价值ETF华夏
    "510160.XSHG",   # 产业升级ETF南方
    
    # ==================== 其他主题 ====================
    "516560.XSHG",   # 养老ETF华宝
    "159973.XSHE",   # 民企ETF弘毅远方
    "515150.XSHG",   # 一带一路ETF富国
    "515110.XSHG",   # 一带一路ETF易方达
    "515990.XSHG",   # 一带一路ETF汇添富
    "159597.XSHE",   # 创业板成长ETF易方达
]

# ==================== ⏱️ 物理时间监控装饰器 ====================
def time_monitor(func_name=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_real = datetime.datetime.now()
            log.info(f"⏱️ [{func_name or func.__name__}] 开始执行 - 真实时间: {start_real.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                end_real = datetime.datetime.now()
                elapsed = end_time - start_time
                log.info(f"✅ [{func_name or func.__name__}] 执行完成 - 耗时: {elapsed*1000:.2f}ms | 真实时间: {end_real.strftime('%H:%M:%S')}")
                if elapsed > 2.0:
                    log.warning(f"⚠️ [{func_name or func.__name__}] 执行耗时过长: {elapsed*1000:.2f}ms")
                return result
            except Exception as e:
                end_time = time.time()
                elapsed = end_time - start_time
                log.error(f"❌ [{func_name or func.__name__}] 执行异常 - 耗时: {elapsed*1000:.2f}ms | 错误: {str(e)[:100]}")
                raise
        return wrapper
    return decorator

# ==================== 📐 中英文混排对齐工具 ====================
def get_display_width(s):
    width = 0
    for ch in str(s):
        if '\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u303f' or '\uff00' <= ch <= '\uffef':
            width += 2
        else:
            width += 1
    return width

def pad_to_width(s, target_width):
    s = str(s)
    current = get_display_width(s)
    if current >= target_width:
        return s
    return s + ' ' * (target_width - current)

def format_table_row(columns, widths):
    return ' '.join(pad_to_width(col, w) for col, w in zip(columns, widths))


# ==================== 初始化模块 ====================
def initialize(context):
    # ---------- 交易设置 ----------
    set_option("avoid_future_data", True)
    set_option("use_real_price", True)
    set_slippage(PriceRelatedSlippage(0.0001), type="fund")
    set_order_cost(
        OrderCost(
            open_tax=0,
            close_tax=0,
            open_commission=0.0001,
            close_commission=0.0001,
            close_today_commission=0,
            min_commission=5,
        ),
        type="fund",
    )
    set_benchmark("161226.XSHE")

    log.set_level('order', 'error')
    log.set_level('system', 'error')
    log.set_level('strategy', 'debug')
    log.info("🚀================ 策略初始化开始 ================🚀")

    # ---------- ETF池 ----------
    g.etf_pool_bak = [
        "518880.XSHG",   # 黄金ETF
        "159985.XSHE",   # 豆粕ETF
        "501018.XSHG",   # 南方原油
        "161226.XSHE",   # 白银LOF
        "513100.XSHG",   # 纳指ETF
        "159915.XSHE",   # 创业板ETF
        "511220.XSHG",   # 城投债ETF
    ]
    g.etf_pool = MASTER_ETF_POOL.copy()
    g.industry_etf_pool = INDUSTRY_ETF_POOL
    g.all_etf_pool = list(set(g.etf_pool + g.industry_etf_pool))
    
    g.seesaw_etf_pool = [
        # 银行
        "512800.XSHG", "516310.XSHG", "515020.XSHG", "159887.XSHE",
        "512820.XSHG", "512700.XSHG", "515290.XSHG", "512730.XSHG",
        "516210.XSHG", "517900.XSHG",
        # 电力/公用事业
        "560620.XSHG", "560190.XSHG", "159669.XSHE", "512580.XSHG",
        "159611.XSHE", "561560.XSHG", "562550.XSHG", "562960.XSHG",
        "561170.XSHG", "159625.XSHE", "562350.XSHG", "561700.XSHG",
        "560580.XSHG", "159301.XSHE", "159320.XSHE", "561380.XSHG",
        "159326.XSHE",
        # 红利
        "159336.XSHE", "159332.XSHE", "512390.XSHG", "562060.XSHG",
        "561680.XSHG", "560700.XSHG", "512530.XSHG",
        # 高股息
        "159207.XSHE", "563180.XSHG",
        # 央企/国企
        "560810.XSHG", "563060.XSHG", "510060.XSHG", "561960.XSHG",
        "517090.XSHG", "515900.XSHG", "515680.XSHG", "515600.XSHG",
        "159974.XSHE", "512960.XSHG", "159959.XSHE", "562380.XSHG",
        "563050.XSHG", "517180.XSHG", "159719.XSHE", "510810.XSHG",
        "510270.XSHG", "159528.XSHE", "159335.XSHE", "560170.XSHG",
        "512950.XSHG", "562850.XSHG", "515760.XSHG",
        # 黄金/黄金股（避险资产）
        "159322.XSHE", "517520.XSHG", "159562.XSHE", "517400.XSHG",
        "159315.XSHE", "159321.XSHE",
        # 石油/能源/煤炭（周期资源）
        "561260.XSHG", "159930.XSHE", "159945.XSHE", "515220.XSHG",
        "561790.XSHG", "561360.XSHG",
        # 农业/养殖（防御属性）
        "516770.XSHG", "159855.XSHE",
    ]
    
    # ---------- 动态扩容池参数 ----------
    g.dynamic_etf_pool = {}
    g.broadcast_history = []
    g.dynamic_pool_days = 10
    g.dynamic_pool_entry_days = 2

    # ---------- 核心参数 ----------
    g.lookback_days = 25
    g.holdings_num = 1
    g.min_money = 5000

    # ---------- 盈利保护参数 ----------
    g.enable_profit_protection = True
    g.profit_protection_lookback = 1
    g.profit_protection_threshold = 0.05
    g.profit_protection_check_times = ['11:00']

    g.loss = 0.97
    g.min_score_threshold = 0
    g.max_score_threshold = 100.0

    # ---------- 成交量过滤 ----------
    g.enable_volume_check = True
    g.volume_lookback = 5
    g.volume_threshold = 2
    g.volume_return_limit = 1

    # ---------- 短期动量过滤 ----------
    g.use_short_momentum_filter = True
    g.short_lookback_days = 10
    g.short_momentum_threshold = 0.0

    # ---------- 溢价率过滤 ----------
    g.enable_premium_filter = True
    g.premium_threshold = 0.20

    # ---------- 运行时变量 ----------
    g.rankings_cache = {'date': None, 'data': None}
    g.trade_log = {'records': [], 'sell_records': []}
    g.prev_total_value = None
    g.initial_cash = None  

    # ---------- 震荡期参数 ----------
    g.enable_range_bound_mode = True
    g.current_filter = '正常期'
    g.risk_state = '正常期'
    g.lookback_high_low_days = 20
    g.risk_benchmark = '510300.XSHG'
    g.laplace_s_param = 0.05
    g.laplace_min_slope = 0.001
    g.gaussian_sigma = 1.2
    g.gaussian_min_slope = 0.002
    g.enable_bias_trigger = True
    g.bias_threshold = 0.10
    g.ma_period = 20
    g.enable_rsi_trigger = True
    g.rsi_overbought = 75
    g.rsi_pullback = 60
    g.previous_rsi = None
    g.enable_stop_loss_trigger = False
    g.stop_loss_triggered_today = False
    g.stop_loss_triggered_date = None
    g.enable_low_point_rise_trigger = True
    g.low_point_rise_threshold = 0.03
    g.enable_stable_signal_trigger = True
    g.drawdown_recovery = 0.03
    g.max_range_bound_days = 15
    g.stable_days = 0
    g.filter_switch_cooldown = 2
    g.last_switch_date = None
    g.range_bound_start_date = None
    g.range_bound_days_count = 0
    g.previous_drawdown = None

    # ---------- 龙头家族变量 ----------
    g.dragon_head_etf = None
    g.dragon_head_name = None
    g.dragon_family = {}

    # ---------- 交易调度 ----------
    run_daily(pre_market_correlation_analysis, time='09:00')
    run_daily(check_positions, time='09:10')
    run_daily(get_cached_rankings, time='13:19')
    run_daily(etf_sell_trade, time='13:20')
    run_daily(etf_buy_trade, time='13:21')

    for check_time in g.profit_protection_check_times:
        run_daily(profit_protection_check, time=check_time)
        log.info(f"已注册盈利保护检查时间：{check_time}")

    run_daily(check_range_bound, time='13:05')
    run_daily(reset_range_bound_daily, time='15:10')

    # ---------- 动态池调度 ----------
    run_daily(manage_dynamic_pool_lifecycle, time='09:05')
    run_daily(check_dynamic_pool_entry, time='15:00')
    log.info("✅ 已注册动态池管理时间：09:05(生命周期管理), 15:00(准入检查)")

    # ---------- 播报调度 ----------
    run_daily(run_broadcasts, time='10:30')
    run_daily(dragon_stagnant_monitor, time='15:01')
    run_daily(run_broadcasts, time='14:50')
    log.info("✅ 已注册全市场ETF播报时间：10:30, 14:50（5日+10日双周期）")
    log.info("✅ 已注册盘后龙头监测时间：15:01")

    # ---------- 盘后总结 ----------
    run_daily(daily_summary, time='15:05')
    log.info("✅ 已注册盘后总结时间：15:05")

    # 首次运行，判断震荡期
    init_range_bound_status(context)

    # ---------- 打印初始化清单 ----------
    print_strategy_config(context)

    log.info("========== 策略初始化完成 ==========")
    log.info(f"交易ETF池{len(g.etf_pool)}只，行业ETF池{len(g.industry_etf_pool)}只，播报全池{len(g.all_etf_pool)}只")

# ==================== 📋 策略初始化清单打印 ====================
def print_strategy_config(context):
    log.info("=" * 70)
    log.info("📋 策略配置清单 [ 🚀七星1.72+行业全市场播报 🚀 ]")
    log.info("=" * 70)
    log.info("📌 ETF池配置:")
    log.info(f"  交易主ETF池数量: {len(g.etf_pool)} 只")
    log.info(f"  行业ETF池数量（播报用）: {len(g.industry_etf_pool)} 只")
    log.info(f"  播报全市场ETF池: {len(g.all_etf_pool)} 只（主池+行业池去重）")
    log.info(f"  动态扩容池: {len(g.dynamic_etf_pool)} 只")
    for etf, days in g.dynamic_etf_pool.items():
        log.info(f"    {etf} {get_name(etf)} - 剩余{days}天")
    log.info("📌 核心参数:")
    log.info(f"  动量计算周期: {g.lookback_days} 天")
    log.info(f"  最大持仓数量: {g.holdings_num} 只")
    log.info(f"  最小交易金额: {g.min_money} 元")
    log.info(f"  得分范围: [{g.min_score_threshold}, {g.max_score_threshold}]")
    log.info("📌 过滤条件:")
    log.info(f"  盈利保护: {'✅ 开启' if g.enable_profit_protection else '❌ 关闭'}")
    if g.enable_profit_protection:
        log.info(f"    回看天数: {g.profit_protection_lookback} 天")
        log.info(f"    回撤阈值: {g.profit_protection_threshold*100:.0f}%")
        log.info(f"    检查时间: {', '.join(g.profit_protection_check_times)}")
    log.info(f"  溢价率过滤: {'✅ 开启' if g.enable_premium_filter else '❌ 关闭'}")
    if g.enable_premium_filter:
        log.info(f"    溢价率阈值: {g.premium_threshold*100:.0f}%")
    log.info(f"  成交量过滤: {'✅ 开启' if g.enable_volume_check else '❌ 关闭'}")
    if g.enable_volume_check:
        log.info(f"    回看天数: {g.volume_lookback} 天")
        log.info(f"    量比阈值: {g.volume_threshold} 倍")
        log.info(f"    收益触发线: {g.volume_return_limit*100:.0f}%")
    log.info(f"  短期动量过滤: {'✅ 开启' if g.use_short_momentum_filter else '❌ 关闭'}")
    if g.use_short_momentum_filter:
        log.info(f"    回看天数: {g.short_lookback_days} 天")
        log.info(f"    阈值: {g.short_momentum_threshold*100:.0f}%")
    log.info(f"  近3日跌幅过滤: 阈值 {g.loss*100:.0f}%")
    log.info("📌 震荡期机制:")
    log.info(f"  功能开关: {'✅ 开启' if g.enable_range_bound_mode else '❌ 关闭'}")
    if g.enable_range_bound_mode:
        log.info(f"    当前状态: {g.risk_state} (滤波器: {g.current_filter})")
        log.info(f"    高低点回看: {g.lookback_high_low_days} 天")
        log.info(f"    切换冷却期: {g.filter_switch_cooldown} 个交易日")
        log.info(f"    最大震荡天数: {g.max_range_bound_days} 天")
        log.info(f"   【拉普拉斯参数】 s: {g.laplace_s_param}, min_slope: {g.laplace_min_slope}")
        log.info(f"   【高斯参数】 sigma: {g.gaussian_sigma}, min_slope: {g.gaussian_min_slope}")
        log.info(f"   【进入条件】 乖离率触发: {'✅' if g.enable_bias_trigger else '❌'} 阈值 {g.bias_threshold*100:.0f}%")
        log.info(f"               RSI超买回落: {'✅' if g.enable_rsi_trigger else '❌'} 超买 {g.rsi_overbought} 回落 {g.rsi_pullback}")
        log.info(f"               盈利保护触发: {'✅' if g.enable_stop_loss_trigger else '❌'}")
        log.info(f"   【退出条件】 低点上涨退出: {'✅' if g.enable_low_point_rise_trigger else '❌'} 阈值 {g.low_point_rise_threshold*100:.0f}%")
        log.info(f"               稳定信号退出: {'✅' if g.enable_stable_signal_trigger else '❌'} 回撤收窄 {g.drawdown_recovery*100:.0f}%")
    log.info("📌 交易调度:")
    log.info(f"  09:00 - pre_market_correlation_analysis（📊 开盘前相关性分析）")
    log.info(f"  09:10 - check_positions（持仓检查）")
    log.info(f"  10:30 - run_broadcasts（📢 全市场ETF播报 7日+10日）")
    log.info(f"  11:00 - profit_protection_check（盈利保护检查）")
    log.info(f"  13:10 - get_cached_rankings（计算ETF排名）")
    log.info(f"  13:20 - etf_sell_trade（卖出操作）")
    log.info(f"  13:21 - etf_buy_trade（买入操作）")
    log.info(f"  13:05 - check_range_bound（震荡期检查）")
    log.info(f"  14:50 - run_broadcasts（📢 全市场ETF播报 7日+10日）")
    log.info(f"  15:05 - daily_summary（📊 盘后总结）")
    log.info(f"  15:10 - reset_range_bound_daily（震荡期重置）")
    log.info("📌 当前运行状态:")
    log.info(f"  震荡期: {g.risk_state}")
    log.info("✅ 配置清单打印完成")
    log.info("=" * 70)

# ==================== 🏷️ 主题分类工具 ====================
def get_theme(name):
    if not name:
        return '其他'
    theme_keywords = {
        '芯片半导体': ['芯片','半导体','集成电路','科创芯片','芯片设计','半导体设备'],
        '科创': ['科创','科创板','科创50','科创新'],
        '红利': ['红利','股息','高股息'],
        '电力': ['电力','绿电','公用事业','电网'],
        '消费': ['消费','食品饮料','家电','酒','消费电子'],
        '医药': ['医药','医疗','生物','创新药','中药'],
        '通信': ['通信','5G','电信'],
        '证券': ['证券','券商','保险'],
        '银行': ['银行','金融'],
        '新能源': ['新能源','光伏','电池','碳中和','储能'],
        '有色': ['有色','稀土','稀有金属','矿业','黄金'],
        '化工': ['化工','石化','能源化工'],
        '人工智能': ['人工智能','AI','云计算','软件','大数据','信创'],
        '机器人': ['机器人','智能制造','工业母机','机床'],
        '军工': ['军工','国防','航空航天','卫星','通用航空'],
        '石油': ['石油','油气','能源','煤炭'],
        '旅游': ['旅游','出行'],
        '农业': ['农业','养殖','畜牧','粮食','豆粕'],
        '物流': ['物流','运输'],
        '教育': ['教育'],
        '成长': ['成长'],
        '价值': ['价值'],
        '跨境': ['跨境','海外','港股','纳指','标普','恒生','日经','德国','法国','东南亚','中韩'],
        '债券': ['债券','国债','城投','可转债'],
        '地产': ['房地产','地产','基建','建材'],
        '传媒': ['传媒','游戏','影视','VR'],
        '汽车': ['汽车','智能驾驶','汽车零部件'],
        '创业板': ['创业板'],
        '中证': ['中证'],
        '沪深': ['沪深'],
        'A500': ['A500'],
    }
    for theme, keywords in theme_keywords.items():
        for kw in keywords:
            if kw in name:
                return theme
    return '其他'

def compress_etfs_by_theme(etf_list, score_key='cum_score', max_per_theme=6):
    groups = {}
    for item in etf_list:
        theme = get_theme(item['name'])
        groups.setdefault(theme, []).append(item)
    compressed = []
    for theme, items in groups.items():
        items_sorted = sorted(items, key=lambda x: x.get(score_key, 0), reverse=True)
        compressed.extend(items_sorted[:max_per_theme])
    compressed.sort(key=lambda x: x.get(score_key, 0), reverse=True)
    return compressed

def interleave_by_theme(compressed_list, max_count=20):
    theme_groups = {}
    for item in compressed_list:
        theme = get_theme(item['name'])
        theme_groups.setdefault(theme, []).append(item)
    for theme, items in theme_groups.items():
        score_key = 'composite_score' if 'composite_score' in items[0] else 'cum_score'
        items.sort(key=lambda x: x.get(score_key, 0), reverse=True)
    theme_order = sorted(theme_groups.keys(),
                         key=lambda t: theme_groups[t][0].get('composite_score', theme_groups[t][0].get('cum_score', 0)),
                         reverse=True)
    result = []
    indices = {theme: 0 for theme in theme_groups}
    while len(result) < max_count:
        any_added = False
        for theme in theme_order:
            if len(result) >= max_count:
                break
            idx = indices[theme]
            if idx < len(theme_groups[theme]):
                result.append(theme_groups[theme][idx])
                indices[theme] += 1
                any_added = True
        if not any_added:
            break
    return result

# ==================== 📢 全市场ETF播报函数 ====================
def market_broadcast(context, days=5):
    """遍历主池+行业池，按主题压缩+轮询展示前20名"""
    log.info("=" * 70)
    log.info(f"📢 全市场ETF行情播报（{days}日周期）- {context.current_dt.strftime('%Y-%m-%d %H:%M')}")
    log.info("=" * 70)

    etf_performance = []
    all_etfs = g.all_etf_pool
    # 性能优化(真机): 一次性批量预热快照(名称/HALT/最新价),
    # 否则 get_current_data 逐只构建会产生约 3 次远程调用 × 全池数量。
    try:
        _nw = pt_warm_snapshot(all_etfs)
        log.info(f"🔥 快照预热完成: {_nw}只")
    except Exception as _e:
        log.debug(f"快照预热跳过: {_e}")
    # 性能优化(真机): 逐只 attribute_history 是数百次独立远程查询(单次
    # 200-400ms),改为每字段一次批量预取;聚宽环境无 pt_batch_hist_multi 自动回退逐只。
    _batch = None
    try:
        _n = max(days, 7)
        _batch = pt_batch_hist_multi(all_etfs, _n,
                                     ['close', 'high', 'low', 'open'])
        log.info(f"📦 批量预取OHLC完成: "
                 f"{len(_batch.get('close').columns) if _batch.get('close') is not None else 0}只")
    except Exception as _e:
        log.debug(f"批量预取不可用,回退逐只查询: {_e}")
        _batch = None
    for etf in all_etfs:
        try:
            if get_current_data()[etf].paused:
                continue
            if _batch is not None and etf in _batch['close'].columns:
                hist = {f: _batch[f][etf] for f in ('close', 'high', 'low', 'open')}
            else:
                hist = attribute_history(etf, max(days, 7), '1d', ['close', 'high', 'low', 'open'])
            if len(hist['close']) < days:
                continue
            
            closes = hist['close'].tolist()
            highs = hist['high'].tolist()
            lows = hist['low'].tolist()
            opens = hist['open'].tolist()
            
            live = get_current_data()[etf].last_price
            if live is not None and live > 0:
                closes.append(live)
                highs.append(live)
                lows.append(live)
            else:
                continue
            
            pos_days = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
            neg_days = len(closes) - 1 - pos_days
            cum_score = closes[-1] / closes[0] - 1
            
            alpha003 = calculate_alpha003(closes, lows, highs)
            
            # 检查是否有连续三日高开（开盘价 > 前一日收盘价）
            has_consecutive_high_open = False
            for i in range(2, len(opens)):
                if opens[i] > closes[i-1] and opens[i-1] > closes[i-2] and opens[i-2] > closes[i-3]:
                    has_consecutive_high_open = True
                    break
            
            # 🎯 修复：更严格的"优选"标准
            is_preferred = False
            mid = len(closes) // 2
            threshold = 0.06 if days == 10 else 0.03
            if len(closes) >= days + 1 and cum_score > threshold:
                first_half_score = closes[mid] / closes[0] - 1
                second_half_score = closes[-1] / closes[mid] - 1
                first_half_pos = sum(1 for i in range(1, mid + 1) if closes[i] > closes[i-1])
                second_half_pos = sum(1 for i in range(mid + 1, len(closes)) if closes[i] > closes[i-1])
                if second_half_score > first_half_score * 1.5 and second_half_pos >= first_half_pos and second_half_score > 0:
                    is_preferred = True
            elif len(closes) >= 4 and cum_score > threshold:
                if cum_score > 0 and pos_days >= 2:
                    is_preferred = True

            etf_performance.append({
                'etf': etf,
                'name': get_name(etf),
                'cum_score': cum_score,
                'pos_days': pos_days,
                'neg_days': neg_days,
                'alpha003': alpha003,
                'is_preferred': is_preferred,
                'has_consecutive_high_open': has_consecutive_high_open
            })
        except Exception:
            continue

    if not etf_performance:
        log.info("📭 无有效数据")
        log.info("=" * 70)
        return

    for item in etf_performance:
        pos_ratio = item['pos_days'] / float(days)
        item['composite_score'] = item['cum_score'] * (0.6 + 0.4 * pos_ratio)

    alpha003_sorted = sorted(etf_performance, key=lambda x: x['alpha003'], reverse=True)
    alpha003_rank_map = {item['etf']: idx + 1 for idx, item in enumerate(alpha003_sorted)}

    compressed = compress_etfs_by_theme(etf_performance, score_key='composite_score')
    max_count = 10
    final_top20 = interleave_by_theme(compressed, max_count=max_count)

    total = len(etf_performance)
    full_sorted = sorted(etf_performance, key=lambda x: x['composite_score'], reverse=True)
    rank_map = {item['etf']: idx for idx, item in enumerate(full_sorted)}

    star_list = []
    for item in final_top20:
        idx = rank_map.get(item['etf'], total)
        percentile = idx / total if total > 0 else 1
        if percentile < 0.10:
            star = "★★★★★"
        elif percentile < 0.30:
            star = "★★★★"
        elif percentile < 0.50:
            star = "★★★"
        elif percentile < 0.70:
            star = "★★"
        else:
            star = "★"
        star_list.append(star)

    headers = ['排名', 'ETF代码', '名称', f'{days}日涨幅', '上涨天数', '负天数', 'Alpha003', 'A003排名', '星级', '优选', '三连高开', '龙头家族']
    widths = [4, 14, 16, 10, 6, 6, 10, 8, 6, 4, 6, 8]
    log.info(format_table_row(headers, widths))
    log.info("-" * 92)
    
    for i, item in enumerate(final_top20):
        tag = "⭐" if item['is_preferred'] else ""
        
        family_tag = ""
        if g.dragon_head_etf is not None:
            if item['etf'] == g.dragon_head_etf or item['etf'] in g.dragon_family:
                family_tag = "👑龙家"
        
        name_display = item['name'][:10] if len(item['name']) > 10 else item['name']
        alpha003_rank = alpha003_rank_map.get(item['etf'], "-")
        high_open_tag = "↑" if item['has_consecutive_high_open'] else ""
        cols = [
            str(i+1),
            item['etf'],
            name_display,
            f"{item['cum_score']*100:>9.2f}%",
            str(item['pos_days']),
            str(item['neg_days']),
            f"{item['alpha003']*100:>9.2f}%",
            str(alpha003_rank),
            star_list[i],
            tag,
            high_open_tag,
            family_tag
        ]
        log.info(format_table_row(cols, widths))
    log.info("-" * 88)
    log.info(f"📊 总计: {total} 只ETF | 展示前{len(final_top20)}只")
    log.info("=" * 88)
    
    if context.current_dt.hour >= 14:
        top5_etfs = [item['etf'] for item in final_top20[:5]]
        record_broadcast_history(context, top5_etfs)

def run_broadcasts(context):
    """运行所有独立播报"""
    market_broadcast(context, days=7)
    market_broadcast(context, days=10)

# ==================== 🔄 代码修改后自动刷新 ====================
def after_code_changed(context):
    """
    实盘修改代码后自动刷新ETF池，并按分类展示明细
    """
    log.info("🔄 ========== 检测到代码修改，开始刷新策略配置 ==========")
    
    # 重新加载 ETF 池，保留动态池
    update_etf_pool_with_dynamic()
    g.rankings_cache = {'date': None, 'data': None}
    
    # 使用 getattr 安全获取参数，避免 KeyError
    log.info(f"📈 盈利保护：{'开' if g.enable_profit_protection else '关'}，回撤{g.profit_protection_threshold*100:.0f}%")
    
    # ========== 展示动态ETF池 ==========
    log.info("📋 ========== ETF池明细 ==========")
    log.info(f"📊 主池总计：{len(MASTER_ETF_POOL)} 只标的")
    
    if g.dynamic_etf_pool:
        log.info("🔄 动态池（{}只）：".format(len(g.dynamic_etf_pool)))
        for etf, days in sorted(g.dynamic_etf_pool.items(), key=lambda x: -x[1]):
            try:
                name = get_name(etf)
            except:
                name = "未知"
            log.info(f"  {etf}({name}) - 剩余{days}天")
    else:
        log.info("� 动态池：空")
    
    log.info("📋 ========== 展示完毕 ==========")
    log.info("🔄 ========== 配置刷新完成 ==========\n")

# ==================== 开盘持仓检查 ====================
def check_positions(context):
    log.info(f"\n======================🐂🧨🧨🧨🧨🧨{context.current_dt.strftime('%Y-%m-%d')}📌策略运行开始📌一路长红🧨🧨🧨🧨🧨🐂======================")
    g.profit_protection_sold_today = []
    g.trade_log['sell_records'] = []
    if g.initial_cash is None:
        g.initial_cash = context.portfolio.portfolio_value
        log.info(f"📌 记录初始总资产: {g.initial_cash:,.2f}")
    for sec in context.portfolio.positions:
        pos = context.portfolio.positions[sec]
        if pos.total_amount > 0:
            log.info(f"📊 持仓：{sec} {get_name(sec)} 数量{pos.total_amount} 成本{pos.avg_cost:.3f} 现价{pos.price:.3f}")

# ==================== 🚫 停牌检测函数 ====================
def is_etf_suspended(etf, context):
    """
    判断ETF是否停牌
    返回: True=停牌, False=正常交易
    """
    try:
        today = context.current_dt.date()
        minute_data = get_price(
            etf,
            start_date=today,
            end_date=context.current_dt,
            frequency='1m',
            fields=['volume'],
            skip_paused=False,
            panel=False
        )
        name = get_name(etf)
        
        if minute_data is None or minute_data.empty:
            if context.current_dt.hour >= 9:
                log.debug(f"🚫 {etf} ({name}) 停牌（无分钟数据）")
                return True
            return False
        
        minute_count = len(minute_data)
        check_minutes = min(5, minute_count)
        recent_vol = minute_data['volume'].tail(check_minutes).sum()
        
        if recent_vol == 0:
            log.debug(f"🚫 {etf} ({name}) 停牌（最近{check_minutes}分钟无成交）")
            return True
        
        return False
    except Exception as e:
        log.debug(f"{etf} 停牌检测异常: {e}")
        return False

# ==================== 盈利保护 ====================
def profit_protection_check(context):
    if not g.enable_profit_protection:
        return
    log.info("========== 盈利保护独立检查开始 ==========")
    for sec in list(context.portfolio.positions.keys()):
        pos = context.portfolio.positions[sec]
        if pos.total_amount == 0:
            continue
        
        if sec not in g.etf_pool:
            if smart_order_target_value(sec, 0, context):
                log.info(f"📤 盈利保护卖出（不在交易池）：{sec} {get_name(sec)}")
            continue
        
        if check_profit_protection(sec, context):
            if smart_order_target_value(sec, 0, context):
                log.info(f"🛡️ 盈利保护卖出（独立检查）：{sec} {get_name(sec)}")
                if getattr(g, 'enable_stop_loss_trigger', False):
                    g.stop_loss_triggered_today = True
                    g.stop_loss_triggered_date = context.current_dt.date()
                    log.info("【盈利保护触发】记录止损信号")
    log.info("========== 盈利保护独立检查完成 ==========")

def check_profit_protection(security, context, lookback=None, threshold=None):
    if not g.enable_profit_protection:
        return False
    lookback = lookback or g.profit_protection_lookback
    threshold = threshold or g.profit_protection_threshold
    hist = attribute_history(security, lookback, '1d', ['high'])
    if hist.empty or len(hist) < lookback:
        return False
    max_high = hist['high'].max()
    current_price = get_current_data()[security].last_price
    if current_price <= max_high * (1 - threshold):
        log.info(f"🔻 {security} {get_name(security)} 触发盈利保护：回撤{(1 - current_price/max_high)*100:.2f}%")
        return True
    return False

def get_premium_rate(code, date, max_back_days=5):
    price_data = get_price(code, start_date=date, end_date=date, frequency='daily', fields=['close'])
    if price_data.empty:
        return None, None, None
    price = price_data['close'].iloc[0]
    net_value = None
    used_date = date
    start_date = date - datetime.timedelta(days=max_back_days*2)
    trade_days = get_trade_days(start_date=start_date, end_date=date)
    trade_days = [pd.to_datetime(d).date() for d in trade_days]
    for dt in reversed(trade_days):
        if dt > date:
            continue
        net_data = get_extras('unit_net_value', code, start_date=dt, end_date=dt, df=True)
        if not net_data.empty and not pd.isna(net_data[code].iloc[0]):
            net_value = net_data[code].iloc[0]
            used_date = dt
            break
        try:
            q = query(finance.FUND_NET_VALUE).filter(
                finance.FUND_NET_VALUE.code == code,
                finance.FUND_NET_VALUE.day == dt
            )
            net_df = finance.run_query(q)
            if not net_df.empty:
                net_value = net_df['net_value'].iloc[0]
                used_date = dt
                break
        except:
            continue
    if net_value is None:
        return None, None, None
    premium_rate = (price - net_value) / net_value
    return premium_rate, price, net_value

# ==================== 震荡期机制 ====================
def calculate_rsi(close, period=14):
    try:
        if len(close) < period + 1:
            return None
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except:
        return None

def laplace_filter(price, s=0.05):
    alpha = 1 - np.exp(-s)
    L = np.zeros(len(price))
    L[0] = price[0]
    for t in range(1, len(price)):
        L[t] = alpha * price[t] + (1 - alpha) * L[t - 1]
    return L

def gaussian_filter_last_two(price, sigma=1.2):
    n = len(price)
    if n < 2:
        return 0, 0
    idx_1 = np.arange(n)
    weights_1 = np.exp(-((idx_1+1)**2) / (2 * sigma**2))[::-1]
    weights_1 /= np.sum(weights_1)
    g1 = np.sum(price * weights_1)
    price_2 = price[:-1]
    idx_2 = np.arange(n-1)
    weights_2 = np.exp(-((idx_2+1)**2) / (2 * sigma**2))[::-1]
    weights_2 /= np.sum(weights_2)
    g2 = np.sum(price_2 * weights_2)
    return g1, g2

def get_risk_benchmark_state(context):
    required_days = max(g.ma_period, g.lookback_high_low_days)
    lookback = required_days + 30
    end_date = getattr(context, 'previous_date', None)
    if end_date is None:
        return None
    df = get_price(g.risk_benchmark, end_date=end_date, count=lookback,
                   frequency='daily', fields=['close', 'high', 'low'], panel=False)
    if df is None or len(df) < required_days:
        return None
    daily_close = df['close'].values.astype(float)
    daily_high = df['high'].values.astype(float)
    daily_low = df['low'].values.astype(float)
    current_price = float(daily_close[-1])
    intraday_high = current_price
    intraday_low = current_price
    data_source = '昨日日线'
    try:
        today = context.current_dt.date()
        minute_df = get_price(
            g.risk_benchmark, start_date=today, end_date=context.current_dt,
            frequency='1m', fields=['close', 'high', 'low'],
            panel=False, fill_paused=False
        )
        if minute_df is not None and not minute_df.empty:
            minute_close = minute_df['close'].dropna()
            minute_high = minute_df['high'].dropna()
            minute_low = minute_df['low'].dropna()
            if not minute_close.empty:
                current_price = float(minute_close.iloc[-1])
                intraday_high = float(minute_high.max()) if not minute_high.empty else current_price
                intraday_low = float(minute_low.min()) if not minute_low.empty else current_price
                data_source = '当日盘中'
    except Exception:
        pass
    if current_price <= 0:
        try:
            current_data = get_current_data()
            live_price = current_data[g.risk_benchmark].last_price
            if live_price is not None and live_price > 0:
                current_price = float(live_price)
                intraday_high = max(intraday_high, current_price)
                intraday_low = min(intraday_low, current_price)
                data_source = '实时快照'
        except Exception:
            current_price = float(daily_close[-1])
    close_series = np.append(daily_close, current_price)
    high_series = np.append(daily_high, max(intraday_high, current_price))
    low_series = np.append(daily_low, min(intraday_low, current_price))
    recent_high = np.max(high_series[-g.lookback_high_low_days:])
    recent_low = np.min(low_series[-g.lookback_high_low_days:])
    ma = np.mean(close_series[-g.ma_period:])
    current_rsi = calculate_rsi(close_series, period=14)
    previous_rsi = calculate_rsi(daily_close, period=14)
    return {
        'close_series': close_series,
        'high_series': high_series,
        'low_series': low_series,
        'current_price': current_price,
        'recent_high': recent_high,
        'recent_low': recent_low,
        'ma': ma,
        'current_rsi': current_rsi,
        'previous_rsi': previous_rsi,
        'data_source': data_source,
    }

def is_fresh_stop_loss_signal(context):
    signal_date = getattr(g, 'stop_loss_triggered_date', None)
    if signal_date is None:
        return False
    today = context.current_dt.date()
    previous_date = getattr(context, 'previous_date', None)
    if signal_date == today:
        return True
    if previous_date is not None and signal_date == previous_date:
        return True
    g.stop_loss_triggered_today = False
    g.stop_loss_triggered_date = None
    return False

def init_range_bound_status(context):
    if not g.enable_range_bound_mode:
        return
    log.info("【首次运行】初始化震荡期状态...")
    try:
        if context.previous_date is None:
            log.warning("【首次运行】无法获取前一个交易日，保持正常期")
            return
        end_date = context.previous_date
        lookback = max(g.ma_period, g.lookback_high_low_days) + 30
        df = get_price(g.risk_benchmark, end_date=end_date, count=lookback,
                       frequency='daily', fields=['close', 'high', 'low'], panel=False)
        if df is None or len(df) < max(g.ma_period, g.lookback_high_low_days):
            log.warning("【首次运行】数据不足，保持正常期")
            return
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        current_price = close[-1]
        if len(close) >= g.lookback_high_low_days:
            recent_high = np.max(high[-g.lookback_high_low_days:])
            recent_low = np.min(low[-g.lookback_high_low_days:])
        else:
            recent_high = np.max(high)
            recent_low = np.min(low)
        ma = np.mean(close[-g.ma_period:])
        bias = (current_price - ma) / ma if ma > 0 else 0
        rise_from_low = (current_price - recent_low) / recent_low if recent_low > 0 else 0
        current_rsi = calculate_rsi(close, period=14)
        should_enter = False
        signals = []
        if g.enable_bias_trigger and bias > g.bias_threshold:
            should_enter = True
            signals.append(f"乖离率{bias:.2%}>{g.bias_threshold:.0%}")
        if g.enable_rsi_trigger and current_rsi is not None and len(close) >= 15:
            prev_rsi = calculate_rsi(close[:-1], period=14)
            if prev_rsi is not None and prev_rsi > g.rsi_overbought and current_rsi < g.rsi_pullback:
                should_enter = True
                signals.append(f"RSI超买回落{prev_rsi:.1f}->{current_rsi:.1f}")
        if should_enter:
            g.current_filter = '震荡期'
            g.risk_state = '震荡期'
            g.range_bound_start_date = end_date
            g.range_bound_days_count = 0
            log.info(f"【首次运行】初始化进入震荡期: {'; '.join(signals)}")
        else:
            g.current_filter = '正常期'
            g.risk_state = '正常期'
            if len(close) >= g.lookback_high_low_days:
                g.previous_drawdown = (recent_high - current_price) / recent_high if recent_high > 0 else 0
            else:
                g.previous_drawdown = 0
            g.previous_rsi = current_rsi
            rsi_str = f"{current_rsi:.1f}" if current_rsi is not None else "N/A"
            log.info(f"【首次运行】初始状态: 正常期, 乖离率: {bias:.2%}, RSI: {rsi_str}, 从低点涨幅: {rise_from_low:.2%}")
    except Exception as e:
        log.warning(f"【首次运行】初始化震荡期状态异常: {e}，保持正常期")

def check_and_exit_range_bound_mode(context):
    if not g.enable_range_bound_mode:
        return
    if g.current_filter != '震荡期':
        return
    log.info("【震荡期退出检查】开始检测退出条件...")
    try:
        benchmark_state = get_risk_benchmark_state(context)
        if benchmark_state is None:
            log.warning("【震荡期退出检查】数据不足，跳过")
            return
        close = benchmark_state['close_series']
        current_price = benchmark_state['current_price']
        recent_high = benchmark_state['recent_high']
        recent_low = benchmark_state['recent_low']
        current_drawdown = (recent_high - current_price) / recent_high if recent_high > 0 else 0
        rise_from_low = (current_price - recent_low) / recent_low if recent_low > 0 else 0
        recovery_signals = []
        ma = benchmark_state['ma']
        current_rsi = benchmark_state['current_rsi']
        log.info(f"【震荡期数据】当前价: {current_price:.3f}, 近{g.lookback_high_low_days}日高点: {recent_high:.3f}, 低点: {recent_low:.3f}")
        log.info(f"【震荡期数据】回撤: {current_drawdown:.2%}, 从低点涨幅: {rise_from_low:.2%}")
        if g.enable_low_point_rise_trigger:
            if rise_from_low >= g.low_point_rise_threshold:
                recovery_signals.append(f"从低点上涨{rise_from_low:.2%}>={g.low_point_rise_threshold:.0%}")
                log.info(f"【退出条件触发】从低点上涨: {rise_from_low:.2%}")
        if g.enable_stable_signal_trigger:
            if current_price > ma:
                recovery_signals.append("价格站上均线")
            if len(close) >= 2 and close[-1] > close[-2]:
                recovery_signals.append("价格回升")
            if g.previous_drawdown is not None and current_drawdown < g.previous_drawdown:
                recovery_signals.append(f"回撤收窄({current_drawdown:.2%}<{g.previous_drawdown:.2%})")
            if current_rsi is not None and g.previous_rsi is not None and current_rsi > g.previous_rsi:
                recovery_signals.append(f"RSI回升({current_rsi:.1f})")
            drawdown_safe = current_drawdown < g.drawdown_recovery
            if drawdown_safe:
                g.stable_days += 1
                log.info(f"【企稳计数】连续企稳天数: {g.stable_days}")
            else:
                g.stable_days = 0
        g.previous_drawdown = current_drawdown
        g.previous_rsi = current_rsi
        range_bound_days = 0
        if g.range_bound_start_date is not None:
            trade_days = get_trade_days(start_date=g.range_bound_start_date, end_date=context.current_dt.date())
            range_bound_days = len(trade_days) - 1
            if range_bound_days >= g.max_range_bound_days:
                recovery_signals.append(f"震荡期满({range_bound_days}天)")
                log.info(f"【退出条件触发】震荡期已满{range_bound_days}天")
        low_point_condition = g.enable_low_point_rise_trigger and rise_from_low >= g.low_point_rise_threshold
        stable_condition = False
        if g.enable_stable_signal_trigger:
            drawdown_safe = current_drawdown < g.drawdown_recovery
            stable_condition = drawdown_safe and len(recovery_signals) >= 2 and g.stable_days >= 2
        force_condition = range_bound_days >= g.max_range_bound_days
        should_recover = low_point_condition or stable_condition or force_condition
        if should_recover:
            can_switch = True
            if g.last_switch_date is not None:
                trade_days = get_trade_days(start_date=g.last_switch_date, end_date=context.current_dt.date())
                days_since = len(trade_days) - 1
                if days_since < g.filter_switch_cooldown:
                    can_switch = False
                    log.info(f"【震荡期退出】冷却期中，距上次切换{days_since}天")
            if can_switch:
                g.current_filter = '正常期'
                g.risk_state = '正常期'
                g.last_switch_date = context.current_dt.date()
                g.range_bound_start_date = None
                g.range_bound_days_count = 0
                g.stable_days = 0
                log.info(f"【退出震荡期】切换回拉普拉斯滤波器: {'; '.join(recovery_signals)}")
        else:
            log.info("【震荡期退出检查】未满足退出条件，保持震荡期(高斯滤波器)")
    except Exception as e:
        log.warning(f"【震荡期退出检查】判断出错: {e}")

def check_and_enter_range_bound_mode(context):
    if not g.enable_range_bound_mode:
        return
    log.info("【震荡期进入检查】开始检测...")
    stop_loss_signal_active = is_fresh_stop_loss_signal(context)
    can_switch = True
    if g.last_switch_date is not None:
        trade_days = get_trade_days(start_date=g.last_switch_date, end_date=context.current_dt.date())
        days_since = len(trade_days) - 1
        if days_since < g.filter_switch_cooldown:
            can_switch = False
            log.info(f"【震荡期检查】冷却期中，距上次切换{days_since}天")
    if g.current_filter == '震荡期':
        log.info("【震荡期检查】当前已在震荡期")
        return
    if not can_switch:
        return
    risk_signals = []
    try:
        benchmark_state = get_risk_benchmark_state(context)
        if benchmark_state is not None:
            close = benchmark_state['close_series']
            current_price = benchmark_state['current_price']
            if g.enable_bias_trigger:
                ma = benchmark_state['ma']
                bias = (current_price - ma) / ma if ma > 0 else 0
                if bias > g.bias_threshold:
                    risk_signals.append(f"乖离率过大({bias:.2%}>{g.bias_threshold:.0%})")
                    log.info(f"【条件触发】乖离率: {bias:.2%} (数据源:{benchmark_state['data_source']})")
            if g.enable_rsi_trigger:
                current_rsi = benchmark_state['current_rsi']
                if len(close) >= 15 and current_rsi is not None:
                    prev_rsi = benchmark_state['previous_rsi']
                    if prev_rsi is not None:
                        if prev_rsi > g.rsi_overbought and current_rsi < g.rsi_pullback and current_rsi < prev_rsi:
                            risk_signals.append(f"RSI超买回落({prev_rsi:.1f}->{current_rsi:.1f})")
                            log.info(f"【条件触发】RSI超买回落: {prev_rsi:.1f}->{current_rsi:.1f}")
    except Exception as e:
        log.warning(f"【震荡期检查】获取基准数据异常: {e}")
    if g.enable_stop_loss_trigger and stop_loss_signal_active:
        risk_signals.append("盈利保护触发止损")
        log.info("【条件触发】盈利保护触发止损信号")
    if len(risk_signals) > 0:
        g.current_filter = '震荡期'
        g.risk_state = '震荡期'
        g.last_switch_date = context.current_dt.date()
        g.range_bound_start_date = context.current_dt.date()
        g.range_bound_days_count = 0
        g.stable_days = 0
        g.stop_loss_triggered_today = False
        g.stop_loss_triggered_date = None
        log.info(f"【进入震荡期】切换到高斯滤波器: {'; '.join(risk_signals)}")
    else:
        log.info("【震荡期检查】未满足进入条件，保持正常期(拉普拉斯滤波器)")

def check_range_bound(context):
    if not g.enable_range_bound_mode:
        return
    log.info("========== 震荡期检查开始 ==========")
    log.info(f"当前状态: {g.current_filter}")
    check_and_exit_range_bound_mode(context)
    check_and_enter_range_bound_mode(context)
    log.info(f"检查后状态: {g.current_filter}")
    g.rankings_cache = {'date': None, 'data': None}
    log.info("========== 震荡期检查完成 ==========")

def reset_range_bound_daily(context):
    if g.current_filter == '震荡期' and g.range_bound_start_date is not None:
        trade_days = get_trade_days(start_date=g.range_bound_start_date, end_date=context.current_dt.date())
        g.range_bound_days_count = len(trade_days) - 1
        log.info(f"震荡期已持续 {g.range_bound_days_count} 个交易日")

# ==================== 动态池管理函数 ====================
def check_dynamic_pool_entry(context):
    today = context.current_dt.date()
    if not g.broadcast_history:
        return
    
    entry_days = g.dynamic_pool_entry_days
    pool_days = g.dynamic_pool_days
    
    for etf in set(g.broadcast_history[-1]['etfs']):
        if etf in MASTER_ETF_POOL:
            continue
        
        try:
            if etf in g.dynamic_etf_pool:
                g.dynamic_etf_pool[etf] += 1
                log.info(f"🔄 动态池续期: {etf} {get_name(etf)} 再次进入前5，持续时间+1，剩余{g.dynamic_etf_pool[etf]}天")
                update_etf_pool_with_dynamic()
                continue
            
            prices = get_price(etf, count=6, end_date=today, fields='close')
            if len(prices) < 6:
                log.debug(f"🔄 {etf} {get_name(etf)} 价格数据不足，跳过")
                continue
            
            five_day_return = (prices['close'][-1] - prices['close'][-6]) / prices['close'][-6]
            three_day_return = (prices['close'][-1] - prices['close'][-4]) / prices['close'][-4]
            up_days = sum(1 for i in range(1, 6) if prices['close'][i] > prices['close'][i-1])
            
            consecutive_days = 0
            for record in reversed(g.broadcast_history):
                if etf in record['etfs']:
                    consecutive_days += 1
                else:
                    break
            
            if consecutive_days < entry_days:
                continue
            
            if five_day_return <= 0.05:
                log.debug(f"🔄 {etf} {get_name(etf)} 5日涨幅{five_day_return*100:.2f}%<=5%，不满足准入条件")
                continue
            
            if up_days < 3:
                log.debug(f"🔄 {etf} {get_name(etf)} 5日上涨天数{up_days}<3，不满足准入条件")
                continue
            
            if three_day_return < five_day_return * 0.6:
                log.debug(f"🔄 {etf} {get_name(etf)} 3日涨幅{three_day_return*100:.2f}% < 5日涨幅{five_day_return*100:.2f}%的60%({five_day_return*0.6*100:.2f}%)，不满足准入条件")
                continue
            
            g.dynamic_etf_pool[etf] = pool_days
            log.info(f"🔄 动态池扩容: {etf} {get_name(etf)} 连续{consecutive_days}天进入前5，5日涨幅{five_day_return*100:.2f}%，5日上涨天数{up_days}，3日涨幅{three_day_return*100:.2f}%，加入动态池，持续{pool_days}天")
            update_etf_pool_with_dynamic()
        except Exception as e:
            log.warning(f"🔄 {etf} {get_name(etf)} 涨幅计算失败: {e}")

def manage_dynamic_pool_lifecycle(context):
    today = context.current_dt.date()
    expired_etfs = []
    
    for etf in list(g.dynamic_etf_pool.keys()):
        if etf in MASTER_ETF_POOL:
            del g.dynamic_etf_pool[etf]
            continue
        g.dynamic_etf_pool[etf] -= 1
        if g.dynamic_etf_pool[etf] <= 0:
            expired_etfs.append(etf)
            log.info(f"🔄 动态池到期: {etf} {get_name(etf)} 从动态池移除")
    
    for etf in expired_etfs:
        del g.dynamic_etf_pool[etf]
    
    update_etf_pool_with_dynamic()

def update_etf_pool_with_dynamic():
    dynamic_etfs = list(g.dynamic_etf_pool.keys())
    g.etf_pool = list(dict.fromkeys(MASTER_ETF_POOL + dynamic_etfs))
    g.all_etf_pool = list(set(g.etf_pool + g.industry_etf_pool))
    g.rankings_cache = {'date': None, 'data': None}

def record_broadcast_history(context, top_etfs):
    today = context.current_dt.date()
    if g.broadcast_history and g.broadcast_history[-1]['date'] == today:
        g.broadcast_history[-1]['etfs'] = top_etfs
    else:
        g.broadcast_history.append({'date': today, 'etfs': top_etfs})
        if len(g.broadcast_history) > 30:
            g.broadcast_history = g.broadcast_history[-30:]

# ==================== 📊 Alpha_003 因子计算 ====================
def calculate_alpha003(close, low, high):
    """
    Alpha_003 因子计算：SUM((CLOSE=DELAY(CLOSE,1)?0:CLOSE-(CLOSE>DELAY(CLOSE,1)?MIN(LOW,DELAY(CLOSE,1)):MAX(HIGH,DELAY(CLOSE,1)))),6)
    
    输入：
    close: 收盘价数组（包含当日实时价）
    low: 最低价数组
    high: 最高价数组
    
    输出：
    alpha003_norm: 归一化后的Alpha_003值（除以收盘价转为百分比）
    """
    close_arr = np.array(close, dtype=float)
    low_arr = np.array(low, dtype=float)
    high_arr = np.array(high, dtype=float)
    
    prev_close = np.roll(close_arr, 1)
    prev_close[0] = np.nan
    
    same = close_arr == prev_close
    up = close_arr > prev_close
    
    ref_price = np.where(up, np.minimum(low_arr, prev_close), np.maximum(high_arr, prev_close))
    
    daily = np.where(same, 0, close_arr - ref_price)
    alpha003_raw = np.nansum(daily[-6:])
    
    if close_arr[-1] != 0:
        alpha003_norm = alpha003_raw / close_arr[-1]
    else:
        alpha003_norm = 0.0
    
    return alpha003_norm

# ==================== 📊 Alpha_004 因子计算 ====================
def calculate_alpha004(enddate, index='all'):
    """
    Alpha_004 因子计算：最近20天下跌次数统计
    
    输入：
    enddate: 必选参数，计算哪一天的因子
    index: 默认参数，股票指数，默认为所有股票'all'，'seesaw'表示跷跷板ETF池
    
    输出：
    一个 Series：index 为成分股代码，values 为最近20天下跌次数
    """
    if index == 'all':
        etf_list = g.all_etf_pool
    elif index == 'seesaw':
        etf_list = g.seesaw_etf_pool
    else:
        etf_list = index
    
    factor_results = {}
    
    for etf in etf_list:
        try:
            daily_hist = get_price(etf, end_date=enddate, count=21, frequency='daily', fields=['close'], skip_paused=False)
            if len(daily_hist) < 20:
                continue
            
            closes = daily_hist['close'].values[-20:]
            down_count = 0
            for i in range(1, len(closes)):
                if closes[i] < closes[i-1]:
                    down_count += 1
            
            factor_results[etf] = down_count
        except Exception:
            continue
    
    return pd.Series(factor_results)

# ==================== 辅助函数 ====================
def get_name(security):
    try:
        return get_current_data()[security].name
    except:
        return "未知"

def smart_order_target_value(security, target_value, context):
    data = get_current_data()
    name = get_name(security)
    
    if data[security].paused:
        log.info(f"{security} {name} 停牌，跳过")
        return False
    price = data[security].last_price
    if price == 0:
        log.info(f"{security} {name} 当前价格0，跳过")
        return False
    target_amount = int(target_value / price)
    target_amount = (target_amount // 100) * 100
    if target_amount <= 0 and target_value > 0:
        target_amount = 100
    cur_pos = context.portfolio.positions.get(security, None)
    cur_amount = cur_pos.total_amount if cur_pos else 0
    diff = target_amount - cur_amount
    if diff > 0:
        if data[security].last_price >= data[security].high_limit:
            log.info(f"{security} {name} 涨停，跳过买入")
            return False
    elif diff < 0:
        if data[security].last_price <= data[security].low_limit:
            log.info(f"{security} {name} 跌停，跳过卖出")
            return False
        recent_vol = attribute_history(security, 5, '1m', ['volume'], skip_paused=False)
        if len(recent_vol) > 0 and np.nansum(recent_vol['volume'].values) == 0:
            log.info(f"🚫 {security} {name} 最近5分钟无成交量，判定临时停牌，跳过卖出")
            return False
    trade_val = abs(diff) * price
    if 0 < trade_val < g.min_money:
        log.info(f"{security} {name} 交易金额{trade_val:.2f} < {g.min_money}，跳过")
        return False
    if diff < 0:
        closeable = cur_pos.closeable_amount if cur_pos else 0
        if closeable == 0:
            log.info(f"{security} {name} 当天买入不可卖出")
            return False
        diff = -min(abs(diff), closeable)
    if diff != 0:
        order_result = order(security, diff)
        if order_result:
            log.info(f"{'📥 买入' if diff>0 else '📤 卖出'} {security} {name} 数量{abs(diff)} 价格{price:.3f}")
            if diff > 0:
                g.trade_log['records'].append({
                    'time': context.current_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'security': security,
                    'name': name,
                    'direction': '买入',
                    'amount': abs(diff),
                    'price': price,
                    'value': abs(diff) * price
                })
            else:
                g.trade_log['sell_records'].append({
                    'time': context.current_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'security': security,
                    'name': name,
                    'direction': '卖出',
                    'amount': abs(diff),
                    'price': price,
                    'value': abs(diff) * price
                })
            return True
        else:
            log.warning(f"下单失败: {security} {name} 数量{diff}")
            return False
    return False

# ==================== 核心计算模块 ====================
def get_cached_rankings(context):
    today = context.current_dt.date()
    if g.rankings_cache['date'] != today:
        log.info("重新计算ETF排名...")
        ranked = get_ranked_etfs(context)
        g.rankings_cache = {'date': today, 'data': ranked}
    else:
        log.debug("使用缓存的ETF排名")
    return g.rankings_cache['data']

def get_ranked_etfs(context):
    etf_metrics = []
    for etf in g.etf_pool:
        # 🎯 停牌检测：排名计算时过滤
        if is_etf_suspended(etf, context):
            continue
        
        if get_current_data()[etf].paused:
            continue
        
        metrics = calculate_momentum_metrics(context, etf)
        if metrics is not None:
            if g.min_score_threshold < metrics['score'] < g.max_score_threshold:
                etf_metrics.append(metrics)
            else:
                log.debug(f"{etf} {metrics['etf_name']} 得分{metrics['score']:.2f}超出阈值，过滤")
    etf_metrics.sort(key=lambda x: x['score'], reverse=True)
    return etf_metrics

def calculate_momentum_metrics(context, etf):
    try:
        name = get_name(etf)
        lookback = max(g.lookback_days, g.short_lookback_days) + 20
        prices = attribute_history(etf, lookback, '1d', ['close', 'high'])
        if len(prices) < g.lookback_days:
            log.debug(f"{etf} {name} 历史数据不足{len(prices)}天，跳过")
            return None
        current_price = get_current_data()[etf].last_price
        price_series = np.append(prices["close"].values, current_price)
        # 盈利保护
        if check_profit_protection(etf, context):
            log.info(f"🚫 {etf} {name} 触发盈利保护，从排名中排除")
            return None
        # 溢价率
        if g.enable_premium_filter:
            prev_date = get_trade_days(end_date=context.current_dt.date(), count=2)[0]
            premium, _, _ = get_premium_rate(etf, prev_date)
            if premium is not None:
                if premium > g.premium_threshold:
                    log.info(f"🚫 {etf} {name} 溢价率{premium*100:.2f}% > {g.premium_threshold*100:.0f}%，从排名中排除")
                    return None
            else:
                log.debug(f"{etf} {name} 无法获取溢价率，跳过溢价率过滤")
        # 成交量
        if g.enable_volume_check:
            vol_ratio = get_volume_ratio(context, etf)
            if vol_ratio is not None:
                annualized = get_annualized_returns(price_series, g.lookback_days)
                if annualized > g.volume_return_limit:
                    log.info(f"📉 {etf} {name} 成交量放量{vol_ratio:.1f}倍，且年化{annualized*100:.1f}% > 阈值{g.volume_return_limit*100:.1f}%，过滤")
                    return None
        # 短期动量
        if len(price_series) >= g.short_lookback_days + 1:
            short_return = price_series[-1] / price_series[-(g.short_lookback_days + 1)] - 1
            short_annualized = (1 + short_return) ** (250 / g.short_lookback_days) - 1
        else:
            short_annualized = 0
        if g.use_short_momentum_filter and short_annualized < g.short_momentum_threshold:
            return None
        # 长期动量
        recent = price_series[-(g.lookback_days + 1):]
        y = np.log(recent)
        x = np.arange(len(y))
        weights = np.linspace(1, 2, len(y))
        slope, intercept = np.polyfit(x, y, 1, w=np.sqrt(weights))
        annualized_returns = math.exp(slope * 250) - 1
        y_bar_w = np.sum(weights * y) / np.sum(weights)
        ss_res = np.sum(weights * (y - (slope * x + intercept)) ** 2)
        ss_tot = np.sum(weights * (y - y_bar_w) ** 2)
        r_squared = ss_res / ss_tot if ss_tot != 0 else 0
        score = annualized_returns * r_squared
        # 近3日跌幅
        if len(price_series) >= 4:
            day1 = price_series[-1] / price_series[-2]
            day2 = price_series[-2] / price_series[-3]
            day3 = price_series[-3] / price_series[-4]
            if min(day1, day2, day3) < g.loss:
                log.info(f"⚠️ {etf} {name} 近3日有单日跌幅超{(1-g.loss)*100:.1f}%，直接排除")
                return None
        # 动态滤波器
        if g.enable_range_bound_mode and len(price_series) >= 10:
            try:
                laplace_values = laplace_filter(price_series, s=g.laplace_s_param)
                laplace_slope = laplace_values[-1] - laplace_values[-2] if len(laplace_values) >= 2 else 0
                passed_laplace = (current_price > laplace_values[-1] and laplace_slope > g.laplace_min_slope)
                g1_val, g2_val = gaussian_filter_last_two(price_series, sigma=g.gaussian_sigma)
                gaussian_slope = g1_val - g2_val
                passed_gaussian = (current_price > g1_val and gaussian_slope > g.gaussian_min_slope)
                if g.current_filter == '正常期':
                    passed_filter = passed_laplace
                    filter_name = '拉普拉斯'
                else:
                    passed_filter = passed_gaussian
                    filter_name = '高斯'
                if not passed_filter:
                    return None
            except Exception as e:
                log.debug(f"{etf} {name} 滤波器计算异常: {e}")
        return {
            'etf': etf,
            'etf_name': name,
            'annualized_returns': annualized_returns,
            'r_squared': r_squared,
            'score': score,
            'current_price': current_price,
            'short_annualized': short_annualized,
        }
    except Exception as e:
        log.warning(f"计算{etf} {get_name(etf)}时出错: {e}")
        return None

def get_annualized_returns(price_series, lookback_days):
    recent = price_series[-(lookback_days + 1):]
    y = np.log(recent)
    x = np.arange(len(y))
    weights = np.linspace(1, 2, len(y))
    slope, _ = np.polyfit(x, y, 1, w=np.sqrt(weights))
    return math.exp(slope * 250) - 1

def get_volume_ratio(context, security, lookback=None, threshold=None):
    lookback = lookback or g.volume_lookback
    threshold = threshold or g.volume_threshold
    try:
        name = get_name(security)
        hist = attribute_history(security, lookback, '1d', ['volume'])
        if hist.empty or len(hist) < lookback:
            return None
        avg_vol = hist['volume'].mean()
        today = context.current_dt.date()
        df_vol = get_price(security, start_date=today, end_date=context.current_dt,
                           frequency='1m', fields=['volume'], skip_paused=False, fq='pre')
        if df_vol is None or df_vol.empty:
            return None
        current_vol = df_vol['volume'].sum()
        ratio = current_vol / avg_vol if avg_vol > 0 else 0
        if ratio > threshold:
            log.debug(f"{security} {name} 成交量比{ratio:.2f} > {threshold}")
            return ratio
        return None
    except Exception as e:
        log.warning(f"成交量计算失败 {security}: {e}")
        return None

@time_monitor("卖出操作")
def etf_sell_trade(context):
    log.info("========== 卖出操作开始 ==========")
    
    ranked = get_cached_rankings(context)
    target_etfs = []
    for m in ranked[:g.holdings_num]:
        if m['score'] >= g.min_score_threshold:
            target_etfs.append(m['etf'])
    target_set = set(target_etfs)
    if not target_set:
        log.info("💤 无目标ETF，清仓所有持仓")
    for sec in list(context.portfolio.positions.keys()):
        pos = context.portfolio.positions[sec]
        if pos.total_amount == 0:
            continue
        
        if sec not in g.etf_pool:
            if smart_order_target_value(sec, 0, context):
                log.info(f"📤 卖出不在交易池的持仓：{sec} {get_name(sec)}")
            continue
        
        if sec not in target_set:
            if smart_order_target_value(sec, 0, context):
                log.info(f"📤 卖出不在目标的持仓：{sec} {get_name(sec)}")
    log.info("========== 卖出操作完成 ==========")

@time_monitor("买入操作")
def etf_buy_trade(context):
    log.info("========== 买入操作开始 ==========")
    ranked = get_cached_rankings(context)
    log.info("=== ETF排名前5 ===")
    for i, m in enumerate(ranked[:5]):
        log.info(f"排名{i+1}: {m['etf']} {m['etf_name']} 得分{m['score']:.4f} 年化{m['annualized_returns']*100:.2f}% R²={m['r_squared']:.4f}")
    
    target_etfs = []
    for m in ranked:
        if len(target_etfs) >= g.holdings_num:
            break
        etf = m['etf']
        target_etfs.append(etf)
        log.info(f"🎯 目标ETF {len(target_etfs)}: {etf} {m['etf_name']} 得分{m['score']:.4f}")
    if not target_etfs:
        log.info(" 无目标ETF，保持空仓")
        return
    current_etf_pos = [s for s in context.portfolio.positions if context.portfolio.positions[s].total_amount > 0]
    pool_positions = [s for s in current_etf_pos if s in g.etf_pool]
    to_sell = [s for s in pool_positions if s not in target_etfs]
    if to_sell:
        to_sell_names = [get_name(s) for s in to_sell]
        log.info(f"尚有持仓需要卖出：{list(zip(to_sell, to_sell_names))}，等待卖出完成再买入")
        return
    total_val = context.portfolio.total_value
    target_per_etf = total_val / len(target_etfs)
    for etf in target_etfs:
        current_val = 0
        if etf in context.portfolio.positions:
            pos = context.portfolio.positions[etf]
            if pos.total_amount > 0:
                current_val = pos.total_amount * pos.price
        if abs(current_val - target_per_etf) > target_per_etf * 0.05 or current_val == 0:
            if smart_order_target_value(etf, target_per_etf, context):
                action = "买入" if current_val < target_per_etf else "调仓"
                log.info(f"📦 {action}：{etf} {get_name(etf)} 目标金额{target_per_etf:.2f}")
    log.info("========== 买入操作完成 ==========")

# ==================== 📊 盘后总结 ====================
def daily_summary(context):
    log.info("=" * 70)
    log.info(f"📊 盘后总结 - {context.current_dt.strftime('%Y-%m-%d')}")
    log.info("=" * 70)

    portfolio = context.portfolio
    total_value = portfolio.portfolio_value
    cash = portfolio.cash
    positions_value = total_value - cash
    position_count = len([s for s, p in portfolio.positions.items() if p.total_amount > 0])

    if hasattr(g, 'initial_cash') and g.initial_cash is not None and g.initial_cash > 0:
        cum_return = (total_value / g.initial_cash - 1) * 100
    else:
        cum_return = 0.0

    if g.prev_total_value is not None and g.prev_total_value > 0:
        daily_return = (total_value / g.prev_total_value - 1) * 100
    else:
        daily_return = 0.0
    g.prev_total_value = total_value

    log.info(f"💰 总资产: {total_value:,.2f} | 可用: {cash:,.2f} | 市值: {positions_value:,.2f} | 累计收益: {cum_return:+.2f}% | 当日收益: {daily_return:+.2f}%")

    if position_count > 0:
        for sec, pos in portfolio.positions.items():
            if pos.total_amount == 0:
                continue
            cur_price = pos.price
            cost = pos.avg_cost
            pnl_pct = (cur_price / cost - 1) * 100 if cost > 0 else 0
            hold_days = 0
            if hasattr(pos, 'init_time') and pos.init_time:
                try:
                    start_date = pos.init_time.date()
                    end_date = context.current_dt.date()
                    trade_days = get_trade_days(start_date=start_date, end_date=end_date)
                    hold_days = len(trade_days) - 1
                    if hold_days < 0:
                        hold_days = 0
                except:
                    hold_days = 0
            log.info(f"{sec} {get_name(sec)} | 成本: {cost:.3f} | 当前: {cur_price:.3f} | 收益: {pnl_pct:+.2f}% | 持有: {hold_days}天")
    else:
        log.info("📭 当前空仓")

    all_trades = g.trade_log.get('records', []) + g.trade_log.get('sell_records', [])
    if all_trades:
        all_trades.sort(key=lambda x: x['time'])
        log.info("-" * 70)
        log.info("📝 今日交易记录:")
        for trade in all_trades:
            row = (f"{trade['security']} {trade['name']} | "
                   f"{trade['direction']} | "
                   f"数量: {trade['amount']} | "
                   f"价格: {trade['price']:.3f} | "
                   f"金额: {trade['value']:.2f}")
            log.info(row)
        g.trade_log['records'] = []
        g.trade_log['sell_records'] = []
    else:
        log.info("📭 今日无交易")
    log.info("-" * 70)
    log.info("⚙️ 策略状态:")
    log.info(f"  震荡期: {g.current_filter} (滤波器: {'拉普拉斯' if g.current_filter=='正常期' else '高斯'})")
    log.info(f"  动态扩容池: {len(g.dynamic_etf_pool)} 只")
    for etf, days in g.dynamic_etf_pool.items():
        log.info(f"    {etf} {get_name(etf)} - 剩余{days}天")
    log.info("=" * 70)
    log.info("🧨🐂🚩🐂🚩🐂🚩🚩🚩🚩🚩🚩🚩🚩🚩报告结束 🚩🚩🚩🚩🚩🚩🚩🚩🚩🐂🚩🐂🚩🐂🧨")
    log.info(" ")

# ==================== 📊 开盘前ETF相关性分析 ====================
def get_top20_etfs_by_growth(context, lookback_days=10):
    """获取10日内涨幅最高的top20 ETF（全市场ETF池）"""
    etf_list = []
    all_etfs = g.all_etf_pool
    total_count = len(all_etfs)
    processed_count = 0
    # 性能优化(真机): 批量预取收盘/成交量,聚宽环境自动回退逐只查询
    _batch = None
    try:
        _batch = pt_batch_hist_multi(all_etfs, lookback_days + 5,
                                     ['close', 'volume'])
        log.info(f"📦 批量预取完成: {len(_batch.get('close').columns)}只(收盘/成交量)")
    except Exception as _e:
        log.debug(f"批量预取不可用,回退逐只查询: {_e}")
        _batch = None

    for etf in all_etfs:
        try:
            if _batch is not None and etf in _batch['close'].columns:
                closes = _batch['close'][etf].values
                volumes = _batch['volume'][etf].values
            else:
                hist = attribute_history(etf, lookback_days + 5, '1d', ['close', 'volume'])
                closes = hist['close'].values
                volumes = hist['volume'].values
            if len(closes) < lookback_days:
                continue
            
            growth = closes[-1] / closes[-lookback_days] - 1
            turnovers = volumes[-lookback_days:] * closes[-lookback_days:]
            avg_turnover = turnovers.mean()
            
            etf_list.append({
                'etf': etf,
                'name': get_name(etf),
                'growth': growth,
                'avg_turnover': avg_turnover,
                'closes': closes[-lookback_days:]
            })
        except Exception:
            continue
        
        processed_count += 1
        if processed_count % 100 == 0:
            log.debug(f"📊 已处理{processed_count}/{total_count}只ETF")
    
    etf_list.sort(key=lambda x: x['growth'], reverse=True)
    log.info(f"📊 共处理{processed_count}只ETF，筛选出{len(etf_list)}只有效数据")
    return etf_list[:20]

def calculate_correlation(etf1_returns, etf2_returns):
    """计算两个ETF之间的涨跌同步程度（相关性检验）"""
    if len(etf1_returns) != len(etf2_returns):
        return {'pearson': 0.0, 'sign_match': 0.0, 'composite': 0.0}
    
    returns1 = np.array(etf1_returns, dtype=float)
    returns2 = np.array(etf2_returns, dtype=float)
    
    mask = ~(np.isnan(returns1) | np.isnan(returns2))
    returns1 = returns1[mask]
    returns2 = returns2[mask]
    
    if len(returns1) < 2:
        return {'pearson': 0.0, 'sign_match': 0.0, 'composite': 0.0}
    
    mean1 = np.mean(returns1)
    mean2 = np.mean(returns2)
    std1 = np.std(returns1)
    std2 = np.std(returns2)
    
    if std1 == 0 or std2 == 0:
        sign_match = np.sum(np.sign(returns1) == np.sign(returns2)) / len(returns1)
        return {'pearson': 0.0, 'sign_match': sign_match, 'composite': sign_match}
    
    covariance = np.mean((returns1 - mean1) * (returns2 - mean2))
    pearson = covariance / (std1 * std2)
    
    sign_match = np.sum(np.sign(returns1) == np.sign(returns2)) / len(returns1)
    
    composite = (pearson + sign_match) / 2
    
    return {'pearson': pearson, 'sign_match': sign_match, 'composite': composite}

@time_monitor("开盘前相关性分析")
def pre_market_correlation_analysis(context):
    """开盘前监测10日内涨幅最高的top20 ETF，进行相关性检验"""
    log.info("=" * 70)
    log.info(f"📊 开盘前ETF相关性分析 - {context.current_dt.strftime('%Y-%m-%d %H:%M')}")
    log.info("=" * 70)
    
    g.dragon_head_etf = None
    g.dragon_head_name = None
    g.dragon_family = {}
    
    top20_etfs = get_top20_etfs_by_growth(context, lookback_days=10)
    
    if len(top20_etfs) < 2:
        log.info("📭 ETF数据不足，跳过相关性分析")
        log.info("=" * 70)
        return
    
    reference_etf = top20_etfs[0]
    
    log.info(f"\n🎯 参考ETF（涨幅Top1）：{reference_etf['etf']} {reference_etf['name']}")
    
    ref_closes = reference_etf['closes']
    ref_returns = []
    for i in range(1, len(ref_closes)):
        if ref_closes[i - 1] != 0:
            ref_returns.append(ref_closes[i] / ref_closes[i - 1] - 1)
        else:
            ref_returns.append(0.0)
    
    correlation_results = []
    for item in top20_etfs:
        if item['etf'] == reference_etf['etf']:
            continue
        
        etf_closes = item['closes']
        etf_returns = []
        for i in range(1, len(etf_closes)):
            if etf_closes[i - 1] != 0:
                etf_returns.append(etf_closes[i] / etf_closes[i - 1] - 1)
            else:
                etf_returns.append(0.0)
        
        corr = calculate_correlation(ref_returns, etf_returns)
        correlation_results.append({
            'etf': item['etf'],
            'name': item['name'],
            'growth': item['growth'],
            'pearson': corr['pearson'],
            'sign_match': corr['sign_match'],
            'composite': corr['composite']
        })
    
    correlation_results.sort(key=lambda x: x['composite'], reverse=True)
    
    high_sync_count = sum(1 for item in correlation_results if item['composite'] >= 0.7)
    medium_sync_count = sum(1 for item in correlation_results if 0.4 <= item['composite'] < 0.7)
    
    log.info(f"\n🔗 与{reference_etf['name']}涨跌同步程度排名（强同步{high_sync_count}只，中同步{medium_sync_count}只）")
    headers = ['排名', 'ETF代码', '名称', '10日涨幅', '皮尔逊相关', '涨跌方向一致', '综合同步']
    widths = [4, 14, 16, 12, 10, 10, 10]
    log.info(format_table_row(headers, widths))
    log.info("-" * 80)
    
    for i, item in enumerate(correlation_results):
        if i >= 10:
            break
        if item['composite'] < 0.4:
            continue
        name_display = item['name'][:12] if len(item['name']) > 12 else item['name']
        sync_level = "强同步" if item['composite'] >= 0.7 else "中同步"
        cols = [
            str(i + 1),
            item['etf'],
            name_display,
            f"{item['growth'] * 100:>11.2f}%",
            f"{item['pearson'] * 100:>9.1f}%",
            f"{item['sign_match'] * 100:>9.1f}%",
            f"{item['composite'] * 100:>9.1f}% {sync_level}"
        ]
        log.info(format_table_row(cols, widths))
    log.info("-" * 80)
    
    top10_strong = [item for item in correlation_results[:10] if item['composite'] >= 0.7]
    top5_strong = [item for item in correlation_results[:5] if item['composite'] >= 0.7]
    
    try:
        if len(top10_strong) > 5 and len(top5_strong) >= 3:
            g.dragon_head_etf = reference_etf['etf']
            g.dragon_head_name = reference_etf['name']
            dragon_subordinates = [item for item in correlation_results if item['composite'] >= 0.7]
            g.dragon_family = {item['etf']: {'name': item['name'], 'composite': item['composite'], 'growth': item['growth']} for item in dragon_subordinates}
            
            log.info(f"\n👑 🌟 龙头家族判定结果：{reference_etf['name']} 所在板块被列为龙头家族！")
            log.info(f"   判定条件：Top10强同步{len(top10_strong)}只(>5)，Top5强同步{len(top5_strong)}只(≥3)")
            log.info(f"   龙头家族成员总数：{len(g.dragon_family) + 1}只（含龙头）")
            family_list = [f"{g.dragon_head_etf}({g.dragon_head_name[:6]})"]
            for etf in list(g.dragon_family)[:4]:
                name = g.dragon_family[etf]['name']
                family_list.append(f"{etf}({name[:6]})")
            family_str = ', '.join(family_list)
            if len(g.dragon_family) > 4:
                family_str += '...'
            log.info(f"   龙头家族列表：{family_str}")
        else:
            log.info(f"\n👑 龙头家族判定：未达标（Top10强同步{len(top10_strong)}只，Top5强同步{len(top5_strong)}只）")
    except Exception as e:
        log.error(f"⚠️ 龙头家族判定过程出现异常：{e}")
    
    log.info("=" * 70)

# ==================== 🔍 尾盘龙头监测 ====================
def is_stagnant_with_volume(etf, lookback_days=5, context=None):
    """盘后判断单个ETF是否见顶：放量滞涨 或 慢性滞涨见顶"""
    try:
        end_date = context.current_dt.date()
        daily_hist = get_price(etf, end_date=end_date, count=7, frequency='daily', fields=['close', 'volume'], skip_paused=False)
        if len(daily_hist) < 7:
            return False, None, None, None, None, None
        
        today_close = daily_hist['close'].iloc[-1]
        yesterday_close = daily_hist['close'].iloc[-2]
        day_before_yesterday_close = daily_hist['close'].iloc[-3]
        five_days_ago_close = daily_hist['close'].iloc[-6]
        
        today_volume = daily_hist['volume'].iloc[-1]
        yesterday_volume = daily_hist['volume'].iloc[-2]
        day_before_yesterday_volume = daily_hist['volume'].iloc[-3]
        
        today_change = (today_close - yesterday_close) / yesterday_close * 100
        yesterday_change = (yesterday_close - day_before_yesterday_close) / day_before_yesterday_close * 100
        
        today_turnover = today_volume * today_close
        yesterday_turnover = yesterday_volume * yesterday_close
        day_before_yesterday_turnover = day_before_yesterday_volume * day_before_yesterday_close
        
        five_day_growth = (today_close - five_days_ago_close) / five_days_ago_close * 100
        
        turnover_increased = today_turnover > yesterday_turnover if yesterday_turnover > 0 else False
        
        closes = daily_hist['close'].values
        daily_changes = []
        for i in range(1, len(closes)):
            daily_changes.append((closes[i] - closes[i-1]) / closes[i-1] * 100)
        
        recent_changes = daily_changes[-5:]
        down_count = sum(1 for c in recent_changes if c < 0)
        big_down_count = sum(1 for c in recent_changes if c < -3)
        
        condition_vol_stagnant1 = today_change < yesterday_change
        condition_vol_stagnant2 = turnover_increased
        condition_vol_stagnant3 = five_day_growth > 20
        is_vol_stagnant = condition_vol_stagnant1 and condition_vol_stagnant2 and condition_vol_stagnant3
        
        condition_chronic1 = down_count >= 3
        condition_chronic2 = big_down_count >= 2
        condition_chronic3 = today_turnover > yesterday_turnover and yesterday_turnover > day_before_yesterday_turnover
        is_chronic_stagnant = condition_chronic1 and condition_chronic2 and condition_chronic3
        
        is_stagnant = is_vol_stagnant or is_chronic_stagnant
        stagnant_type = "放量滞涨" if is_vol_stagnant else ("慢性滞涨" if is_chronic_stagnant else None)
        
        return is_stagnant, None, today_change, None, turnover_increased, stagnant_type
    except Exception:
        return False, None, None, None, None, None

@time_monitor("盘后龙头监测")
def dragon_stagnant_monitor(context):
    """盘后15:01监测龙头家族是否见顶（放量滞涨或慢性滞涨）"""
    log.info("=" * 70)
    log.info(f"🔍 盘后龙头监测 - {context.current_dt.strftime('%Y-%m-%d %H:%M')}")
    log.info("=" * 70)
    
    if g.dragon_head_etf is None or not g.dragon_family:
        log.info("📭 当前无龙头家族，跳过监测")
        log.info("=" * 70)
        return
    
    head_etf = g.dragon_head_etf
    head_name = g.dragon_head_name
    
    all_members = list(g.dragon_family.keys()) + [head_etf]
    stagnant_count = 0
    details = []
    
    for etf in all_members:
        is_stagnant, amplitude, change, gap_down, turnover_increased, stagnant_type = is_stagnant_with_volume(etf, context=context)
        name = get_name(etf)
        
        change_str = f"涨幅{change:.2f}%" if change else "涨幅N/A"
        turnover_str = "成交额放大" if turnover_increased else "成交额未放大"
        
        if is_stagnant:
            stagnant_count += 1
            log.info(f"   🚨 {etf} {name[:8]}: {stagnant_type}, {change_str}, {turnover_str}")
            details.append(f"{etf} {name[:8]}: {stagnant_type}, 涨幅{change:.2f}%, 成交额放大")
        else:
            log.info(f"   ✅ {etf} {name[:8]}: {change_str}, {turnover_str}")
    
    log.info(f"👑 龙头家族：{head_name} 板块")
    log.info(f"👨‍👩‍👧‍👦 家族成员总数：{len(all_members)}只，见顶信号：{stagnant_count}只")
    
    if details:
        log.info("📉 见顶信号成员：")
        for detail in details:
            log.info(f"   {detail}")
    
    half_count = (len(all_members) + 1) // 2
    if stagnant_count >= half_count:
        log.info(f"\n🚨 警报！超过一半成员({stagnant_count}/{len(all_members)})出现见顶信号！")
        log.info(f"⚠️ 龙头家族{head_name}放量滞涨提醒（仅播报，不触发制裁）")
    else:
        log.info(f"\n✅ 正常状态（需{half_count}只滞涨，当前{stagnant_count}只）")
    
    if stagnant_count > 0:
        log.info("\n🔻 资金高切低监测 - 跷跷板ETF池最弱ETF（因子004）：")
        log.info("-" * 70)
        try:
            end_date = context.current_dt.date()
            alpha004_series = calculate_alpha004(end_date, index='seesaw')
            if not alpha004_series.empty:
                weakest_etfs = alpha004_series.sort_values(ascending=False).head(10)
                for i, (etf, factor_value) in enumerate(weakest_etfs.items(), 1):
                    name = get_name(etf)
                    log.info(f"   {i}. {etf} {name[:8]}: 20天下跌{factor_value}天")
                log.info("⚠️ 龙头见顶时，资金可能从高位流向银行/国企/红利/公用事业/黄金/能源/农业（仅供参考）")
            else:
                log.info("   暂无有效数据")
        except Exception as e:
            log.info(f"   因子004计算异常：{e}")
        log.info("-" * 70)
    
    log.info("=" * 70)
    
    
    
    #以下代码为PTRADE版的打新和逆回购
    '''
    import time


def initialize(context):
    run_daily(context, auto_ipo_subscribe, '9:55')  # 申购新股和可转债
    run_daily(context, reverse_repurchase, '14:55')  # 账户剩余资金自动逆回购深市1天期


def reverse_repurchase(context):
    """自动逆回购深市1天期R-001"""
    # 获取资金信息
    cash = context.portfolio.cash  # 可用资金
    total_value = context.portfolio.total_value  # 总资产
    positions_value = context.portfolio.positions_value  # 持仓市值
    
    log.info(f"【资金诊断】可用资金={cash:.2f}元, 总资产={total_value:.2f}元, 持仓市值={positions_value:.2f}元")
    
    # 强制使用所有可用资金进行逆回购
    available_for_rp = cash
    
    # 逆回购131810.SZ（R-001）：PTrade下单单位为"张"，1张=100元，最低10张起（1000元）
    if available_for_rp < 1000:
        log.info(f"【逆回购跳过】 可用资金{available_for_rp:.2f}元，低于1000元门槛（最低10张）")
        return

    # 计算可下单张数（必须是10的倍数）
    zhang_num = int(available_for_rp / 100)
    zhang_num = (zhang_num // 10) * 10
    if zhang_num <= 0:
        log.info(f"【逆回购跳过】 可下单张数为0，可用资金{cash:.2f}元")
        return

    # 逆回购下单：卖出（-）对应张数
    try:
        order_id = order('131810.XSHE', -1 * zhang_num)
        if order_id:
            log.info(f"【已完成逆回购】 品种：131810.XSHE（R-001），下单张数：{zhang_num}，对应金额：{zhang_num * 100}元")
        else:
            log.error(f"【逆回购失败】 下单张数{zhang_num}，可用资金{cash:.2f}元")
    except Exception as e:
        log.error(f"【逆回购异常】 错误原因：{str(e)}")


def auto_ipo_subscribe(context):
    """自动申购当日所有新股 + 可转债"""
    try:
        # 1. 获取当日可申购标的（新股+可转债）
        ipo_info = get_ipo_stocks()
        if not ipo_info:
            log.info("【自动打新】今日无可申购新股/可转债")
            return

        # 2. 一键申购所有可打标的（PTrade官方接口）
        order_result = ipo_stocks_order()

        # 3. 打印申购结果日志
        log.info("=" * 50)
        log.info(f"【可申购标的】 {ipo_info}")
        log.info(f"【自动打新完成】 申购结果：{order_result}")
        log.info("=" * 50)

    except Exception as e:
        log.error(f"【自动打新异常】 错误信息：{str(e)}")


def handle_data(context, data):
    pass
'''