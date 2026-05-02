import os
import json
import math
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import bcrypt
import MySQLdb

load_dotenv()

# AI Setup
gemini_key = os.getenv('GEMINI_API_KEY')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'smartwatch_secret_2024')
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'smart_watch_db')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', 3306))
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['MYSQL_CHARSET'] = 'utf8mb4'
app.config['MYSQL_COLLATION'] = 'utf8mb4_unicode_ci'

mysql = MySQL(app)
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ─────────────────────────── User Model ────────────────────────────
class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.full_name = user_data['full_name']
        self.email = user_data['email']
        self.role = user_data['role']
        self.phone = user_data.get('phone', '')

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s AND is_active = 1", (user_id,))
    user = cur.fetchone()
    cur.close()
    if user:
        return User(user)
    return None

# ─────────────────────────── Auth Routes ────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s AND is_active = 1", (email,))
        user = cur.fetchone()
        cur.close()
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            login_user(User(user), remember=True)
            return redirect(url_for('dashboard'))
        flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO users (full_name, email, phone, password_hash) VALUES (%s, %s, %s, %s)",
                (full_name, email, phone, hashed)
            )
            mysql.connection.commit()
            cur.close()
            flash('تم إنشاء حسابك بنجاح! يمكنك تسجيل الدخول الآن.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('البريد الإلكتروني مستخدم بالفعل.', 'error')
    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        new_password = request.form.get('new_password', '').strip()
        
        cur = mysql.connection.cursor()
        if new_password:
            hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute("""
                UPDATE users SET full_name = %s, phone = %s, password_hash = %s WHERE id = %s
            """, (full_name, phone, hashed, current_user.id))
        else:
            cur.execute("""
                UPDATE users SET full_name = %s, phone = %s WHERE id = %s
            """, (full_name, phone, current_user.id))
            
        mysql.connection.commit()
        cur.close()
        
        current_user.full_name = full_name
        current_user.phone = phone
        
        flash('تم تحديث البيانات الشخصية بنجاح', 'success')
        return redirect(url_for('profile'))
        
    return render_template('profile.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ─────────────────────────── Dashboard ────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    # Stats
    cur.execute("SELECT COUNT(*) as cnt FROM devices WHERE user_id = %s", (current_user.id,))
    device_count = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM sos_alerts WHERE user_id = %s AND status = 'active'", (current_user.id,))
    active_sos = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM sos_alerts WHERE user_id = %s", (current_user.id,))
    total_sos = cur.fetchone()['cnt']
    cur.execute("SELECT * FROM devices WHERE user_id = %s ORDER BY registered_at DESC", (current_user.id,))
    devices = cur.fetchall()
    cur.execute("""
        SELECT sa.*, d.device_name FROM sos_alerts sa
        JOIN devices d ON sa.device_id = d.id
        WHERE sa.user_id = %s ORDER BY sa.created_at DESC LIMIT 5
    """, (current_user.id,))
    recent_alerts = cur.fetchall()
    cur.execute("SELECT COUNT(*) as cnt FROM notifications WHERE user_id = %s AND is_read = 0", (current_user.id,))
    unread_notifs = cur.fetchone()['cnt']
    cur.close()
    return render_template('dashboard.html',
        device_count=device_count,
        active_sos=active_sos,
        total_sos=total_sos,
        devices=devices,
        recent_alerts=recent_alerts,
        unread_notifs=unread_notifs
    )

# ─────────────────────────── Devices ────────────────────────────
@app.route('/devices')
@login_required
def devices():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM devices WHERE user_id = %s ORDER BY registered_at DESC", (current_user.id,))
    devices = cur.fetchall()
    cur.close()
    return render_template('devices.html', devices=devices)

@app.route('/devices/add', methods=['GET', 'POST'])
@login_required
def add_device():
    if request.method == 'POST':
        device_name = request.form.get('device_name')
        serial = request.form.get('serial_number')
        device_id = f"SW-{random.randint(100000, 999999)}"
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO devices (device_id, user_id, device_name, serial_number)
                VALUES (%s, %s, %s, %s)
            """, (device_id, current_user.id, device_name, serial))
            mysql.connection.commit()
            flash(f'تم تسجيل الجهاز بنجاح! معرف الجهاز: {device_id}', 'success')
            return redirect(url_for('devices'))
        except MySQLdb.IntegrityError as e:
            mysql.connection.rollback()
            if e.args[0] == 1062:
                flash('خطأ: الرقم التسلسلي (Serial Number) مسجل مسبقاً لجهاز آخر!', 'error')
            else:
                flash('حدث خطأ أثناء تسجيل الجهاز.', 'error')
        finally:
            cur.close()
    return render_template('add_device.html')

@app.route('/devices/<int:device_id>/detail')
@login_required
def device_detail(device_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM devices WHERE id = %s AND user_id = %s", (device_id, current_user.id))
    device = cur.fetchone()
    if not device:
        flash('الجهاز غير موجود', 'error')
        return redirect(url_for('devices'))
    cur.execute("""
        SELECT * FROM location_logs WHERE device_id = %s ORDER BY recorded_at DESC LIMIT 20
    """, (device_id,))
    locations = cur.fetchall()
    cur.execute("""
        SELECT * FROM nearby_devices WHERE device_id = %s ORDER BY detected_at DESC LIMIT 10
    """, (device_id,))
    nearby = cur.fetchall()
    cur.execute("""
        SELECT * FROM sos_alerts WHERE device_id = %s ORDER BY created_at DESC LIMIT 5
    """, (device_id,))
    alerts = cur.fetchall()
    cur.close()
    return render_template('device_detail.html', device=device, locations=locations, nearby=nearby, alerts=alerts)

# ─────────────────────────── SOS Alerts ────────────────────────────
@app.route('/sos')
@login_required
def sos_list():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT sa.*, d.device_name, rt.team_name
        FROM sos_alerts sa
        JOIN devices d ON sa.device_id = d.id
        LEFT JOIN rescue_teams rt ON sa.rescue_team_id = rt.id
        WHERE sa.user_id = %s ORDER BY sa.created_at DESC
    """, (current_user.id,))
    alerts = cur.fetchall()
    cur.execute("SELECT * FROM devices WHERE user_id = %s", (current_user.id,))
    devices = cur.fetchall()
    cur.close()
    return render_template('sos.html', alerts=alerts, devices=devices)

@app.route('/sos/trigger', methods=['POST'])
@login_required
def trigger_sos():
    data = request.get_json()
    device_db_id = data.get('device_id')
    lat = data.get('latitude', 24.7136)
    lng = data.get('longitude', 46.6753)
    alert_type = data.get('alert_type', 'manual')
    nearby_count = data.get('nearby_devices', 0)
    msg = data.get('message', 'نداء استغاثة عاجل')
    cur = mysql.connection.cursor()
    # Get rescue team
    cur.execute("""
        SELECT *, 
        (6371 * acos(cos(radians(%s)) * cos(radians(latitude)) * 
         cos(radians(longitude) - radians(%s)) + 
         sin(radians(%s)) * sin(radians(latitude)))) AS distance
        FROM rescue_teams WHERE is_available = 1
        ORDER BY distance LIMIT 1
    """, (lat, lng, lat))
    team = cur.fetchone()
    team_id = team['id'] if team else None
    cur.execute("""
        INSERT INTO sos_alerts 
        (device_id, user_id, alert_type, latitude, longitude, nearby_devices_count, message, rescue_team_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (device_db_id, current_user.id, alert_type, lat, lng, nearby_count, msg, team_id))
    sos_id = cur.lastrowid
    mysql.connection.commit()
    # Insert notification
    cur.execute("""
        INSERT INTO notifications (user_id, title, message, type) VALUES (%s, %s, %s, 'sos')
    """, (current_user.id, '🆘 تم إرسال نداء الاستغاثة', f'تم إرسال نداء استغاثة من موقعك. فريق الإنقاذ في الطريق إليك.'))
    mysql.connection.commit()
    cur.close()
    socketio.emit('sos_alert', {
        'sos_id': sos_id,
        'lat': lat,
        'lng': lng,
        'team': team['team_name'] if team else 'يتم البحث عن فريق',
        'message': msg
    })
    return jsonify({'success': True, 'sos_id': sos_id, 'team': team['team_name'] if team else None})

@app.route('/api/ai-analyze/<int:sos_id>', methods=['GET'])
@login_required
def ai_analyze_sos(sos_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT sa.id, sa.latitude, sa.longitude, sa.message, sa.status, sa.created_at,
               d.device_name, d.battery_level, d.satellite_connected,
               (SELECT COUNT(*) FROM nearby_devices nd WHERE nd.device_id = d.id) as nearby_count
        FROM sos_alerts sa
        LEFT JOIN devices d ON sa.device_id = d.id
        WHERE sa.id = %s
    """, (sos_id,))
    row = cur.fetchone()
    cur.close()
    
    if not row:
        return jsonify({'success': False, 'message': 'النداء غير موجود'}), 404
        
    prompt = f"""
أنت مساعد ذكاء اصطناعي متخصص في إدارة الطوارئ والإنقاذ (Smart Survival Watch).
بيانات الاستغاثة:
- رقم الحالة: {row['id']}
- الرسالة: {row['message'] or 'لا توجد رسالة'}
- البطارية: {row['battery_level'] or 0}%
- اتصال الأقمار المتصلة: {'نعم' if row['satellite_connected'] else 'لا'}
- عدد الأجهزة القريبة المحتملة: {row['nearby_count'] or 0}
- الموقع: {row['latitude']}, {row['longitude']}

بناءً على المعطيات، قم بالرد المباشر بـ 3 نقاط قصيرة ومختصرة باللغة العربية:
1. تقييم خطورة الحالة (مرتفع، متوسط، إلخ) مع السبب.
2. خطة إنقاذ سريعة من خطوتين لفرق الإنقاذ.
3. توصية للنجاة بناءً على المعطيات.
"""
    try:
        from google import genai
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        text = response.text.replace('*', '').replace('#', '')
        return jsonify({'success': True, 'analysis': text})
    except Exception as e:
        return jsonify({'success': False, 'message': f'تعذر الاتصال بالنموذج: {str(e)}'})

# ─────────────────────────── Map / Tracking ────────────────────────────
@app.route('/map')
@login_required
def map_view():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM devices WHERE user_id = %s", (current_user.id,))
    devices = cur.fetchall()
    cur.execute("""
        SELECT sa.*, d.device_name FROM sos_alerts sa
        JOIN devices d ON sa.device_id = d.id
        WHERE sa.user_id = %s AND sa.status = 'active'
    """, (current_user.id,))
    active_sos = cur.fetchall()
    cur.execute("SELECT * FROM rescue_teams WHERE is_available = 1")
    teams = cur.fetchall()
    cur.close()
    return render_template('map.html', devices=devices, active_sos=active_sos, teams=teams)

# ─────────────────────────── Rescue Teams ────────────────────────────
@app.route('/rescue-teams')
@login_required
def rescue_teams():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM rescue_teams ORDER BY team_name")
    teams = cur.fetchall()
    cur.close()
    return render_template('rescue_teams.html', teams=teams)

# ─────────────────────────── Notifications ────────────────────────────
@app.route('/notifications')
@login_required
def notifications():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC
    """, (current_user.id,))
    notifs = cur.fetchall()
    cur.execute("UPDATE notifications SET is_read = 1 WHERE user_id = %s", (current_user.id,))
    mysql.connection.commit()
    cur.close()
    return render_template('notifications.html', notifications=notifs)

# ─────────────────────────── API Endpoints ────────────────────────────
@app.route('/api/device/<device_id>/update', methods=['POST'])
def api_update_device(device_id):
    """API for the physical watch to send data"""
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM devices WHERE device_id = %s", (device_id,))
    device = cur.fetchone()
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    # Update device status
    cur.execute("""
        UPDATE devices SET battery_level=%s, solar_charging=%s, satellite_connected=%s, last_seen=NOW()
        WHERE device_id=%s
    """, (data.get('battery', 100), data.get('solar', 0), data.get('satellite', 0), device_id))
    # Log location
    if data.get('lat') and data.get('lng'):
        cur.execute("""
            INSERT INTO location_logs (device_id, latitude, longitude, altitude, satellite_count, speed)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (device['id'], data['lat'], data['lng'], data.get('alt', 0),
              data.get('satellites', 0), data.get('speed', 0)))
    # Log nearby devices
    if data.get('nearby'):
        for nd in data['nearby']:
            cur.execute("""
                INSERT INTO nearby_devices (device_id, detected_signal_type, signal_strength, estimated_distance)
                VALUES (%s, %s, %s, %s)
            """, (device['id'], nd.get('type', 'bluetooth'), nd.get('rssi', 0), nd.get('distance', 0)))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True})

