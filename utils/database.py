import sqlite3
from pprint import pprint

from utils.config import config

def connect_db(path=config.PATH_DB.get_secret_value()):
    conn = sqlite3.connect(path)
    db = conn.cursor()
    return conn, db

########## INIT ##########
def init_db(path=config.PATH_DB.get_secret_value()):
    init_table_trade_links(path)

def init_table_trade_links(path=config.PATH_DB.get_secret_value()):
    conn, db = connect_db(path)
    db.execute(f"""CREATE TABLE IF NOT EXISTS LINKS (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link_trade TEXT,
        check_collect INTEGER);
        """)
    conn.commit()
    conn.close()

########## INSERT ##########

def insert_link_collect(link_trade,path=config.PATH_DB.get_secret_value()):
    conn, db = connect_db(path)
    sql_select = "SELECT link_trade FROM LINKS WHERE link_trade=?"
    db.execute(sql_select, [link_trade])
    data_Select = db.fetchall()
    if not data_Select:
        sql_insert = "INSERT INTO LINKS (link_trade,check_collect) VALUES (?,?)"
        db.execute(sql_insert, [link_trade, 0])
        conn.commit()
    conn.close()

###### CHECK ###############




######## GET ##############
def get_links_not_collect(path=config.PATH_DB.get_secret_value()):
    conn, db = connect_db(path)
    sql = f"""SELECT link_trade FROM LINKS WHERE check_collect=?;"""
    db.execute(sql,[0])
    data_Select = db.fetchall()
    conn.close()
    return [x[0] for x in data_Select]  if data_Select else []

####### UPDATE #############

def update_status_collect_link(link_trade:str,path=config.PATH_DB.get_secret_value()):
    conn, db = connect_db(path)
    sql = f"UPDATE LINKS SET check_collect=1  WHERE link_trade=? "
    db.execute(sql, [link_trade])
    conn.commit()
    conn.close()


####### DELETE #############




##### OTHER ############


if __name__ == '__main__':
    pprint("")