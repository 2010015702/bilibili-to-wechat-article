---
name: bilibili-to-wechat-article
description: "End-to-end pipeline that turns a Bilibili video (single part or 分P) into a published-ready WeChat Official Account draft: download → local offline transcription → '二次创作' viral-article rewrite → context-aware illustration generation → typeset HTML → auto-create/update WeChat draft via API. Encodes all hard-won gotchas (preflight format check, no \n in content, CSS-var inlining, draft.add vs draft.update, IP allowlist). Trigger when the user pastes a bilibili.com/video/BV... link and asks to turn it into a 公众号文章 / 公众号草稿 / 二次创作 / 自动建草稿."
agent_created: true
---

# Bilibili 视频 → 公众号文章（全自动流水线）

## 总览
把一个 B 站教学/干货视频，自动变成一篇可直接在公众号后台「草稿箱」里看到、可群发的排版文章。
全流程 6 步，跨章节连贯、图文一体、自动建草稿，并内置「创建前的格式预检」拦截脏草稿。

```
① 下载(B站分P) → ② 转写(本地离线) → ③ 二次创作(爆款文) → ④ 配图(按上下文)
  → ⑤ 排版HTML(内联样式/无主标题) → ⑥ 草稿(预检→API建/改)
```

## 触发条件（When to use）
- 用户贴 `bilibili.com/video/BV...` 链接，并要求「转公众号文章 / 做成公众号 / 二次创作 / 自动建草稿」。
- 用户说「把视频做成公众号」「这集也跑一遍流水线」「继续下一集 p=N」。
- 已有一篇公众号 HTML，要求「自动创建草稿 / 修订草稿 / 改封面」。

## 前置依赖 / 环境
- 已安装技能：`bilibili-video-download`（第①步）、`video-to-text`（第②步）。
- Python 托管运行时：`C:/Users/wualei/.workbuddy/binaries/python/envs/default/Scripts/python.exe`
  （含 `yt-dlp`、Pillow；`faster-whisper` 如需离线转写）。
- 生图：`ImageGen` 工具（混元，扁平矢量风、中文标注清晰）。
- 微信公众号凭证（**仅放 Windows 用户级环境变量，不落盘**）：
  `WECHAT_APP_ID` / `WECHAT_APP_SECRET`（脚本里映射为 `WX_APPID` / `WX_SECRET`）。
- 账号要求：已认证的服务号/订阅号；**IP 白名单**含运行机器的出口 IPv4（沙箱常见 `223.74.64.157`，以微信 40164 报错为准）。

## 工作目录约定
每集建立一个独立目录，例如 `downloads/`，产物：
```
Pxx-标题.mp4                      # ① 下载
Pxx-标题.transcript.txt           # ② 转写纯文本
Pxx-标题-公众号文章.txt           # ③ 二次创作纯文字版（可选留存）
Pxx-标题-二次创作.html             # ⑤ 排版图文版（最终交付）
images/img01..06_*.png            # ④ 正文配图
images/cover_*.png                # 专用封面（建议单独生成）
publish_draft.py / fix_draft.py   # ⑥ 发布/修订脚本（见 references/）
```

---

## 6 步流水线

### ① 下载 B 站视频（调用 `bilibili-video-download` 技能）
- 单集：`URL?...&p=N`；整季：确认集数范围再批量（90 集可能 5–15GB，先与用户确认）。
- 关键参数：UA + Referer 应对 412；重试循环应对瞬时拦截。
- 产物：1080p 的 `Pxx-标题.mp4`。

### ② 转写为逐字稿（调用 `video-to-text` 技能 / faster-whisper）
- 优先本地离线（`HF_HUB_OFFLINE=1`，绕过沙箱代理 502）；模型用缓存的 `small` 即可。
- 产物：`Pxx-标题.transcript.txt`（纯转录）+ 可加一份含摘要版供创作参考。

### ③ 二次创作（爆款公众号文）
- 不要照搬逐字稿。按 `references/article_prompt.md` 的提示词做「总-分-总」重塑：
  - 4 个 `###` 大标题分节（h3，结构骨架）。
  - 文风：短句、朋友圈爆款感；穿插「敲黑板」「注意看」等钩子词。
  - 末尾设 `⚠️ 避坑指南` 板块（高收藏价值）。
  - 在需要配图处埋 `[📸 建议插图]` 标注（随后第④步实现）。
- **禁止把文章主标题写成 `<h1>`**（见下方「关键纪律」）。
- 产物：纯文字版 `.md/.txt`，以及埋好插图点的结构。

### ④ 配图（用 `ImageGen`)
- **必须按上下文具体场景生图，禁止模板化套壳**。
- 每张图对应第③步某个 `[📸 建议插图]` 点：读取该段文字，提炼出可视觉化的具体场景/对比/流程，生成含**中文标注**的扁平矢量图。
- 逐张生成（并行易撞文件名）；保存为 `images/imgNN_场景.png`。
- 封面单独生成（横向 16:9 左右，含大标题 + 蓝橙配色），生成后**裁掉右下角默认水印**（Pillow `crop` 底部条带，角色不重叠即可）。

