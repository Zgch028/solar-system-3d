#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证「页面内置自检面板」与「命令行 verify.mjs」是否给出同一组结果。

不依赖浏览器、不依赖 Three.js / 网络：抽取《太阳系八大行星动态运转.html》的普通脚本，在 Node 里
用 DOM stub 执行，取回 window.SOLAR.comparisonTable() 的现场重算结果，再与
`node verify.mjs --json` 的 16 行逐项比对。

判据（可证伪）：
  1. 两份脚本语法均通过 node --check；
  2. 内联 REFERENCE 与 reference.json 逐位一致（含历元、岁差、黄经、日距）；
  3. 16 行 dLon / dR / pass 完全一致（容差 1e-12）；
  4. 页面与命令行总体判定一致，且时标 ΔJD < 1e-4。

用法：python3 verify_page.py   （失败时退出码非 0）
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
html = (ROOT / '太阳系八大行星动态运转.html').read_text(encoding='utf-8')
ref = json.loads((ROOT / 'reference.json').read_text(encoding='utf-8'))
tmp = pathlib.Path(tempfile.mkdtemp(prefix='solar_page_'))

blocks = re.findall(r'<script>\n([\s\S]*?)\n</script>', html)
plain = [b for b in blocks if 'window.SOLAR = Object.freeze(' in b]
fallback = [b for b in blocks if 'window.__SOLAR_FALLBACK__=render' in b]
layer3d = [b for b in blocks if '3D-LAYER-BEGIN' in b]
if len(plain) != 1 or len(layer3d) != 1 or len(fallback) != 1:
    raise SystemExit('脚本块定位失败：plain=%d fallback=%d 3d=%d' %
                     (len(plain), len(fallback), len(layer3d)))
p_plain, p_fb, p_3d = tmp / 'plain.js', tmp / 'fallback.js', tmp / 'layer3d.js'
p_plain.write_text(plain[0], encoding='utf-8')
p_fb.write_text(fallback[0], encoding='utf-8')
p_3d.write_text(layer3d[0], encoding='utf-8')

for f, label in [(p_plain, '数值层普通脚本'), (p_fb, '降级视图普通脚本'),
                 (p_3d, '3D 层普通脚本')]:
    r = subprocess.run(['node', '--check', str(f)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit('%s 语法失败：%s' % (label, r.stderr))
    print('语法 OK：' + label)

runner = '''
import fs from 'node:fs';
globalThis.window = {};
const stub = {innerHTML:'', style:{}, textContent:'', appendChild(){}, addEventListener(){}};
globalThis.document = {getElementById:()=>stub};
const realLog = console.log;
console.log = () => {};
new Function(fs.readFileSync(%r,'utf8'))();
console.log = realLog;
const S = globalThis.window.SOLAR;
console.log(JSON.stringify({ref:S.REFERENCE, cmp:S.comparisonTable(),
  verdict:globalThis.window.__SELFTEST__.comparison.pass,
  detailLen:globalThis.window.__SELFTEST__.html.length}));
''' % str(p_plain)
p_run = tmp / 'run.mjs'
p_run.write_text(runner, encoding='utf-8')
page = json.loads(subprocess.check_output(['node', str(p_run)], text=True))
vt = json.loads(subprocess.check_output(['node', 'verify.mjs', '--json'], cwd=ROOT, text=True))

pr, gr = page['ref'], ref
assert pr['source'] == gr['meta']['source'] and pr['version'] == gr['meta']['ephemVersion']
assert pr['toleranceDeg'] == gr['meta']['toleranceDeg']
assert pr['generatedAt'] == gr['meta']['generatedAt']
assert len(pr['epochs']) == len(gr['epochs']) == 2
for pe, ge in zip(pr['epochs'], gr['epochs']):
    assert pe['label'] == ge['label'] and pe['jdTDB'] == ge['jdTDB']
    assert pe['precessionDeg'] == ge['precessionDeg']
    assert len(pe['planets']) == len(ge['planets']) == 8
    for pp, gp in zip(pe['planets'], ge['planets']):
        assert pp['n'] == gp['name']
        assert pp['lonDate'] == gp['lonDate'] and pp['lonJ2000'] == gp['lonJ2000']
        assert pp['rAU'] == gp['rAU']
print('内联参照：与 reference.json 逐位一致（2 时刻 × 8 行星 × 4 类数值）')

pr_rows, vt_rows = page['cmp']['rows'], vt['comparison']['rows']
assert len(pr_rows) == len(vt_rows) == 16, '误差表行数不是 16'
worst = 0.0
for a, b in zip(pr_rows, vt_rows):
    assert a['epoch'] == b['epoch'] and a['planet'] == b['planet']
    d1, d2 = abs(a['dLon'] - b['dLon']), abs(a['dR'] - b['dR'])
    worst = max(worst, d1, d2)
    assert d1 < 1e-12 and d2 < 1e-12 and a['pass'] == b['pass']
print('16 组误差逐行比对：一致，最大数值差 %.2e' % worst)
assert page['verdict'] == vt['comparison']['pass'] is True, '总体判定不一致'
assert all(t['pass'] for t in page['cmp']['timeAlign']), '时标未对齐'
print('总体判定：PASS（页面 / 命令行一致）；最大 |Δ黄经| = %.4f°' %
      max(r['dLon'] for r in pr_rows))
print('时标对齐：' + ', '.join('%s ΔJD=%.1e' % (t['label'][:10], t['deltaJd'])
                            for t in page['cmp']['timeAlign']))
print('2026 参考系证据：修正前平均 %.4f° → 修正后 %.4f°' %
      (sum(r['dLonRaw'] for r in pr_rows[8:]) / 8,
       sum(r['dLon'] for r in pr_rows[8:]) / 8))
print('自检面板 HTML：%d 字符' % page['detailLen'])

for bad in ["$('stbody')", '⑤ 第三方星历逐项误差表由']:
    assert bad not in html, '旧代码残留：' + bad
assert html.count('function selfTest()') == 1
assert html.count('const REFERENCE = Object.freeze(') == 1
assert '不依赖 Three.js / 网络' in html
print('结构检查 OK：无重复自检、无旧文案、离线解耦说明已落地')

# 兼容加固结构检查（去 ESM / WebGL 降级 / 分享元信息 / 零运行时外链）
assert 'type="importmap"' not in html and 'type="module"' not in html
assert 'src="./vendor/three.iife.js"' in html
assert 'window.__WEBGL__' in html and 'window.__SOLAR_FALLBACK__=render' in html
assert 'webglcontextlost' in html and 'body.fb-on' in html
for tag in ('og:title', 'og:description', 'og:image', 'og:url', 'twitter:card'):
    assert ('property="%s"' % tag) in html or ('name="%s"' % tag) in html, \
        '缺少分享元信息：' + tag
runtime_srcs = (re.findall(r'<script[^>]+src="([^"]+)"', html) +
                re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html))
external = [u for u in runtime_srcs if re.match(r'https?://', u)]
assert not external, '运行时存在外链资源：' + ', '.join(external)
print('兼容检查 OK：无 importmap/ESM、无运行时外链、WebGL 降级与 og 元信息齐全')
print('\n页面自检面板与 verify.mjs 一致 —— 验证通过。')
