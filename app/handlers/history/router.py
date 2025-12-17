from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from app.guards import is_owner
from app.handlers.menus import main_menu
from .helpers import get_transactions_page, format_transaction_short, get_history_stats

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(lambda c: c.data == "history")
async def show_history(call: types.CallbackQuery, state: FSMContext):
    """Показать историю транзакций - первая страница"""
    if not is_owner(call.from_user.id):
        return

    await state.clear()
    await show_transactions_page(call, page=1)


async def show_transactions_page(call: types.CallbackQuery, page: int = 1, is_refresh: bool = False):
    """Показать конкретную страницу транзакций"""
    if not is_owner(call.from_user.id):
        return

    # Получаем данные
    transactions, total_pages, total_count = get_transactions_page(page=page, limit=20)
    stats = get_history_stats()

    # Рассчитываем баланс (total_outcome уже включает комиссии)
    actual_balance = stats['total_income'] - stats['total_outcome']

    # Формируем текст
    if not transactions:
        await call.message.edit_text(
            "📭 <b>История транзакций пуста</b>\n\n"
            "Создайте первую транзакцию через меню ➕",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
        await call.answer()
        return

    text_lines = [
        f"📜 <b>ИСТОРИЯ ТРАНЗАКЦИЙ</b>\n",
        f"• Всего: {total_count} транзакций",
        f"• 📥 Получено: <code>${stats['total_income']:,.2f}</code>",
        f"• 📤 Отправлено: <code>${stats['total_outcome']:,.2f}</code>",
        f"• 📊 Баланс: <code>${actual_balance:,.2f}</code>",
        f"\n<b>Страница {page}/{total_pages}:</b>\n"
    ]

    # Добавляем транзакции
    start_num = (page - 1) * 20 + 1
    for i, tx in enumerate(transactions, start=start_num):
        text_lines.append(f"{i}. {format_transaction_short(tx)}")

    text = "\n".join(text_lines)

    # Создаем клавиатуру пагинации
    keyboard_buttons = []

    # Кнопки навигации
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"page_{page - 1}"))

    nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="current_page"))

    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"page_{page + 1}"))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    # Кнопки быстрого перехода (если много страниц)
    if total_pages > 5:
        quick_nav = []
        if page > 1:
            quick_nav.append(InlineKeyboardButton(text="⏪ 1", callback_data="page_1"))
        if page > 3:
            quick_nav.append(InlineKeyboardButton(text=f"...", callback_data="current_page"))
        if page > 2:
            quick_nav.append(InlineKeyboardButton(text=f"{page - 1}", callback_data=f"page_{page - 1}"))

        quick_nav.append(InlineKeyboardButton(text=f"• {page} •", callback_data="current_page"))

        if page < total_pages - 1:
            quick_nav.append(InlineKeyboardButton(text=f"{page + 1}", callback_data=f"page_{page + 1}"))
        if page < total_pages - 2:
            quick_nav.append(InlineKeyboardButton(text=f"...", callback_data="current_page"))
        if page < total_pages:
            quick_nav.append(InlineKeyboardButton(text=f"{total_pages} ⏩", callback_data=f"page_{total_pages}"))

        if quick_nav:
            keyboard_buttons.append(quick_nav)

    # Кнопки действий
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="history_refresh"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    # Отправляем или редактируем сообщение
    try:
        if is_refresh:
            await call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Ошибка отображения истории: {e}")
            if not is_refresh:
                await call.message.answer(text, parse_mode="HTML", reply_markup=keyboard)

    await call.answer()


@router.callback_query(lambda c: c.data.startswith("page_"))
async def handle_page_navigation(call: types.CallbackQuery):
    """Обработка перехода по страницам"""
    try:
        page = int(call.data.replace("page_", ""))
        await show_transactions_page(call, page=page)
    except ValueError:
        await call.answer("❌ Неверный номер страницы")
    except Exception as e:
        logger.error(f"Ошибка навигации по страницам: {e}")
        await call.answer("❌ Ошибка загрузки страницы")


@router.callback_query(lambda c: c.data == "history_refresh")
async def refresh_history(call: types.CallbackQuery):
    """Обновить историю"""
    try:
        await show_transactions_page(call, page=1, is_refresh=True)
        await call.answer("🔄 История обновлена")
    except Exception as e:
        logger.error(f"Ошибка обновления истории: {e}")
        await call.answer("❌ Ошибка обновления", show_alert=True)