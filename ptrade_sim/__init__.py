"""PTrade 本地模拟(回测)环境。

在本地以与 PTrade 一致的事件模型运行策略,支持三种数据源:
合成行情 / 通达信终端真实数据 / 网络真实数据(前复权)。
"""
from .engine import SimEngine, run_strategy_file

__version__ = "1.0.0"

__all__ = ["SimEngine", "run_strategy_file", "__version__"]
