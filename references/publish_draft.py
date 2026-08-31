#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【模板】将本地产出的公众号文章自动创建为微信公众号【草稿】。
来源：bilibili-to-wechat-article 技能。使用前改顶部 4 个路径常量 + TITLE。

流程：取 access_token -> 内联化 HTML 样式 -> 上传本地图片到素材库拿图链
      -> 替换 <img> -> 调 cgi-bin/draft/add 创建草稿。
凭证：环境变量 WX_APPID / WX_SECRET（不写入任何文件）。

关键内联化逻辑（踩坑沉淀）：
  - CSS 变量 var(--x) 解析为字面量（<style> 会被丢弃，否则失效）
  - 选择器支持 复合(tag.class) + 后代(figure.img img)，靠父级栈匹配
  - 保留 <img> 全部原始属性（src/alt），避免图链丢失
  - 折叠 \n（公众号会把 \n 渲染成空行）
  - 丢弃 <h1>/<title>（标题由 TITLE 常量提供，正文不写主标题）
  - 创建前 preflight() 预检，不过则 sys.exit(1) 拦截
"""
import os, re, json, sys, mimetypes
from html.parser import HTMLParser
import urllib.request, urllib.parse, urllib.error

# ===== 使用前必须修改这 4 个常量 =====
HTML_PATH = r"E:/WorkBuddy1/视频转公众号文章/downloads/P07-提示词介绍-二次创作.html"
IMG_DIR = r"E:/WorkBuddy1/视频转公众号文章/downloads/images"
COVER_PATH = r"E:/WorkBuddy1/视频转公众号文章/downloads/images/cover_公众号封面.png"
TITLE = '同样用 AI，别人产出 10 倍？差的根本不是模型'   # 文章标题（HTML 正文不写主标题）

def parse_css(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    vars = {}
    mroot = re.search(r':root\{([^{}]*)\}', css)
    if mroot:
        for d in mroot.group(1).split(';'):
            d = d.strip()
            if d.startswith('--') and ':' in d:
                k, v = d.split(':', 1)
                vars[k.strip()] = v.strip()
    rules = []
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
        selectors = [s.strip() for s in m.group(1).split(',')]
        decls = {}
        for d in m.group(2).split(';'):
            d = d.strip()
            if ':' in d:
                k, v = d.split(':', 1)
                v = v.strip()
                v = re.sub(r'var\(\s*(--[\w-]+)\s*\)', lambda mm: vars.get(mm.group(1), ''), v)
                decls[k.strip()] = v
        for sel in selectors:
            rules.append((sel, decls))
    return rules

class Inliner(HTMLParser):
    def __init__(self, rules):
        super().__init__(convert_charrefs=True)
        self.rules = rules
        self.out = []
        self.in_style = False
        self.skip_tags = {'html', 'head', 'body', 'meta', 'title', 'style'}
        self.drop_tags = {'h1', 'title'}
        self.in_drop = False
        self.stack = []

    def _match_simple(self, tag, attrs, simple):
        simple = simple.strip()
        if simple == '*':
            return True
        if simple.startswith('#'):
            return dict(attrs).get('id') == simple[1:]
        if simple.startswith('.'):
            a = dict(attrs)
            return 'class' in a and simple[1:] in a['class'].split()
        if '.' in simple:
            tag_part, _, cls_part = simple.partition('.')
            a = dict(attrs)
            return tag == tag_part and 'class' in a and cls_part in a['class'].split()
        return tag == simple

    def match(self, tag, attrs, selector):
        parts = [p for p in selector.split() if p]
        if not parts:
            return False
        if len(parts) == 1:
            return self._match_simple(tag, attrs, parts[0])
        *ancestors, target = parts
        if not self._match_simple(tag, attrs, target):
            return False
        for i, anc in enumerate(reversed(ancestors)):
            idx = len(self.stack) - 1 - i
            if idx < 0:
                return False
            atag, aattrs = self.stack[idx]
            if not self._match_simple(atag, aattrs, anc):
                return False
        return True

    def handle_starttag(self, tag, attrs):
        if tag == 'style':
            self.in_style = True
            return
        if tag in self.drop_tags:
            self.in_drop = True
            return
        if tag in self.skip_tags:
            return
        style = ''
        for sel, decls in self.rules:
            if self.match(tag, attrs, sel):
                for k, v in decls.items():
                    style += f'{k}:{v};'
        parts = [f'{k}="{v}"' for k, v in attrs]
        if style:
            parts.append(f'style="{style}"')
        self.out.append(f'<{tag} {" ".join(parts)}>')
        if tag not in ('img', 'br', 'hr', 'meta', 'input', 'link',
                       'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'):
            self.stack.append((tag, dict(attrs)))

    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_style = False
            return
        if tag in self.drop_tags:
            self.in_drop = False
            return
        if tag in self.skip_tags:
            return
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        self.out.append(f'</{tag}>')

    def handle_data(self, data):
        if self.in_style or self.in_drop:
            return
        self.out.append(data)

def extract_and_inline(html_text):
    m = re.search(r'<style>(.*?)</style>', html_text, re.S)
    css = m.group(1) if m else ''
    rules = parse_css(css)
    p = Inliner(rules)
    p.feed(html_text)
    body = ''.join(p.out)
    body = re.sub(r'\n+', '', body)   # 折叠换行，防公众号空行
    body = body.strip()
    return body

def extract_title(html_text=None):
    return TITLE

def extract_digest(body):
    text = re.sub(r'<[^>]+>', '', body)
    text = re.sub(r'\s+', ' ', text).strip()
    mm = re.search(r'[^。！？]+[。！？]?', text)
    s = mm.group(0).strip() if mm else text
    return s if len(s) <= 48 else s[:48]

def preflight(html_text):
    """创建草稿前的格式预检（纯本地，不消耗配额）。返回 issues 列表，空=通过。"""
    issues = []
    body = extract_and_inline(html_text)
    title = extract_title(html_text)
    digest = extract_digest(body)
    if re.search(r'<h1', html_text, re.I):
        issues.append('HTML 源含 <h1> 主标题（约定：HTML 不写主标题，标题由 TITLE 常量提供）')
    if re.search(r'<title', html_text, re.I):
        issues.append('HTML <head> 含 <title>（约定：不写标题）')
    if '<h1' in body.lower():
        issues.append('抽取后正文仍含 <h1>')
    if '\n' in body:
        issues.append(r'正文含 \n 换行（公众号会渲染成空行）')
    if 'var(' in body:
        issues.append('正文含未解析 CSS 变量 var()')
    imgs = re.findall(r'<img[^>]*>', body)
    if imgs and not all('width:100%' in im for im in imgs):
        issues.append('存在未设 width:100% 的图片')
    figs = re.findall(r'<figure[^>]*>', body)
    if figs and not all('text-align:center' in f for f in figs):
        issues.append('figure 未居中')
    h3s = re.findall(r'<h3[^>]*>', body)
    if h3s and not all('color:#2b6fff' in h for h in h3s):
        issues.append('h3 标题未变蓝')
    caps = re.findall(r'<figcaption[^>]*>', body)
    if caps and not all('color:#646a73' in c for c in caps):
        issues.append('figcaption 未变灰')
    if not title or title == '未命名文章':
        issues.append('标题为空或为默认值「未命名文章」')
    if digest == title:
        issues.append('digest 与标题重复')
    return issues

def get_token(appid, secret):
    url = (f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential'
           f'&appid={urllib.parse.quote(appid)}&secret={urllib.parse.quote(secret)}')
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.loads(r.read())
    if 'access_token' not in data:
        raise SystemExit(f'[token 失败] {data}')
    return data['access_token']

def upload_image(token, path):
    url = (f'https://api.weixin.qq.com/cgi-bin/material/add_material'
           f'?access_token={token}&type=image')
    boundary = '----pyboundary7Qx'
    fn = os.path.basename(path)
    ctype = mimetypes.guess_type(fn)[0] or 'image/png'
    with open(path, 'rb') as f:
        filedata = f.read()
    body = b''
    body += f'--{boundary}\r\n'.encode()
    body += (f'Content-Disposition: form-data; name="media"; filename="{fn}"\r\n').encode()
    body += f'Content-Type: {ctype}\r\n\r\n'.encode()
    body += filedata + b'\r\n'
    body += f'--{boundary}--\r\n'.encode()
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())

def add_draft(token, title, content, digest, thumb_media_id, author=''):
    url = f'https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}'
    payload = {'articles': [{
        'title': title, 'author': author, 'digest': digest, 'content': content,
        'thumb_media_id': thumb_media_id, 'content_source_url': '',
        'need_open_comment': 0, 'only_fans_can_comment': 0,
    }]}
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def main():
    appid = os.environ.get('WX_APPID')
    secret = os.environ.get('WX_SECRET')
    if not appid or not secret:
        raise SystemExit('缺少环境变量 WX_APPID / WX_SECRET')

    html_text = open(HTML_PATH, encoding='utf-8').read()
    body = extract_and_inline(html_text)
    title = extract_title(html_text)
    digest = extract_digest(body)

    issues = preflight(html_text)
    if issues:
        print('✗ 预检未通过，已阻止草稿创建：')
        for i in issues:
            print('  -', i)
        sys.exit(1)
    print('[0/4] 格式预检通过 ✓')

    print(f'[1/4] 已内联样式，标题：《{title}》，摘要：{digest}')
    token = get_token(appid, secret)
    print('[2/4] access_token 获取成功')

    thumb_media_id = None
    if os.path.exists(COVER_PATH):
        for attempt in range(3):
            resp = upload_image(token, COVER_PATH)
            if 'url' in resp and 'media_id' in resp:
                thumb_media_id = resp['media_id']
                print(f'  + 封面上传成功 thumb_media_id={thumb_media_id}')
                break
            print(f'  ! 封面上传第{attempt+1}次失败: {resp}'); import time; time.sleep(3)
    if not thumb_media_id:
        print('  ! 封面上传失败，放弃本次草稿创建'); sys.exit(1)

    media_ids = []
    def repl(m):
        rel = m.group(1)
        local = os.path.join(IMG_DIR, os.path.basename(rel))
        if not os.path.exists(local):
            print(f'  ! 图片缺失: {local}，保留原 src'); return m.group(0)
        resp = None
        for attempt in range(3):
            try:
                resp = upload_image(token, local)
                if 'url' in resp: break
            except Exception as e:
                print(f'  ! {os.path.basename(local)} 第{attempt+1}次上传异常: {e}')
            if resp is None or 'url' not in resp: import time; time.sleep(3)
        if resp and 'url' in resp:
            print(f'  + 上传成功: {os.path.basename(local)}')
            if 'media_id' in resp: media_ids.append(resp['media_id'])
            return f'<img src="{resp["url"]}"'
        print(f'  ! 上传失败: {resp}'); return m.group(0)
    new_body = re.sub(r'<img src="(\.\./images/[^']+)"', repl, body)
    print('[3/4] 正文图片已上传并替换图链')

    if not thumb_media_id:
        print('[4/4] 没有可用封面图 media_id，无法创建草稿'); sys.exit(1)
    resp = add_draft(token, title, new_body, digest, thumb_media_id)
    if 'media_id' in resp:
        print('[4/4] 草稿创建成功！media_id =', resp['media_id'])
        print('（在公众号后台「草稿箱」即可看到，可继续编辑/群发）')
    else:
        print('[4/4] 草稿创建失败：', resp); sys.exit(1)

if __name__ == '__main__':
    main()
