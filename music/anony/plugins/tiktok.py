import hashlib
import logging
import os
import re
import time
import asyncio 
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import aiohttp
from bs4 import BeautifulSoup
from pyrogram import enums, filters, types
from pyrogram.types import InputMediaPhoto, Message


from anony import app, lang, config
from anony.helpers.fsub import check_force_sub



logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

DOWNLOAD_ROOT = os.path.join("downloads", "tiktok")
os.makedirs(DOWNLOAD_ROOT, exist_ok=True)

TIKTOK_URL_PATTERN = r"(?:https?://)?(?:www\\.|vm\\.|vt\\.)?tiktok\\.com/[^\\s]+"
TIKTOK_SHORT_URL_PATTERN = r"(?:https?://)?(?:vm\\.|vt\\.)tiktok\\.com/[A-Za-z0-9]+"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


async def get_developer_name_on_demand():

    try:
        user = await app.get_users(config.OWNER_ID)
        if user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.first_name
    except Exception as e:
        logger.error(f"[TikTok DL Error] فشل في جلب اسم المطور: {e}")
        return "المطور"

async def cleanup_files(file_paths: List[str]) -> None:
    
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info("Cleaned up cached file immediately: %s", file_path)
        except Exception as exc:
            logger.error("Error cleaning up file %s: %s", file_path, exc)

async def schedule_chat_cleanup(message_or_messages: Message | List[Message] | None, delay: int = 3600):
    
    if delay > 0:
        await asyncio.sleep(delay)
    
    if message_or_messages:
        messages = message_or_messages if isinstance(message_or_messages, list) else [message_or_messages]
        for msg in messages:
            try:
                await msg.delete()
                logger.info(f"Self-destructed message {msg.id} from chat after {delay}s")
            except Exception as e:
                logger.warning(f"Failed to self-destruct message {msg.id}: {e}")



async def expand_tiktok_short_url(url: str) -> str:

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
            async with session.get(url, allow_redirects=True) as response:
                final_url = str(response.url)
                if final_url != url:
                    logger.info("Expanded short URL: %s -> %s", url, final_url)
                    return final_url
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, "html.parser")
                    meta_refresh = soup.find("meta", {"http-equiv": "refresh"})
                    if meta_refresh and "url=" in meta_refresh.get("content", ""):
                        redirect_url = meta_refresh["content"].split("url=")[1]
                        if redirect_url.startswith("//"):
                            redirect_url = "https:" + redirect_url
                        elif redirect_url.startswith("/"):
                            redirect_url = "https://www.tiktok.com" + redirect_url
                        return redirect_url
                    url_patterns = [
                        r"https://www\\.tiktok\\.com/[^\\s\"']+",
                        r"https://vm\\.tiktok\\.com/[^\\s\"']+",
                        r"https://vt\\.tiktok\\.com/[^\\s\"']+",
                    ]
                    for pattern in url_patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            if match != url and "/photo/" in match:
                                return match
                            if match != url and "/video/" in match:
                                return match
                    for pattern in url_patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            if match != url:
                                return match
            async with session.get(url, allow_redirects=False) as response:
                if response.status in (301, 302, 307, 308):
                    location = response.headers.get("Location")
                    if location:
                        if location.startswith("//"):
                            location = "https:" + location
                        elif location.startswith("/"):
                            location = "https://www.tiktok.com" + location
                        return location
    except Exception as exc:
        logger.error("Error expanding TikTok URL %s: %s", url, exc)
    return url


