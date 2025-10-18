from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui!'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Classe Usuário
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('appstore.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return User(row[0], row[1], row[2])
    return None

# Banco de dados
def init_db():
    conn = sqlite3.connect('appstore.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            filename TEXT NOT NULL,
            size INTEGER,
            downloads INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# Rotas
@app.route('/')
def home():
    conn = sqlite3.connect('appstore.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM apps ORDER BY created_at DESC LIMIT 10')
    apps = cursor.fetchall()
    conn.close()
    return render_template('home.html', apps=apps)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('appstore.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user_row = cursor.fetchone()
        conn.close()
        
        if user_row and check_password_hash(user_row[3], password):
            user = User(user_row[0], user_row[1], user_row[2])
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('❌ Usuário ou senha inválidos!')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        
        try:
            conn = sqlite3.connect('appstore.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                         (username, email, password))
            conn.commit()
            conn.close()
            flash('✅ Cadastro realizado com sucesso!')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('❌ Usuário ou email já existe!')
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect('appstore.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM apps WHERE user_id = ? ORDER BY created_at DESC', 
                   (current_user.id,))
    my_apps = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', apps=my_apps)

@app.route('/upload', methods=['POST'])
@login_required
def upload_app():
    if 'file' not in request.files:
        flash('❌ Nenhum arquivo selecionado!')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    name = request.form['name']
    description = request.form['description']
    
    if file.filename == '':
        flash('❌ Nenhum arquivo selecionado!')
        return redirect(url_for('dashboard'))
    
    if file:
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        conn = sqlite3.connect('appstore.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO apps (user_id, name, description, filename, size)
            VALUES (?, ?, ?, ?, ?)
        ''', (current_user.id, name, description, filename, os.path.getsize(filepath)))
        conn.commit()
        conn.close()
        
        flash('✅ App enviado com sucesso!')
    return redirect(url_for('dashboard'))

@app.route('/download/<int:app_id>')
def download_app(app_id):
    conn = sqlite3.connect('appstore.db')
    cursor = conn.cursor()
    cursor.execute('SELECT filename FROM apps WHERE id = ?', (app_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        filename = result[0]
        # Incrementa download
        conn = sqlite3.connect('appstore.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE apps SET downloads = downloads + 1 WHERE id = ?', (app_id,))
        conn.commit()
        conn.close()
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    return 'Arquivo não encontrado', 404

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
