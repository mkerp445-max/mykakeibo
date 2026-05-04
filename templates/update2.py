import sqlite3

def update_db_v2():
    conn = sqlite3.connect('kakeibo.db')
    cur = conn.cursor()
    
    # 1. usersテーブルを新しく作成（ユーザー情報を保存する場所）
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # 2. categoriesテーブルに user_id カラムを追加
    try:
        cur.execute('ALTER TABLE categories ADD COLUMN user_id INTEGER')
    except sqlite3.OperationalError:
        pass # 既にあればスキップ
        
    # 3. transactionsテーブルに user_id カラムを追加
    try:
        cur.execute('ALTER TABLE transactions ADD COLUMN user_id INTEGER')
    except sqlite3.OperationalError:
        pass # 既にあればスキップ

    conn.commit()
    conn.close()
    print("データベースの準備（ユーザー対応）が完了しました！")

if __name__ == '__main__':
    update_db_v2()