#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 vendor/three.module.js + OrbitControls.js 合成单个 IIFE 全局脚本。

零依赖：只用 Python 标准库做三处机械改写（ESM import/export → 全局命名空间），
不改写任何库代码本身，产物可与源文件逐行对照；不联网、不需要 npm。

  1. three.module.js 末尾的唯一 export 列表 → window.THREE = { ... }
  2. OrbitControls.js 顶部的 import { ... } from 'three' → const { ... } = window.THREE
  3. OrbitControls.js 末尾的 export { OrbitControls } → window.THREE.OrbitControls = ...

两段各自包在 IIFE 里，避免污染全局；ESM 默认严格模式，IIFE 内显式 "use strict"。
产物：vendor/three.iife.js（不压缩，便于第三方审计）。

用法：python3 build/build_iife.py && node build/verify_bundle.mjs
"""
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
P_THREE = ROOT / 'vendor/three.module.js'
P_CTRL = ROOT / 'vendor/addons/controls/OrbitControls.js'
P_OUT = ROOT / 'vendor/three.iife.js'

three_raw = P_THREE.read_text(encoding='utf-8')
ctrl_raw = P_CTRL.read_text(encoding='utf-8')


def parse_names(block):
    """返回 [(源名, 导出名)]，支持 `A as B`。"""
    out = []
    for item in block.split(','):
        item = item.strip()
        if not item:
            continue
        parts = re.split(r'\s+as\s+', item)
        if len(parts) > 2 or not re.fullmatch(r'[A-Za-z_$][\w$]*', parts[0].strip()):
            raise SystemExit('无法解析导出项：%r' % item)
        out.append((parts[0].strip(), parts[-1].strip()))
    return out


def sha(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]


# ---- 1) Three.js：末尾 export 列表 → 全局命名空间 -------------------------
three = three_raw.rstrip()
m = re.search(r'(?m)^export\s*\{([^}]*)\}\s*;?\s*\Z', three)
if not m:
    raise SystemExit('three.module.js 末尾未找到唯一 export 列表，未修改任何文件。')
names = parse_names(m.group(1))
rev = re.search(r"const REVISION = '([^']+)'", three)
if not rev:
    raise SystemExit('无法读取 REVISION。')
entries = ',\n  '.join(('%s: %s' % (a, b)) if a != b else b for a, b in names)
three_assign = 'window.THREE = {\n  %s\n};\n' % entries
three_body = three[:m.start()] + three_assign

# ---- 2) OrbitControls：import / export 改写 -------------------------------
ctrl = ctrl_raw.rstrip()
mi = re.search(r"(?ms)^import\s*\{([^}]*)\}\s*from\s*['\"]three['\"]\s*;?\s*\n", ctrl)
if not mi:
    raise SystemExit('OrbitControls.js 顶部未找到 import ... from three。')
imp = parse_names(mi.group(1))
destruct = ',\n  '.join(('%s: %s' % (a, b)) if a != b else a for a, b in imp)
ctrl_head = 'const {\n  %s\n} = window.THREE;\n' % destruct

me = re.search(r'(?m)^export\s*\{\s*OrbitControls\s*\}\s*;?\s*\Z', ctrl)
if not me:
    raise SystemExit('OrbitControls.js 末尾未找到 export { OrbitControls }。')
ctrl_body = ctrl[:mi.start()] + ctrl_head + ctrl[mi.end():me.start()] + \
    'window.THREE.OrbitControls = OrbitControls;\n'

if "from 'three'" in ctrl_body or 'from "three"' in ctrl_body:
    raise SystemExit('OrbitControls 中仍有未解析的裸导入。')

# ---- 3) 组装 --------------------------------------------------------------
banner = (
    '/* three.iife.js — 由 build/build_iife.py 生成，请勿手工编辑\n'
    ' * 输入：vendor/three.module.js (Three.js r%s, MIT)\n'
    ' *       vendor/addons/controls/OrbitControls.js (MIT)\n'
    ' * 方式：零依赖机械改写 3 处模块语法，库代码本身逐字保留；两段各自 IIFE 包裹\n'
    ' * 复现：python3 build/build_iife.py && node build/verify_bundle.mjs\n'
    ' * 许可：MIT，全文见 vendor/THREE-LICENSE.txt\n'
    ' * 源 sha256 前 16 位：three=%s controls=%s\n'
    ' */\n' % (rev.group(1), sha(three_raw), sha(ctrl_raw))
)

out = (banner +
       '(function(){\n"use strict";\n' + three_body + '\n})();\n' +
       '(function(){\n"use strict";\n' + ctrl_body + '\n})();\n')
P_OUT.write_text(out, encoding='utf-8')

print('已生成：%s（%d 字节）' % (P_OUT, len(out.encode('utf-8'))))
print('Three.js r%s，导出 %d 项；OrbitControls 解构 %d 项' %
      (rev.group(1), len(names), len(imp)))
print('源文件 sha256 前 16 位：three=%s controls=%s' % (sha(three_raw), sha(ctrl_raw)))
print('下一步：node --check vendor/three.iife.js && node build/verify_bundle.mjs')
