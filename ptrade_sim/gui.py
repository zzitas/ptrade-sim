# -*- coding: utf-8 -*-
"""PTrade 模拟环境图形界面(Tkinter,无第三方依赖)。

启动:  python -m ptrade_sim.gui
"""
import datetime as dt
import glob
import os
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from .engine import SimEngine, load_strategy
from . import data as simdata

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ACCENT = "#1f77b4"
RED = "#d62728"
GREEN = "#2ca02c"
GRAY = "#666666"


class SimulatorSession:
    """在后台线程中运行一次模拟,供 GUI 轮询状态。"""

    def __init__(self):
        self.engine = None
        self.thread = None
        self.done = True
        self.error = None

    def start(self, strategy_path, start, end, capital, source="tdx",
              show_data_logs=False):
        mod = load_strategy(strategy_path)
        ds = None
        if source == "tdx":
            from .tdxdata import TdxDataSource
            ds = TdxDataSource()
        elif source == "real":
            from .redata import RealDataSource
            ds = RealDataSource()
        self.engine = SimEngine(capital=capital, verbose=False, data_source=ds)
        if ds is not None:
            ds.log = self.engine.log
            if show_data_logs:
                ds.show_data_logs = True
        self.done = False
        self.error = None

        def worker():
            try:
                self.engine.run(mod, start, end)
            except Exception:
                self.error = traceback.format_exc()
            finally:
                self.done = True

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()

    def stop(self):
        if self.engine:
            self.engine.stop()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PTrade 模拟环境")
        self.geometry("1080x720")
        self.minsize(860, 560)

        self.session = SimulatorSession()
        self._log_index = 0
        self._equity_count = 0
        self._order_count = 0

        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()
        self.after(200, self._poll)

    # ---------------- 界面构建 ----------------
    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(fill="x")

        ttk.Label(bar, text="策略文件:").grid(row=0, column=0, sticky="w")
        self.path_var = tk.StringVar(value=os.path.join(BASE_DIR, "ptrade_sim", "demo_strategy.py"))
        self.path_combo = ttk.Combobox(bar, textvariable=self.path_var, width=46)
        self.path_combo.grid(row=0, column=1, columnspan=3, sticky="we", padx=6)
        self.path_combo["values"] = self._list_strategies()
        ttk.Button(bar, text="浏览...", command=self._browse).grid(row=0, column=4, padx=(0, 12))
        ttk.Label(bar, text="数据源:").grid(row=0, column=5, sticky="w")
        self.source_var = tk.StringVar(value="通达信终端数据(前复权)")
        self.source_combo = ttk.Combobox(bar, textvariable=self.source_var, width=22,
                                         state="readonly",
                                         values=["通达信终端数据(前复权)",
                                                 "真实历史数据-网络(前复权)",
                                                 "模拟行情(合成)"])
        self.source_combo.grid(row=0, column=6, columnspan=2, sticky="w")
        self.detail_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="数据加载明细", variable=self.detail_var)\
            .grid(row=0, column=8, padx=(10, 0))

        ttk.Label(bar, text="开始日期:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.start_var = tk.StringVar(value=(dt.date.today() - dt.timedelta(days=60)).isoformat())
        ttk.Entry(bar, textvariable=self.start_var, width=12).grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Label(bar, text="结束日期:").grid(row=1, column=2, sticky="w", pady=(8, 0), padx=(10, 0))
        self.end_var = tk.StringVar(value=dt.date.today().isoformat())
        ttk.Entry(bar, textvariable=self.end_var, width=12).grid(row=1, column=3, sticky="w", pady=(8, 0))
        ttk.Label(bar, text="初始资金:").grid(row=1, column=4, sticky="w", pady=(8, 0), padx=(12, 0))
        self.capital_var = tk.StringVar(value="1000000")
        ttk.Entry(bar, textvariable=self.capital_var, width=12).grid(row=1, column=5, sticky="w", pady=(8, 0))

        self.run_btn = ttk.Button(bar, text="▶ 运行", command=self._on_run)
        self.run_btn.grid(row=1, column=6, padx=(16, 0), pady=(8, 0))
        self.stop_btn = ttk.Button(bar, text="■ 停止", command=self._on_stop, state="disabled")
        self.stop_btn.grid(row=1, column=7, padx=(6, 0), pady=(8, 0))
        self.clear_btn = ttk.Button(bar, text="清空", command=self._on_clear)
        self.clear_btn.grid(row=1, column=8, padx=(6, 0), pady=(8, 0))
        self.logdir_btn = ttk.Button(bar, text="日志目录", command=self._open_log_dir)
        self.logdir_btn.grid(row=1, column=9, padx=(6, 0), pady=(8, 0))

        bar.columnconfigure(1, weight=1)
        bar.columnconfigure(3, weight=1)

    def _list_strategies(self):
        files = sorted(glob.glob(os.path.join(BASE_DIR, "*.py")))
        files += sorted(glob.glob(os.path.join(BASE_DIR, "ptrade_sim", "*.py")))
        return [f for f in files if not os.path.basename(f).startswith("temp_")]

    def _build_tabs(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        # 日志页
        log_frame = ttk.Frame(self.nb)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap="none", state="disabled",
                                                  font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True)
        for tag, color in (("ERROR", RED), ("WARN", "#b8860b"), ("INFO", "#222222")):
            self.log_text.tag_configure(tag, foreground=color)
        self.nb.add(log_frame, text=" 运行日志 ")

        # 资产曲线页
        eq_frame = ttk.Frame(self.nb)
        self.canvas = tk.Canvas(eq_frame, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._draw_equity())
        self.eq_label = ttk.Label(eq_frame, text="尚未运行", foreground=GRAY)
        self.eq_label.pack(anchor="w", padx=8, pady=4)
        self.nb.add(eq_frame, text=" 资产曲线 ")

        # 持仓/成交页
        pos_frame = ttk.Frame(self.nb)
        cols = ("code", "name", "total", "available", "frozen", "cost", "price", "value")
        self.pos_tree = ttk.Treeview(pos_frame, columns=cols, show="headings", height=8)
        for cid, text, w, anchor in (
                ("code", "代码", 110, "w"), ("name", "名称", 130, "w"),
                ("total", "总持仓", 90, "e"), ("available", "可用", 90, "e"),
                ("frozen", "冻结(今日买入)", 120, "e"), ("cost", "成本价", 80, "e"),
                ("price", "现价", 80, "e"), ("value", "市值", 110, "e")):
            self.pos_tree.heading(cid, text=text)
            self.pos_tree.column(cid, width=w, anchor=anchor)
        self.pos_tree.pack(fill="x", padx=6, pady=(6, 2))

        ttk.Label(pos_frame, text="成交记录(最近 300 笔)").pack(anchor="w", padx=6, pady=(8, 2))
        ocols = ("time", "side", "code", "amount", "price", "fee_note")
        self.order_tree = ttk.Treeview(pos_frame, columns=ocols, show="headings")
        for cid, text, w, anchor in (
                ("time", "时间", 140, "w"), ("side", "方向", 50, "center"),
                ("code", "代码", 110, "w"), ("amount", "数量", 90, "e"),
                ("price", "成交价", 80, "e"), ("fee_note", "状态", 100, "w")):
            self.order_tree.heading(cid, text=text)
            self.order_tree.column(cid, width=w, anchor=anchor)
        self.order_tree.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.order_tree.tag_configure("buy", foreground=RED)
        self.order_tree.tag_configure("sell", foreground=GREEN)
        self.nb.add(pos_frame, text=" 持仓 / 成交 ")

        # 统计页
        stat_frame = ttk.Frame(self.nb)
        self.stat_text = scrolledtext.ScrolledText(stat_frame, wrap="word", state="disabled",
                                                   font=("Microsoft YaHei UI", 11))
        self.stat_text.pack(fill="both", expand=True)
        self.nb.add(stat_frame, text=" 统计报告 ")

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="就绪")
        bar = ttk.Frame(self, relief="sunken", padding=(8, 3))
        bar.pack(fill="x", side="bottom")
        ttk.Label(bar, textvariable=self.status_var, foreground=GRAY).pack(side="left")
        self.now_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.now_var, foreground=ACCENT).pack(side="right")

    # ---------------- 事件 ----------------
    def _browse(self):
        path = filedialog.askopenfilename(
            initialdir=BASE_DIR, title="选择策略文件",
            filetypes=[("Python 策略", "*.py"), ("所有文件", "*.*")])
        if path:
            self.path_var.set(path)

    def _on_run(self):
        if not self.session.done:
            return
        path = self.path_var.get().strip()
        if not os.path.isfile(path):
            messagebox.showerror("错误", f"策略文件不存在:\n{path}")
            return
        try:
            start = dt.date.fromisoformat(self.start_var.get().strip())
            end = dt.date.fromisoformat(self.end_var.get().strip())
            capital = float(self.capital_var.get())
            if start > end:
                raise ValueError("开始日期不能晚于结束日期")
            if capital <= 0:
                raise ValueError("初始资金必须大于 0")
        except ValueError as e:
            messagebox.showerror("参数错误", f"日期格式应为 YYYY-MM-DD,资金为正数\n{e}")
            return

        self._on_clear()
        label = self.source_var.get()
        source = "tdx" if label.startswith("通达信") else ("real" if label.startswith("真实") else "sim")
        self._append_log(f"数据源: {label}")
        self._append_log(f"加载策略: {path}")
        self._append_log(f"区间 {start} ~ {end}, 初始资金 {capital:,.0f}")
        try:
            self.session.start(path, start, end, capital, source=source,
                               show_data_logs=self.detail_var.get())
        except Exception:
            messagebox.showerror("加载失败", traceback.format_exc())
            return
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("模拟运行中...")

    def _on_stop(self):
        self.session.stop()
        self.stop_btn.config(state="disabled")
        self.status_var.set("正在停止...")

    def _on_clear(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        self._log_index = 0
        self._equity_count = 0
        self._order_count = 0
        for tree in (self.pos_tree, self.order_tree):
            tree.delete(*tree.get_children())
        self.stat_text.config(state="normal")
        self.stat_text.delete("1.0", "end")
        self.stat_text.config(state="disabled")
        self.eq_label.config(text="尚未运行", foreground=GRAY)

    def _open_log_dir(self):
        """打开回测日志目录(每次回测的完整日志自动保存在这里)。"""
        log_dir = os.environ.get("PTRADE_SIM_LOG_DIR") \
            or os.path.join(os.getcwd(), "logs")
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        try:
            os.startfile(log_dir)          # Windows
        except AttributeError:
            import subprocess
            subprocess.Popen(["xdg-open", log_dir])
        except Exception:
            messagebox.showinfo("日志目录", f"日志目录:\n{log_dir}")

    # ---------------- 轮询刷新 ----------------
    def _poll(self):
        try:
            self._poll_once()
        finally:
            self.after(200, self._poll)

    def _poll_once(self):
        eng = self.session.engine
        if not eng:
            return

        # 新日志
        logs = eng.logs
        while self._log_index < len(logs):
            self._append_log(logs[self._log_index])
            self._log_index += 1

        # 时钟与状态
        self.now_var.set(f"模拟时间 {eng.now:%Y-%m-%d %H:%M}")

        # 资产曲线有新点则重画
        if len(eng.daily_equity) != self._equity_count:
            self._equity_count = len(eng.daily_equity)
            self._draw_equity()
            self._update_positions(eng)
        if len(eng.orders) != self._order_count:
            self._order_count = len(eng.orders)
            self._update_orders(eng)

        if self.session.done:
            self.run_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            if self.session.error:
                self._append_log("模拟线程异常:\n" + self.session.error)
                self.status_var.set("运行失败")
                messagebox.showerror("运行失败", self.session.error)
                self.session.error = None
            else:
                self.status_var.set("运行结束")
                self._append_log("========== 模拟结束 ==========")
                self._show_report(eng)
            self._update_positions(eng)
            self._update_orders(eng)
            self._draw_equity()
            self.session.engine = None  # 避免重复汇报

    def _append_log(self, line):
        self.log_text.config(state="normal")
        tag = "ERROR" if "[ERROR]" in line else ("WARN" if "[WARN]" in line else "INFO")
        self.log_text.insert("end", line + "\n", tag)
        if int(self.log_text.index("end-1c").split(".")[0]) > 5000:
            self.log_text.delete("1.0", "200.0")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    @staticmethod
    def _sec_name(eng, code):
        """优先取数据源中的证券名称(真实数据源含全市场),回退到内置表。"""
        try:
            return eng.ds.security_info(code)["display_name"]
        except Exception:
            return simdata.SEC_NAMES.get(code, "")

    def _update_positions(self, eng):
        for i in self.pos_tree.get_children():
            self.pos_tree.delete(i)
        for code, p in eng.positions.items():
            if p.total_amount <= 0:
                continue
            price = eng.get_price(code)
            self.pos_tree.insert("", "end", values=(
                code, self._sec_name(eng, code),
                p.total_amount, p.amount, p.frozen,
                f"{p.cost:.3f}", f"{price:.3f}", f"{p.total_amount * price:,.0f}"))

    def _update_orders(self, eng):
        for i in self.order_tree.get_children():
            self.order_tree.delete(i)
        for o in eng.orders[-300:]:
            self.order_tree.insert("", "end", tags=(o.side,), values=(
                o.time.strftime("%m-%d %H:%M"), "买入" if o.side == "buy" else "卖出",
                o.code, o.amount, f"{o.price:.3f}", o.status))

    def _draw_equity(self):
        eng = self.session.engine
        if eng is None:
            return
        points = list(eng.daily_equity)
        c = self.canvas
        c.delete("all")
        # 窗口尚未布局时 winfo 尺寸为 1,用后备尺寸先画,布局后会触发重画
        w, h = c.winfo_width(), c.winfo_height()
        if w < 60 or h < 60:
            w, h = 900, 320
            c.config(width=w, height=h)
        if not points:
            c.create_text(w // 2, h // 2, text="运行后显示资产曲线", fill=GRAY)
            return

        pad_l, pad_r, pad_t, pad_b = 66, 24, 22, 36
        vals = [v for _, v in points]
        vmin, vmax = min(vals), max(vals)
        if vmax - vmin < 1e-9:
            vmax = vmin + 1.0
        n = len(points)

        def X(i):
            return pad_l + (w - pad_l - pad_r) * (i / max(n - 1, 1))

        def Y(v):
            return pad_t + (h - pad_t - pad_b) * (1 - (v - vmin) / (vmax - vmin))

        for k in range(5):
            v = vmin + (vmax - vmin) * k / 4
            y = Y(v)
            c.create_line(pad_l, y, w - pad_r, y, fill="#e8e8e8")
            c.create_text(pad_l - 6, y, text=f"{v:,.0f}", anchor="e", fill=GRAY,
                          font=("Microsoft YaHei UI", 8))
        for idx in sorted({0, (n - 1) // 2, n - 1}):
            c.create_text(X(idx), h - pad_b + 16, text=points[idx][0].strftime("%m-%d"),
                          fill=GRAY, font=("Microsoft YaHei UI", 8))

        baseline = eng.start_capital
        if vmin <= baseline <= vmax:
            c.create_line(pad_l, Y(baseline), w - pad_r, Y(baseline),
                          fill="#999999", dash=(4, 3))

        coords = []
        for i, (_, v) in enumerate(points):
            coords += [X(i), Y(v)]
        if n > 1:
            c.create_polygon(coords + [X(n - 1), h - pad_b, X(0), h - pad_b],
                             fill="#dbeaf7", outline="")
        c.create_line(*coords, fill=ACCENT, width=2)
        lx, ly = X(n - 1), Y(vals[-1])
        c.create_oval(lx - 3, ly - 3, lx + 3, ly + 3, fill=ACCENT, outline="")

        ret = vals[-1] / baseline - 1
        peak, mdd = 0.0, 0.0
        for v in vals:
            peak = max(peak, v)
            mdd = min(mdd, v / peak - 1)
        color = RED if ret < 0 else GREEN
        self.eq_label.config(
            text=(f"期末资产 {vals[-1]:,.2f}    收益率 {ret*100:+.2f}%    "
                  f"最大回撤 {mdd*100:.2f}%    交易日 {n} 天"),
            foreground=color)

    def _show_report(self, eng):
        pf = eng._portfolio()
        vals = [v for _, v in eng.daily_equity]
        peak, mdd = 0.0, 0.0
        for v in vals:
            peak = max(peak, v)
            mdd = min(mdd, v / peak - 1)
        days = eng.daily_equity
        lines = [
            "================ 模拟统计 ================",
            f"运行区间   : {days[0][0]} ~ {days[-1][0]} (共 {len(days)} 个交易日)"
            if days else "运行区间   : 无交易日",
            f"初始资金   : {eng.start_capital:,.2f}",
            f"期末总资产 : {pf.portfolio_value:,.2f}",
            f"  现金     : {eng.cash:,.2f}",
            f"  持仓市值 : {pf.positions_value:,.2f}",
            f"总收益率   : {pf.returns*100:+.2f}%",
            f"最大回撤   : {mdd*100:.2f}%",
            f"成交笔数   : {len(eng.orders)}",
            "",
            "-------------- 期末持仓 --------------",
        ]
        for code, p in eng.positions.items():
            if p.total_amount:
                price = eng.get_price(code)
                pnl = (price - p.cost) * p.total_amount
                lines.append(
                    f"{code}  {self._sec_name(eng, code):<10} "
                    f"{p.total_amount:>8} 股  成本 {p.cost:.3f}  现价 {price:.3f}  "
                    f"市值 {p.value:>12,.0f}  浮盈 {pnl:+,.0f}")
        if not any(p.total_amount for p in eng.positions.values()):
            lines.append("(空仓)")
        lines.append("========================================")
        text = "\n".join(lines)
        self.stat_text.config(state="normal")
        self.stat_text.delete("1.0", "end")
        self.stat_text.insert("1.0", text)
        self.stat_text.config(state="disabled")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
