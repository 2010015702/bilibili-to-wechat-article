# bilibili-to-wechat-article

> 把 B 站视频一键变成可直接群发的公众号草稿 —— WorkBuddy 技能（Skill）

一个端到端的流水线 Skill：把一个 B 站教学 / 干货视频，自动变成一篇图文并茂、排版干净、
**可直接在公众号后台「草稿箱」里看到、可群发**的文章。全流程 6 步，内置「创建前的格式预检」
拦截脏草稿，并把所有踩过的坑（微信 API 行为、内联样式、空行、凭证注入）固化进脚本。

---

## 这个技能能做什么

```
① 下载(B站分P) → ② 转写(本地离线) → ③ 二次创作(爆款文) → ④ 配图(按上下文)
  → ⑤ 排版HTML(内联样式/无主标题) → ⑥ 草稿(预检→API建/改)
```

- 从 `bilibili.com/video/BV...` 链接出发，直到产出公众号草稿箱里的一篇图文。
- 跨步骤连贯：逐字稿 → 爆款二次创作 → 按上下文生图 → 内联样式排版 → 自动建/改草稿。
- 发布前 `preflight()` 11 项格式预检，不过不建，避免线上错版。

---

## 触发条件（When to use）

- 用户贴 `bilibili.com/video/BV...` 链接，并要求「转公众号文章 / 做成公众号 / 二次创作 / 自动建草稿」。
- 用户说「把视频做成公众号」「这集也跑一遍流水线」「继续下一集 p=N」。
- 已有一篇公众号 HTML，要求「自动创建草稿 / 修订草稿 / 改封面」。

---

## 仓库结构

```
bilibili-to-wechat-article/
├── SKILL.md                # 技能主文件（6 步流水线、关键纪律、踩坑清单、排错速查）
├── references/
│   ├── publish_draft.py     # ⑥ 自动创建草稿脚本（内联化 + 预检 + draft.add）
│   ├── fix_draft.py         # ⑥ 修订已有草稿脚本（draft.update 就地改，复用图链）
│   └── article_prompt.md    # ③ 二次创作提示词模板 + HTML 骨架（CSS 变量/选择器写法）
├── .gitignore
└── README.md               # 本文件
```

---

## 安装到 WorkBuddy

将本仓库放入用户级技能目录即可（跨项目可用）：

```bash
# 方式一：直接 clone 到技能目录
git clone https://github.com/2010015702/bilibili-to-wechat-article.git \
  ~/.workbuddy/skills/bilibili-to-wechat-article

# 方式二：或把仓库内容拷过去（保留 SKILL.md 与 references/ 的相对位置）
```

放入后，在 WorkBuddy 对话里贴 B 站链接并说「转成公众号文章」即可触发。

---

## 前置依赖

- **技能依赖**：`bilibili-video-download`（第①步下载）、`video-to-text`（第②步转写）。
- **Python 托管运行时**：`~/.workbuddy/binaries/python/envs/default/Scripts/python.exe`
  （含 `yt-dlp`、Pillow；`faster-whisper` 按需用于离线转写）。
- **生图工具**：`ImageGen`（第④步，扁平矢量风、中文标注清晰）。
- **微信公众号凭证**（**仅放 Windows 用户级环境变量，不落盘**）：
  `WECHAT_APP_ID` / `WECHAT_APP_SECRET`。
- **账号要求**：已认证服务号 / 订阅号；**IP 白名单**含运行机器出口 IPv4。

---

## 使用流程