@app.route('/api/stats')
@login_required
def api_stats():
    cur = mysql.connection.cursor()
    # SOS per month for chart
    cur.execute("""
        SELECT MONTH(created_at) as month, COUNT(*) as cnt 
        FROM sos_alerts WHERE user_id = %s AND YEAR(created_at) = YEAR(NOW())
        GROUP BY MONTH(created_at) ORDER BY month
    """, (current_user.id,))
    sos_monthly = cur.fetchall()
    cur.execute("""
        SELECT status, COUNT(*) as cnt FROM sos_alerts WHERE user_id = %s GROUP BY status
    """, (current_user.id,))
    sos_by_status = cur.fetchall()
    cur.close()
    return jsonify({
        'sos_monthly': [{'month': r['month'], 'count': r['cnt']} for r in sos_monthly],
        'sos_by_status': [{'status': r['status'], 'count': r['cnt']} for r in sos_by_status]
    })

@app.route('/api/simulate-scan/<int:device_id>', methods=['POST'])
@login_required
def simulate_scan(device_id):
    """Simulate nearby device scan for demo"""
    cur = mysql.connection.cursor()
    count = random.randint(0, 5)
    for i in range(count):
        distance = random.uniform(50, 2000)
        rssi = random.randint(-90, -40)
        cur.execute("""
            INSERT INTO nearby_devices (device_id, detected_signal_type, signal_strength, estimated_distance)
            VALUES (%s, 'bluetooth', %s, %s)
        """, (device_id, rssi, distance))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True, 'devices_found': count})