def extract_video_id(url: str) -> Optional[str]:
   
    try:
        patterns = [
            r"/video/(\d+)",
            r"/photo/(\d+)",
            r"@[^/]+/video/(\d+)",
            r"@[^/]+/photo/(\d+)",
            r"/(\d{19})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        parsed = urlparse(url)
        if parsed.query:
            params = parse_qs(parsed.query)
            if "id" in params:
                return params["id"][0]
        return None
    except Exception as exc:
        logger.error("Error extracting video ID from %s: %s", url, exc)
        return None


def is_photo_slideshow(url: str) -> bool:

    if "/photo/" in url or "photo" in url.lower():
        return True
    photo_patterns = [r"/photo/", r"photo", r"images", r"gallery"]
    return any(re.search(pattern, url, re.IGNORECASE) for pattern in photo_patterns)


async def download_with_tikwm(url: str) -> Dict[str, Any]:

    try:
        headers = {
            "User-Agent": HEADERS["User-Agent"],
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www.tikwm.com/",
            "Origin": "https://www.tikwm.com",
        }
        data = {"url": url, "count": 12, "cursor": 0, "web": 1, "hd": 1}
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "https://www.tikwm.com/api/",
                headers=headers,
                data=data,
            ) as response:
                if response.status != 200:
                    logger.error("TikWM API returned status %s", response.status)
                    return {"success": False, "error": f"API returned status {response.status}"}
                json_data = await response.json(content_type=None)
                result: Dict[str, Any] = {
                    "success": False,
                    "video_url": None,
                    "audio_url": None,
                    "images": [],
                    "title": "",
                    "author": "",
                }
                if json_data.get("code") == 0 and "data" in json_data:
                    data_obj = json_data["data"]
                    result["title"] = data_obj.get("title", "")
                    result["author"] = data_obj.get("author", {}).get("unique_id", "")
                    video_url = data_obj.get("hdplay") or data_obj.get("play") or data_obj.get("wmplay")
                    if video_url:
                        if video_url.startswith("/"):
                            video_url = "https://www.tikwm.com" + video_url
                        result["video_url"] = video_url
                    audio_url = data_obj.get("music")
                    if audio_url:
                        if audio_url.startswith("/"):
                            audio_url = "https://www.tikwm.com" + audio_url
                        result["audio_url"] = audio_url
                    images = data_obj.get("images") or []
                    if images:
                        parsed_images = []
                        for img_url in images:
                            if img_url.startswith("/"):
                                parsed_images.append("https://www.tikwm.com" + img_url)
                            else:
                                parsed_images.append(img_url)
                        result["images"] = parsed_images
                    if result["video_url"] or result["images"]:
                        result["success"] = True
                return result
    except Exception as exc:
        logger.error("Error downloading with TikWM: %s", exc)
        return {"success": False, "error": str(exc)}


async def download_file(url: str, filename: str) -> bool:
    
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error("Failed to download file: HTTP %s", response.status)
                    return False
                with open(filename, "wb") as file_handle:
                    async for chunk in response.content.iter_chunked(8192):
                        file_handle.write(chunk)
                return True
    except Exception as exc:
        logger.error("Error downloading file %s: %s", url, exc)
        return False


def generate_filename(url: str, content_type: str, index: int = 0) -> str:
    
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    timestamp = int(time.time())
    if content_type == "video":
        extension = "mp4"
    elif content_type == "audio":
        extension = "mp3"
    else:
        extension = "jpg"
    if index > 0:
        filename = f"tiktok_{url_hash}_{timestamp}_{index}.{extension}"
    else:
        filename = f"tiktok_{url_hash}_{timestamp}.{extension}"
    return os.path.join(DOWNLOAD_ROOT, filename)


