# -*- coding: utf-8 -*-
"""
P3 音频工具箱
- 转换标签页：WAV/常见音频 <-> P3
- 播放标签页：播放 .p3 文件（Opus 流式格式）
P3 格式：每个音频帧 = 4 字节头部 [1字节类型,1字节保留,2字节长度] + Opus 数据
采样率固定 16000Hz，单声道，每帧 60ms。
"""

import os
import sys
import struct
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import opuslib
import soundfile as sf
import scipy.signal as sg
import pyloudnorm as pyln


# ===========================================================================
# 核心编解码逻辑（不变）
# ===========================================================================

def _to_mono(audio):
    if audio.ndim == 2:
        return np.mean(audio, axis=1)
    return audio


def encode_audio_to_opus(input_file, output_file, target_lufs=None, log=None):
    def say(msg):
        if log: log(msg)
        else: print(msg)

    audio, sample_rate = sf.read(input_file, dtype='float32', always_2d=False)
    audio = _to_mono(audio)

    if target_lufs is not None:
        try:
            meter = pyln.Meter(sample_rate)
            current = meter.integrated_loudness(audio)
            if np.isfinite(current):
                audio = pyln.normalize.loudness(audio, current, target_lufs)
                say(f"响度调整: {current:.1f} LUFS -> {target_lufs} LUFS")
            else:
                say("警告: 音频过短，跳过响度调整")
        except Exception as e:
            say(f"警告: 响度调整失败，已跳过: {e}")

    target_sr = 16000
    if sample_rate != target_sr:
        gcd = np.gcd(int(sample_rate), int(target_sr))
        up = int(target_sr) // gcd
        down = int(sample_rate) // gcd
        audio = sg.resample_poly(audio, up, down)
        sample_rate = target_sr

    audio = np.clip(audio, -1.0, 1.0)
    audio = (audio * 32767).astype(np.int16)

    encoder = opuslib.Encoder(sample_rate, 1, opuslib.APPLICATION_AUDIO)
    frame_size = int(sample_rate * 60 / 1000)
    total = max(0, (len(audio) - frame_size) // frame_size + 1)
    done = 0
    with open(output_file, 'wb') as f:
        for i in range(0, len(audio) - frame_size, frame_size):
            frame = audio[i:i + frame_size]
            opus_data = encoder.encode(frame.tobytes(), frame_size=frame_size)
            packet = struct.pack('>BBH', 0, 0, len(opus_data)) + opus_data
            f.write(packet)
            done += 1
            if total and done % 50 == 0:
                say(f"  编码进度: {done * frame_size / len(audio) * 100:.0f}%")
    say(f"完成: {os.path.basename(output_file)}")


def decode_p3_to_audio(input_file, output_file, log=None):
    def say(msg):
        if log: log(msg)
        else: print(msg)

    sample_rate = 16000; channels = 1
    decoder = opuslib.Decoder(sample_rate, channels)
    frame_size = int(sample_rate * 60 / 1000)
    pcm_frames = []

    with open(input_file, "rb") as f:
        while True:
            header = f.read(4)
            if not header or len(header) < 4: break
            _ptype, _reserved, opus_len = struct.unpack(">BBH", header)
            opus_data = f.read(opus_len)
            if len(opus_data) != opus_len: break
            pcm = decoder.decode(opus_data, frame_size)
            pcm_frames.append(np.frombuffer(pcm, dtype=np.int16))

    if not pcm_frames:
        raise ValueError("未找到有效的音频数据")

    pcm_data = np.concatenate(pcm_frames)
    sf.write(output_file, pcm_data, sample_rate, subtype="PCM_16")
    say(f"完成: {os.path.basename(output_file)}")


def play_p3_file(input_file, stop_event=None, pause_event=None, log=None):
    def say(msg):
        if log: log(msg)
        else: print(msg)

    sample_rate = 16000; channels = 1
    decoder = opuslib.Decoder(sample_rate, channels)
    frame_size = int(sample_rate * 60 / 1000)

    import sounddevice as sd
    stream = sd.OutputStream(samplerate=sample_rate, channels=channels, dtype='int16')
    stream.start()
    try:
        with open(input_file, 'rb') as f:
            say(f"正在播放: {os.path.basename(input_file)}")
            while True:
                if stop_event and stop_event.is_set(): break
                if pause_event and pause_event.is_set():
                    import time; time.sleep(0.05); continue
                header = f.read(4)
                if not header or len(header) < 4: break
                _ptype, _reserved, data_len = struct.unpack('>BBH', header)
                opus_data = f.read(data_len)
                if not opus_data or len(opus_data) < data_len: break
                pcm_data = decoder.decode(opus_data, frame_size)
                audio_array = np.frombuffer(pcm_data, dtype=np.int16)
                stream.write(audio_array)
    finally:
        try: stream.stop(); stream.close()
        except Exception: pass
        say("播放结束")


# ===========================================================================
# 配色 / 字体
# ===========================================================================

COLORS = {
    'bg':          '#ffffff',  # 主背景
    'bg2':         '#f5f9fc',  # 次级背景
    'bg_in':       '#fafcfd',  # 输入区
    'panel_bg':    '#ffffff',  # 面板
    'cyan':        '#00acc1',  # 边框/强调
    'cyan_dark':   '#00838f',  # 标题文字
    'cyan_glow':   '#00e5ff',  # 高亮
    'red':         '#e53935',
    'orange':      '#ef6c00',
    'green':       '#2e7d32',
    'txt':         '#1f2933',  # 正文
    'txt2':        '#5a6b80',  # 辅助
    'bdr':         '#cfdde6',  # 边框
    'sep':         '#e3eef4',  # 分隔线
}

FONT      = ('Microsoft YaHei UI', 10)
FONT_BOLD = ('Microsoft YaHei UI', 10, 'bold')
FONT_HD   = ('Microsoft YaHei UI', 11, 'bold')
FONT_S    = ('Microsoft YaHei UI', 9)
FONT_MONO = ('Consolas', 9)


# ===========================================================================
# P3Studio 主应用
# ===========================================================================

class P3Studio:
    def __init__(self, master):
        self.master = master
        master.title("P3 音频工具箱")
        master.geometry("780x700")
        master.minsize(680, 560)
        master.configure(bg=COLORS['bg'])

        self.default_output = self._exedir()
        self.playlist = []
        self.current_index = 0
        self.is_playing = False
        self.is_paused = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

        self._apply_ttk_theme()

        # —— 顶部主标题栏 ——
        self._build_title_bar(master)

        # —— 内容区（Notebook） ——
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.convert_frame = ttk.Frame(self.notebook)
        self.player_frame  = ttk.Frame(self.notebook)
        self.notebook.add(self.convert_frame, text='  ◆  转换  ')
        self.notebook.add(self.player_frame,  text='  ◇  播放  ')

        self.build_convert_tab()
        self.build_player_tab()

    # ----------------------------------------------------------------- utils
    def _exedir(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.abspath(os.path.dirname(__file__))

    def _hex(self, c): return c.lstrip('#')

    # ----------------------------------------------------------------- 标题栏
    def _build_title_bar(self, parent):
        c = COLORS
        bar = tk.Frame(parent, bg=c['bg'])
        bar.pack(fill=tk.X, padx=10, pady=(10, 6))

        # 左侧 logo + 标题
        left = tk.Frame(bar, bg=c['bg'])
        left.pack(side=tk.LEFT)

        # 装饰方块（机甲小标识）
        logo = tk.Frame(left, bg=c['cyan'], width=24, height=24)
        logo.pack(side=tk.LEFT, padx=(0, 8))
        logo.pack_propagate(False)
        tk.Label(logo, text='》', bg=c['cyan'], fg='#ffffff',
                 font=('Microsoft YaHei UI', 12, 'bold')).pack(expand=True)

        tk.Label(left, text='P3 音频工具箱', bg=c['bg'], fg=c['cyan_dark'],
                 font=FONT_HD).pack(side=tk.LEFT)

        tk.Label(bar, text='//  V1.2', bg=c['bg'], fg=c['txt2'],
                 font=FONT_S).pack(side=tk.RIGHT, padx=4)

    # ----------------------------------------------------------------- ttk 主题
    def _apply_ttk_theme(self):
        c = COLORS
        s = ttk.Style()
        s.theme_use('clam')

        # 通用
        s.configure('.',
                    background=c['bg'], foreground=c['txt'],
                    fieldbackground=c['bg_in'], font=FONT,
                    borderwidth=1, relief='flat')

        # Frame
        s.configure('TFrame', background=c['bg'])

        # LabelFrame —— 干净边框 + 青色标题
        s.configure('TLabelframe',
                    background=c['panel_bg'], foreground=c['cyan_dark'],
                    bordercolor=c['cyan'], borderwidth=1,
                    relief='solid', labelmargins=[10, 0, 8, 0],
                    padding=[10, 6, 8, 8])
        s.configure('TLabelframe.Label',
                    background=c['bg'], foreground=c['cyan_dark'],
                    font=FONT_BOLD)

        # Label
        s.configure('TLabel', background=c['bg'], foreground=c['txt'], font=FONT)
        s.configure('Small.TLabel', background=c['bg'], foreground=c['txt2'], font=FONT_S)

        # Section heading (用于各区域标题)
        s.configure('Head.TLabel',
                    background=c['bg'], foreground=c['cyan_dark'],
                    font=FONT_BOLD)

        # Button —— 青色边框 + 浅色填充
        s.configure('TButton',
                    background=c['bg'], foreground=c['cyan_dark'],
                    bordercolor=c['cyan'], borderwidth=1,
                    relief='solid', focusthickness=0,
                    font=FONT, padding=[12, 4])
        s.map('TButton',
              background=[('active', '#e3f6fb'), ('pressed', c['cyan'])],
              foreground=[('active', c['cyan_dark']), ('pressed', '#ffffff')],
              bordercolor=[('active', c['cyan_glow'])])

        # Primary button（action 按钮）
        s.configure('Primary.TButton',
                    background=c['cyan'], foreground='#ffffff',
                    bordercolor=c['cyan_dark'], borderwidth=1,
                    relief='solid', focusthickness=0,
                    font=FONT_BOLD, padding=[14, 5])
        s.map('Primary.TButton',
              background=[('active', c['cyan_dark']), ('pressed', '#006064')],
              foreground=[('active', '#ffffff')])

        # Radiobutton / Checkbutton —— 隐藏默认指示器，使用自己的 widget
        for cls in ('TRadiobutton', 'TCheckbutton'):
            s.configure(cls,
                        background=c['bg'], foreground=c['txt'],
                        font=FONT, focusthickness=0,
                        indicatorcolor=c['bg_in'])
            s.map(cls,
                  foreground=[('selected', c['cyan_dark'])],
                  background=[('active', c['bg'])])

        # Entry
        s.configure('TEntry',
                    fieldbackground=c['bg_in'], foreground=c['txt'],
                    insertcolor=c['cyan_dark'], font=FONT,
                    relief='solid', bordercolor=c['bdr'], borderwidth=1,
                    padding=[6, 4])
        s.map('TEntry', bordercolor=[('focus', c['cyan'])])

        # Notebook
        s.configure('TNotebook',
                    background=c['bg'], borderwidth=0,
                    tabmargins=[8, 0, 8, 0])
        s.configure('TNotebook.Tab',
                    background=c['bg2'], foreground=c['txt2'],
                    font=FONT_BOLD, padding=[18, 8],
                    borderwidth=0)
        s.map('TNotebook.Tab',
              background=[('selected', c['bg'])],
              foreground=[('selected', c['cyan_dark'])])

        # Progressbar
        s.configure('TProgressbar',
                    background=c['cyan'], troughcolor=c['bg_in'],
                    bordercolor=c['bdr'], borderwidth=1,
                    lightcolor=c['cyan'], darkcolor=c['cyan'])

        # Scrollbar
        s.configure('Vertical.TScrollbar',
                    background=c['bg2'], troughcolor=c['bg'],
                    bordercolor=c['bdr'], arrowcolor=c['cyan_dark'],
                    borderwidth=1)

    # ==================================================================
    # 转换标签页
    # ==================================================================
    def build_convert_tab(self):
        f = self.convert_frame
        c = COLORS
        self.mode = tk.StringVar(value='audio_to_p3')
        self.output_dir = tk.StringVar(value=self.default_output)
        self.enable_loudnorm = tk.BooleanVar(value=True)
        self.target_lufs = tk.DoubleVar(value=-16.0)

        # 布局权重分配：
        #   row 0 模式（固定）
        #   row 1 响度（固定）
        #   row 2 文件列表（可扩展）
        #   row 3 输出目录（固定）
        #   row 4 日志（固定高度）
        #   row 5 操作按钮（固定）
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(2, weight=1)  # 文件列表占扩展空间

        # ---- 1. 转换模式 ----
        box1 = ttk.LabelFrame(f, text='  转换模式  ')
        box1.grid(row=0, column=0, padx=0, pady=(0, 8), sticky='ew')
        rb1 = tk.Frame(box1, bg=c['bg'])
        rb1.pack(fill=tk.X, padx=6, pady=4)
        self._rb_audio = self._make_radio(rb1, '音频  →  P3', 'audio_to_p3',
                                           self.mode, True, self.toggle_settings)
        self._rb_audio.pack(side=tk.LEFT, padx=(4, 16))
        self._rb_p3 = self._make_radio(rb1, 'P3  →  音频', 'p3_to_audio',
                                        self.mode, False, self.toggle_settings)
        self._rb_p3.pack(side=tk.LEFT, padx=4)

        # ---- 2. 响度设置 ----
        box2 = ttk.LabelFrame(f, text='  响度调整  ')
        box2.grid(row=1, column=0, padx=0, pady=(0, 8), sticky='ew')
        ln = tk.Frame(box2, bg=c['bg'])
        ln.pack(fill=tk.X, padx=6, pady=4)
        self._cb_loud = self._make_check(ln, '启用响度调整',
                                          self.enable_loudnorm, True)
        self._cb_loud.pack(side=tk.LEFT, padx=(4, 8))
        luf_entry = ttk.Entry(ln, textvariable=self.target_lufs, width=6, justify='center')
        luf_entry.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Label(ln, text='LUFS （TTS 音频建议关闭）',
                  style='Small.TLabel').pack(side=tk.LEFT, padx=4)

        # ---- 3. 输入文件列表（主区域） ----
        box3 = ttk.LabelFrame(f, text='  输入文件  ')
        box3.grid(row=2, column=0, padx=0, pady=(0, 8), sticky='nsew')
        box3.grid_rowconfigure(2, weight=1)
        box3.grid_columnconfigure(0, weight=1)

        bar3 = tk.Frame(box3, bg=c['bg'])
        bar3.grid(row=0, column=0, sticky='ew', pady=(2, 2))
        ttk.Button(bar3, text='添加文件', command=self.add_files, width=10
                   ).pack(side=tk.LEFT, padx=(2, 4))
        ttk.Button(bar3, text='移除选中', command=self.remove_selected, width=10
                   ).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar3, text='清空列表', command=self.clear_files, width=10
                   ).pack(side=tk.LEFT, padx=4)
        ttk.Label(bar3, text='支持 .wav .flac .ogg', style='Small.TLabel'
                  ).pack(side=tk.RIGHT, padx=6)

        # 自带滚动条的 Listbox
        list_wrap = tk.Frame(box3, bg=c['bdr'], bd=1, relief='solid')
        list_wrap.grid(row=2, column=0, sticky='nsew', pady=(2, 4))
        list_wrap.grid_rowconfigure(0, weight=1)
        list_wrap.grid_columnconfigure(0, weight=1)

        self.file_list = tk.Listbox(list_wrap, selectmode=tk.EXTENDED,
            bg=c['bg_in'], fg=c['txt'], font=FONT,
            relief='flat', bd=0, highlightthickness=0,
            selectbackground=c['cyan'], selectforeground='#ffffff',
            activestyle='none')
        self.file_list.grid(row=0, column=0, sticky='nsew', padx=1, pady=1)
        sb1 = ttk.Scrollbar(list_wrap, orient='vertical',
                            command=self.file_list.yview)
        sb1.grid(row=0, column=1, sticky='ns')
        self.file_list.config(yscrollcommand=sb1.set)

        # ---- 4. 输出目录 ----
        box4 = ttk.LabelFrame(f, text='  输出目录  ')
        box4.grid(row=3, column=0, padx=0, pady=(0, 8), sticky='ew')
        out_row = tk.Frame(box4, bg=c['bg'])
        out_row.pack(fill=tk.X, padx=6, pady=4)
        ttk.Entry(out_row, textvariable=self.output_dir
                  ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 6))
        ttk.Button(out_row, text='浏览…', command=self.browse_output, width=8
                   ).pack(side=tk.LEFT, padx=(0, 2))

        # ---- 5. 日志 ----
        box5 = ttk.LabelFrame(f, text='  终端日志  ')
        box5.grid(row=4, column=0, padx=0, pady=(0, 8), sticky='nsew')
        box5.grid_rowconfigure(0, weight=1)
        box5.grid_columnconfigure(0, weight=1)
        box5.configure(height=150)
        box5.grid_propagate(False)

        log_wrap = tk.Frame(box5, bg=c['bdr'], bd=1, relief='solid')
        log_wrap.grid(row=0, column=0, sticky='nsew', pady=(2, 4))
        log_wrap.grid_rowconfigure(0, weight=1)
        log_wrap.grid_columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_wrap, height=6, wrap='word',
            bg=c['bg_in'], fg=c['txt'],
            insertbackground=c['cyan_dark'], font=FONT_MONO,
            relief='flat', bd=0, highlightthickness=0, padx=6, pady=4,
            selectbackground=c['cyan'], selectforeground='#ffffff')
        self.log_text.grid(row=0, column=0, sticky='nsew', padx=1, pady=1)
        sb2 = ttk.Scrollbar(log_wrap, orient='vertical',
                            command=self.log_text.yview)
        sb2.grid(row=0, column=1, sticky='ns')
        self.log_text.config(yscrollcommand=sb2.set)

        # ---- 6. 操作按钮 + 进度 ----
        bar6 = tk.Frame(f, bg=c['bg'])
        bar6.grid(row=5, column=0, sticky='ew', pady=(0, 2))
        ttk.Button(bar6, text='▶  开始转换', style='Primary.TButton',
                   command=self.start_convert, width=16
                   ).pack(side=tk.LEFT, padx=(2, 6))
        ttk.Button(bar6, text='打开输出目录', command=self.open_output_dir,
                   width=14).pack(side=tk.LEFT, padx=4)
        self.convert_progress = ttk.Progressbar(bar6, mode='indeterminate',
                                                length=200)
        self.convert_progress.pack(side=tk.RIGHT, padx=6)

    # ==================================================================
    # 播放标签页
    # ==================================================================
    def build_player_tab(self):
        f = self.player_frame
        c = COLORS
        self.loop_playback = tk.BooleanVar(value=False)

        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(1, weight=1)  # 播放列表占扩展空间

        # ---- 1. 播放列表 ----
        box1 = ttk.LabelFrame(f, text='  播放列表  ')
        box1.grid(row=1, column=0, padx=0, pady=(0, 12), sticky='nsew')
        box1.grid_rowconfigure(1, weight=1)
        box1.grid_columnconfigure(0, weight=1)

        bar = tk.Frame(box1, bg=c['bg'])
        bar.grid(row=0, column=0, sticky='ew', pady=(2, 2))
        ttk.Button(bar, text='添加文件', command=self.player_add, width=10
                   ).pack(side=tk.LEFT, padx=(2, 4))
        ttk.Button(bar, text='移除选中', command=self.player_remove, width=10
                   ).pack(side=tk.LEFT, padx=4)
        self._cb_loop = self._make_check(bar, '循环播放',
                                          self.loop_playback, False)
        self._cb_loop.pack(side=tk.RIGHT, padx=6)

        pl_wrap = tk.Frame(box1, bg=c['bdr'], bd=1, relief='solid')
        pl_wrap.grid(row=1, column=0, sticky='nsew', pady=(2, 4))
        pl_wrap.grid_rowconfigure(0, weight=1)
        pl_wrap.grid_columnconfigure(0, weight=1)

        self.playlist_listbox = tk.Listbox(pl_wrap, selectmode=tk.SINGLE,
            bg=c['bg_in'], fg=c['txt'], font=FONT,
            relief='flat', bd=0, highlightthickness=0,
            selectbackground=c['cyan'], selectforeground='#ffffff',
            activestyle='none')
        self.playlist_listbox.grid(row=0, column=0, sticky='nsew', padx=1, pady=1)
        sb3 = ttk.Scrollbar(pl_wrap, orient='vertical',
                            command=self.playlist_listbox.yview)
        sb3.grid(row=0, column=1, sticky='ns')
        self.playlist_listbox.config(yscrollcommand=sb3.set)

        # ---- 2. 控制按钮 + 状态 ----
        box2 = ttk.LabelFrame(f, text='  播放控制  ')
        box2.grid(row=2, column=0, padx=0, pady=(0, 4), sticky='ew')

        ctrl_row = tk.Frame(box2, bg=c['bg'])
        ctrl_row.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(ctrl_row, text='▶  播放', style='Primary.TButton',
                   command=self.player_play, width=12
                   ).pack(side=tk.LEFT, padx=(2, 6))
        ttk.Button(ctrl_row, text='⏸  暂停',
                   command=self.player_pause, width=12
                   ).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl_row, text='■  停止',
                   command=self.player_stop, width=12
                   ).pack(side=tk.LEFT, padx=4)

        self.status_label = tk.Label(ctrl_row, text=' ◆  系统待命',
            bg=c['bg'], fg=c['cyan_dark'], font=FONT_BOLD)
        self.status_label.pack(side=tk.RIGHT, padx=8)

    # ==================================================================
    # 自定义指示器（菱形 = radio，六边形 = checkbox）
    # ==================================================================
    def _make_radio(self, parent, text, value, variable, checked, command):
        """单选框：自定义菱形指示器，替代默认圆形。"""
        c = COLORS
        img_on, img_off = self._diamond_icons()
        var = variable

        # 用 tk.Label + 绑定 click 模拟 radio
        wrap = tk.Frame(parent, bg=c['bg'])
        indicator = tk.Label(wrap, image=img_on if checked else img_off,
                             bg=c['bg'], bd=0, highlightthickness=0)
        indicator.pack(side=tk.LEFT, padx=(2, 6))
        label = tk.Label(wrap, text=text, bg=c['bg'],
                         fg=c['cyan_dark'] if checked else c['txt'],
                         font=FONT, cursor='hand2')
        label.pack(side=tk.LEFT)

        def pick(_=None):
            var.set(value)
            if command: command()
            # 刷新所有 radio 视觉
            for child in parent.winfo_children():
                if child is wrap: continue
                if isinstance(child, tk.Frame):
                    for sub in child.winfo_children():
                        if isinstance(sub, tk.Label) and sub.cget('image'):
                            sub.config(image=img_off)
                            # 兄弟 label 也恢复
                    for sub in child.winfo_children():
                        if isinstance(sub, tk.Label) and not sub.cget('image'):
                            sub.config(fg=c['txt'])
            indicator.config(image=img_on)
            label.config(fg=c['cyan_dark'])

        indicator.bind('<Button-1>', pick)
        label.bind('<Button-1>', pick)
        wrap._set_checked = lambda v: (indicator.config(image=img_on if v else img_off),
                                       label.config(fg=c['cyan_dark'] if v else c['txt']))
        return wrap

    def _make_check(self, parent, text, variable, checked):
        """多选框：自定义六边形指示器。"""
        c = COLORS
        img_on, img_off = self._hex_icons()

        wrap = tk.Frame(parent, bg=c['bg'])
        indicator = tk.Label(wrap, image=img_on if checked else img_off,
                             bg=c['bg'], bd=0, highlightthickness=0)
        indicator.pack(side=tk.LEFT, padx=(2, 6))
        label = tk.Label(wrap, text=text, bg=c['bg'],
                         fg=c['cyan_dark'] if checked else c['txt'],
                         font=FONT, cursor='hand2')
        label.pack(side=tk.LEFT)

        var = variable

        def toggle(_=None):
            new_state = not var.get()
            var.set(new_state)
            indicator.config(image=img_on if new_state else img_off)
            label.config(fg=c['cyan_dark'] if new_state else c['txt'])

        indicator.bind('<Button-1>', toggle)
        label.bind('<Button-1>', toggle)
        return wrap

    # ---- 像素图标（缓存在实例上） ----
    def _diamond_icons(self):
        if not hasattr(self, '_diamond_on'):
            self._diamond_on, self._diamond_off = _make_diamond_pair()
        return self._diamond_on, self._diamond_off

    def _hex_icons(self):
        if not hasattr(self, '_hex_on'):
            self._hex_on, self._hex_off = _make_hex_pair()
        return self._hex_on, self._hex_off

    # ==================================================================
    # 转换逻辑
    # ==================================================================
    def log(self, msg):
        self.log_text.insert(tk.END, msg + '\n')
        self.log_text.see(tk.END)

    def add_files(self):
        paths = filedialog.askopenfilenames(title='选择音频文件',
            filetypes=[('音频文件', '*.wav *.flac *.ogg *.mp3'),
                       ('所有文件', '*.*')])
        for p in paths:
            if p not in self.file_list.get(0, tk.END):
                self.file_list.insert(tk.END, p)

    def clear_files(self):
        self.file_list.delete(0, tk.END)

    def remove_selected(self):
        for i in reversed(self.file_list.curselection()):
            self.file_list.delete(i)

    def browse_output(self):
        d = filedialog.askdirectory(title='选择输出目录')
        if d:
            self.output_dir.set(d)

    def open_output_dir(self):
        d = self.output_dir.get()
        if os.path.isdir(d):
            os.startfile(d)

    def toggle_settings(self):
        if self.mode.get() == 'p3_to_audio':
            self.enable_loudnorm.set(False)
            self._cb_loud._set_checked(False)
        else:
            self._cb_loud._set_checked(True)
            self.enable_loudnorm.set(True)

    def start_convert(self):
        paths = list(self.file_list.get(0, tk.END))
        if not paths:
            messagebox.showwarning('提示', '请先添加文件！')
            return
        out_dir = self.output_dir.get()
        if not os.path.isdir(out_dir):
            messagebox.showwarning('提示', '输出目录不存在！')
            return
        self.master.config(cursor='watch')
        self.convert_progress.start()
        threading.Thread(target=self._run_convert, args=(paths, out_dir),
                         daemon=True).start()

    def _run_convert(self, paths, out_dir):
        try:
            m = self.mode.get()
            for i, p in enumerate(paths, 1):
                if not os.path.isfile(p):
                    self.log(f"[跳过] 文件不存在: {p}")
                    continue
                base = os.path.splitext(os.path.basename(p))[0]
                if m == 'audio_to_p3':
                    tgt_lufs = self.target_lufs.get() if self.enable_loudnorm.get() else None
                    out = os.path.join(out_dir, base + '.p3')
                    self.log(f"[{i}/{len(paths)}] 编码: {os.path.basename(p)}")
                    try:
                        encode_audio_to_opus(p, out, target_lufs=tgt_lufs, log=self.log)
                    except Exception as e:
                        self.log(f"  !! 编码失败: {e}")
                else:
                    out = os.path.join(out_dir, base + '.wav')
                    self.log(f"[{i}/{len(paths)}] 解码: {os.path.basename(p)}")
                    try:
                        decode_p3_to_audio(p, out, log=self.log)
                    except Exception as e:
                        self.log(f"  !! 解码失败: {e}")
            self.log('全部完成。')
        finally:
            self.master.after(0, lambda: self.master.config(cursor=''))
            self.master.after(0, self.convert_progress.stop)

    # ==================================================================
    # 播放逻辑
    # ==================================================================
    def player_add(self):
        paths = filedialog.askopenfilenames(title='选择 P3 文件',
            filetypes=[('P3 文件', '*.p3'), ('所有文件', '*.*')])
        for p in paths:
            if p not in self.playlist:
                self.playlist.append(p)
                self.playlist_listbox.insert(tk.END, os.path.basename(p))

    def player_remove(self):
        sel = self.playlist_listbox.curselection()
        if not sel: return
        i = sel[0]
        del self.playlist[i]
        self.playlist_listbox.delete(i)

    def player_set_status(self, text, color_key='cyan'):
        color_map = {'cyan': COLORS['cyan_dark'], 'green': COLORS['green'],
                     'orange': COLORS['orange'], 'red': COLORS['red']}
        self.status_label.config(
            text=text, fg=color_map.get(color_key, COLORS['txt']))

    def player_play(self):
        if not self.playlist:
            messagebox.showwarning('警告', '播放列表为空！')
            return
        if self.is_paused:
            self.is_paused = False
            self.pause_event.clear()
            name = os.path.basename(self.playlist[self.current_index])
            self.player_set_status(f'▶  {name}', 'green')
            return
        if self.is_playing:
            return
        self.is_playing = True
        self.stop_event.clear()
        self.pause_event.clear()
        sel = self.playlist_listbox.curselection()
        self.current_index = sel[0] if sel else 0
        threading.Thread(target=self._player_run, daemon=True).start()
        name = os.path.basename(self.playlist[self.current_index])
        self.player_set_status(f'▶  {name}', 'green')

    def player_pause(self):
        if not self.is_playing: return
        self.is_paused = True
        self.pause_event.set()
        self.player_set_status('⏸  播放已暂停', 'orange')

    def player_stop(self):
        if not self.is_playing: return
        self.is_playing = False
        self.is_paused = False
        self.stop_event.set()
        self.pause_event.clear()
        self.player_set_status('■  播放已停止', 'red')

    def _player_run(self):
        idx = self.current_index
        while True:
            if self.stop_event.is_set(): break
            p = self.playlist[idx]
            try:
                play_p3_file(p, stop_event=self.stop_event,
                             pause_event=self.pause_event)
            except Exception as e:
                self.master.after(0, lambda: self.player_set_status(
                    f'播放出错: {e}', 'red'))
                break
            if not self.is_playing or self.stop_event.is_set():
                break
            if self.loop_playback.get():
                idx = (idx + 1) % len(self.playlist)
                self.current_index = idx
                name = os.path.basename(self.playlist[idx])
                self.master.after(0, lambda: self.player_set_status(
                    f'▶  {name}', 'green'))
            else:
                break
        if not self.loop_playback.get():
            self.is_playing = False
            self.master.after(0, lambda: self.player_set_status(
                '■  播放已停止', 'red'))


