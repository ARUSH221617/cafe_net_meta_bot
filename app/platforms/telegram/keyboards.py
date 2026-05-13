from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

from app.core import text


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(text.CONTACT_BUTTON, request_contact=True)]], resize_keyboard=True, one_time_keyboard=True
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["بدهی‌های من", "تاریخچه پرداخت‌ها"], ["ارسال تیکت پشتیبانی"], ["جستجوی GitHub", "جستجوی YouTube"], ["راهنما"]],
        resize_keyboard=True,
    )


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("کاربران", callback_data="admin:users:1")],
            [InlineKeyboardButton("بدهی جدید", callback_data="admin:due:new")],
            [InlineKeyboardButton("پرداخت‌ها", callback_data="admin:payments:1")],
            [InlineKeyboardButton("تیکت‌ها", callback_data="admin:tickets:1")],
        ]
    )


def due_actions_keyboard(due_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("ارسال رسید پرداخت", callback_data=f"pay:start:{due_id}")]])


def payment_review_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("تأیید", callback_data=f"pay:approve:{payment_id}"), InlineKeyboardButton("رد", callback_data=f"pay:reject:{payment_id}")]]
    )


def ticket_actions_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("پاسخ", callback_data=f"admin:ticket:reply:{ticket_id}"), InlineKeyboardButton("بستن", callback_data=f"tickets:close:{ticket_id}")]]
    )
