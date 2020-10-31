import os
import sqlite3


def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return conn

def view_items_db(shop_dir):
    if os.path.exists(shop_dir+'/scraped_data.db'):
        # create a database connection
        conn = create_connection(shop_dir+'/'+'scraped_data.db')
        
        cur = conn.cursor()
        cur.execute('SELECT * FROM items')
        rows = cur.fetchall()
        for row in rows:
            print(row)
        return None
    else:
        return "No scraped data."

def view_models_db(shop_dir, item_name):
    if os.path.exists(shop_dir+'/scraped_data.db'):
        # create a database connection
        conn = create_connection(shop_dir+'/'+'scraped_data.db')
        
        cur = conn.cursor()
        cur.execute('SELECT * FROM models WHERE item_name=?', (item_name,))
        rows = cur.fetchall()
        for row in rows:
            print(row)
        return None
    else:
        return "No scraped data."
