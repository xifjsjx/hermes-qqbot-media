# hermes-qqbot-media

Hermes Agent 插件 — 为 QQ Bot 通道启用原生图片/视频/语音/文件发送能力。

## 问题

Hermes 内置的 `send_message` 工具在 QQ Bot 通道上只能发送纯文本和 Markdown，无法发送文件附件。本插件通过拦截发送管道并使用 QQ 原生文件上传 API 来解决这个问题。

## 功能

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
```

## 用法

在 Hermes 的 `send_message` 中使用标准的 `MEDIA:/abs/path/to/file` 语法，插件会透明地拦截媒体文件并通过 QQ 原生上传 API 发送。

## 依赖

- Hermes Agent ≥ v0.20.0
- `httpx`（通常已随 Hermes 安装）

## 协议

MIT
