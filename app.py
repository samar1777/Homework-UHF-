from flask import Flask, render_template, request, redirect, session, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import sqlite3
from functools import wraps
import requests
import json
import base64
import datetime

# Server URL configuration - update with your PythonAnywhere URL
SERVER_URL = 'https://homeworkserver.pythonanywhere.com/'

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Ensure database exists
DB_PATH = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        message TEXT NOT NULL,
        subject TEXT,
        timestamp TEXT NOT NULL,
        status TEXT DEFAULT 'pending'
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        display_until TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'UHFthebest'

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    # Default list of subjects to ensure we always have content
    default_subjects = ['Mathematics', 'Science', 'Economics', 'Geography', 'History', 'Civics', 'Hindi', 'English', 'IT']
    
    # Fetch subjects from server
    try:
        response = requests.get(f"{SERVER_URL}/api/subjects")
        if response.status_code == 200:
            server_subjects = response.json().get('subjects', [])
            # Only use server subjects if the list is not empty
            if server_subjects:
                subjects = server_subjects
            else:
                subjects = default_subjects
                print("Server returned empty subject list, using default subjects")
        else:
            subjects = default_subjects
            print(f"Failed to get subjects from server: {response.status_code}")
    except Exception as e:
        subjects = default_subjects
        print(f"Error fetching subjects: {e}")
    
    # Make sure we have all the default subjects
    if subjects:
        # Add any missing default subjects to ensure they're always shown
        for default_subject in default_subjects:
            if default_subject not in subjects:
                subjects.append(default_subject)
    
    # Get latest update for notification
    latest_update = get_latest_update()
    
    print(f"Displaying subjects: {subjects}")
    return render_template('home.html', subjects=subjects, latest_update=latest_update)

@app.route('/subject/<subject>')
def subject(subject):
    try:
        response = requests.get(f"{SERVER_URL}/api/chapters/{subject}")
        if response.status_code == 200:
            chapters = response.json()['chapters']
        else:
            chapters = []
    except:
        chapters = []
    
    return render_template('subject.html', subject=subject, chapters=chapters)

