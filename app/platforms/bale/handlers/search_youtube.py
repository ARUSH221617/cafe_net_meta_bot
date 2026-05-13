import httpx
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.services.youtube import YouTubeService


# -------------------------------------------------------------------
# 1. Entry point: user triggers YouTube search mode
# -------------------------------------------------------------------
async def prompt_youtube_search(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Clear previous results and ask for a query."""
    context.application.bot_data["state"].youtube_results[update.effective_chat.id] = []
    await update.effective_message.reply_text(
        "🎬 لطفاً عبارت مورد نظر برای جستجو در یوتیوب را وارد کنید:"
    )


# -------------------------------------------------------------------
# 2. Handle user text when in YouTube search mode
# -------------------------------------------------------------------
async def handle_youtube_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    state = context.application.bot_data["state"]
    chat_id = update.effective_chat.id
    # Only process if search mode is active and no results stored yet
    if chat_id not in state.youtube_results or state.youtube_results[chat_id]:
        return False

    settings = state.settings
    cookies_file = getattr(settings, "youtube_cookies_file", None)

    service = YouTubeService(
        enabled=getattr(settings, "youtube_search_enabled", True),
        cookies_file=cookies_file,
    )

    try:
        results = await service.search(update.message.text, max_results=10)
    except Exception as e:
        await update.effective_message.reply_text(
            f"❌ خطا در جستجوی یوتیوب:\n{str(e)[:200]}"
        )
        state.youtube_results.pop(chat_id, None)
        return True

    state.youtube_results[chat_id] = results
    if not results:
        await update.effective_message.reply_text("🔍 نتیجه‌ای یافت نشد.")
        return True

    query_text = update.message.text
    total = len(results)

    # Build message
    lines = [f"🎬 *نتایج جستجو برای _{query_text}_* ({total} مورد)\n\n"]
    keyboard_rows = []
    row = []

    for idx, video in enumerate(results, start=1):
        # Video line
        lines.append(
            f"{idx}. [{video.title}]({video.url})\n"
            f"   👤 {video.channel_name} | ⏱ {video.duration} | 👀 {video.views:,}"
        )
        row.append(
            InlineKeyboardButton(str(idx), callback_data=f"yt:video:{video.video_id}")
        )
        if len(row) == 5:
            keyboard_rows.append(row)
            row = []

    message_text = "\n".join(lines)
    if row:
        keyboard_rows.append(row)
    reply_markup = InlineKeyboardMarkup(keyboard_rows)

    await update.effective_message.reply_text(
        message_text,
        parse_mode="Markdown",
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )
    return True


# -------------------------------------------------------------------
# 3. Callback handler for all YouTube actions
# -------------------------------------------------------------------
async def handle_youtube_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    parts: list[str],
) -> bool:
    query = update.callback_query
    if query is None:
        return False

    action = parts[1] if len(parts) > 1 else ""

    match action:
        case "video":
            return await show_video_details(query, update, context, parts)
        case "formats":
            return await choose_format(query, update, context, parts)
        case "download":
            return await download_video(query, update, context, parts)
        case "back_to_results":
            return await show_search_results_yt(query, update, context)
        case _:
            return False
    return False


# -------------------------------------------------------------------
# 4. Show details of a single video (from search result or video ID)
# -------------------------------------------------------------------
async def show_video_details(
    query, update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]
) -> bool:
    await query.answer()
    video_id = parts[2]
    state = context.application.bot_data["state"]
    chat_id = update.effective_chat.id
    video = None

    # Try to find in cached results first
    if chat_id in state.youtube_results:
        for v in state.youtube_results[chat_id]:
            if v.video_id == video_id:
                video = v
                break

    if video is None:
        settings = state.settings
        cookies_file = getattr(settings, "youtube_cookies_file", None)
        service = YouTubeService(
            enabled=getattr(settings, "youtube_search_enabled", True),
            cookies_file=cookies_file,
        )
        try:
            video = await service.get_video_info(video_id)
        except Exception:
            await query.edit_message_text("❌ خطا در دریافت اطلاعات ویدئو.")
            return True

    if video is None:
        await query.edit_message_text("❌ ویدئوی مورد نظر یافت نشد.")
        return True

    # Format detail message
    msg = (
        f"🎬 *{video.title}*\n\n"
        f"👤 [{video.channel_name}]({video.channel_url})\n"
        f"⏱ {video.duration} | 👀 {video.views:,}\n"
        f"📅 {video.published_at[:10]}\n"
        f"🔗 [مشاهده در یوتیوب]({video.url})\n\n"
        f"{video.description[:300]}..."
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "📥 دانلود", callback_data=f"yt:formats:{video.video_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت به نتایج جستجو", callback_data="yt:back_to_results"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        msg,
        parse_mode="Markdown",
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )
    return True


# -------------------------------------------------------------------
# 5. Show available download formats for a video
# -------------------------------------------------------------------
async def choose_format(
    query, update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]
) -> bool:
    await query.answer("دریافت فرمت‌های دانلود...")
    video_id = parts[2]
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    state = context.application.bot_data["state"]
    settings = state.settings
    cookies_file = getattr(settings, "youtube_cookies_file", None)

    service = YouTubeService(
        enabled=True,
        cookies_file=cookies_file,
    )

    try:
        formats = await service.get_formats(video_url)
    except Exception as e:
        await query.edit_message_text(f"❌ خطا در استخراج لینک دانلود:\n{str(e)[:200]}")
        return True

    if not formats:
        await query.edit_message_text("⚠️ هیچ فرمت قابل دانلودی یافت نشد.")
        return True

    # Build keyboard: show first 5-6 options (audio + best videos)
    keyboard = []
    for fmt in formats[:8]:
        size = ""
        if fmt.get("filesize"):
            mb = fmt["filesize"] / (1024 * 1024)
            size = f" (~{mb:.1f}MB)"
        label = f"{'🎵' if fmt['kind'] == 'audio' else '🎬'} {fmt['resolution']} {fmt['ext']}{size}"
        keyboard.append(
            [
                InlineKeyboardButton(
                    label, callback_data=f"yt:download:{video_id}:{fmt['format_id']}"
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("🔙 اطلاعات ویدئو", callback_data=f"yt:video:{video_id}")]
    )

    await query.edit_message_text(
        "📥 *انتخاب فرمت دانلود:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return True


# -------------------------------------------------------------------
# 6. Download a video/audio and send it as a Telegram document
# -------------------------------------------------------------------
async def download_video(
    query, update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]
) -> bool:
    await query.answer("در حال آماده‌سازی فایل...")
    video_id = parts[2]
    format_id = parts[3]
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    state = context.application.bot_data["state"]
    settings = state.settings
    cookies_file = getattr(settings, "youtube_cookies_file", None)

    service = YouTubeService(
        enabled=True,
        cookies_file=cookies_file,
    )

    try:
        direct_url = await service.get_direct_url(video_url, format_id)
        if not direct_url:
            raise Exception("لینک دانلود مستقیم استخراج نشد.")
    except Exception as e:
        await query.edit_message_text(f"❌ خطا: {str(e)[:200]}")
        return True

    # Download the file (with size limit warning)
    try:
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            resp = await client.get(direct_url)
            resp.raise_for_status()
            content = resp.content
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > 50:
            await query.edit_message_text(
                f"⚠️ حجم فایل ({file_size_mb:.1f}MB) بیش از حد مجاز تلگرام است. امکان ارسال مستقیم وجود ندارد. لینک مستقیم:\n`{direct_url[:100]}...`",
                parse_mode="Markdown",
            )
            return True

        # Determine filename extension from format
        ext = "mp4" if "video" in format_id else "m4a"  # simplification
        filename = f"{video_id}.{ext}"
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=BytesIO(content),
            filename=filename,
            caption=f"🎬 دانلود شده از {video_url}",
        )
        await query.answer("✅ فایل با موفقیت ارسال شد.", show_alert=True)
    except Exception as e:
        await query.edit_message_text(f"❌ خطا در دانلود: {str(e)[:200]}")
    return True


# -------------------------------------------------------------------
# 7. Show original search results again (re-display)
# -------------------------------------------------------------------
async def show_search_results_yt(
    query, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    state = context.application.bot_data["state"]
    chat_id = update.effective_chat.id

    if chat_id not in state.youtube_results or not state.youtube_results[chat_id]:
        await query.answer(
            "نتایج جستجو منقضی شده است. دوباره جستجو کنید.", show_alert=True
        )
        return True

    results = state.youtube_results[chat_id]
    total = len(results)
    lines = [f"🎬 *نتایج جستجو* ({total} مورد)\n\n"]
    keyboard_rows = []
    row = []

    for idx, video in enumerate(results, start=1):
        lines.append(
            f"{idx}. [{video.title}]({video.url})\n"
            f"   👤 {video.channel_name} | ⏱ {video.duration} | 👀 {video.views:,}"
        )
        row.append(
            InlineKeyboardButton(str(idx), callback_data=f"yt:video:{video.video_id}")
        )
        if len(row) == 5:
            keyboard_rows.append(row)
            row = []

    if row:
        keyboard_rows.append(row)

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard_rows),
        disable_web_page_preview=True,
    )
    return True
