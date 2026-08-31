#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【模板】修订当前已存在的草稿（就地改，不新建第 2/3 份）。
来源：bilibili-to-wechat-article 技能。使用前改 DRAFT_DIR / HTML_PATH / DRAFT_MEDIA_ID。

逻辑：拉当前草稿 -> 取 thumb_media_id 和已上传图链 -> 用更新后的 HTML 重建正文
      -> preflight 预检 -> 按序复用图链 -> draft.update 就地改（media_id 不变）。

关键：draft.update 的 articles 是【单个对象】（不是数组，draft.add 才是数组）。
凭证：环境变量 WX_APPID / WX_SECRET。
依赖：同目录 publish_draft.py（import 复用其 inliner / token / preflight）。
"""
import os, json, sys, re
import urllib.request
import publish_draft as pd

DRAFT_DIR = r'E:/WorkBuddy1/视频转公众号文章/downloads'
HTML_PATH = os.path.join(DRAFT_DIR, 'P07-提示词介绍-二次创作.html')
DRAFT_MEDIA_ID = 'ZK8m-yBoAErV_eoJQprB0S1t4gUiFRUt5hy-krC1lKopRsraiOTC_n77YRHFmuxZ'

def get_draft(token, media_id):
    url = f'https://api.weixin.qq.com/cgi-bin/draft/get?access_token={token}'
    req = urllib.request.Request(url, data=json.dumps({'media_id': media_id}).encode(), method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def draft_update(token, media_id, payload):
    url = f'https://api.weixin.qq.com/cgi-bin/draft/update?access_token={token}'
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def main():
    appid = os.environ.get('WX_APPID'); secret = os.environ.get('WX_SECRET')
    if not appid or not secret: raise SystemExit('缺少 WX_APPID / WX_SECRET')

    token = pd.get_token(appid, secret)
    cur = get_draft(token, DRAFT_MEDIA_ID)
    if 'news_item' not in cur: raise SystemExit(f'取草稿失败: {cur}')
    item = cur['news_item'][0]
    thumb = item['thumb_media_id']
    cur_content = item['content']
    cur_digest = item.get('digest', '')
    src_urls = re.findall(r'<img[^>]*src="([^"]+)"', cur_content)
    print(f'当前 thumb_media_id: {thumb}；正文含 {len(src_urls)} 张图链（将被复用）')

    html_text = open(HTML_PATH, encoding='utf-8').read()
    body = pd.extract_and_inline(html_text)
    title = pd.extract_title(html_text)
    digest = pd.extract_digest(body)

    issues = pd.preflight(html_text)
    if issues:
        print('✗ 预检未通过，已阻止草稿更新：')
        for i in issues: print('  -', i)
        sys.exit(1)
    print('[0] 格式预检通过 ✓')
    print(f'新标题: 《{title}》\n原 digest: {cur_digest}\n新 digest: {digest}')

    assert '<h1' not in body.lower(), '重建后的 body 仍含 <h1>！'
    assert digest != title, f'digest 与标题重复：{digest}'

    counter = [0]
    def repl(m):
        idx = counter[0]; counter[0] += 1
        if idx < len(src_urls):
            return f'<img src="{src_urls[idx]}"'
        return m.group(0)
    new_body = re.sub(r'<img src="(\.\./images/[^']+)"', repl, body)
    n_img = len(re.findall(r'<img[^>]*src="', new_body))
    assert n_img == len(src_urls), f'图链数不匹配 {n_img} vs {len(src_urls)}'
    print(f'图链替换完成，正文新图数: {n_img}')

    article = {
        'title': title, 'author': item.get('author', ''), 'digest': digest,
        'content': new_body, 'content_source_url': '', 'thumb_media_id': thumb,
        'need_open_comment': 0, 'only_fans_can_comment': 0,
    }
    payload = {'media_id': DRAFT_MEDIA_ID, 'index': 0, 'articles': article}
    resp = draft_update(token, DRAFT_MEDIA_ID, payload)
    err = resp.get('errcode', None)
    if err == 0 or (err is None and 'errmsg' not in resp):
        print(f'✓ 草稿修订成功！media_id 保持不变: {DRAFT_MEDIA_ID}')
    else:
        print('修订失败:', resp); sys.exit(1)

if __name__ == '__main__':
    main()
