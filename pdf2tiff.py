# -*- coding: utf-8 -*-
"""PDF 转 TIFF 桌面小工具

支持：
- 选择一个或多个 PDF 文件进行转换
- 可设置 DPI、色彩模式（彩色/灰度/黑白）、是否合并为单个多页 TIFF
- 转换进度实时显示
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:
    import fitz  # 旧版 PyMuPDF
from PIL import Image

DPI_OPTIONS = [72, 150, 200, 300, 400, 600]
COLOR_MODES = {"彩色": "RGB", "灰度": "L", "黑白": "1"}


class Pdf2TiffApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PDF 转 TIFF 转换器")
        self.root.geometry("560x480")
        self.root.minsize(520, 420)

        self.pdf_files = []
        self.converting = False

        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # 文件选择区
        frame_files = ttk.LabelFrame(self.root, text="1. 选择 PDF 文件")
        frame_files.pack(fill="x", **pad)

        self.listbox = tk.Listbox(frame_files, height=6, selectmode=tk.EXTENDED)
        self.listbox.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=8)

        btn_bar = ttk.Frame(frame_files)
        btn_bar.pack(side="left", fill="y", padx=4, pady=8)
        ttk.Button(btn_bar, text="添加文件", command=self.add_files).pack(fill="x", pady=2)
        ttk.Button(btn_bar, text="移除选中", command=self.remove_selected).pack(fill="x", pady=2)
        ttk.Button(btn_bar, text="清空列表", command=self.clear_list).pack(fill="x", pady=2)

        # 参数设置区
        frame_opts = ttk.LabelFrame(self.root, text="2. 转换设置")
        frame_opts.pack(fill="x", **pad)

        ttk.Label(frame_opts, text="分辨率 (DPI):").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.dpi_var = tk.IntVar(value=200)
        ttk.Combobox(
            frame_opts, textvariable=self.dpi_var, values=DPI_OPTIONS,
            width=8, state="readonly",
        ).grid(row=0, column=1, sticky="w")

        ttk.Label(frame_opts, text="色彩模式:").grid(row=0, column=2, sticky="w", padx=(24, 8))
        self.color_var = tk.StringVar(value="彩色")
        ttk.Combobox(
            frame_opts, textvariable=self.color_var, values=list(COLOR_MODES.keys()),
            width=8, state="readonly",
        ).grid(row=0, column=3, sticky="w")

        self.merge_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame_opts, text="每个 PDF 合并为一个多页 TIFF（不勾选则每页一个文件）",
            variable=self.merge_var,
        ).grid(row=1, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 8))

        # 输出目录
        frame_out = ttk.LabelFrame(self.root, text="3. 输出目录")
        frame_out.pack(fill="x", **pad)
        self.out_var = tk.StringVar(value="")
        ttk.Entry(frame_out, textvariable=self.out_var).pack(
            side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        ttk.Button(frame_out, text="浏览…", command=self.choose_out_dir).pack(side="left", padx=(4, 8), pady=8)

        # 转换按钮 + 进度
        frame_run = ttk.Frame(self.root)
        frame_run.pack(fill="x", **pad)
        self.convert_btn = ttk.Button(frame_run, text="开始转换", command=self.start_convert)
        self.convert_btn.pack(side="left")

        self.progress = ttk.Progressbar(frame_run, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(12, 0))

        # 日志
        frame_log = ttk.LabelFrame(self.root, text="转换日志")
        frame_log.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(frame_log, height=8, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

    # ---------------- 文件管理 ----------------
    def add_files(self):
        files = filedialog.askopenfilenames(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        for f in files:
            if f not in self.pdf_files:
                self.pdf_files.append(f)
                self.listbox.insert("end", f)

    def remove_selected(self):
        for idx in reversed(self.listbox.curselection()):
            self.listbox.delete(idx)
            del self.pdf_files[idx]

    def clear_list(self):
        self.listbox.delete(0, "end")
        self.pdf_files.clear()

    def choose_out_dir(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.out_var.set(d)

    def log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ---------------- 转换 ----------------
    def start_convert(self):
        if self.converting:
            return
        if not self.pdf_files:
            messagebox.showwarning("提示", "请先添加 PDF 文件")
            return
        out_dir = self.out_var.get().strip()
        if not out_dir:
            messagebox.showwarning("提示", "请选择输出目录")
            return
        os.makedirs(out_dir, exist_ok=True)

        self.converting = True
        self.convert_btn.configure(state="disabled")
        self.progress.configure(value=0, maximum=len(self.pdf_files))

        threading.Thread(target=self._convert_worker, args=(out_dir,), daemon=True).start()

    def _convert_worker(self, out_dir: str):
        dpi = self.dpi_var.get()
        mode = COLOR_MODES[self.color_var.get()]
        merge = self.merge_var.get()
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        ok, fail = 0, 0
        try:
            for i, pdf_path in enumerate(self.pdf_files):
                name = os.path.splitext(os.path.basename(pdf_path))[0]
                try:
                    doc = fitz.open(pdf_path)
                    images = []
                    for page in doc:
                        pix = page.get_pixmap(matrix=mat, alpha=False)
                        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                        if mode != "RGB":
                            img = img.convert(mode)
                        images.append(img)

                    if merge:
                        out_path = os.path.join(out_dir, name + ".tiff")
                        images[0].save(
                            out_path, format="TIFF", save_all=True,
                            append_images=images[1:], compression="tiff_lzw",
                            resolution=dpi, resolutionunit=2,
                        )
                        self.log(f"✔ {os.path.basename(pdf_path)} → {out_path}（{len(images)} 页）")
                    else:
                        stem = os.path.join(out_dir, name)
                        for idx, img in enumerate(images, 1):
                            img.save(f"{stem}_第{idx:03d}页.tiff", format="TIFF",
                                     compression="tiff_lzw", resolution=dpi, resolutionunit=2)
                        self.log(f"✔ {os.path.basename(pdf_path)} → 拆分为 {len(images)} 个 TIFF")
                    doc.close()
                    ok += 1
                except Exception as e:
                    fail += 1
                    self.log(f"✘ {os.path.basename(pdf_path)} 转换失败：{e}")
                self.progress.configure(value=i + 1)
        finally:
            self.root.after(0, self._convert_done, ok, fail)

    def _convert_done(self, ok: int, fail: int):
        self.converting = False
        self.convert_btn.configure(state="normal")
        self.log(f"完成：成功 {ok} 个，失败 {fail} 个")
        if fail == 0:
            messagebox.showinfo("完成", f"转换完成！共成功 {ok} 个文件。")
        else:
            messagebox.showwarning("完成", f"转换结束：成功 {ok} 个，失败 {fail} 个，详情见日志。")


def main():
    root = tk.Tk()
    Pdf2TiffApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
