from flask import Flask, render_template, request, redirect, session, url_for, flash, send_file
from werkzeug.utils import secure_filename
import os
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'UHFthebest'

def init_db():
    conn = sqlite3.connect('homework.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS materials
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  subject TEXT NOT NULL,
                  chapter TEXT NOT NULL,
                  filename TEXT NOT NULL)''')
    conn.commit()
    conn.close()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    subjects = ['Mathematics', 'Science', 'Economics','Geography','History','Civis', 'Hindi', 'IT']
    return render_template('home.html', subjects=subjects)

@app.route('/subject/<subject>')
def subject(subject):
    conn = sqlite3.connect('homework.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT chapter FROM materials WHERE subject=?', (subject,))
    chapters = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template('subject.html', subject=subject, chapters=chapters)

@app.route('/view/<subject>/<chapter>')
def view_pdf(subject, chapter):
    conn = sqlite3.connect('homework.db')
    c = conn.cursor()
    c.execute('SELECT filename FROM materials WHERE subject=? AND chapter=?', (subject, chapter))
    result = c.fetchone()
    conn.close()
    
    if result:
        filename = result[0]
        return render_template('viewer.html', pdf_file=f'/static/uploads/{filename}', 
                             subject=subject, chapter=chapter)
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
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            conn = sqlite3.connect('homework.db')
            c = conn.cursor()
            c.execute('INSERT INTO materials (subject, chapter, filename) VALUES (?, ?, ?)',
                     (subject, chapter, filename))
            conn.commit()
            conn.close()
            
            flash('File uploaded successfully!')
            return redirect(url_for('admin'))
    
    return render_template('admin.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if (request.form['username'] == ADMIN_USERNAME and 
            request.form['password'] == ADMIN_PASSWORD):
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        flash('Invalid credentials!')
    return render_template('admin_login.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=80)
