#!/usr/bin/env python3
"""
PC Club Telegram Bot
Позволяет клиентам бронировать компьютеры через Telegram
"""
import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
import pytz

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load settings
with open('settings.json', 'r') as f:
    SETTINGS = json.load(f)

CLUB_TZ = pytz.timezone(SETTINGS['CLUB_TZ'])
DB_PATH = 'club.db'

# Bot token from environment
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN environment variable must be set!")
    exit(1)

# Conversation states
SELECTING_ZONE, SELECTING_TIME, SELECTING_DURATION, SELECTING_QTY, SELECTING_PCS = range(5)


def get_db():
    """Get database connection"""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    welcome_text = (
        "🎮 Добро пожаловать в бот ПК Клуба!\n\n"
        "Доступные команды:\n"
        "/book - Забронировать компьютер\n"
        "/mybookings - Мои бронирования\n"
        "/zones - Посмотреть зоны и цены\n"
        "/cancel - Отменить текущее действие\n"
        "/help - Помощь"
    )
    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = (
        "📖 Помощь по использованию бота\n\n"
        "🎯 Как забронировать:\n"
        "1. Используйте /book\n"
        "2. Выберите зону\n"
        "3. Выберите время начала\n"
        "4. Укажите длительность (часы)\n"
        "5. Укажите количество ПК\n"
        "6. Выберите свободные компьютеры\n"
        "7. Подтвердите бронирование\n\n"
        "📋 Другие команды:\n"
        "/mybookings - Посмотреть свои бронирования\n"
        "/zones - Информация о зонах и ценах\n"
        "/cancel - Отменить текущее действие"
    )
    await update.message.reply_text(help_text)


