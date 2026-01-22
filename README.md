# Hunter - PC Club Admin Web App

Веб-приложение на Flask для управления бронированиями компьютерного клуба, зонами и листами ожидания.
A Flask-based web application for managing PC club bookings, zones, and waitlists.

## Особенности / Features

- **Аутентификация администратора / Admin Authentication**: Безопасный вход с защитой паролем / Secure login with password protection
- **Управление ожидающими бронированиями / Pending Bookings Management**: Просмотр, подтверждение, отмена или удаление групп ожидающих бронирований / View, confirm, cancel, or delete pending booking groups
- **Список бронирований / Bookings List**: Фильтрация и управление всеми бронированиями с функцией удаления / Filter and manage all bookings with delete functionality
- **Управление ПК / PC Management**: Просмотр всех ПК и переключение их активного статуса / View all PCs and toggle their active status
- **Зоны / Zones**: Просмотр всех зон с информацией о ценах / View all zones with pricing information
- **Лист ожидания / Waitlist**: Отслеживание записей клиентов в листе ожидания / Track customer waitlist entries
- **Умное создание / Smart Create**: Интеллектуальный процесс создания бронирования с отображением доступных ПК для выбранных временных слотов / Intelligent booking creation flow that shows available PCs for selected time slots
- **Русский язык / Russian Language**: Полная поддержка русского языка в интерфейсе / Full Russian language support in the interface
- **Telegram бот / Telegram Bot**: Бот для клиентов для создания бронирований через Telegram / Bot for customers to create bookings via Telegram

## Установка / Setup

### Требования / Prerequisites

- Python 3.7 или выше / Python 3.7 or higher
- pip (менеджер пакетов Python / Python package manager)
- (Опционально) Telegram бот токен для бота / (Optional) Telegram bot token for the bot

### Установка / Installation

1. Клонируйте репозиторий / Clone the repository:
```bash
git clone https://github.com/baikadamrasul-lang/hunter.git
cd hunter
```

2. Создайте виртуальное окружение (рекомендуется) / Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Установите зависимости / Install dependencies:
```bash
pip install -r requirements.txt
```

4. Установите пароль администратора / Set the admin password environment variable:
```bash
export ADMIN_WEB_PASS=your_secure_password  # On Windows: set ADMIN_WEB_PASS=your_secure_password
```

5. (Опционально) Включите режим отладки для разработки / (Optional) Enable debug mode for development:
```bash
export FLASK_DEBUG=true  # On Windows: set FLASK_DEBUG=true
```

6. (Опционально) Для Telegram бота установите токен / (Optional) For Telegram bot, set the token:
```bash
export TELEGRAM_BOT_TOKEN=your_bot_token  # On Windows: set TELEGRAM_BOT_TOKEN=your_bot_token
```

### Запуск приложения / Running the Application

#### Веб-приложение администратора / Admin Web Application

Запустите сервер разработки Flask / Start the Flask development server:
```bash
python admin_app.py
```

Приложение будет доступно по адресу / The application will be available at `http://localhost:5000`

#### Telegram бот / Telegram Bot

Запустите Telegram бота / Start the Telegram bot:
```bash
python telegram_bot.py
```

Бот будет ожидать команд от пользователей Telegram / The bot will listen for commands from Telegram users.

### Первый запуск / First Run

При первом запуске приложение / On first run, the application will:
- Инициализирует базу данных SQLite (`club.db`) / Initialize the SQLite database (`club.db`)
- Создаст все необходимые таблицы / Create all necessary tables
- Заполнит базу данных зонами и ПК из `settings.json` / Seed the database with zones and PCs from `settings.json`

## Configuration

### settings.json

The `settings.json` file contains:

- **CLUB_TZ**: Timezone for the club (e.g., "Asia/Almaty")
- **SEED**: Initial data for zones and PCs
  - **zones**: List of zones with names and hourly rates
    - STANDART (500 ₸/hour)
    - COMFORT (700 ₸/hour)
    - VIP (1000 ₸/hour)
    - BOOT CAMP (600 ₸/hour)
    - PREMIUM ZONE (1200 ₸/hour)
  - **pcs**: List of PCs with their zone assignments
    - STANDART: PCs 1-25
    - COMFORT: PCs 26-43
    - BOOT CAMP: PCs 44-53
    - VIP: PCs 101-105
    - PREMIUM ZONE: PCs 106-115

