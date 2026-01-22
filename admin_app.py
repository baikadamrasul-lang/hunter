#!/usr/bin/env python3
"""
PC Club Admin Web Application
"""
import os
import json
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_babel import Babel, gettext as _
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure Babel for internationalization
app.config['BABEL_DEFAULT_LOCALE'] = 'ru'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

def get_locale():
    # Try to get language from session, otherwise use default
    return session.get('language', 'ru')

babel = Babel(app, locale_selector=get_locale)

# Load settings
with open('settings.json', 'r') as f:
    SETTINGS = json.load(f)

CLUB_TZ = pytz.timezone(SETTINGS['CLUB_TZ'])
DB_PATH = 'club.db'

# Admin password from environment
ADMIN_PASSWORD = os.environ.get('ADMIN_WEB_PASS')

if not ADMIN_PASSWORD:
    print("ERROR: ADMIN_WEB_PASS environment variable must be set!")
    exit(1)


def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database schema"""
    db = get_db()
    
    # Create tables
    db.execute('''
        CREATE TABLE IF NOT EXISTS zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            price_per_hour INTEGER NOT NULL,
            active INTEGER DEFAULT 1
        )
    ''')
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS pcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number INTEGER UNIQUE NOT NULL,
            zone_id INTEGER NOT NULL,
            active INTEGER DEFAULT 1,
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        )
    ''')
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pc_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            group_id TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            customer_telegram_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pc_id) REFERENCES pcs(id)
        )
    ''')
    
    # Add new columns if they don't exist (for existing databases)
    try:
        db.execute('ALTER TABLE bookings ADD COLUMN customer_name TEXT')
    except:
        pass
    try:
        db.execute('ALTER TABLE bookings ADD COLUMN customer_phone TEXT')
    except:
        pass
    try:
        db.execute('ALTER TABLE bookings ADD COLUMN customer_telegram_id TEXT')
    except:
        pass
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id INTEGER NOT NULL,
            requested_pcs INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            duration_hours REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        )
    ''')
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT NOT NULL,
            message TEXT NOT NULL,
            sent INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    db.commit()


def sync_seed_data():
    """Sync seed data from settings.json"""
    db = get_db()
    
    # Sync zones
    for zone_data in SETTINGS['SEED']['zones']:
        cursor = db.execute(
            'SELECT id FROM zones WHERE name = ?',
            (zone_data['name'],)
        )
        if not cursor.fetchone():
            db.execute(
                'INSERT INTO zones (name, price_per_hour) VALUES (?, ?)',
                (zone_data['name'], zone_data['price_per_hour'])
            )
    
    # Sync PCs
    for pc_data in SETTINGS['SEED']['pcs']:
        # Get zone_id
        cursor = db.execute(
            'SELECT id FROM zones WHERE name = ?',
            (pc_data['zone'],)
        )
        zone = cursor.fetchone()
        if zone:
            zone_id = zone['id']
            cursor = db.execute(
                'SELECT id FROM pcs WHERE number = ?',
                (pc_data['number'],)
            )
            if not cursor.fetchone():
                db.execute(
                    'INSERT INTO pcs (number, zone_id) VALUES (?, ?)',
                    (pc_data['number'], zone_id)
                )
    
    db.commit()


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('pending'))
        else:
            flash(_('Invalid password'), 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout"""
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/language/<lang>')
def set_language(lang):
    """Set language preference"""
    session['language'] = lang
    return redirect(request.referrer or url_for('index'))


@app.route('/')
@login_required
def index():
    """Home page - redirect to pending"""
    return redirect(url_for('pending'))


