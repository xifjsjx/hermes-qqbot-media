"""QQBot Media Plugin -- enable image/file sending for QQbot channel.

v1.1.0: added MEME:<keyword> syntax -- send stickers/memes from a local
library directory by matching filenames, plus MEME:random and MEME:list.
"""

import asyncio
import base64
import logging
import os
import random
import re
from pathlib import Path

logger = logging.getLogger(__name__)

MSG_TYPE_MEDIA = 7
MEDIA_TYPE_IMAGE = 1
MEDIA_TYPE_VIDEO = 2
MEDIA_TYPE_VOICE = 3
MEDIA_TYPE_FILE = 4

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".3gp"}
_AUDIO_EXTS = {".ogg", ".opus", ".mp3", ".wav", ".m4a", ".flac"}
_VOICE_EXTS = {".ogg", ".opus"}

_MAX_BASE64_SIZE = 10 * 1024 * 1024

# ---- meme library ----
_MEME_DIR = os.path.expanduser(os.getenv("QQ_MEME_DIR", "~/.hermes/memes"))
_MEME_EXTS = _IMAGE_EXTS | _VIDEO_EXTS
# MEME:keyword -- keyword runs until whitespace or trailing punctuation
_MEME_TOKEN_RE = re.compile(r"MEME:([^\s，。！？；、,.!?;]+)")
_MEME_LIST_WORDS = {"list", "ls", "?", "？", "列表"}
_MEME_RANDOM_WORDS = {"random", "rand", "随机", "随便"}


def _guess_file_type(media_path: str, is_voice: bool) -> int:
    ext = os.path.splitext(media_path)[1].lower()
    if ext in _IMAGE_EXTS:
        return MEDIA_TYPE_IMAGE
    if ext in _VIDEO_EXTS:
        return MEDIA_TYPE_VIDEO
    if is_voice and ext in _VOICE_EXTS:
        return MEDIA_TYPE_VOICE
    if ext in _AUDIO_EXTS:
        return MEDIA_TYPE_VOICE
    return MEDIA_TYPE_FILE


def _is_url(path: str) -> bool:
    return path.startswith(("http://", "https://", "ftp://"))


def _meme_library() -> dict:
    """Scan the meme dir, return {filename_stem: absolute_path}."""
    lib = {}
    d = Path(_MEME_DIR)
    if not d.is_dir():
        return lib
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix.lower() in _MEME_EXTS:
            lib[p.stem] = str(p)
    return lib


def _meme_listing(lib: dict) -> str:
    if not lib:
        return f"表情包库为空（目录：{_MEME_DIR}）"
    names = "、".join(sorted(lib))
    return f"表情包库共 {len(lib)} 个：{names}"


def _resolve_meme(keyword: str, lib: dict):
    """Exact stem match first; otherwise pick a random substring match.

    Returns (path, stem) or (None, None) when nothing matches.
    """
    kw = keyword.lower()
    for stem, path in lib.items():
        if stem.lower() == kw:
            return path, stem
    matches = [(s, p) for s, p in lib.items() if kw and kw in s.lower()]
    if matches:
        stem, path = random.choice(matches)
        return path, stem
    return None, None


async def _get_qq_token(appid: str, secret: str) -> str | None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://bots.qq.com/app/getAppAccessToken",
                json={"appId": str(appid), "clientSecret": str(secret)},
            )
            if resp.status_code != 200:
                logger.warning("QQ token request failed: %s", resp.status_code)
                return None
            return resp.json().get("access_token")
    except Exception as e:
        logger.warning("QQ token request failed: %s", e)
        return None


async def _upload_media(
    access_token: str, chat_id: str, media_path: str, file_type: int
) -> dict:
    import httpx

    headers = {
        "Authorization": f"QQBot {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "file_type": file_type,
        "srv_send_msg": False,
    }
    if _is_url(media_path):
        body["url"] = media_path
        if file_type == MEDIA_TYPE_FILE:
            body["file_name"] = Path(media_path).name or "file"
    else:
        file_size = os.path.getsize(media_path)
        if file_size > _MAX_BASE64_SIZE:
            return {"error": f"File too large ({file_size} bytes). Max 10 MB."}
        with open(media_path, "rb") as f:
            body["file_data"] = base64.b64encode(f.read()).decode()
        if file_type == MEDIA_TYPE_FILE:
            body["file_name"] = os.path.basename(media_path)

    async with httpx.AsyncClient(timeout=120) as client:
        url = f"https://api.sgroup.qq.com/v2/users/{chat_id}/files"
        resp = await client.post(url, json=body, headers=headers)
        if resp.status_code in {200, 201}:
            return resp.json()
        url = f"https://api.sgroup.qq.com/v2/groups/{chat_id}/files"
        resp = await client.post(url, json=body, headers=headers)
        if resp.status_code in {200, 201}:
            return resp.json()
        return {"error": f"Upload failed (C2C/group): {resp.status_code}"}


