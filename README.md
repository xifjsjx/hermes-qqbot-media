# hermes-qqbot-media

Hermes Agent 插件 — 为 QQ Bot 通道启用原生图片/视频/语音/文件发送能力，并内置表情包库（`MEME:` 语法）。

## 问题

Hermes 内置的 `send_message` 工具在 QQ Bot 通道上只能发送纯文本和 Markdown，无法发送文件附件。本插件通过拦截发送管道并使用 QQ 原生文件上传 API 来解决这个问题。

## 功能

- **表情包库（v1.1 新增）**：消息里写 `MEME:关键词`，从本地图库按文件名匹配发图
- **图片**：jpg / jpeg / png / webp / gif
- **视频**：mp4 / mov / avi / mkv / 3gp
- **语音**：ogg / opus（自动识别）
- **文件**：任意格式（pdf / docx / xlsx / md 等）
- 按扩展名自动判断文件类型
- 10 MB 以内文件使用 base64 直传，超出后返回明确错误
- 双回退机制：优先 C2C，失败后尝试群聊
- 保持原有 `send_message` 语义（返回 `message_id`）

## 安装

1. 将 `plugin.yaml` 和 `__init__.py` 复制到 `~/.hermes/plugins/qqbot-media/`
2. 重启 Hermes 网关：`hermes gateway restart`

## 配置

通过环境变量或在 `config.yaml` 的 `platforms.qqbot.extra` 中设置：

```bash
export QQ_APP_ID="你的AppID"
export QQ_CLIENT_SECRET="你的AppSecret"

# 表情包目录（可选，默认 ~/.hermes/memes）
export QQ_MEME_DIR="/abs/path/to/memes"
```

## 用法

### 发送任意媒体文件

在 Hermes 的 `send_message` 中使用标准的 `MEDIA:/abs/path/to/file` 语法，插件会透明地拦截媒体文件并通过 QQ 原生上传 API 发送。

### 发表情包（MEME: 语法）

把表情包文件丢进图库目录，**文件名就是关键词**，例如 `开心-柴犬.gif`、`无语-猫猫.png`。然后在消息里写：

| 写法 | 行为 |
| --- | --- |
| `MEME:开心-柴犬` | 精确匹配文件名（不含扩展名） |
| `MEME:开心` | 模糊匹配；命中多个时随机挑一张 |
| `MEME:random`（或 `MEME:随机`） | 全库随机一张 |
| `MEME:list`（或 `MEME:列表`） | 不发图，回复当前图库清单 |

细节：

- 一条消息可以带多个 `MEME:`（自动去重），发送后关键词会从文本中剔除
- 关键词未命中时插件返回错误并附上可用清单，Agent 可以换个词重试
- 图库支持 gif 动图和短视频，单文件不超过 10 MB

## 依赖

- Hermes Agent ≥ v0.20.0
- `httpx`（通常已随 Hermes 安装）

## 协议

MIT