@app.route('/pending')
@login_required
def pending():
    """Pending bookings page with group actions"""
    db = get_db()
    
    # Get all pending bookings grouped by group_id
    cursor = db.execute('''
        SELECT b.id, b.group_id, b.start_time, b.end_time, b.created_at,
               p.number as pc_number, z.name as zone_name
        FROM bookings b
        JOIN pcs p ON b.pc_id = p.id
        JOIN zones z ON p.zone_id = z.id
        WHERE b.status = 'pending'
        ORDER BY b.group_id, b.start_time, p.number
    ''')
    
    bookings = cursor.fetchall()
    
    # Group bookings by group_id
    groups = {}
    for booking in bookings:
        group_id = booking['group_id'] or f"single_{booking['id']}"
        if group_id not in groups:
            groups[group_id] = []
        groups[group_id].append(dict(booking))
    
    # Convert to list for template
    grouped_items = [{'group_id': k, 'bookings': v} for k, v in groups.items()]
    
    return render_template('pending.html', items=grouped_items)


@app.route('/pending/confirm/<group_id>', methods=['POST'])
@login_required
def confirm_group(group_id):
    """Confirm a pending group"""
    db = get_db()
    
    # Get bookings with customer telegram IDs before confirming
    cursor = db.execute('''
        SELECT DISTINCT customer_telegram_id, customer_name
        FROM bookings
        WHERE group_id = ? AND status = 'pending' AND customer_telegram_id IS NOT NULL
    ''', (group_id,))
    customers = cursor.fetchall()
    
    db.execute(
        'UPDATE bookings SET status = ? WHERE group_id = ? AND status = ?',
        ('confirmed', group_id, 'pending')
    )
    db.commit()
    
    # Send notifications to customers via Telegram
    # Note: This requires the bot to be running and accessible
    # Store notification in a table or use a webhook
    # For now, we'll add a simple notification mechanism
    for customer in customers:
        if customer['customer_telegram_id']:
            # Booking rules message
            rules_message = (
                f"✅ Ваше бронирование подтверждено администратором!\n\n"
                f"🔴ВАЖНО🔴 - Правила брони!!!\n\n"
                f"1. Бронь держится 15 мин, после переходит к следующему игроку.\n\n"
                f"2. Бронь больше 5 ПК оплата 50% от общей суммы.\n\n"
                f"3. В случае отмены брони менее чем за 4 часа аванс не возвращается! "
                f"(Повторная отмена брони, номер телефона добавляется в черный список)\n\n"
                f"4. В случае неявки номер телефона добавляется в черный список."
            )
            # Store notification for bot to send
            db.execute('''
                INSERT INTO notifications (telegram_id, message, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (customer['customer_telegram_id'], rules_message))
    
    db.commit()
    flash(_('Group %s confirmed') % group_id, 'success')
    return redirect(url_for('pending'))


@app.route('/pending/cancel/<group_id>', methods=['POST'])
@login_required
def cancel_group(group_id):
    """Cancel a pending group"""
    db = get_db()
    db.execute(
        'UPDATE bookings SET status = ? WHERE group_id = ? AND status = ?',
        ('cancelled', group_id, 'pending')
    )
    db.commit()
    flash(_('Group %s cancelled') % group_id, 'success')
    return redirect(url_for('pending'))


@app.route('/pending/delete/<group_id>', methods=['POST'])
@login_required
def delete_group(group_id):
    """Delete a pending group"""
    db = get_db()
    db.execute(
        'DELETE FROM bookings WHERE group_id = ? AND status = ?',
        (group_id, 'pending')
    )
    db.commit()
    flash(_('Group %s deleted') % group_id, 'success')
    return redirect(url_for('pending'))


@app.route('/bookings')
@login_required
def bookings():
    """Bookings list with filters"""
    db = get_db()
    
    # Get filter parameters
    zone_filter = request.args.get('zone')
    status_filter = request.args.get('status')
    
    # Build query
    query = '''
        SELECT b.id, b.start_time, b.end_time, b.status, b.group_id, b.created_at,
               b.customer_name, b.customer_phone,
               p.number as pc_number, z.name as zone_name
        FROM bookings b
        JOIN pcs p ON b.pc_id = p.id
        JOIN zones z ON p.zone_id = z.id
        WHERE 1=1
    '''
    params = []
    
    if zone_filter:
        query += ' AND z.name = ?'
        params.append(zone_filter)
    
    if status_filter:
        query += ' AND b.status = ?'
        params.append(status_filter)
    
    query += ' ORDER BY b.start_time DESC, p.number'
    
    cursor = db.execute(query, params)
    booking_list = [dict(row) for row in cursor.fetchall()]
    
    # Get zones for filter dropdown
    cursor = db.execute('SELECT name FROM zones ORDER BY name')
    zones = [row['name'] for row in cursor.fetchall()]
    
    return render_template('bookings.html', bookings=booking_list, zones=zones,
                         selected_zone=zone_filter, selected_status=status_filter)


@app.route('/booking/delete/<int:booking_id>', methods=['POST'])
@login_required
def delete_booking(booking_id):
    """Delete a single booking"""
    db = get_db()
    db.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
    db.commit()
    flash(_('Booking %d deleted') % booking_id, 'success')
    return redirect(url_for('bookings'))


@app.route('/pcs')
@login_required
def pcs():
    """PCs list with toggle active"""
    db = get_db()
    cursor = db.execute('''
        SELECT p.id, p.number, p.active, z.name as zone_name
        FROM pcs p
        JOIN zones z ON p.zone_id = z.id
        ORDER BY p.number
    ''')
    pc_list = [dict(row) for row in cursor.fetchall()]
    
    return render_template('pcs.html', pcs=pc_list)


@app.route('/pc/toggle/<int:pc_id>', methods=['POST'])
@login_required
def toggle_pc(pc_id):
    """Toggle PC active status"""
    db = get_db()
    cursor = db.execute('SELECT active FROM pcs WHERE id = ?', (pc_id,))
    pc = cursor.fetchone()
    if pc:
        new_status = 0 if pc['active'] else 1
        db.execute('UPDATE pcs SET active = ? WHERE id = ?', (new_status, pc_id))
        db.commit()
        flash(_('PC status updated'), 'success')
    return redirect(url_for('pcs'))


@app.route('/pc/occupy/<int:pc_id>', methods=['POST'])
@login_required
def occupy_pc(pc_id):
    """Mark PC as occupied for walk-in customer"""
    db = get_db()
    
    customer_name = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    duration = float(request.form.get('duration', 1))
    
    if not customer_name or not customer_phone:
        flash('Customer name and phone are required', 'error')
        return redirect(url_for('pcs'))
    
    # Create occupied booking starting now
    now = datetime.now(CLUB_TZ)
    start_time = now.strftime('%Y-%m-%d %H:%M')
    end_time = (now + timedelta(hours=duration)).strftime('%Y-%m-%d %H:%M')
    group_id = f"walk_in_{now.strftime('%Y%m%d%H%M%S')}"
    
    db.execute('''
        INSERT INTO bookings (pc_id, start_time, end_time, status, group_id, customer_name, customer_phone)
        VALUES (?, ?, ?, 'occupied', ?, ?, ?)
    ''', (pc_id, start_time, end_time, group_id, customer_name, customer_phone))
    
    db.commit()
    flash(f'PC marked as occupied for {customer_name}', 'success')
    return redirect(url_for('pcs'))


@app.route('/zones')
@login_required
def zones():
    """Zones list"""
    db = get_db()
    cursor = db.execute('SELECT * FROM zones ORDER BY name')
    zone_list = [dict(row) for row in cursor.fetchall()]
    
    return render_template('zones.html', zones=zone_list)


@app.route('/waitlist')
@login_required
def waitlist():
    """Waitlist"""
    db = get_db()
    cursor = db.execute('''
        SELECT w.id, w.requested_pcs, w.start_time, w.duration_hours, w.created_at,
               z.name as zone_name
        FROM waitlist w
        JOIN zones z ON w.zone_id = z.id
        ORDER BY w.created_at DESC
    ''')
    waitlist_items = [dict(row) for row in cursor.fetchall()]
    
    return render_template('waitlist.html', waitlist=waitlist_items)


@app.route('/smart-create', methods=['GET', 'POST'])
@login_required
def smart_create():
    """Smart create booking flow - step 1: select zone, start, hours, qty"""
    db = get_db()
    
    if request.method == 'POST':
        zone_id = request.form.get('zone_id')
        start_slot = request.form.get('start_slot')
        hours = request.form.get('hours')
        qty = request.form.get('qty')
        
        # Store in session and redirect to preview
        session['smart_create'] = {
            'zone_id': zone_id,
            'start_slot': start_slot,
            'hours': hours,
            'qty': qty
        }
        return redirect(url_for('smart_preview'))
    
    # Get zones
    cursor = db.execute('SELECT * FROM zones WHERE active = 1 ORDER BY name')
    zone_list = [dict(row) for row in cursor.fetchall()]
    
    # Generate time slots (30-min intervals for next 48 hours)
    now = datetime.now(CLUB_TZ)
    slots = []
    for i in range(96):  # 48 hours * 2 (30-min slots)
        slot_time = now + timedelta(minutes=30 * i)
        slots.append(slot_time.strftime('%Y-%m-%d %H:%M'))
    
    return render_template('smart_create.html', zones=zone_list, slots=slots)


@app.route('/smart-preview', methods=['GET', 'POST'])
@login_required
def smart_preview():
    """Smart create preview - step 2: choose free PCs and create"""
    smart_data = session.get('smart_create')
    if not smart_data:
        return redirect(url_for('smart_create'))
    
    db = get_db()
    
    if request.method == 'POST':
        # Create bookings
        selected_pcs = request.form.getlist('pc_ids')
        
        if not selected_pcs:
            flash(_('Please select at least one PC'), 'error')
            return redirect(url_for('smart_preview'))
        
        # Generate group_id
        group_id = f"group_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Parse times
        start_time = smart_data['start_slot']
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        end_dt = start_dt + timedelta(hours=float(smart_data['hours']))
        end_time = end_dt.strftime('%Y-%m-%d %H:%M')
        
        # Create bookings
        for pc_id in selected_pcs:
            db.execute(
                'INSERT INTO bookings (pc_id, start_time, end_time, group_id, status) VALUES (?, ?, ?, ?, ?)',
                (int(pc_id), start_time, end_time, group_id, 'pending')
            )
        
        db.commit()
        session.pop('smart_create', None)
        flash(_('Created %d pending bookings in group %s') % (len(selected_pcs), group_id), 'success')
        return redirect(url_for('pending'))
    
    # Find free PCs in the zone
    zone_id = int(smart_data['zone_id'])
    start_time = smart_data['start_slot']
    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
    end_dt = start_dt + timedelta(hours=float(smart_data['hours']))
    end_time = end_dt.strftime('%Y-%m-%d %H:%M')
    
    # Get all PCs in zone
    cursor = db.execute('''
        SELECT p.id, p.number
        FROM pcs p
        WHERE p.zone_id = ? AND p.active = 1
        ORDER BY p.number
    ''', (zone_id,))
    all_pcs = [dict(row) for row in cursor.fetchall()]
    
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
            free_pcs.append(pc)
    
    # Get zone name
    cursor = db.execute('SELECT name FROM zones WHERE id = ?', (zone_id,))
    zone_name = cursor.fetchone()['name']
    
    return render_template('smart_preview.html',
                         zone_name=zone_name,
                         start_time=start_time,
                         end_time=end_time,
                         hours=smart_data['hours'],
                         qty=smart_data['qty'],
                         free_pcs=free_pcs)


if __name__ == '__main__':
    with app.app_context():
        init_db()
        sync_seed_data()
    
    print("Starting PC Club Admin Web Application...")
    print(f"Admin password is set: {bool(ADMIN_PASSWORD)}")
    
    # Only enable debug mode if explicitly set in environment
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
