#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布目录的静态服务 HTTP 验收（不占用固定端口、不留后台进程）。

在线程里起一个临时 HTTP 服务，逐项请求 publish/ 的资源，校验：
  1. 全部 HTTP 200（含 URL 编码的中文主文件名）；
  2. Content-Type 与文件类型相符；
  3. 响应字节与本地文件逐字节一致（sha256）；
结束后主动 shutdown，不遗留进程。

用法：python3 build/verify_http.py [--root publish]
"""
import functools
import hashlib
import http.server
import pathlib
import sys
import threading
import urllib.parse
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent.parent
ROOT = BASE / 'publish'
if '--root' in sys.argv:
    ROOT = (BASE / sys.argv[sys.argv.index('--root') + 1]).resolve()
if not (ROOT / 'index.html').exists():
    raise SystemExit('未找到发布目录：%s（先运行 python3 build/make_publish.py）' % ROOT)

CASES = [
    ('/', 'index.html', 'text/html'),
    ('/index.html', 'index.html', 'text/html'),
    ('/%E5%A4%AA%E9%98%B3%E7%B3%BB%E5%85%AB%E5%A4%A7%E8%A1%8C%E6%98%9F%E5%8A%A8%E6%80%81%E8%BF%90%E8%BD%AC.html',
     '太阳系八大行星动态运转.html', 'text/html'),
    ('/vendor/three.iife.js', 'vendor/three.iife.js', None),
    ('/vendor/three.module.js', 'vendor/three.module.js', None),
    ('/vendor/addons/controls/OrbitControls.js',
     'vendor/addons/controls/OrbitControls.js', None),
    ('/vendor/THREE-LICENSE.txt', 'vendor/THREE-LICENSE.txt', 'text/plain'),
    ('/assets/preview.png', 'assets/preview.png', 'image/png'),
    ('/reference.json', 'reference.json', 'application/json'),
    ('/verify.mjs', 'verify.mjs', None),
    ('/verify_page.py', 'verify_page.py', None),
    ('/verify_compat.py', 'verify_compat.py', None),
    ('/build/verify_runtime.mjs', 'build/verify_runtime.mjs', None),
    ('/SOURCES.md', 'SOURCES.md', None),
    ('/README.md', 'README.md', None),
    ('/.nojekyll', '.nojekyll', None),
]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


handler = functools.partial(Quiet, directory=str(ROOT))
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
t = threading.Thread(target=srv.serve_forever, daemon=True)
t.start()
base = 'http://127.0.0.1:%d' % srv.server_address[1]
print('临时静态服务：%s  →  %s' % (base, ROOT))

fail = []
try:
    for path, rel, mime in CASES:
        try:
            with urllib.request.urlopen(base + path, timeout=10) as r:
                body = r.read()
                code, ctype = r.status, r.headers.get_content_type()
        except Exception as e:
            fail.append('%s → %s' % (path, e))
            print('  FAIL %-58s %s' % (path, e))
            continue
        disk = (ROOT / rel).read_bytes()
        same = hashlib.sha256(body).digest() == hashlib.sha256(disk).digest()
        mime_ok = (mime is None) or (ctype == mime)
        good = code == 200 and same and mime_ok
        if not good:
            fail.append('%s → code=%s mime=%s bytes=%s' % (path, code, ctype, same))
        print('  %s %-56s %3d  %-18s %8d B  %s' %
              ('OK  ' if good else 'FAIL', path, code, ctype, len(body),
               'hash 一致' if same else 'hash 不一致'))
finally:
    srv.shutdown()
    srv.server_close()
    t.join(timeout=3)

if fail:
    raise SystemExit('HTTP 验收失败 %d 项：\n  %s' % (len(fail), '\n  '.join(fail)))
print('\n静态服务 HTTP 验收：%d/%d 全部 200、MIME 正确、字节哈希一致；服务已关闭。' %
      (len(CASES), len(CASES)))
