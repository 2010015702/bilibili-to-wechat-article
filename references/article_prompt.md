# 二次创作提示词模板 + HTML 骨架

## 一、二次创作提示词（角色：10万粉公众号干货博主）
把下面这段作为 System/角色设定，再把逐字稿（transcript.txt）作为素材喂进去：

```
你现在是一名拥有 10 万粉丝的微信公众号干货博主。
我将给你一段 B 站教学视频的逐字稿，请帮我做「二次创作」：

1) 结构重塑（总-分-总）：
   - 开头用 1 段钩子（痛点/反差/名场面）抓住注意力；
   - 中间设 4 个 ### 大标题分节（h3），层层递进；
   - 结尾回扣开头，给「行动建议 / 收藏理由」。

2) 文风转化（朋友圈爆款）：
   - 短句为主，多用「敲黑板：」「注意看」「说白了」「别急」等口语钩子；
   - 适当用「⚠️」标记重点，制造收藏感。

3) ⚠️ 避坑指南：文章末尾单独设一个「⚠️ 避坑指南」板块，
   列出 3-5 条新手最容易踩的坑（源自逐字稿里被强调的点）。

4) 插图埋点：在正文中需要配图的地方写 [📸 建议插图：<一句话描述该图要表达的具体场景/对比/流程>],
   每张图都要具体到「能画出来的画面」，不要泛泛而谈。

5) 字数：1500-3000 字。不要写文章主标题（<h1>），主标题由发布流程单独给定。

逐字稿位于：<transcript 文件路径>
```

## 二、配图执行（第④步）
对每一处 `[📸 建议插图：...]`，用 `ImageGen` 工具生成扁平矢量图：
- 读取该段上下文，提炼**具体可视觉化**的画面（如「左边杂乱文件堆 vs 右边清晰 AI 方案清单」）；
- 图上加**中文标注**（关键词/箭头/对比文字）；
- 蓝橙配色、信息清晰；保存为 `images/imgNN_场景.png`；
- **禁止模板化套壳**（不要把同一张示意图反复换标题）。

## 三、HTML 排版骨架（第⑤步）
CSS 变量 + 复合/后代选择器写法（发布脚本会内联化，本地预览也正常）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- 注意：不写 <title>，不写正文 <h1>；主标题由发布脚本 TITLE 常量提供 -->
<style>
:root{
  --brand:#2b6fff;
  --sub:#646a73;
  --bg:#fff;
  --accent:#ff7a45;
}
.wrap{max-width:680px;margin:0 auto;background:var(--bg);border-radius:14px;padding:0 32px 48px;box-shadow:0 4px 20px rgba(0,0,0,.06);}
h3{color:var(--brand);border-left:5px solid var(--brand);padding-left:12px;margin:34px 0 14px;font-size:20px;}
p{line-height:1.9;color:#1f2329;font-size:16px;margin:14px 0;}
blockquote{margin:18px 0;padding:12px 16px;border-left:4px solid var(--brand);background:#f3f7ff;border-radius:8px;color:#1f2329;}
figure.img{margin:26px 0;text-align:center;}
figure.img img{width:100%;border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,.08);}
figcaption{color:var(--sub);font-size:13px;margin-top:8px;}
.warn{background:#fff4e6;border-left:4px solid var(--accent);padding:14px 16px;border-radius:8px;margin:20px 0;}
</style>
</head>
<body>
<div class="wrap">
  <p>你肯定经历过这个名场面。</p>

  <h3>一、先搞懂：提示词到底是什么</h3>
  <p>...</p>
  <figure class="img">
    <img src="./images/img01_场景.png" alt="...">
    <figcaption>图注：...</figcaption>
  </figure>

  <h3>二、别急着写：先想清楚这三件事</h3>
  ...

  <h3>三、硬核干货：五原则四技巧六要素</h3>
  ...

  <h3>四、⚠️ 避坑指南</h3>
  <div class="warn">⚠️ 坑 1：...</div>
  <div class="warn">⚠️ 坑 2：...</div>
</div>
</body>
</html>
```

## 四、封面（单独生成）
- 横向 16:9 左右（如 1536×1024 → 裁掉底部水印后约 1.69:1）；
- 含大标题 + 蓝橙配色 + 1 句副标；
- 生成后用 Pillow `crop` 掉右下角默认水印（底部条带，角色不重叠即可）。
