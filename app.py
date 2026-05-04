import os
import sqlite3
import matplotlib
# Render(Linux)環境でグラフを表示するための設定
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key_12345' # セッション用の秘密鍵

# データベース名を以前と変えることで、古いデータとの衝突を避けます
DATABASE = 'kakeibo_v3.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# テーブルを自動作成する関数
def init_db():
    conn = get_db()
    cur = conn.cursor()
    # ユーザーテーブル
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # カテゴリーテーブル
    cur.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            user_id INTEGER,
            is_active INTEGER DEFAULT 1
        )
    ''')
    # 収支データテーブル
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category_id INTEGER,
            amount INTEGER NOT NULL,
            user_id INTEGER
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# ★最重要：関数の外で実行することで、起動時に必ずテーブルが作られるようにします
init_db()

# --- A: ログイン・ユーザー登録関連 ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return "そのユーザー名は既に使われています。"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cur.fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            return "ユーザー名またはパスワードが違います。"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- B: 家計簿メイン機能 ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/category', methods=['GET', 'POST'])
def category():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name')
        income_expense = request.form.get('type')
        cur.execute('INSERT INTO categories (name, type, user_id) VALUES (?, ?, ?)', (name, income_expense, user_id))
        conn.commit()
        return redirect(url_for('category'))
    cur.execute('SELECT * FROM categories WHERE user_id = ? AND is_active = 1', (user_id,))
    cat_list = cur.fetchall()
    conn.close()
    return render_template('category.html', categories=cat_list)

@app.route('/input', methods=['GET', 'POST'])
def input_data():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        date = request.form.get('date')
        category_id = request.form.get('category_id')
        amount = request.form.get('amount')
        cur.execute('INSERT INTO transactions (date, category_id, amount, user_id) VALUES (?, ?, ?, ?)', (date, category_id, amount, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    cur.execute('SELECT id, name, type FROM categories WHERE user_id = ? AND is_active = 1', (user_id,))
    cat_list = cur.fetchall()
    conn.close()
    return render_template('input.html', categories=cat_list)

@app.route('/list')
def list_view():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT t.id, t.date, c.name, c.type, t.amount 
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
        ORDER BY t.date DESC
    ''', (user_id,))
    data = cur.fetchall()
    conn.close()
    return render_template('list.html', transactions=data)

# --- C: 集計・グラフ関連 ---

@app.route('/summary_month')
def summary_month():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    # 2026年5月で固定（必要に応じて変更）
    target_month = "2026-05" 
    cur.execute('''
        SELECT c.name, SUM(t.amount)
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.date LIKE ? AND t.user_id = ?
        GROUP BY c.name
    ''', (target_month + '%', user_id))
    data = cur.fetchall()
    conn.close()
    if not data:
        return "今月のデータがありません。<a href='/'>戻る</a>"
    
    labels = [row[0] for row in data]
    values = [row[1] for row in data]
    plt.figure(figsize=(6, 6))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
    plt.title(f'User:{session["username"]} - {target_month}')
    
    if not os.path.exists('static'):
        os.makedirs('static')
    graph_path = os.path.join('static', 'graph.png')
    plt.savefig(graph_path)
    plt.close()
    
    return render_template('summary.html', month=target_month, data=data, graph_url=graph_path)

# --- サーバー起動設定 ---

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
