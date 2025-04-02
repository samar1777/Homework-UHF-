from flask import Flask, render_template, request, redirect, session, url_for, flash, send_file
from werkzeug.utils import secure_filename
import os
import sqlite3
from functools import wraps
import requests
import json
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'UHFthebest'

# Server URL configuration - update with your PythonAnywhere URL
SERVER_URL = 'https://clientserver.pythonanywhere.com'

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
            if server_subjects and len(server_subjects) > 1:
                subjects = server_subjects
            else:
                subjects = default_subjects
                print("Server returned empty or single subject list, using default subjects")
        else:
            subjects = default_subjects
            print(f"Failed to get subjects from server: {response.status_code}")
    except Exception as e:
        subjects = default_subjects
        print(f"Error fetching subjects: {e}")
    
    print(f"Displaying subjects: {subjects}")
    return render_template('home.html', subjects=subjects)

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
        
    return render_template('admin.html', subjects=subjects)

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
