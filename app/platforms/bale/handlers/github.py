import httpx
from io import BytesIO
from typing import Optional

from telegram import CallbackQuery, Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
from telegram.ext import ContextTypes

from app.core import text
from app.services.github import GitHubService


async def handle_github_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]) -> bool:
    query = update.callback_query
    if query is None:
        return False
    
    action = parts[1] if len(parts) > 1 else ""
    
    match action:
        case "repo":
            return await load_github_repo(query, update, context, parts)
        case "download":
            return await load_github_releases_list(query, update, context, parts)
        case "release":
            return await load_github_release(query, update, context, parts)
        case "asset":
            return await download_github_asset(query, update, context, parts)
        case "tags":
            return await load_github_tags(query, update, context, parts)
        case "issues":
            return await load_github_issues(query, update, context, parts)
        case "commit":
            return await load_github_commits(query, update, context, parts)
        case "back_to_results":
            return await show_search_results(query, update, context)
        case _:
            return False
    
    return False


def _reconstruct_url(parts: list[str], start_idx: int) -> str:
    """Reconstruct a URL from split parts after 'github:' prefix.
    Assumes the URL was originally 'https://github.com/...' and got split into ['https', '//github.com/...'].
    """
    return f"{parts[start_idx]}:{parts[start_idx+1]}"


async def load_github_repo(query: CallbackQuery, update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]) -> bool:
    await query.answer()
    
    repo_url = _reconstruct_url(parts, 2)
    state = context.application.bot_data["state"]
    chat_id = update.effective_chat.id
    
    # Try to find the repository in cached results
    repo = None
    if chat_id in state.github_results:
        results = state.github_results[chat_id]
        for r in results:
            if getattr(r, 'html_url', '') == repo_url:
                repo = r
                break
    
    if repo is None:
        try:
            service = GitHubService(state.settings.github_search_enabled)
            repo = await service.get_repository(repo_url)
        except Exception:
            await query.edit_message_text("❌ خطا در دریافت اطلاعات مخزن. ممکن است مخزن حذف شده باشد.")
            return True
    
    if repo is None:
        await query.edit_message_text("❌ اطلاعات مخزن یافت نشد.")
        return True

    full_name = getattr(repo, 'full_name', 'Unknown')
    html_url = getattr(repo, 'html_url', repo_url)
    description = getattr(repo, 'description', '') or 'بدون توضیحات'
    language = getattr(repo, 'language', '-') or '-'
    stars = getattr(repo, 'stars', 0)
    forks = getattr(repo, 'forks_count', getattr(repo, 'forks', 0))
    watchers = getattr(repo, 'watchers_count', getattr(repo, 'watchers', 0))
    open_issues = getattr(repo, 'open_issues_count', getattr(repo, 'open_issues', 0))
    default_branch = getattr(repo, 'default_branch', 'main')
    created_at = getattr(repo, 'created_at', None)
    updated_at = getattr(repo, 'updated_at', None)
    topics = getattr(repo, 'topics', [])
    license_info = getattr(repo, 'license', None)
    owner_login = getattr(repo, 'owner_login', full_name.split('/')[0] if '/' in full_name else 'Unknown')
    owner_type = getattr(repo, 'owner_type', 'User')
    
    message_parts = [
        f"📦 *{full_name}*",
        f"",
        f"📝 {description}",
        f"",
        f"👤 *مالک:* {owner_login} ({owner_type})",
        f"🔤 *زبان اصلی:* {language}",
        f"⭐ *ستاره‌ها:* {stars:,}",
        f"🍴 *فورک‌ها:* {forks:,}",
        f"👁 *بازدیدها:* {watchers:,}",
        f"❗ *Issues باز:* {open_issues:,}",
        f"🌿 *شاخه پیش‌فرض:* {default_branch}",
    ]
    
    if topics:
        message_parts.append(f"🏷 *موضوعات:* {' '.join(f'`{t}`' for t in topics)}")
    
    if license_info:
        license_name = getattr(license_info, 'spdx_id', getattr(license_info, 'name', license_info if isinstance(license_info, str) else 'Unknown'))
        message_parts.append(f"📜 *مجوز:* {license_name}")
    
    if created_at:
        created_str = created_at.strftime('%Y-%m-%d') if hasattr(created_at, 'strftime') else str(created_at)
        message_parts.append(f"📅 *ساخته شده:* {created_str}")
    
    if updated_at:
        updated_str = updated_at.strftime('%Y-%m-%d') if hasattr(updated_at, 'strftime') else str(updated_at)
        message_parts.append(f"🔄 *آخرین بروزرسانی:* {updated_str}")
    
    message_parts.append(f"")
    message_parts.append(f"🔗 [مشاهده در GitHub]({html_url})")
    
    message_text = "\n".join(message_parts)
    
    keyboard = [
        [
            InlineKeyboardButton("📥 دانلود نسخه‌ها", callback_data=f"github:download:{repo_url}"),
        ],
        [
            InlineKeyboardButton("🏷 تگ‌ها و نسخه‌ها", callback_data=f"github:tags:{repo_url}"),
            InlineKeyboardButton("📝 Commit ها", callback_data=f"github:commit:{repo_url}"),
        ],
        [
            InlineKeyboardButton("❗ Issues", callback_data=f"github:issues:{repo_url}"),
        ],
        [
            InlineKeyboardButton("🔙 برگشت به نتایج جستجو", callback_data="github:back_to_results"),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
    return True


async def load_github_releases_list(query: CallbackQuery, update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]) -> bool:
    """Show a list of recent releases for the repository."""
    await query.answer()
    
    repo_url = _reconstruct_url(parts, 2)
    state = context.application.bot_data["state"]
    
    try:
        service = GitHubService(state.settings.github_search_enabled)
        releases = await service.get_releases(repo_url, limit=5)
    except Exception:
        await query.edit_message_text("❌ خطا در دریافت لیست نسخه‌ها.")
        return True
    
    if not releases:
        await query.edit_message_text(
            "📭 هیچ نسخه‌ای برای این مخزن منتشر نشده است.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 برگشت به اطلاعات مخزن", callback_data=f"github:repo:{repo_url}")
            ]])
        )
        return True
    
    message_text = f"📦 *نسخه‌های منتشر شده*\n\n"
    
    keyboard = []
    for release in releases[:5]:
        tag = release.get("tag_name", "Unknown")
        name = release.get("name") or tag
        published = release.get("published_at", "")[:10]
        release_id = release.get("id")
        btn_text = f"{name} ({published})" if published else name
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"github:release:{repo_url}:{release_id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 برگشت به اطلاعات مخزن", callback_data=f"github:repo:{repo_url}")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
    return True