1. **下载**（①）：调用 `bilibili-video-download`，单集 `URL?p=N`，产物 `Pxx-标题.mp4`。
2. **转写**（②）：调用 `video-to-text` / faster-whisper（优先本地离线 `HF_HUB_OFFLINE=1`），产物 `Pxx-标题.transcript.txt`。
3. **二次创作**（③）：按 `references/article_prompt.md` 做「总-分-总」重塑，4 个 `###` 分节、埋 `[📸 建议插图]`，产物 `Pxx-标题-二次创作.md`。
4. **配图**（④）：用 `ImageGen` 按具体场景生图（禁止模板套壳），封面单独生成后裁掉右下角水印。
5. **排版**（⑤）：拼成 `Pxx-标题-二次创作.html`，CSS 写在 `<style>`（脚本会内联化）。**不写 `<h1>` / `<title>`**。
6. **建草稿**（⑥）：编辑 `publish_draft.py` 顶部 4 个路径常量 + `TITLE`，注入凭证后运行：

   ```powershell
   $id=[Environment]::GetEnvironmentVariable('WECHAT_APP_ID','User')
   $secret=[Environment]::GetEnvironmentVariable('WECHAT_APP_SECRET','User')
   $env:WX_APPID=$id; $env:WX_SECRET=$secret
   & "~/.workbuddy/binaries/python/envs/default/Scripts/python.exe" -u publish_draft.py 2>&1
   ```

   脚本先跑 `preflight()`，通过后取 `access_token` → 上传封面 → 上传正文图 → `draft.add` 建草稿。
   修订已有草稿填 `fix_draft.py` 的 `DRAFT_MEDIA_ID` 后运行。

---

## 关键纪律（每次必须遵守）

1. **HTML 正文不带主标题**：不写 `<h1>`、不写 `<head><title>`。标题只在 `TITLE` 常量里给。
2. **创建 / 修订前必须过 `preflight()`**：11 项检查（无 h1 / 无 title / 无 `\n` / 无未解析 `var()` / 图满宽 / figure 居中 / h3 蓝 / figcaption 灰 / digest≠标题）。
3. **正文不要保留 `\n`**：微信富文本会把 `\n` 渲染成可见空行；换行用 `<br>`，块级标签间换行全部折叠。
4. **封面优先单独生成并裁水印**，用 `thumb_media_id` 指定，不要拿正文某图凑数。
5. **凭证只走环境变量 / 注册表**，绝不写入脚本或日志。

---

## 微信 API 踩坑清单（血泪经验）

| # | 现象 | 根因 | 解决 |
|---|---|---|---|
| 1 | 40164 | 出口 IP 不在白名单 | 后台加机器出口 IPv4 |
| 2 | 40007 | `draft.add` 缺 `thumb_media_id` | 先上传封面拿 media_id 填入 |
| 3 | 47001 | `draft.update` data format | `articles` 是**单对象**（`draft.add` 才是数组） |
| 4 | 图从未真正上传 | 重建标签丢 `src` | 保留全部原始属性再附加 style |
| 5 | 顶部空行 | 正文 `\n` 被渲染 + 卡片 padding-top | 折叠 `\n`、顶边距归 0 |
| 6 | 标题变蓝 / 图满宽失效 | `<style>` 被丢弃后 `var()` 无定义、复合选择器匹配不到 | `parse_css` 解析变量；`Inliner` 支持复合 + 后代选择器 |
| 7 | 预览顶部重复大标题 | 只在脚本丢 h1，源文件仍留 | 源文件删 h1+title，标题用常量 |
| 8 | 本地预览正常、线上错版 | 本地有 `<style>`、线上无 | 一切样式必须能内联化，预检拦截 |
| 9 | Bash 读不到凭证 | 不加载 Windows 用户变量 | PowerShell 从注册表读后注入 `$env:` |

---

## 排错速查

- **转写卡顿 / 502** → 离线 `HF_HUB_OFFLINE=1` + 缓存 `small` 模型。
- **下载 412** → 必带 UA + Referer + 重试循环。
- **草稿建了但格式错** → 别新建第 2 份，用 `fix_draft.py` 就地修订。
- **旧脏草稿残留** → `draft/delete` 清掉，只留最终版。

---

## License

本仓库为个人工作流沉淀，按 MIT 协议开源，可自由复用与改造。
