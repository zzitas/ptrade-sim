# PTrade-SIM 安装说明

## 1. 系统要求

| 项目 | 要求 |
|---|---|
| 操作系统 | Windows 10 / 11(图形界面);命令行模式亦可在 Linux/macOS 运行 |
| Python | 3.9 及以上(需包含 tkinter,官方安装包默认自带) |
| 第三方依赖 | `pandas>=1.3`、`pytdx>=1.72`(安装时自动拉取) |
| 可选 | 通达信终端(提供本地真实行情,推荐) |

## 2. 安装方式

### 方式一:wheel 包(推荐)

```bash
pip install ptrade_sim-1.0.0-py3-none-any.whl
```

### 方式二:源码目录安装

```bash
cd ptrade-sim
pip install .
```

### 方式三:不安装直接运行

将 `ptrade_sim/` 目录放到任意工作目录下,在该目录执行:

```bash
python -m ptrade_sim.gui          # 图形界面
python -m ptrade_sim._selftest    # 冒烟测试
```

### 离线环境安装

在有网的机器上先下载依赖到本地目录:

```bash
pip download pandas pytdx -d vendor/
```

拷贝整个发布包与 `vendor/` 到目标机器后:

```bash
pip install --no-index --find-links vendor/ ptrade_sim-1.0.0-py3-none-any.whl
```

## 3. 验证安装

```bash
ptrade-selftest
```

看到 `errors: 0` 与模拟结果报告即安装成功。四个命令行入口:

| 命令 | 功能 |
|---|---|
| `ptrade-gui` | 启动图形界面 |
| `ptrade-run` | 命令行回测 |
| `ptrade-selftest` | 无头冒烟测试 |
| `ptrade-prefetch` | 全市场行情预热下载 |

若提示"不是内部或外部命令",请确认 Python 的 `Scripts` 目录已在 PATH 中,
或改用模块方式:`python -m ptrade_sim.gui`。

## 4. 数据源配置

### 4.1 通达信终端(推荐)

- 打开通达信终端并登录行情即可,**无需其他配置**;
- 程序自动探测本机端口:**17709 → 7709**,均失败后自动切换公共行情主站;
- 若终端监听其他端口,可在代码中指定:
  ```python
  from ptrade_sim.tdxdata import TdxDataSource
  ds = TdxDataSource(host="127.0.0.1")   # 端口在 SERVERS 列表中调整
  ```

### 4.2 网络真实数据

无需通达信终端时使用。腾讯行情为主源、东方财富为备用源;全市场 ETF 列表
来自东财 clist / 天天基金代码表,缓存 7 天。接口被限流时自动切换,无需干预。

### 4.3 合成行情

零配置,用于验证策略语法与调度逻辑,**结果不代表真实收益**。

## 5. 数据缓存

所有下载数据落盘于用户数据目录 `data_cache/`(首次运行自动创建):

| 文件 | 说明 |
|---|---|
| `<代码>.csv` | 各标的日线(前复权),增量更新 |
| `all_etfs.csv` | 全市场上市 ETF 列表,7 天自动刷新 |
| `names.json` | 代码-名称映射 |
| `bad_codes.txt` | 确认无行情的无效代码黑名单(未上市等),自动维护 |

> 提示:该目录会随预热增长到约 30–60 MB;删除即重建,不影响程序运行。

建议在正式回测前先执行一次全市场预热(约 10–60 分钟,视网络):

```bash
ptrade-prefetch            # 后台挂着跑完即可,之后所有回测秒开
```

## 6. 常见安装问题

**Q: `pip install` 报 SSL/超时?**
A: 换国内镜像:`pip install xxx.whl -i https://pypi.tuna.tsinghua.edu.cn/simple`

**Q: GUI 无法启动,报 tkinter 相关错误?**
A: 重装 Python 并勾选 "tcl/tk and IDLE" 组件。

**Q: 回测时报 `无法连接通达信行情服务器`?**
A: 未开通达信终端且公共主站不可达。打开通达信终端,或改用数据源 `real`/`sim`
   (GUI 下拉选择;命令行第 5 个参数)。

**Q: 杀毒软件拦截 pytdx?**
A: pytdx 为纯 Python 协议库,添加信任即可。
