#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成干净、自洽、可复核的 GitHub Pages 发布目录 publish/。

只复制白名单文件（不含构建缓存、node_modules、临时文件），并补 .nojekyll。
发布目录刻意保留「源文件 + 构建脚本 + golden file + 校验脚本」全链条：
这个作品的卖点是第三方可复核，而不是体积最小。

用法：python3 build/make_publish.py && python3 verify_compat.py --root publish
"""
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'publish'

FILES = [
    'index.html',
    '太阳系八大行星动态运转.html',
    'assets/preview.png',
    'vendor/three.iife.js',
    'vendor/three.module.js',
    'vendor/addons/controls/OrbitControls.js',
    'vendor/THREE-LICENSE.txt',
    'reference.json',
    'reference_ephem.py',
    'sync_reference.py',
    'verify.mjs',
    'verify_page.py',
    'verify_compat.py',
    'SOURCES.md',
    'README.md',
    'build/build_iife.py',
    'build/verify_bundle.mjs',
    'build/make_preview.py',
    'build/set_pages_base.py',
    'build/make_publish.py',
    'build/verify_http.py',
]

keep = set(FILES) | {'.nojekyll'}
if OUT.exists():
    # 只清理非白名单的陈旧文件，目录结构复用（避免受本地删除保护策略影响）
    for p in OUT.rglob('*'):
        if p.is_file() and p.relative_to(OUT).as_posix() not in keep:
            p.unlink()
else:
    OUT.mkdir()

for rel in FILES:
    src = ROOT / rel
    if not src.exists():
        raise SystemExit('缺少待发布文件：' + rel)
    dst = OUT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

(OUT / '.nojekyll').write_text('', encoding='utf-8')

total = sum((OUT / rel).stat().st_size for rel in FILES)
print('已生成发布目录：%s' % OUT)
for rel in FILES + ['.nojekyll']:
    p = OUT / rel
    print('  %-52s %9d B' % (rel, p.stat().st_size))
print('共 %d 个文件，%d 字节（约 %.2f MB）' % (len(FILES) + 1, total, total / 1048576))
print('下一步：python3 verify_compat.py --root publish')
