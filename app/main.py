import asyncio
import signal
import sys
import logging
from telegram.error import TimedOut
from app.core.config import get_settings
from app.core.enums import Platform
from app.core.logging import configure_logging
from app.platforms.telegram.app import TelegramPlatform
from app.platforms.bale.app import BalePlatform

settings = get_settings()
telegram = TelegramPlatform(settings)
bale = BalePlatform(settings)

_shutdown_in_progress = False


# ------------------------------------------------------------------
# Optional: shorten the read timeout for the final get_updates call
# to avoid waiting and showing a long traceback.
# ------------------------------------------------------------------
def _set_short_timeout(bot):
    from telegram.request import HTTPXRequest

    # 2 seconds connect + 2 seconds read
    bot._request = HTTPXRequest(connect_timeout=2.0, read_timeout=2.0)


if settings.bot_platform == Platform.TELEGRAM:
    # Uncomment if you can access the bot instance before run()
    # _set_short_timeout(telegram.application.bot)
    pass
# ------------------------------------------------------------------


async def _shutdown_bots():
    """Stop the active bot and exit gracefully."""
    global _shutdown_in_progress
    if _shutdown_in_progress:
        return
    _shutdown_in_progress = True

    print("\nShutting down gracefully...")

    try:
        if settings.bot_platform == Platform.TELEGRAM:
            # PTB's native stop method
            await telegram.application.stop()
            print("Telegram shut down successfully.")
        elif settings.bot_platform == Platform.BALE:
            # Use .stop() – NOT .shutdown()
            await bale.application.stop()
            print("Bale shut down successfully.")
    except TimedOut:
        logging.info("Timeout during final get_updates – ignored")
    except RuntimeError as e:
        # This can happen if stop() is called twice or while starting
        logging.info(f"RuntimeError during shutdown (ignored): {e}")
    except Exception as e:
        logging.warning(f"Unexpected error while stopping: {e}")

    # If the bot's run() method does not exit after a few seconds,
    # force the loop to stop. This is a safety net.
    loop = asyncio.get_running_loop()
    loop.call_later(5.0, loop.stop)


def _signal_handler(signum, frame):
    """Schedule the async shutdown on the running event loop."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_shutdown_bots())
    except RuntimeError:
        # No event loop running – exit immediately
        sys.exit(0)


def main() -> None:
    # Register our own signal handlers (overrides any default)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    configure_logging(settings.log_level)

    try:
        if settings.bot_platform == Platform.TELEGRAM:
            telegram.run()  # Blocking call, runs its own event loop
        elif settings.bot_platform == Platform.BALE:
            bale.run()
        else:
            raise NotImplementedError(
                "Only Telegram and Bale are implemented in the MVP"
            )
    except KeyboardInterrupt:
        print("\nReceived Ctrl+C, shutting down...")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
