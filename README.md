# hermes-qqbot-media

Hermes Agent plugin — enable native image/video/voice/file sending for the QQ Bot channel via the official QQ Bot API v2.

## Problem

Hermes's built-in `send_message` tool cannot send file attachments through the QQ Bot adapter — only plain text and markdown. This plugin bridges that gap by hooking into the send pipeline and using QQ's native file upload API.

## Features

- **Image**: jpg / jpeg / png / webp / gif
- **Video**: mp4 / mov / avi / mkv / 3gp
- **Voice**: ogg / opus (auto-detected)
- **File**: any format (pdf / docx / xlsx / md / etc.)
- Auto type detection by extension
- Files ≤10 MB sent as base64; larger files rejected with clear error
- Dual fallback: C2C first, then group
- Preserves original `send_message` semantics (returns `message_id`)

## Installation

1. Copy `plugin.yaml` and `__init__.py` to `~/.hermes/plugins/qqbot-media/`
2. Restart Hermes gateway: `hermes gateway restart`

## Configuration

Set via environment variables or `config.yaml` under `platforms.qqbot.extra`:

```bash
export QQ_APP_ID="your-app-id"
export QQ_CLIENT_SECRET="your-app-secret"
```

## Usage

Use Hermes's standard `MEDIA:/abs/path/to/file` syntax in `send_message`. The plugin transparently intercepts media files and routes them through QQ's native upload API.

## Requirements

- Hermes Agent ≥ v0.20.0
- `httpx` (usually bundled with Hermes)

## License

MIT
