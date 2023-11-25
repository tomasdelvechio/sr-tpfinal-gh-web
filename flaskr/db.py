import sqlite3

from flask import current_app, g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)

def get_top_users(n=10):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT user, count(repository) FROM interactions GROUP BY user ORDER BY 2 DESC LIMIT {n}")
    rows = cur.fetchall()
    return rows
    #df_repos = pd.read_sql_query("SELECT user, count(repository) FROM interactions GROUP BY user ORDER BY 2 DESC", conn)