async def load_github_release(query: CallbackQuery, update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]) -> bool:
    """Show details of a specific release and its assets."""
    await query.answer()
    
    repo_url = _reconstruct_url(parts, 2)
    release_id = parts[4]
    state = context.application.bot_data["state"]
    
    try:
        service = GitHubService(state.settings.github_search_enabled)
        release = await service.get_release(repo_url, int(release_id))
    except Exception:
        await query.edit_message_text("❌ خطا در دریافت اطلاعات نسخه.")
        return True
    
    if not release:
        await query.edit_message_text(
            "📭 نسخه مورد نظر یافت نشد.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 لیست نسخه‌ها", callback_data=f"github:download:{repo_url}")
            ]])
        )
        return True
    
    tag_name = release.get("tag_name", "Unknown")
    release_name = release.get("name") or tag_name
    body = release.get("body", "بدون توضیحات")[:1000]
    published_at = release.get("published_at", "")[:10]
    zipball_url = release.get("zipball_url")
    tarball_url = release.get("tarball_url")
    assets = release.get("assets", [])
    
    message_parts = [
        f"📦 *{release_name}*",
        f"🏷 `{tag_name}`",
        f"📅 {published_at}",
        f"",
        f"{body}",
    ]
    message_text = "\n".join(message_parts)
    
    keyboard = []
    
    # Source code download buttons (zip/tar)
    if zipball_url:
        keyboard.append([
            InlineKeyboardButton("📥 سورس کد (zip)", callback_data=f"github:asset:{repo_url}:{release_id}:sourcezip")
        ])
    if tarball_url:
        keyboard.append([
            InlineKeyboardButton("📥 سورس کد (tar.gz)", callback_data=f"github:asset:{repo_url}:{release_id}:sourcetar")
        ])
    
    # Asset buttons
    for idx, asset in enumerate(assets):
        asset_name = asset.get("name", "Unknown")
        asset_id = asset.get("id")
        size_kb = asset.get("size", 0) / 1024
        btn_text = f"📥 {asset_name} ({size_kb:.1f} KB)"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"github:asset:{repo_url}:{release_id}:asset:{asset_id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 لیست نسخه‌ها", callback_data=f"github:download:{repo_url}"),
        InlineKeyboardButton("📦 اطلاعات مخزن", callback_data=f"github:repo:{repo_url}"),
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
    return True


