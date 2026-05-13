from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.core.config import Settings
from app.core.enums import RunMode
from app.platforms.base import BotPlatform
from app.platforms.bale.context import RuntimeState
from app.platforms.bale.handlers.admin import admin_command, admin_due_command
from app.platforms.bale.handlers.callbacks import callback_router
from app.platforms.bale.handlers.errors import error_handler
from app.platforms.bale.handlers.messages import message_router
from app.platforms.bale.handlers.registration import handle_contact
from app.platforms.bale.handlers.start import start


class BalePlatform(BotPlatform):
    def __init__(self, settings: Settings) -> None:
        print(settings.bale_api_base_url)
        self.settings = settings
        self.application = Application.builder().base_url(settings.bale_api_base_url).token(settings.bale_bot_token).build()
        self.application.bot_data["state"] = RuntimeState(settings=settings)
        self.register_handlers()

    def register_handlers(self) -> None:
        self.application.add_handler(CommandHandler("start", start))
        self.application.add_handler(CommandHandler("admin", admin_command))
        self.application.add_handler(CommandHandler("admin_due", admin_due_command))
        self.application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
        self.application.add_handler(CallbackQueryHandler(callback_router))
        self.application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_router))
        self.application.add_error_handler(error_handler)

    def run(self) -> None:
        if self.settings.run_mode == RunMode.WEBHOOK:
            self.application.run_webhook(
                listen=self.settings.webhook_host,
                port=self.settings.webhook_port,
                webhook_url=self.settings.webhook_url,
            )
            return
        self.application.run_polling(allowed_updates=None)
