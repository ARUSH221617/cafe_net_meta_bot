# CafeNet Multi-Platform Bot

CafeNet bot is a modular Python bot for CafeNet automation. The MVP implements Telegram first, keeps business logic platform-neutral, and leaves a Bale adapter scaffold for a later Telegram-compatible Bot API integration.

## MVP Features

- Persian Telegram bot UI
- Registration with shared phone number
- Stable identity by platform ID, with optional username storage
- Admin access from `.env` IDs plus database roles
- User dues list and payment receipt submission
- Receipt metadata storage by Telegram file ID
- Admin payment approval/rejection
- Support ticket creation, admin reply, and close flow
- Basic admin panel and `/admin_due` command
- GitHub repository search with download stub
- YouTube feature placeholder
- SQLite database with SQLModel and Alembic
- Configurable polling or webhook runtime

## Out Of Scope For MVP

- Bale runtime adapter
- YouTube downloads and audio extraction
- GitHub ZIP/release downloads
- 5 MB file splitting
- Payment gateway integration
- Admin web dashboard
- External receipt/object storage
- Multi-language switching

## Project Structure

```text
app/
├── core/                  # Settings, enums, logging, Persian copy
├── database/              # SQLModel models, session, repositories
├── platforms/             # Telegram adapter and Bale scaffold
├── services/              # Business rules independent from Telegram
└── utils/                 # Formatting, pagination, small helpers
alembic/                   # Database migrations
tests/                     # Unit and service tests
```

## Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create local config:

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_BOT_TOKEN=your-token
ADMIN_TELEGRAM_IDS=123456789
RUN_MODE=polling
DATABASE_URL=sqlite:///./cafebot.db
```

Run migrations:

```bash
alembic upgrade head
```

Start with polling:

```bash
python -m app.main
```

For webhook mode, set:

```env
RUN_MODE=webhook
WEBHOOK_URL=https://example.com/telegram/webhook
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8080
```

Then run the same command:

```bash
python -m app.main
```

## Admin Usage

Open the bot from an ID listed in `ADMIN_TELEGRAM_IDS`, then use:

```text
/admin
```

Create a due with:

```text
/admin_due USER_ID AMOUNT_IRR TITLE
```

Example:

```text
/admin_due 1 250000 هزینه اینترنت
```

## Development

Run tests:

```bash
pytest
```

The service layer should stay free of Telegram imports. Telegram-specific update parsing, keyboards, and callback data belong under `app/platforms/telegram/`.