## Использование / Usage

### Веб-приложение администратора / Admin Web Application

1. **Вход / Login**: Перейдите по URL приложения и войдите с паролем, установленным в `ADMIN_WEB_PASS` / Navigate to the application URL and log in with the password set in `ADMIN_WEB_PASS`

2. **Просмотр ожидающих бронирований / View Pending Bookings**: Нажмите "Ожидание" / "Pending" для просмотра всех групп ожидающих бронирований / Click "Pending" to see all pending booking groups
   - Подтвердите группу для пометки бронирований как подтвержденных / Confirm a group to mark bookings as confirmed
   - Отмените группу для пометки бронирований как отмененных / Cancel a group to mark bookings as cancelled
   - Удалите группу для окончательного удаления ожидающих бронирований / Delete a group to permanently remove pending bookings

3. **Управление бронированиями / Manage Bookings**: Нажмите "Бронирования" / "Bookings" для просмотра всех бронирований / Click "Bookings" to view all bookings
   - Фильтруйте по зоне или статусу / Filter by zone or status
   - Удаляйте отдельные бронирования / Delete individual bookings

4. **Управление ПК / Manage PCs**: Нажмите "Компьютеры" / "PCs" для просмотра всех ПК / Click "PCs" to view all PCs
   - Переключайте статус ПК активен/неактивен / Toggle PC active/inactive status

5. **Просмотр зон / View Zones**: Нажмите "Зоны" / "Zones" для просмотра всех зон и их цен / Click "Zones" to see all zones and their pricing

6. **Просмотр листа ожидания / View Waitlist**: Нажмите "Лист ожидания" / "Waitlist" для просмотра записей клиентов / Click "Waitlist" to see customer waitlist entries

7. **Умное создание / Smart Create**: Нажмите "Умное Создание" / "Smart Create" для создания новых бронирований / Click "Smart Create" to create new bookings
   - Выберите зону, время начала, длительность и количество ПК / Select zone, start time, duration, and number of PCs
   - Просмотрите доступные ПК для выбранного временного слота / View available PCs for the selected time slot
   - Выберите конкретные ПК и создайте бронирования / Choose specific PCs and create bookings

8. **Смена языка / Change Language**: Нажмите на флаг в верхнем правом углу для переключения между русским и английским / Click the flag in the top right corner to switch between Russian and English

### Telegram бот / Telegram Bot

Клиенты могут использовать Telegram бота для создания бронирований / Customers can use the Telegram bot to create bookings:

**Команды / Commands:**
- `/start` - Начать работу с ботом / Start working with the bot
- `/book` - Создать новое бронирование / Create a new booking
- `/mybookings` - Просмотреть свои бронирования / View your bookings
- `/zones` - Посмотреть зоны и цены / View zones and prices
- `/help` - Помощь / Help
- `/cancel` - Отменить текущее действие / Cancel current action

**Процесс бронирования / Booking Process:**
1. Отправьте команду `/book` / Send the `/book` command
2. Выберите зону / Select a zone
3. Выберите время начала / Select start time
4. Укажите длительность в часах / Specify duration in hours
5. Укажите количество компьютеров / Specify number of computers
6. Выберите конкретные ПК из доступных / Select specific PCs from available ones
7. Подтвердите бронирование / Confirm the booking

Бронирования созданные через Telegram появятся в веб-интерфейсе администратора со статусом "ожидание" / Bookings created via Telegram will appear in the admin web interface with "pending" status.

## Database Schema

- **zones**: PC zones with pricing
- **pcs**: Individual PCs assigned to zones
- **bookings**: Booking records with time slots and status
- **waitlist**: Customer waitlist entries

## Security

- Admin access is protected by password authentication via `ADMIN_WEB_PASS` environment variable
- Session-based authentication with Flask sessions
- Database stored in SQLite file (`club.db`)

## License

MIT