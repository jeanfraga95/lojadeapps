import sqlite3

def init_db():
    conn = sqlite3.connect('appstore.db')
    # (mesmo código do init_db acima)
    conn.close()

if __name__ == '__main__':
    init_db()