async def get_tiktok_photos_info(
    url: str, base_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    
    try:
        data = base_data if base_data is not None else await download_with_tikwm(url)
        if not data.get("success") or not data.get("images"):
            return {"success": False, "error": data.get("error", "No images found")}
        return {
            "success": True,
            "images": data.get("images", []),
            "title": data.get("title", ""),
            "author": data.get("author", ""),
            "count": len(data.get("images", [])),
            "audio_url": data.get("audio_url"),
        }
    except Exception as exc:
        logger.error("Error getting TikTok photos info: %s", exc)
        return {"success": False, "error": str(exc)}


async def download_tiktok_photos(
    url: str, photo_info: Optional[Dict[str, Any]] = None
) -> List[str]:
    
    try:
        info = photo_info if photo_info is not None else await get_tiktok_photos_info(url)
        if not info.get("success"):
            logger.error("Failed to get photo info: %s", info.get("error"))
            return []
        downloaded_files: List[str] = []
        for index, image_url in enumerate(info.get("images", []), start=1):
            filename = generate_filename(url, "photo", index)
            if await download_file(image_url, filename):
                downloaded_files.append(filename)
                logger.info(
                    "Downloaded TikTok photo %s/%s: %s",
                    index,
                    len(info.get("images", [])),
                    filename,
                )
            else:
                logger.error("Failed to download TikTok photo %s", index)
        return downloaded_files
    except Exception as exc:
        logger.error("Error downloading TikTok photos: %s", exc)
        return []


async def download_tiktok_video(
    url: str, video_info: Optional[Dict[str, Any]] = None
) -> str:

    try:
        info = video_info if video_info is not None else await download_with_tikwm(url)
        if not info.get("success") or not info.get("video_url"):
            logger.error("Failed to get video download URL: %s", info.get("error"))
            return ""
        filename = generate_filename(url, "video")
        if await download_file(info["video_url"], filename):
            logger.info("Downloaded TikTok video: %s", filename)
            return filename
        logger.error("Failed to download TikTok video file")
        return ""
    except Exception as exc:
        logger.error("Error downloading TikTok video: %s", exc)
        return ""




TIKTOK_COMMANDS = ["تيك", "تحميل", "tt"]

@app.on_message(
    filters.command(TIKTOK_COMMANDS, prefixes=["/", "!", ".", ""]) 
    & ~app.bl_users
    & (filters.group | filters.channel | filters.private)
)
@lang.language()
@check_force_sub  
async def tiktok_downloader(_, m: types.Message) -> None:
    
    if not m.text:
        return
    
    parts = m.text.split(None, 1)
    if len(parts) < 2:
        await m.reply_text(m.lang.get("tiktok_1", "Usage: /tiktok [URL]"))
        return
        
    raw_url = parts[1].strip()
    if re.match(TIKTOK_SHORT_URL_PATTERN, raw_url):
        raw_url = await expand_tiktok_short_url(raw_url)
        

    sent = await m.reply_text(m.lang.get("tiktok_2", "Processing..."))
    
    try:

        if m.chat.type != enums.ChatType.PRIVATE:
            await m.delete()
        

        tikwm_data = await download_with_tikwm(raw_url)
        if not tikwm_data.get("success"):
            await sent.edit_text(
                m.lang.get("tiktok_3", "Failed to download: {error}").format(
                    error=tikwm_data.get("error", "Unknown")
                )
            )
            return


        button_text = m.lang.get("support", "قناه السورس") 
        button_url = config.SUPPORT_CHANNEL 
        keyboard = None
        if button_url:
            keyboard = types.InlineKeyboardMarkup(
                [
                    [
                        types.InlineKeyboardButton(
                            text=button_text,
                            url=button_url
                        )
                    ]
                ]
            )


        sent_messages: List[Message] = []

        files_to_purge: List[str] = []

        if tikwm_data.get("images"):
            photo_info = await get_tiktok_photos_info(raw_url, tikwm_data)
            if not photo_info.get("success"):
                await sent.edit_text(m.lang.get("tiktok_8", "Failed to get photo info."))
                return
                
            photo_files = await download_tiktok_photos(raw_url, photo_info)
            if not photo_files:
                await sent.edit_text(m.lang.get("tiktok_8", "Failed to download photos."))
                return
                
            await sent.delete()
            files_to_purge.extend(photo_files) 
            
            media_group = []
            total = len(photo_files)
            for index, file_path in enumerate(photo_files):
                caption = None
                if index == 0:
                    caption = m.lang.get("tiktok_11", "Downloaded {count} photos.").format(count=total)
                media_group.append(InputMediaPhoto(media=file_path, caption=caption))
            
            
            sent_messages.extend(await _.send_media_group(
                chat_id=m.chat.id,
                media=media_group,
                reply_to_message_id=m.id,
            ))
            
            if photo_info.get("audio_url"):
                audio_filename = generate_filename(raw_url, "audio")
                if await download_file(photo_info["audio_url"], audio_filename):
                    await _.send_chat_action(
                        chat_id=m.chat.id,
                        action=enums.ChatAction.UPLOAD_AUDIO,
                    )
                    
                    performer_name = await get_developer_name_on_demand()
                    sent_audio = await _.send_audio(
                        chat_id=m.chat.id,
                        audio=audio_filename,
                        caption=m.lang.get("tiktok_12", "Original audio:"),
                        performer=performer_name,
                        title=photo_info.get("title") or "TikTok Audio",
                        reply_to_message_id=m.id,
                        reply_markup=keyboard
                    )
                    sent_messages.append(sent_audio)
                    files_to_purge.append(audio_filename) 
            
        elif tikwm_data.get("video_url"):
            video_file = await download_tiktok_video(raw_url, tikwm_data)
            if not video_file:
                await sent.edit_text(m.lang.get("tiktok_9", "Failed to download video file."))
                return
                
            file_size = os.path.getsize(video_file)
            
            TG_VIDEO_FILESIZE_LIMIT = 50 * 1024 * 1024 
            if file_size > TG_VIDEO_FILESIZE_LIMIT:
                await sent.edit_text(m.lang.get("tiktok_5", "File is too large for Telegram."))
                
                await cleanup_files([video_file])
                return
                
            await _.send_chat_action(
                chat_id=m.chat.id,
                action=enums.ChatAction.UPLOAD_VIDEO,
            )
            
            caption = None
            
            sent_video = await _.send_video(
                chat_id=m.chat.id,
                video=video_file,
                supports_streaming=True,
                caption=caption,
                reply_to_message_id=m.id,
                reply_markup=keyboard
            )
            
            await sent.delete()
            sent_messages.append(sent_video)
            files_to_purge.append(video_file) 
            
        else:
            await sent.edit_text(m.lang.get("tiktok_7", "No video or photos found."))
            return
        
        
        if files_to_purge:
            await cleanup_files(files_to_purge)

        
        if sent_messages:
            asyncio.create_task(schedule_chat_cleanup(sent_messages, 3600))

    except Exception as exc:
        logger.error("Error processing TikTok URL %s: %s", raw_url, exc, exc_info=True)
        await sent.edit_text(
            m.lang.get("tiktok_10", "An error occurred: {error}").format(error=str(exc))
        )