# ─────────────────────────── Admin ────────────────────────────
@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash('غير مصرح لك بالوصول لهذه الصفحة', 'error')
        return redirect(url_for('dashboard'))
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM devices")
    total_devices = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM sos_alerts WHERE status = 'active'")
    active_sos = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM rescue_teams WHERE is_available = 1")
    available_teams = cur.fetchone()['cnt']
    cur.execute("""
        SELECT sa.*, u.full_name, d.device_name, rt.team_name
        FROM sos_alerts sa JOIN users u ON sa.user_id = u.id
        JOIN devices d ON sa.device_id = d.id
        LEFT JOIN rescue_teams rt ON sa.rescue_team_id = rt.id
        ORDER BY sa.created_at DESC LIMIT 10
    """)
    all_alerts = cur.fetchall()
    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    all_users = cur.fetchall()
    cur.close()
    return render_template('admin.html',
        total_users=total_users, total_devices=total_devices,
        active_sos=active_sos, available_teams=available_teams,
        all_alerts=all_alerts, all_users=all_users
    )

@app.route('/api/sos/<int:sos_id>/resolve', methods=['POST'])
@login_required
def resolve_sos(sos_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE sos_alerts SET status = 'resolved', resolved_at = NOW() WHERE id = %s
    """, (sos_id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    socketio.run(app, debug=True, port=int(os.getenv('FLASK_PORT', 5050)), allow_unsafe_werkzeug=True)
