#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量替换两个 HTML 与 README 中的 GitHub Pages 绝对基址（og:url / og:image / canonical）。

分享卡片要求 og:image 是绝对 URL，而爬虫不执行 JavaScript，所以必须写死字面量；
仓库改名时不能只改一处，故用本脚本幂等替换。

用法：
  python3 build/set_pages_base.py solar-system-3d              # owner 默认 zgch028（强制小写）
  python3 build/set_pages_base.py my-new-repo MyOrg
  python3 build/set_pages_base.py --show                       # 只显示当前基址，不改文件
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES = [ROOT / 'index.html', ROOT / '太阳系八大行星动态运转.html',
         ROOT / 'README.md']
PAT = re.compile(r'https://[A-Za-z0-9_.-]+\.github\.io/[A-Za-z0-9_.-]+/')


def current_bases():
    out = {}
    for f in FILES:
        out[f.name] = sorted(set(PAT.findall(f.read_text(encoding='utf-8'))))
    return out


if len(sys.argv) > 1 and sys.argv[1] == '--show':
    for name, bases in current_bases().items():
        print('%s: %s' % (name, ', '.join(bases) or '（无）'))
    raise SystemExit(0)

if len(sys.argv) < 2:
    raise SystemExit('用法：python3 build/set_pages_base.py <repo> [owner]')
repo = sys.argv[1].strip('/')
owner = sys.argv[2] if len(sys.argv) > 2 else 'Zgch028'
if not re.fullmatch(r'[A-Za-z0-9_.-]+', repo) or not re.fullmatch(r'[A-Za-z0-9_.-]+', owner):
    raise SystemExit('owner / repo 只能含字母、数字、点、下划线、连字符。')
# GitHub Pages 实际域名恒为小写；og:url / canonical 必须与真实地址逐字一致。
owner = owner.lower()
new_base = 'https://%s.github.io/%s/' % (owner, repo)

for f in FILES:
    text = f.read_text(encoding='utf-8')
    hits = PAT.findall(text)
    if not hits:
        raise SystemExit('%s 中未找到 Pages 基址，未修改任何文件。' % f.name)
    out = PAT.sub(new_base, text)
    if out != text:
        f.write_text(out, encoding='utf-8')
    print('%s：替换 %d 处 → %s' % (f.name, len(hits), new_base))

# 复核：三个文件的基址必须唯一且一致；两个 HTML 的 og:image / og:url 必须正确
for f in FILES:
    text = f.read_text(encoding='utf-8')
    bases = set(PAT.findall(text))
    assert bases == {new_base}, '%s 基址不一致：%s' % (f.name, bases)
    if f.suffix == '.html':
        assert ('content="%sassets/preview.png"' % new_base) in text, \
            '%s 的 og:image 未指向预览图' % f.name
        assert ('content="%s"' % new_base) in text, '%s 的 og:url 未更新' % f.name
print('复核 OK：两个 HTML 的 og:url / og:image / canonical 与 README 在线地址均指向 %s' % new_base)
print('提示：若已发布过，记得同步更新 publish/ 与远端仓库，并重跑 python3 build/make_publish.py。')
