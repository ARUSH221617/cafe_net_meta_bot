from telegram import Chat, Message, Update, User, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.core import text
from app.services.github import GitHubService


async def prompt_github_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.application.bot_data["state"].github_results[update.effective_chat.id] = []
    await update.effective_message.reply_text(text.GITHUB_QUERY_PROMPT)


async def handle_github_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    state = context.application.bot_data["state"]
    chat_id = update.effective_chat.id
    if chat_id not in state.github_results or state.github_results[chat_id]:
        return False
    service = GitHubService(state.settings.github_search_enabled)
    try:
        results = await service.search_repositories(update.message.text)
    except Exception:
        await update.effective_message.reply_text(text.GENERIC_ERROR)
        state.github_results.pop(chat_id, None)
        return True
    state.github_results[chat_id] = results
    if not results:
        await update.effective_message.reply_text(text.NO_RESULTS if state.settings.github_search_enabled else text.COMING_SOON)
        return True

    query_text = update.message.text
    total = len(results)
    header = f"*نتایج جستجو برای _{query_text}_* ({total} مورد)\n\n"
    lines = [header]

    # Build inline keyboard with numbered buttons (max 5 per row)
    keyboard_rows = []
    row = []
    
    for idx, repo in enumerate(results, start=1):
        # Safely get attributes with defaults
        full_name = getattr(repo, 'full_name', 'Unknown')
        html_url = getattr(repo, 'html_url', '#')
        language = getattr(repo, 'language', '-') or '-'
        stars = getattr(repo, 'stars', 0)
        forks = getattr(repo, 'forks_count', getattr(repo, 'forks', 0))  # fallback to 'forks' if exists
        description = getattr(repo, 'description', '') or ''

        row.append(InlineKeyboardButton(str(idx), callback_data=f"github:repo:{repo.html_url}"))
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

    await update.effective_message.reply_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return True


async def show_youtube_stub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(text.COMING_SOON)
