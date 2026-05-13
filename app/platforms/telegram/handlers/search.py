from telegram import Update
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
    lines = []
    for index, repo in enumerate(results, start=1):
        lines.append(f"{index}. {repo.full_name}\n⭐ {repo.stars} | {repo.language or '-'}\n{repo.description or ''}")
    await update.effective_message.reply_text("\n\n".join(lines) + "\n\nدانلود مخزن به‌زودی فعال می‌شود.")
    return True