async def zones_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show zones and prices"""
    db = get_db()
    cursor = db.execute('SELECT name, price_per_hour FROM zones WHERE active = 1 ORDER BY name')
    zones = cursor.fetchall()
    db.close()
    
    text = "🏢 Зоны и цены:\n\n"
    for zone in zones:
        text += f"• {zone['name']}: {zone['price_per_hour']} ₸/час\n"
    
    await update.message.reply_text(text)


async def book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start booking process - select zone"""
    db = get_db()
    cursor = db.execute('SELECT id, name, price_per_hour FROM zones WHERE active = 1 ORDER BY name')
    zones = cursor.fetchall()
    db.close()
    
    keyboard = []
    for zone in zones:
        keyboard.append([InlineKeyboardButton(
            f"{zone['name']} ({zone['price_per_hour']} ₸/час)",
            callback_data=f"zone_{zone['id']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏢 Выберите зону:",
        reply_markup=reply_markup
    )
    
    return SELECTING_ZONE


async def select_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle zone selection"""
    query = update.callback_query
    await query.answer()
    
    zone_id = int(query.data.split('_')[1])
    context.user_data['zone_id'] = zone_id
    
    # Get zone name
    db = get_db()
    cursor = db.execute('SELECT name FROM zones WHERE id = ?', (zone_id,))
    zone = cursor.fetchone()
    db.close()
    
    context.user_data['zone_name'] = zone['name']
    
    # Generate time slots
    now = datetime.now(CLUB_TZ)
    keyboard = []
    
    for i in range(0, 48, 2):  # Show slots every 2 hours for next 48 hours
        slot_time = now + timedelta(hours=i)
        keyboard.append([InlineKeyboardButton(
            slot_time.strftime('%d.%m %H:%M'),
            callback_data=f"time_{slot_time.strftime('%Y-%m-%d_%H:%M')}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Зона: {zone['name']}\n\n⏰ Выберите время начала:",
        reply_markup=reply_markup
    )
    
    return SELECTING_TIME


async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle time selection"""
    query = update.callback_query
    await query.answer()
    
    time_str = query.data.split('_', 1)[1].replace('_', ' ')
    context.user_data['start_time'] = time_str
    
    keyboard = [
        [InlineKeyboardButton("1 час", callback_data="duration_1")],
        [InlineKeyboardButton("2 часа", callback_data="duration_2")],
        [InlineKeyboardButton("3 часа", callback_data="duration_3")],
        [InlineKeyboardButton("4 часа", callback_data="duration_4")],
        [InlineKeyboardButton("Другое (введите число)", callback_data="duration_custom")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Зона: {context.user_data['zone_name']}\n"
        f"Время: {time_str}\n\n"
        "⏱️ Выберите длительность:",
        reply_markup=reply_markup
    )
    
    return SELECTING_DURATION


async def select_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle duration selection"""
    query = update.callback_query
    await query.answer()
    
    duration_data = query.data.split('_')[1]
    
    if duration_data == 'custom':
        await query.edit_message_text(
            "✏️ Введите количество часов (например: 2.5):"
        )
        return SELECTING_DURATION
    
    duration = float(duration_data)
    context.user_data['duration'] = duration
    
    keyboard = [
        [InlineKeyboardButton("1 ПК", callback_data="qty_1")],
        [InlineKeyboardButton("2 ПК", callback_data="qty_2")],
        [InlineKeyboardButton("3 ПК", callback_data="qty_3")],
        [InlineKeyboardButton("Другое (введите число)", callback_data="qty_custom")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Зона: {context.user_data['zone_name']}\n"
        f"Время: {context.user_data['start_time']}\n"
        f"Длительность: {duration} ч\n\n"
        "🖥️ Сколько компьютеров?",
        reply_markup=reply_markup
    )
    
    return SELECTING_QTY


async def handle_custom_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom duration input"""
    try:
        duration = float(update.message.text)
        if duration <= 0 or duration > 24:
            await update.message.reply_text("❌ Пожалуйста, введите число от 0.5 до 24")
            return SELECTING_DURATION
        
        context.user_data['duration'] = duration
        
        keyboard = [
            [InlineKeyboardButton("1 ПК", callback_data="qty_1")],
            [InlineKeyboardButton("2 ПК", callback_data="qty_2")],
            [InlineKeyboardButton("3 ПК", callback_data="qty_3")],
            [InlineKeyboardButton("Другое (введите число)", callback_data="qty_custom")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Зона: {context.user_data['zone_name']}\n"
            f"Время: {context.user_data['start_time']}\n"
            f"Длительность: {duration} ч\n\n"
            "🖥️ Сколько компьютеров?",
            reply_markup=reply_markup
        )
        
        return SELECTING_QTY
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректное число")
        return SELECTING_DURATION


async def select_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quantity selection"""
    query = update.callback_query
    await query.answer()
    
    qty_data = query.data.split('_')[1]
    
    if qty_data == 'custom':
        await query.edit_message_text(
            "✏️ Введите количество компьютеров:"
        )
        return SELECTING_QTY
    
    qty = int(qty_data)
    context.user_data['qty'] = qty
    
    # Find available PCs
    db = get_db()
    zone_id = context.user_data['zone_id']
    start_time = context.user_data['start_time']
    duration = context.user_data['duration']
    
    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
    end_dt = start_dt + timedelta(hours=duration)
    end_time = end_dt.strftime('%Y-%m-%d %H:%M')
    
    # Get all PCs in zone
    cursor = db.execute('''
        SELECT p.id, p.number
        FROM pcs p
        WHERE p.zone_id = ? AND p.active = 1
        ORDER BY p.number
    ''', (zone_id,))
    all_pcs = cursor.fetchall()
    
    # Check which are free
    free_pcs = []
    for pc in all_pcs:
        cursor = db.execute('''
            SELECT COUNT(*) as count
            FROM bookings
            WHERE pc_id = ?
              AND status IN ('pending', 'confirmed')
              AND NOT (end_time <= ? OR start_time >= ?)
        ''', (pc['id'], start_time, end_time))
        
        if cursor.fetchone()['count'] == 0:
            free_pcs.append(dict(pc))
    
    db.close()
    
    if len(free_pcs) < qty:
        await query.edit_message_text(
            f"❌ К сожалению, свободно только {len(free_pcs)} ПК.\n"
            "Попробуйте выбрать другое время или зону.\n\n"
            "Используйте /book для новой попытки."
        )
        return ConversationHandler.END
    
    # Show available PCs
    keyboard = []
    for pc in free_pcs[:10]:  # Show max 10 PCs at a time
        keyboard.append([InlineKeyboardButton(
            f"ПК #{pc['number']}",
            callback_data=f"pc_{pc['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        "✅ Подтвердить выбор",
        callback_data="confirm_pcs"
    )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['available_pcs'] = free_pcs
    context.user_data['selected_pcs'] = []
    
    await query.edit_message_text(
        f"Зона: {context.user_data['zone_name']}\n"
        f"Время: {start_time}\n"
        f"Длительность: {duration} ч\n"
        f"Количество: {qty} ПК\n\n"
        f"🖥️ Доступно {len(free_pcs)} ПК. Выберите {qty} компьютеров:",
        reply_markup=reply_markup
    )
    
    return SELECTING_PCS


async def handle_custom_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom quantity input"""
    try:
        qty = int(update.message.text)
        if qty <= 0 or qty > 10:
            await update.message.reply_text("❌ Пожалуйста, введите число от 1 до 10")
            return SELECTING_QTY
        
        context.user_data['qty'] = qty
        
        # Find available PCs
        db = get_db()
        zone_id = context.user_data['zone_id']
        start_time = context.user_data['start_time']
        duration = context.user_data['duration']
        
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        end_dt = start_dt + timedelta(hours=duration)
        end_time = end_dt.strftime('%Y-%m-%d %H:%M')
        
        # Get all PCs in zone
        cursor = db.execute('''
            SELECT p.id, p.number
            FROM pcs p
            WHERE p.zone_id = ? AND p.active = 1
            ORDER BY p.number
        ''', (zone_id,))
        all_pcs = cursor.fetchall()
        
        # Check which are free
        free_pcs = []
        for pc in all_pcs:
            cursor = db.execute('''
                SELECT COUNT(*) as count
                FROM bookings
                WHERE pc_id = ?
                  AND status IN ('pending', 'confirmed')
                  AND NOT (end_time <= ? OR start_time >= ?)
            ''', (pc['id'], start_time, end_time))
            
            if cursor.fetchone()['count'] == 0:
                free_pcs.append(dict(pc))
        
        db.close()
        
        if len(free_pcs) < qty:
            await update.message.reply_text(
                f"❌ К сожалению, свободно только {len(free_pcs)} ПК.\n"
                "Попробуйте выбрать другое время или зону.\n\n"
                "Используйте /book для новой попытки."
            )
            return ConversationHandler.END
        
        # Show available PCs
        keyboard = []
        for pc in free_pcs[:10]:  # Show max 10 PCs at a time
            keyboard.append([InlineKeyboardButton(
                f"ПК #{pc['number']}",
                callback_data=f"pc_{pc['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            "✅ Подтвердить выбор",
            callback_data="confirm_pcs"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.user_data['available_pcs'] = free_pcs
        context.user_data['selected_pcs'] = []
        
        await update.message.reply_text(
            f"Зона: {context.user_data['zone_name']}\n"
            f"Время: {start_time}\n"
            f"Длительность: {duration} ч\n"
            f"Количество: {qty} ПК\n\n"
            f"🖥️ Доступно {len(free_pcs)} ПК. Выберите {qty} компьютеров:",
            reply_markup=reply_markup
        )
        
        return SELECTING_PCS
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректное число")
        return SELECTING_QTY


async def select_pc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PC selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_pcs":
        # Confirm selection
        selected_pcs = context.user_data.get('selected_pcs', [])
        qty = context.user_data['qty']
        
        if len(selected_pcs) != qty:
            await query.answer(
                f"⚠️ Выберите ровно {qty} ПК (выбрано: {len(selected_pcs)})",
                show_alert=True
            )
            return SELECTING_PCS
        
        # Create bookings
        db = get_db()
        user_id = update.effective_user.id
        group_id = f"tg_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        start_time = context.user_data['start_time']
        duration = context.user_data['duration']
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        end_dt = start_dt + timedelta(hours=duration)
        end_time = end_dt.strftime('%Y-%m-%d %H:%M')
        
        for pc_id in selected_pcs:
            db.execute(
                'INSERT INTO bookings (pc_id, start_time, end_time, group_id, status) VALUES (?, ?, ?, ?, ?)',
                (pc_id, start_time, end_time, group_id, 'pending')
            )
        
        db.commit()
        db.close()
        
        # Get zone price
        db = get_db()
        cursor = db.execute('SELECT price_per_hour FROM zones WHERE id = ?', (context.user_data['zone_id'],))
        zone = cursor.fetchone()
        db.close()
        
        total_cost = zone['price_per_hour'] * duration * qty
        
        await query.edit_message_text(
            f"✅ Бронирование создано!\n\n"
            f"🏢 Зона: {context.user_data['zone_name']}\n"
            f"⏰ Время: {start_time}\n"
            f"⏱️ Длительность: {duration} ч\n"
            f"🖥️ Компьютеры: {qty} ПК\n"
            f"💰 Стоимость: {total_cost:.0f} ₸\n\n"
            f"📋 ID группы: {group_id}\n"
            f"Статус: Ожидает подтверждения администратором\n\n"
            "Используйте /mybookings для просмотра своих бронирований."
        )
        
        return ConversationHandler.END
    
    # Toggle PC selection
    pc_id = int(query.data.split('_')[1])
    selected_pcs = context.user_data.get('selected_pcs', [])
    
    if pc_id in selected_pcs:
        selected_pcs.remove(pc_id)
    else:
        selected_pcs.append(pc_id)
    
    context.user_data['selected_pcs'] = selected_pcs
    
    # Update keyboard
    available_pcs = context.user_data['available_pcs']
    keyboard = []
    
    for pc in available_pcs[:10]:
        text = f"ПК #{pc['number']}"
        if pc['id'] in selected_pcs:
            text = f"✓ {text}"
        
        keyboard.append([InlineKeyboardButton(
            text,
            callback_data=f"pc_{pc['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        f"✅ Подтвердить выбор ({len(selected_pcs)}/{context.user_data['qty']})",
        callback_data="confirm_pcs"
    )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_reply_markup(reply_markup=reply_markup)
    
    return SELECTING_PCS


async def my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's bookings"""
    user_id = update.effective_user.id
    
    db = get_db()
    cursor = db.execute('''
        SELECT b.id, b.start_time, b.end_time, b.status, b.group_id,
               p.number as pc_number, z.name as zone_name
        FROM bookings b
        JOIN pcs p ON b.pc_id = p.id
        JOIN zones z ON p.zone_id = z.id
        WHERE b.group_id LIKE ?
        ORDER BY b.start_time DESC
        LIMIT 20
    ''', (f'tg_{user_id}%',))
    
    bookings = cursor.fetchall()
    db.close()
    
    if not bookings:
        await update.message.reply_text(
            "📋 У вас пока нет бронирований.\n"
            "Используйте /book для создания бронирования."
        )
        return
    
    text = "📋 Ваши бронирования:\n\n"
    
    current_group = None
    for booking in bookings:
        if booking['group_id'] != current_group:
            current_group = booking['group_id']
            status_emoji = {
                'pending': '⏳',
                'confirmed': '✅',
                'cancelled': '❌'
            }.get(booking['status'], '❓')
            
            text += f"\n{status_emoji} Группа: {booking['group_id']}\n"
            text += f"Время: {booking['start_time']} - {booking['end_time']}\n"
        
        text += f"  • ПК #{booking['pc_number']} ({booking['zone_name']})\n"
    
    await update.message.reply_text(text)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current conversation"""
    await update.message.reply_text(
        "❌ Действие отменено.\n"
        "Используйте /book для создания нового бронирования."
    )
    return ConversationHandler.END


def main():
    """Run the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add conversation handler for booking
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('book', book_start)],
        states={
            SELECTING_ZONE: [CallbackQueryHandler(select_zone, pattern='^zone_')],
            SELECTING_TIME: [CallbackQueryHandler(select_time, pattern='^time_')],
            SELECTING_DURATION: [
                CallbackQueryHandler(select_duration, pattern='^duration_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_duration)
            ],
            SELECTING_QTY: [
                CallbackQueryHandler(select_qty, pattern='^qty_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_qty)
            ],
            SELECTING_PCS: [CallbackQueryHandler(select_pc)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Add command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('zones', zones_command))
    application.add_handler(CommandHandler('mybookings', my_bookings))
    
    # Run the bot
    logger.info("Starting Telegram bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
