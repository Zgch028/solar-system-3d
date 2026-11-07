#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 reference.json 重新生成《太阳系八大行星动态运转.html》内联的 REFERENCE 常量快照。

用途：页面把 golden file 的 16 组参照值内联在普通脚本里，保证零网络可核验。
      重新生成参照数据后，必须运行本脚本，否则页面与 verify.mjs 可能出现分叉。

用法：python3 reference_ephem.py && python3 sync_reference.py && python3 verify_page.py

替换区间：/* ---REF-BEGIN--- */ 与 /* ---REF-END--- */ 之间的整段常量。
数值一律从 reference.json 读取（repr 保留完整精度），不手抄、不四舍五入。
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
html_path = ROOT / '太阳系八大行星动态运转.html'
html = html_path.read_text(encoding='utf-8')
ref = json.loads((ROOT / 'reference.json').read_text(encoding='utf-8'))
q = lambda s: json.dumps(s, ensure_ascii=False)

ep_parts = []
for ep in ref['epochs']:
    pl = ['        {n:%s,lonDate:%s,lonJ2000:%s,rAU:%s}' %
          (q(p['name']), repr(p['lonDate']), repr(p['lonJ2000']), repr(p['rAU']))
          for p in ep['planets']]
    ep_parts.append('      {label:%s,jdTDB:%s,precessionDeg:%s,planets:[\n%s\n      ]}' %
                    (q(ep['label']), repr(ep['jdTDB']), repr(ep['precessionDeg']), ',\n'.join(pl)))

ref_js = ('const REFERENCE = Object.freeze({\n'
          '  source: %s, version: %s, toleranceDeg: %s, generatedAt: %s,\n'
          '  frame: %s,\n'
          '  epochs:[\n%s\n  ]\n'
          '});') % (q(ref['meta']['source']), q(ref['meta']['ephemVersion']),
                    repr(ref['meta']['toleranceDeg']), q(ref['meta']['generatedAt']),
                    q(ref['meta']['frame']), ',\n'.join(ep_parts))

pat = re.compile(r'(/\* ---REF-BEGIN---[^\n]*\*/\n)([\s\S]*?)(\n/\* ---REF-END--- \*/)')
hits = list(pat.finditer(html))
if len(hits) != 1:
    raise SystemExit('REF 标记应恰好出现 1 组，实际 %d 组；未修改文件。' % len(hits))
old = hits[0].group(2)
out = html[:hits[0].start(2)] + ref_js + html[hits[0].end(2):]
if old == ref_js:
    print('内联参照已是最新，无需改动（幂等）。')
else:
    html_path.write_text(out, encoding='utf-8')
    print('已同步内联参照：%d 组 → 太阳系八大行星动态运转.html（%d → %d 字符）' %
          (sum(len(e['planets']) for e in ref['epochs']), len(html), len(out)))
print('提示：接着运行 python3 verify_page.py 复核页面与 verify.mjs 是否一致。')
