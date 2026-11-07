#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容加固一键验收（v1.2）—— 面向朋友圈／小红书／GitHub Pages 发布。

判据（全部可证伪，失败即退出码非 0）：
  1. 主文件无 importmap / ESM / 运行时外链，所有相对资源实际存在；
  2. index.html 的跳转目标（URL 编码中文名）实际存在；
  3. 两个 HTML 的 og:* / twitter:card 齐全且 url / image / title 一致；
  4. assets/preview.png 是 1200×630 的合法 PNG；
  5. vendor/three.iife.js 通过 node --check 与 build/verify_bundle.mjs 导出完整性验收；
  6. 用 DOM stub 在 Node 里模拟「WebGL 被禁用」，端到端执行数值层 + 降级层 + 3D 层：
     必须切换静态视图、不白屏、SVG 含八大行星与太阳、16/16 PASS 仍可见，且 3D 层提前返回；
  7. node verify.mjs --json 的 16 组第三方对照仍全部 PASS；
  8. python3 verify_page.py 仍判定页面自检与命令行逐行一致。

用法：
  python3 verify_compat.py                 # 验收作品目录
  python3 verify_compat.py --root publish # 验收待发布目录
"""
import json
import pathlib
import re
import struct
import subprocess
import sys
import tempfile
from urllib.parse import unquote

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE
if '--root' in sys.argv:
    ROOT = (BASE / sys.argv[sys.argv.index('--root') + 1]).resolve()

MAIN = ROOT / '太阳系八大行星动态运转.html'
INDEX = ROOT / 'index.html'
ok = 0


def step(n, label, fn):
    global ok
    fn()
    ok += 1
    print('  [%d/8] %s —— OK' % (n, label))


def read(p):
    return p.read_text(encoding='utf-8')


def meta_val(text, key):
    for tag in re.findall(r'<meta\s[^>]+>', text):
        if re.search(r'(?:property|name)="%s"' % re.escape(key), tag):
            m = re.search(r'content="([^"]*)"', tag)
            return m.group(1) if m else None
    return None


html, idx = read(MAIN), read(INDEX)
print('验收目录：%s' % ROOT)


def c1():
    assert 'type="importmap"' not in html and 'type="module"' not in html, '仍存在 importmap / ESM'
    assert 'src="./vendor/three.iife.js"' in html, '未引用 IIFE 全局包'
    srcs = (re.findall(r'<script[^>]+src="([^"]+)"', html) +
            re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html))
    assert srcs, '未找到任何运行时资源引用'
    for u in srcs:
        assert not re.match(r'https?://', u), '运行时外链：' + u
        assert (ROOT / u).exists(), '运行时资源缺失：' + u
    assert 'window.__WEBGL__' in html and 'webglcontextlost' in html
    assert 'window.__SOLAR_FALLBACK__=render' in html and 'body.fb-on' in html


step(1, '无 importmap/ESM、运行时零外链、资源齐全、降级钩子齐备', c1)


def c2():
    m = re.search(r'url=\./([^">]+)', idx)
    assert m, 'index.html 缺少 meta refresh 跳转'
    target = unquote(m.group(1))
    assert (ROOT / target).exists(), '跳转目标不存在：' + target
    assert target == MAIN.name, '跳转目标不是中文主文件：' + target
    assert ('./' + m.group(1)) in idx, '可点击的兜底链接缺失'


step(2, 'index.html 薄重定向指向中文主文件且 URL 编码正确', c2)


def c3():
    keys = ['og:type', 'og:site_name', 'og:title', 'og:description', 'og:url',
            'og:image', 'og:image:width', 'og:image:height', 'twitter:card',
            'twitter:title', 'twitter:description', 'twitter:image', 'description']
    for text, label in [(html, '主文件'), (idx, 'index.html')]:
        for k in keys:
            assert meta_val(text, k), '%s 缺少 %s' % (label, k)
    for k in ['og:url', 'og:image', 'og:title', 'og:description']:
        assert meta_val(html, k) == meta_val(idx, k), '两页 %s 不一致' % k
    assert meta_val(html, 'og:image').endswith('/assets/preview.png')
    assert meta_val(html, 'og:image:width') == '1200'
    assert meta_val(html, 'og:image:height') == '630'
    assert 'AI 辅助创作' in html and 'AI 辅助创作' in meta_val(html, 'og:description')


step(3, 'og/twitter 元信息齐全（两页一致）、AI 辅助创作已标注', c3)


def c4():
    data = (ROOT / 'assets/preview.png').read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'preview.png 不是 PNG'
    w, h = struct.unpack('>II', data[16:24])
    assert (w, h) == (1200, 630), '预览图尺寸异常：%d×%d' % (w, h)
    assert len(data) > 10000, '预览图疑似空白'


step(4, '分享预览图 1200×630 PNG 有效', c4)


def c5():
    bundle = ROOT / 'vendor/three.iife.js'
    assert bundle.exists() and bundle.stat().st_size > 1_000_000
    r = subprocess.run(['node', '--check', str(bundle)], capture_output=True, text=True)
    assert r.returncode == 0, 'three.iife.js 语法失败：' + r.stderr
    r = subprocess.run(['node', str(ROOT / 'build/verify_bundle.mjs')],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and 'IIFE 打包验收通过' in r.stdout, \
        'bundle 导出验收失败：' + r.stdout + r.stderr


step(5, 'IIFE 包语法、416+1 导出、无 ESM 残留验收通过', c5)


def c6():
    blocks = re.findall(r'<script>\n([\s\S]*?)\n</script>', html)
    pick = lambda kw: [b for b in blocks if kw in b]
    numeric, fb, layer3d = (pick('window.SOLAR = Object.freeze('),
                            pick('window.__SOLAR_FALLBACK__=render'),
                            pick('3D-LAYER-BEGIN'))
    assert all(len(x) == 1 for x in (numeric, fb, layer3d)), '脚本块定位失败'
    assert 'window.THREE' not in fb[0], '降级层不应依赖 THREE'
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='solar_compat_'))
    paths = []
    for name, code in [('numeric.js', numeric[0]), ('fallback.js', fb[0]),
                       ('layer3d.js', layer3d[0])]:
        p = tmp / name
        p.write_text(code, encoding='utf-8')
        paths.append(str(p))
    runner = r'''
import fs from 'node:fs';
const nodes = new Map();
function el(id){
  if(!nodes.has(id)) nodes.set(id,{id,innerHTML:'',textContent:'',style:{},
    appendChild(){},addEventListener(){}});
  return nodes.get(id);
}
const added = [];
globalThis.window = {__WEBGL__:{ok:false,reason:'verify_compat：模拟禁用 WebGL',renderer:''},
  __bootTimer:null};
globalThis.document = {
  getElementById:el,
  body:{classList:{add:(c)=>added.push(c)},style:{}},
  createElement:()=>({getContext:()=>null,width:0,height:0})
};
const realLog = console.log;
console.log = () => {};
for(const f of process.argv.slice(2)) new Function(fs.readFileSync(f,'utf8'))();
console.log = realLog;
console.log(JSON.stringify({
  fallback:window.__FALLBACK__===true, booted:window.__BOOTED===true,
  mode3d:typeof window.__MODE3D__, svg:el('fb-svg').innerHTML,
  verdict:el('fb-verdict').innerHTML, reason:el('fb-reason').textContent,
  loaderrDisplay:el('loaderr').style.display,
  fallbackDisplay:el('fallback').style.display, classes:added
}));
'''
    rfile = tmp / 'run.mjs'
    rfile.write_text(runner, encoding='utf-8')
    r = subprocess.run(['node', str(rfile)] + paths, capture_output=True, text=True)
    assert r.returncode == 0, '降级模拟执行失败：' + r.stderr
    res = json.loads(r.stdout)
    assert res['fallback'] and res['booted'], '未切换到降级视图'
    assert res['mode3d'] == 'undefined', 'WebGL 不可用时 3D 层不应继续初始化'
    assert 'fb-on' in res['classes'], '未启用降级样式'
    assert res['fallbackDisplay'] == 'block' and res['loaderrDisplay'] == 'none'
    assert '模拟禁用 WebGL' in res['reason']
    for n in ['水星', '金星', '地球', '火星', '木星', '土星', '天王星', '海王星', '太阳']:
        assert n in res['svg'], '降级 SVG 缺少 ' + n
    assert res['svg'].count('<circle') >= 17, '降级 SVG 轨道/天体数量异常'
    assert '16/16' in res['verdict'] and 'PASS' in res['verdict'], '降级页未保留独立星历结论'
    print('        降级模拟：3D 层提前返回；SVG %d 个圆；%s' %
          (res['svg'].count('<circle'), res['reason']))


step(6, 'WebGL 禁用端到端模拟：静态视图 + 16/16 PASS 不白屏', c6)


def c7():
    vt = json.loads(subprocess.check_output(['node', 'verify.mjs', '--json'],
                                           cwd=ROOT, text=True))
    cmp = vt['comparison']
    rows = cmp['rows']
    assert cmp['pass'] is True and len(rows) == 16, '第三方对照未全部通过'
    assert all(r['pass'] for r in rows), '存在 FAIL 行'
    assert max(r['dLon'] for r in rows) < cmp.get('toleranceDeg', 1.0), '超出误差阈值'


step(7, '16 组独立星历对照仍 16/16 PASS', c7)


def c8():
    r = subprocess.run([sys.executable, 'verify_page.py'], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0 and '验证通过' in r.stdout, \
        '页面自检一致性校验失败：' + r.stdout + r.stderr
    assert '兼容检查 OK' in r.stdout


step(8, '页面自检面板与命令行逐行一致（含兼容结构检查）', c8)

print('\n兼容加固验收：%d/8 全部通过 —— %s' % (ok, ROOT))
print('说明：本脚本是静态 + DOM stub 验收，不能替代真实手机微信内核的端到端渲染确认。')