async def _send_media_message(
    access_token: str, chat_id: str, file_info: str, caption: str = ""
) -> dict:
    import httpx

    headers = {
        "Authorization": f"QQBot {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "msg_type": MSG_TYPE_MEDIA,
        "media": {"file_info": file_info},
    }
    if caption:
        body["content"] = caption[:4000]

    async with httpx.AsyncClient(timeout=15) as client:
        url = f"https://api.sgroup.qq.com/v2/users/{chat_id}/messages"
        resp = await client.post(url, json=body, headers=headers)
        if resp.status_code in {200, 201}:
            data = resp.json()
            return {"success": True, "message_id": data.get("id")}
        url = f"https://api.sgroup.qq.com/v2/groups/{chat_id}/messages"
        resp = await client.post(url, json=body, headers=headers)
        if resp.status_code in {200, 201}:
            data = resp.json()
            return {"success": True, "message_id": data.get("id")}
        return {"error": f"Send media message failed: {resp.status_code}"}


def register(ctx):
    import tools.send_message_tool as smt

    _original_send_to_platform = smt._send_to_platform

    async def _patched_send_to_platform(
        platform,
        pconfig,
        chat_id,
        message,
        thread_id=None,
        media_files=None,
        force_document=False,
    ):
        media_files = list(media_files or [])
        message = message or ""

        if platform.value == "qqbot":
            keywords = _MEME_TOKEN_RE.findall(message)
            if keywords:
                lib = _meme_library()

                if any(k.lower() in _MEME_LIST_WORDS for k in keywords):
                    # MEME:list -> reply with the library index as plain text
                    message = _MEME_TOKEN_RE.sub("", message).strip()
                    listing = _meme_listing(lib)
                    message = f"{message}\n{listing}".strip()
                else:
                    resolved, unresolved = [], []
                    for kw in keywords:
                        if kw.lower() in _MEME_RANDOM_WORDS:
                            if lib:
                                resolved.append(random.choice(list(lib.values())))
                            else:
                                unresolved.append(kw)
                            continue
                        path, _stem = _resolve_meme(kw, lib)
                        if path:
                            resolved.append(path)
                        else:
                            unresolved.append(kw)
                    if unresolved:
                        return {
                            "error": (
                                f"表情包库中未找到：{'、'.join(unresolved)}。"
                                + _meme_listing(lib)
                            )
                        }
                    for path in dict.fromkeys(resolved):  # dedupe, keep order
                        media_files.append((path, False))
                    message = _MEME_TOKEN_RE.sub("", message).strip()

            if media_files:
                return await _send_qqbot_with_media(
                    pconfig,
                    chat_id,
                    message,
                    media_files,
                    force_document=force_document,
                )

        return await _original_send_to_platform(
            platform,
            pconfig,
            chat_id,
            message,
            thread_id=thread_id,
            media_files=media_files,
            force_document=force_document,
        )

    smt._send_to_platform = _patched_send_to_platform
    logger.info("QQBot media plugin installed (meme dir: %s)", _MEME_DIR)


async def _send_qqbot_with_media(
    pconfig, chat_id, message, media_files, force_document=False
):
    extra = pconfig.extra or {}
    appid = extra.get("app_id") or os.getenv("QQ_APP_ID", "")
    secret = (
        pconfig.token or extra.get("client_secret") or os.getenv("QQ_CLIENT_SECRET", "")
    )
    if not appid or not secret:
        return {"error": "QQBot: QQ_APP_ID / QQ_CLIENT_SECRET not configured."}

    token = await _get_qq_token(appid, secret)
    if not token:
        return {"error": "QQBot: failed to get access token"}

    import tools.send_message_tool as smt

    last_result = None

    if message.strip():
        last_result = await smt._send_qqbot(pconfig, chat_id, message)
        if isinstance(last_result, dict) and last_result.get("error"):
            return last_result

    for media_path, is_voice in media_files:
        if not os.path.exists(media_path) and not _is_url(media_path):
            return {"error": f"Media file not found: {media_path}"}

        file_type = _guess_file_type(media_path, is_voice)
        if file_type == MEDIA_TYPE_IMAGE and force_document:
            file_type = MEDIA_TYPE_FILE

        upload_result = await _upload_media(token, chat_id, media_path, file_type)
        if "error" in upload_result:
            return upload_result

        fi = upload_result.get("file_info") or (
            upload_result.get("data", {}) or {}
        ).get("file_info")
        if not fi:
            return {"error": f"Upload returned no file_info: {upload_result}"}

        caption = message if last_result is None and message.strip() else ""
        last_result = await _send_media_message(token, chat_id, fi, caption=caption)
        if isinstance(last_result, dict) and last_result.get("error"):
            return last_result

    if last_result is None:
        return {"error": "No deliverable text or media remained"}

    return {
        "success": True,
        "platform": "qqbot",
        "chat_id": chat_id,
        "message_id": last_result.get("message_id"),
    }
