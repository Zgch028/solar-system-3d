#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成分享卡片预览图 assets/preview.png（1200 × 630）。

数据不是手画的：右侧八大行星的 J2000 日心黄经与日距直接读自 golden file
reference.json（PyEphem/VSOP87 独立星历），与页面 16 组误差表同源，可复核。
背景星点与纹理为程序化生成（固定种子），非真实影像。

用法：python3 build/make_preview.py
依赖：Pillow（仅构建期，页面运行时不需要；本机/联网机器均可重跑）
"""
import json
import math
import pathlib
import random

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets/preview.png'
REF = json.loads((ROOT / 'reference.json').read_text(encoding='utf-8'))
W, H = 1200, 630
NAVY, NAVY2 = (5, 11, 23), (18, 41, 74)
TEAL, AMBER, INK, MUTED = (46, 217, 195), (245, 166, 35), (234, 242, 250), (157, 179, 204)

FONTS = [
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
]
font_path = next((p for p in FONTS if pathlib.Path(p).exists()), None)
if not font_path:
    raise SystemExit('未找到可渲染中文的字体；请安装 Hiragino / 文泉驿等中文字体后重跑。')


def f(size):
    return ImageFont.truetype(font_path, size)


COLORS = [0xA9A29B, 0xE8C98A, 0x3D7FD1, 0xC1613C,
          0xD9B48C, 0xE2CE9A, 0x8FD3DE, 0x3F63C8]
NAMES = ['水星', '金星', '地球', '火星', '木星', '土星', '天王星', '海王星']
# 半长轴 a（AU）：JPL Standish 1800–2050 表 J2000 值，与页面 TABLES 逐字一致。
# 轨道圆用 a、行星点用当前日距 r，两者之差正是椭圆轨道近日/远日点的视觉体现。
A_AU = [0.38709927, 0.72333566, 1.00000261, 1.52371034,
        5.20288700, 9.53667594, 19.18916464, 30.06992276]


def rgb(hex_color):
    return ((hex_color >> 16) & 255, (hex_color >> 8) & 255, hex_color & 255)


# 背景：径向深蓝 + 固定种子星点
mask = ImageOps.invert(Image.radial_gradient('L').resize((W, H)))
img = Image.composite(Image.new('RGB', (W, H), NAVY2), Image.new('RGB', (W, H), NAVY), mask)
d = ImageDraw.Draw(img)
rng = random.Random(20261106)
for _ in range(240):
    x, y = rng.randrange(W), rng.randrange(H)
    b = int(90 + rng.random() * 150)
    r = 1 if rng.random() < .85 else 2
    d.ellipse((x - r, y - r, x + r, y + r), fill=(b, b, min(255, b + 12)))

# 右侧太阳系：数据来自 reference.json 的 J2000 历元
cx, cy, max_r = 855, 320, 228
epoch = REF['epochs'][0]
assert epoch['label'].startswith('2000-01-01')
den = math.log10(1 + 30.1 / 0.15)


def norm(r):
    return 16 + (max_r - 16) * math.log10(1 + r / 0.15) / den


d.ellipse((cx - max_r - 8, cy - max_r - 8, cx + max_r + 8, cy + max_r + 8),
          outline=(46, 217, 195, 40), width=1)
for i in range(8):
    color = rgb(COLORS[i])
    R = norm(A_AU[i])
    d.ellipse((cx - R, cy - R, cx + R, cy + R),
              outline=tuple(int(c * .45) for c in color), width=1)
for i, p in enumerate(epoch['planets']):
    color = rgb(COLORS[i])
    R = norm(p['rAU'])
    a = math.radians(p['lonJ2000'])
    x, y = cx + R * math.cos(a), cy - R * math.sin(a)
    rr = 4 + min(8, (4879 if i == 0 else 142984 if i == 4 else 50000) / 22000)
    d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=color, outline=INK, width=1)
    d.text((x + rr + 5, y - rr - 3), NAMES[i], font=f(15), fill=INK)

# 太阳
for k in range(6, 0, -1):
    rr = 12 + k * 3
    glow = tuple(int(NAVY2[j] + (AMBER[j] - NAVY2[j]) * (1 - k / 7) * .55) for j in range(3))
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=glow)
d.ellipse((cx - 13, cy - 13, cx + 13, cy + 13), fill=AMBER)
d.text((cx, cy + 26), '太阳', font=f(15), fill=AMBER, anchor='ma')

# 左侧文案
d.rounded_rectangle((52, 62, 530, 568), radius=18, fill=(8, 20, 38), outline=(46, 217, 195), width=1)
d.text((80, 96), '太阳系八大行星', font=f(46), fill=INK)
d.text((80, 156), '动态运转 · 3D 模型', font=f(34), fill=TEAL)
d.text((80, 216), 'JPL Standish 近似根数 + 开普勒椭圆', font=f(19), fill=MUTED)
d.line((80, 258, 500, 258), fill=(46, 217, 195), width=1)
for y, txt, col, size in [
    (282, '16 组独立星历对照  16/16 PASS', TEAL, 23),
    (322, '最大 |Δ黄经| 0.1437°  <  阈值 1°', INK, 19),
    (362, '判卷人 PyEphem / VSOP87 4.2.1', MUTED, 17),
    (414, '无需外网 · 双击可开 · WebGL 静态降级', INK, 19),
    (452, '程序化纹理 · 双尺度显式声明', MUTED, 17),
    (490, 'AI 辅助创作（已标注）', AMBER, 17),
]:
    d.text((80, y), txt, font=f(size), fill=col)
d.text((80, 534), '教学／科普级 · 物理可核验', font=f(16), fill=MUTED)

d.text((52, 592), '数据源：JPL Standish / NASA Fact Sheet / PyEphem VSOP87 · Three.js r160 (MIT) · 轨道=R(a)、行星位置=R(r)、J2000 · 程序化生成',
       font=f(14), fill=MUTED)

img.save(OUT, 'PNG', optimize=True)
print('已生成 %s（%d × %d，%d 字节，字体 %s）' %
      (OUT, W, H, OUT.stat().st_size, pathlib.Path(font_path).name))
print('行星位置取自 reference.json 的 J2000 历元：' + epoch['label'])