# ===========================================================================
# 像素图标生成
# ===========================================================================

def _make_diamond_pair():
    """返回 (on, off) 两个 PhotoImage 菱形图标。"""
    sz = 14; h = sz // 2
    img_on  = tk.PhotoImage(width=sz, height=sz)
    img_off = tk.PhotoImage(width=sz, height=sz)
    ON_FILL  = '#00838f'
    ON_LINE  = '#00acc1'
    OFF_LINE = '#90a4ae'
    BG       = '#ffffff'

    for y in range(sz):
        for x in range(sz):
            d = abs(x - h) + abs(y - h)
            # on: 实心菱形 + 青色边框
            if d <= h - 2:
                on_pix  = ON_FILL
                off_pix = '#ffffff'
            elif d == h - 1:
                on_pix  = ON_LINE
                off_pix = '#ffffff'
            elif d == h:
                on_pix  = ON_LINE
                off_pix = OFF_LINE
            else:
                on_pix  = BG
                off_pix = BG
            img_on.put('{#%s}' % on_pix.lstrip('#'), (x, y))
            img_off.put('{#%s}' % off_pix.lstrip('#'), (x, y))
    return img_on, img_off


def _make_hex_pair():
    """返回 (on, off) 两个 PhotoImage 六边形图标。"""
    sz = 14; h = sz // 2
    img_on  = tk.PhotoImage(width=sz, height=sz)
    img_off = tk.PhotoImage(width=sz, height=sz)
    ON_FILL  = '#00838f'
    ON_LINE  = '#00acc1'
    OFF_LINE = '#90a4ae'
    BG       = '#ffffff'

    for y in range(sz):
        for x in range(sz):
            # 六边形判定
            dx = abs(x - h); dy = abs(y - h)
            in_hex = (dx * 2 + dy) <= h + 1
            border = (dx * 2 + dy) == h + 2
            if in_hex:
                on_pix  = ON_FILL
                off_pix = '#ffffff'
            elif border:
                on_pix  = ON_LINE
                off_pix = OFF_LINE
            else:
                on_pix  = BG
                off_pix = BG
            img_on.put('{#%s}' % on_pix.lstrip('#'), (x, y))
            img_off.put('{#%s}' % off_pix.lstrip('#'), (x, y))
    return img_on, img_off


# ===========================================================================
# 入口
# ===========================================================================

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        out_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
        os.makedirs(out_dir, exist_ok=True)

        import tempfile
        sample_rate = 16000
        duration = 0.96
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        audio = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
        wav_tmp = os.path.join(tempfile.gettempdir(), 'selftest_src.wav')
        sf.write(wav_tmp, audio, sample_rate, subtype='PCM_16')

        p3_out = os.path.join(out_dir, 'selftest.p3')
        encode_audio_to_opus(wav_tmp, p3_out, target_lufs=None)
        wav_out = os.path.join(out_dir, 'selftest_out.wav')
        decode_p3_to_audio(p3_out, wav_out)

        info = sf.info(wav_out)
        size = os.path.getsize(p3_out)
        print(f'OK duration={info.duration:.2f}s p3_size={size}B')

        try: os.remove(wav_tmp)
        except: pass
    else:
        root = tk.Tk()
        P3Studio(root)
        root.mainloop()