@app.route('/view/<subject>/<chapter>')
def view_pdf(subject, chapter):
    try:
        response = requests.get(f"{SERVER_URL}/api/file/{subject}/{chapter}")
        if response.status_code == 200:
            file_data = response.json()
            if file_data and 'filename' in file_data:
                filename = file_data['filename']
                
                # Check if file exists locally, if not, download it
                local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if not os.path.exists(local_path):
                    file_response = requests.get(f"{SERVER_URL}/api/download/{subject}/{chapter}")
                    if file_response.status_code == 200:
                        with open(local_path, 'wb') as f:
                            f.write(file_response.content)
                    
                return render_template('viewer.html', pdf_file=f'/static/uploads/{filename}', 
                                    subject=subject, chapter=chapter)
    except Exception as e:
        print(f"Error fetching file: {e}")
    
    return render_template('not_found.html')

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin():
    if request.method == 'POST':
        subject = request.form['subject']
        chapter = request.form['chapter']
        file = request.files['pdf']
        
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Upload the file to the server
            with open(file_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode('utf-8')
            
            data = {
                'subject': subject,
                'chapter': chapter,
                'filename': filename,
                'file_data': file_data
            }
            
            try:
                response = requests.post(f"{SERVER_URL}/api/upload", json=data)
                if response.status_code == 200:
                    flash('File uploaded successfully!')
                else:
                    flash('Error uploading to server, but saved locally')
            except:
                flash('Could not connect to server, but saved locally')
            
            return redirect(url_for('admin'))
    
    # Get the list of subjects from the server or use default subjects
    default_subjects = ['Mathematics', 'Science', 'Economics', 'Geography', 'History', 'Civics', 'Hindi', 'English', 'IT']
    try:
        response = requests.get(f"{SERVER_URL}/api/subjects")
        if response.status_code == 200:
            server_subjects = response.json().get('subjects', [])
            # Only use server subjects if the list is not empty
            if server_subjects and len(server_subjects) > 1:
                subjects = server_subjects
            else:
                subjects = default_subjects
        else:
            subjects = default_subjects
    except:
        subjects = default_subjects
    
    # Get all pending requests
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requests WHERE status = 'pending' ORDER BY timestamp DESC")
    pending_requests = [dict(row) for row in cursor.fetchall()]
    conn.close()
        
    return render_template('admin.html', subjects=subjects, pending_requests=pending_requests)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if (request.form['username'] == ADMIN_USERNAME and 
            request.form['password'] == ADMIN_PASSWORD):
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        flash('Invalid credentials!')
    return render_template('admin_login.html')

# Add a function to synchronize files with the server
def sync_all_files_from_server():
    """Download all files from server to local storage"""
    success_count = 0
    failed_count = 0
    try:
        print(f"Attempting to connect to server at {SERVER_URL}...")
        response = requests.get(f"{SERVER_URL}/api/all_files")
        if response.status_code == 200:
            files = response.json().get('files', [])
            print(f"Found {len(files)} files on the server")
            
            for file_info in files:
                local_path = os.path.join(app.config['UPLOAD_FOLDER'], file_info['filename'])
                if os.path.exists(local_path):
                    print(f"File {file_info['filename']} already exists locally")
                    success_count += 1
                    continue
                    
                print(f"Downloading {file_info['filename']}...")
                file_response = requests.get(
                    f"{SERVER_URL}/api/download/{file_info['subject']}/{file_info['chapter']}"
                )
                if file_response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(file_response.content)
                    print(f"Successfully downloaded {file_info['filename']}")
                    success_count += 1
                else:
                    print(f"Failed to download {file_info['filename']}: {file_response.status_code}")
                    failed_count += 1
                    
            print(f"Synchronization completed: {success_count} files synchronized, {failed_count} failed")
            return success_count, failed_count
        else:
            print(f"Failed to get file list from server: {response.status_code}")
            return 0, 0
    except Exception as e:
        print(f"Error during synchronization: {e}")
        return 0, 0

# Modify the sync route to provide more info
@app.route('/sync')
@admin_required
def sync_files():
    try:
        success_count, failed_count = sync_all_files_from_server()
        if success_count > 0:
            flash(f"Synchronized {success_count} files from server{' (plus ' + str(failed_count) + ' failed)' if failed_count > 0 else ''}")
        else:
            flash("No files synchronized from server")
    except Exception as e:
        flash(f"Error connecting to server: {str(e)}")
    
    return redirect(url_for('admin'))

# New endpoints for requests and notifications
@app.route('/submit_request', methods=['POST'])
def submit_request():
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    subject = request.form.get('subject', '')
    message = request.form.get('message', '')
    
    if not name or not message:
        return jsonify({'success': False, 'message': 'Name and message are required'}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO requests (name, email, subject, message, timestamp) 
            VALUES (?, ?, ?, ?, ?)
        ''', (name, email, subject, message, timestamp))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Request submitted successfully'}), 200
    except Exception as e:
        print(f"Error submitting request: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/admin/requests', methods=['GET'])
@admin_required
def view_requests():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requests ORDER BY timestamp DESC")
    all_requests = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return render_template('admin_requests.html', requests=all_requests)

@app.route('/admin/update_request_status/<int:request_id>', methods=['POST'])
@admin_required
def update_request_status(request_id):
    status = request.form.get('status', 'pending')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE requests SET status = ? WHERE id = ?", (status, request_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('view_requests'))

@app.route('/admin/create_update', methods=['GET', 'POST'])
@admin_required
def create_update():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        display_days = int(request.form.get('display_days', 7))
        send_notification = 'send_notification' in request.form
        
        if not title or not content:
            flash('Title and content are required!')
            return redirect(url_for('create_update'))
        
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        display_until = (now + datetime.timedelta(days=display_days)).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO updates (title, content, timestamp, display_until) 
                VALUES (?, ?, ?, ?)
            ''', (title, content, timestamp, display_until))
            update_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            flash(f'Update notification created successfully! Will be displayed for {display_days} days.')
            
            # Add a flag to the response to trigger browser notifications
            if send_notification:
                # Create a notification record in the session
                session['notify_users'] = {
                    'id': update_id,
                    'title': title, 
                    'content': content,
                    'display_until': display_until
                }
            
            return redirect(url_for('admin'))
        except Exception as e:
            flash(f'Error creating notification: {str(e)}')
            return redirect(url_for('create_update'))
    
    return render_template('create_update.html')

@app.route('/admin/view_updates', methods=['GET'])
@admin_required
def view_updates():
    """View all updates/notifications"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT *, 
                   CASE 
                       WHEN display_until > datetime('now') THEN 'Active'
                       ELSE 'Expired'
                   END as status
            FROM updates 
            ORDER BY timestamp DESC
        ''')
        updates = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return render_template('admin_updates.html', updates=updates)
    except Exception as e:
        flash(f'Error loading updates: {str(e)}')
        return redirect(url_for('admin'))

@app.route('/admin/delete_update/<int:update_id>', methods=['POST'])
@admin_required
def delete_update(update_id):
    """Delete an update/notification"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM updates WHERE id = ?", (update_id,))
        conn.commit()
        conn.close()
        
        flash('Update deleted successfully!')
    except Exception as e:
        flash(f'Error deleting update: {str(e)}')
    
    return redirect(url_for('view_updates'))

@app.route('/get_active_updates', methods=['GET'])
def get_active_updates():
    """Get all currently active updates"""
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM updates 
            WHERE display_until > ? 
            ORDER BY timestamp DESC
        ''', (now,))
        updates = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'updates': updates})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check_notifications')
def check_notifications():
    # Check if there are any notifications to be sent
    if 'notify_users' in session:
        notification_data = session['notify_users']
        # Remove it from session so it's only sent once
        session.pop('notify_users', None)
        return jsonify(notification_data)
    return jsonify({'status': 'no_notifications'})

@app.route('/get_pending_requests', methods=['GET'])
@admin_required
def get_pending_requests():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM requests WHERE status = 'pending'")
    count = cursor.fetchone()['count']
    conn.close()
    
    return jsonify({'count': count})

def get_latest_update():
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM updates 
            WHERE display_until > ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (now,))
        update = cursor.fetchone()
        conn.close()
        
        if update:
            update_dict = dict(update)
            # Calculate days remaining
            display_until = datetime.datetime.strptime(update_dict['display_until'], "%Y-%m-%d %H:%M:%S")
            now_dt = datetime.datetime.now()
            days_remaining = (display_until - now_dt).days
            update_dict['days_remaining'] = max(0, days_remaining)
            return update_dict
        return None
    except Exception as e:
        print(f"Error getting latest update: {e}")
        return None

if __name__ == '__main__':
    # Ensure upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        print(f"Created upload folder: {UPLOAD_FOLDER}")
    else:
        print(f"Upload folder exists: {UPLOAD_FOLDER}")
    
    # Synchronize with server on startup
    print("Starting synchronization with server...")
    success_count, failed_count = sync_all_files_from_server()
    print(f"Initial synchronization: {success_count} files downloaded, {failed_count} failed")
    
    app.run(host='0.0.0.0', port=80)