### ⑤ 排版 HTML（内联样式、无主标题）
- 把 `.md` 内容 + 6 张图拼成 `Pxx-标题-二次创作.html`，CSS 写在 `<style>` 里。
- **关键纪律（必看下方「踩坑清单」）**：
  - HTML **不写主标题 `<h1>`**，也**不写 `<title>`**；标题统一由发布脚本的 `TITLE` 常量提供（避免预览/草稿里重复大标题）。
  - 用 CSS 变量（`:root{--brand:...}`）+ 复合/后代选择器（`figure.img`、`figure.img img`）没问题——发布脚本会内联化并解析变量（见 `references/publish_draft.py` 的 `parse_css`/`Inliner`）。
  - 图片：`figure.img img{width:100%}`、`figure.img{text-align:center;margin:26px 0}`；图注 `figcaption{color:var(--sub)}`。

### ⑥ 自动创建 / 修订草稿（微信 API）
- 用 `references/publish_draft.py`：
  1. 抽取并内联化 HTML（CSS 变量→字面量、选择器→内联 style、`\n` 折叠）。
  2. **先跑 `preflight()` 格式预检**（纯本地，不消耗配额）；任何一项不过 → 打印清单并 `sys.exit(1)` 拦截。
  3. 取 `access_token` → 上传封面拿 `thumb_media_id` → 上传 6 张正文图替换 `<img src>` → `draft.add` 建草稿。
- 修订已有草稿用 `references/fix_draft.py`：拉当前草稿复用图链，`draft.update` 就地改（`media_id` 不变，不产生第 3 份草稿）。
- 凭证注入（沙箱 Bash 不自动加载 Windows 用户变量）：
  ```powershell
  $id=[Environment]::GetEnvironmentVariable('WECHAT_APP_ID','User')
  $secret=[Environment]::GetEnvironmentVariable('WECHAT_APP_SECRET','User')
  $env:WX_APPID=$id; $env:WX_SECRET=$secret
  & "C:/Users/wualei/.workbuddy/binaries/python/envs/default/Scripts/python.exe" -u publish_draft.py 2>&1
  ```

---

## 关键纪律（每次都必须遵守）
1. **HTML 正文不带主标题**：不写 `<h1>`、不写 `<head><title>`。标题只在发布脚本 `TITLE` 常量里。
2. **创建/修订草稿前必须过 `preflight()`**：11 项检查（含无 h1/无 title/无 `\n`/无未解析 `var()`/图满宽/figure居中/h3蓝/figcaption灰/digest≠标题）。不过不建。
3. **正文不要保留 `\n`**：微信富文本编辑器会把 `\n` 渲染成可见空行。正文换行一律用 `<br>`，块级标签间换行全部折叠。
4. **封面优先单独生成并裁水印**，用 `thumb_media_id` 指定，不要拿正文某图凑数（3:2 在手机列表会被裁切）。
5. **凭证只走环境变量/注册表**，绝不写入脚本或日志。

## 微信 API 踩坑清单（血泪经验）
| # | 现象 | 根因 | 解决 |
|---|---|---|---|
| 1 | 40164 | 出口 IP 不在白名单 | 后台加机器出口 IPv4（沙箱常 `223.74.64.157`） |
| 2 | 40007 | `draft.add` 缺 `thumb_media_id` | 先上传封面拿 media_id 填入 |
| 3 | 47001 | `draft.update` 报 data format | `articles` 是**单个对象**不是数组（`draft.add` 才是数组） |
| 4 | 图从未真正上传 | `Inliner` 重建标签丢 `src` 属性 | 保留全部原始属性再附加 style |
| 5 | 顶部空行 | 正文 `\n` 被渲染成空行 + 卡片 padding-top | 折叠 `\n`、卡片顶边距归 0 |
| 6 | 标题变蓝/图满宽「静默失效」 | `<style>` 被丢弃后 `var()` 无定义、复合/后代选择器匹配不到 | `parse_css` 解析变量为字面量；`Inliner` 支持复合+后代选择器 |
| 7 | 预览顶部重复大标题 | 只在脚本丢 h1，源文件仍留 | 源文件删 h1+title，标题用常量 |
| 8 | 本地预览正常、线上错版 | 本地有 `<style>`，线上无 | 一切样式必须能内联化，预检拦截 |
| 9 | 沙箱 Bash 读不到凭证 | 不加载 Windows 用户变量 | PowerShell 从注册表读后注入 `$env:` |

## 排错速查
- 转写卡顿/502 → 改离线 `HF_HUB_OFFLINE=1` + 缓存 `small` 模型。
- 下载 412 → 必带 UA+Referer+重试。
- 草稿建了但格式错 → 别新建第 2 份，用 `fix_draft.py` 就地修订（复用图链）。
- 旧脏草稿残留 → `draft/delete` 清掉，只留最终版。

## 参考文件（本技能 `references/`）
- `publish_draft.py`：完整可运行的「内联化 + 预检 + 建草稿」脚本（使用前改顶部 4 个路径常量 + `TITLE`）。
- `fix_draft.py`：修订已有草稿脚本（填 `DRAFT_MEDIA_ID` 即可复用图链就地改）。
- `article_prompt.md`：二次创作提示词模板 + HTML 骨架（含 CSS 变量/选择器写法）。