async def download_github_asset(query: CallbackQuery, update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]) -> bool:
    await query.answer("در حال دریافت فایل...")

    repo_url = _reconstruct_url(parts, 2)
    release_id = int(parts[4])
    asset_type = parts[5]
    asset_id = 0
    if asset_type == "asset":
        asset_id = int(parts[6])

    state = context.application.bot_data["state"]
    service = GitHubService(state.settings.github_search_enabled)

    try:
        if asset_type in ("sourcezip", "sourcetar"):
            release = await service.get_release(repo_url, release_id)
            if not release:
                await query.answer("نسخه یافت نشد.", show_alert=True)
                return True
            if asset_type == "sourcezip":
                download_url = release.get("zipball_url")
                file_name = f"{repo_url.split('/')[-1]}-{release.get('tag_name')}.zip"
            else:
                download_url = release.get("tarball_url")
                file_name = f"{repo_url.split('/')[-1]}-{release.get('tag_name')}.tar.gz"
            if not download_url:
                await query.answer("لینک دانلود موجود نیست.", show_alert=True)
                return True
        else:
            asset = await service.get_release_asset(repo_url, asset_id)
            if not asset:
                await query.answer("فایل مورد نظر یافت نشد.", show_alert=True)
                return True
            download_url = asset.get("browser_download_url")
            file_name = asset.get("name", "download")
            if not download_url:
                await query.answer("لینک دانلود موجود نیست.", show_alert=True)
                return True

        # دانلود فایل
        file_content = await service.download_file(download_url)

        # ارسال به عنوان سند
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=BytesIO(file_content),
            filename=file_name,
            caption=f"📦 فایل از {repo_url}"
        )

        # نمایش پیام موفقیت کوتاه (اختیاری)
        await query.answer("✅ فایل با موفقیت ارسال شد.", show_alert=False)
        return True

    except httpx.ConnectError:
        await query.answer("❌ اتصال به گیت‌هاب ممکن نیست. لطفاً بعداً تلاش کنید.", show_alert=True)
        return True
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 150:
            error_msg = error_msg[:150] + "..."
        await query.answer(f"❌ خطا: {error_msg}", show_alert=True)
        return True


async def load_github_tags(query: CallbackQuery, update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]) -> bool:
    await query.answer()
    
    repo_url = _reconstruct_url(parts, 2)
    state = context.application.bot_data["state"]
    
    try:
        service = GitHubService(state.settings.github_search_enabled)
        tags = await service.get_repository_tags(repo_url, limit=10)
    except Exception:
        await query.edit_message_text("❌ خطا در دریافت تگ‌ها.")
        return True
    
    if not tags:
        await query.edit_message_text(
            "📭 هیچ تگی برای این مخزن یافت نشد.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 برگشت به اطلاعات مخزن", callback_data=f"github:repo:{repo_url}")
            ]])
        )
        return True
    
    message_parts = [f"🏷 *تگ‌های مخزن*", f""]
    
    for idx, tag in enumerate(tags, 1):
        tag_name = tag.get("name", "Unknown")
        commit_sha = tag.get("commit", {}).get("sha", "")[:7]
        message_parts.append(f"{idx}. `{tag_name}` ({commit_sha})")
    
    message_text = "\n".join(message_parts)
    
    keyboard = [[
        InlineKeyboardButton("🔙 برگشت به اطلاعات مخزن", callback_data=f"github:repo:{repo_url}")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return True


async def load_github_issues(query: CallbackQuery, update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]) -> bool:
    await query.answer()
    
    repo_url = _reconstruct_url(parts, 2)
    state = context.application.bot_data["state"]
    
    try:
        service = GitHubService(state.settings.github_search_enabled)
        issues = await service.get_repository_issues(repo_url, limit=5)
    except Exception:
        await query.edit_message_text("❌ خطا در دریافت Issues.")
        return True
    
    if not issues:
        await query.edit_message_text(
            "✨ هیچ Issue بازی برای این مخزن وجود ندارد!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 برگشت به اطلاعات مخزن", callback_data=f"github:repo:{repo_url}")
            ]])
        )
        return True
    
    message_parts = [f"❗ *Issues باز*", f""]
    keyboard = []
    
    for idx, issue in enumerate(issues, 1):
        if "pull_request" in issue:
            continue
            
        issue_title = issue.get("title", "Unknown")
        issue_number = issue.get("number", 0)
        issue_url = issue.get("html_url", "#")
        issue_labels = issue.get("labels", [])
        created_at = issue.get("created_at", "")[:10]
        
        label_text = ""
        if issue_labels:
            label_names = [label.get("name", "") for label in issue_labels[:3]]
            label_text = f" [{', '.join(label_names)}]"
        
        message_parts.append(f"{idx}. [#{issue_number}]({issue_url}) {issue_title}{label_text}")
        message_parts.append(f"   📅 {created_at}")
        message_parts.append("")
        
        keyboard.append([
            InlineKeyboardButton(f"#{issue_number} - {issue_title[:50]}", url=issue_url)
        ])
    
    message_text = "\n".join(message_parts)
    
    keyboard.append([
        InlineKeyboardButton("🔙 برگشت به اطلاعات مخزن", callback_data=f"github:repo:{repo_url}")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
    return True


async def load_github_commits(query: CallbackQuery, update: Update, context: ContextTypes.DEFAULT_TYPE, parts: list[str]) -> bool:
    await query.answer()
    
    repo_url = _reconstruct_url(parts, 2)
    state = context.application.bot_data["state"]
    
    try:
        service = GitHubService(state.settings.github_search_enabled)
        commits = await service.get_repository_commits(repo_url, limit=5)
    except Exception:
        await query.edit_message_text("❌ خطا در دریافت Commit ها.")
        return True
    
    if not commits:
        await query.edit_message_text(
            "📭 هیچ Commiti برای این مخزن یافت نشد.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 برگشت به اطلاعات مخزن", callback_data=f"github:repo:{repo_url}")
            ]])
        )
        return True
    
    message_parts = [f"📝 *آخرین Commit ها*", f""]
    
    for idx, commit in enumerate(commits, 1):
        commit_message = commit.get("commit", {}).get("message", "Unknown").split("\n")[0][:100]
        commit_sha = commit.get("sha", "")[:7]
        commit_url = commit.get("html_url", "#")
        author_name = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
        date = commit.get("commit", {}).get("author", {}).get("date", "")[:10]
        
        message_parts.append(f"{idx}. [`{commit_sha}`]({commit_url}) {commit_message}")
        message_parts.append(f"   👤 {author_name} | 📅 {date}")
        message_parts.append("")
    
    message_text = "\n".join(message_parts)
    
    keyboard = [[
        InlineKeyboardButton("🔙 برگشت به اطلاعات مخزن", callback_data=f"github:repo:{repo_url}")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
    return True


async def show_search_results(query: CallbackQuery, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Show the original search results again."""
    state = context.application.bot_data["state"]
    chat_id = update.effective_chat.id
    
    if chat_id not in state.github_results or not state.github_results[chat_id]:
        await query.answer("نتایج جستجو منقضی شده است. لطفاً دوباره جستجو کنید.", show_alert=True)
        return True
    
    results = state.github_results[chat_id]
    
    total = len(results)
    header = f"*نتایج جستجو* ({total} مورد)\n\n"
    lines = [header]
    
    keyboard_rows = []
    row = []
    
    for idx, repo in enumerate(results, start=1):
        full_name = getattr(repo, 'full_name', 'Unknown')
        html_url = getattr(repo, 'html_url', '#')
        language = getattr(repo, 'language', '-') or '-'
        stars = getattr(repo, 'stars', 0)
        forks = getattr(repo, 'forks_count', getattr(repo, 'forks', 0))
        description = getattr(repo, 'description', '') or ''
        
        row.append(InlineKeyboardButton(str(idx), callback_data=f"github:repo:{html_url}"))
        if len(row) == 5:
            keyboard_rows.append(row)
            row = []
        
        repo_line = f"[*{full_name}*]({html_url}) [{language}]"
        stats_line = f"⭐ {stars} | 🍴 {forks}"
        lines.append(f"{idx}. {repo_line}\n{stats_line}\n{description}")
    
    message_text = "\n\n".join(lines)
    
    if row:
        keyboard_rows.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard_rows)
    
    await query.edit_message_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
    return True