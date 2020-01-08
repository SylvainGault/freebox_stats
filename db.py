import sqlite3
import config



def new_connection():
    cnx = sqlite3.connect(config.database, isolation_level="DEFERRED")
    cur = cnx.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA threads=4")
    return cnx



def create_tables(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS adsl_connection (
        date TEXT,
        isbootup INT,
        event TEXT,
        bw_down INT,
        bw_up INT
    )""")

    cur.execute("""CREATE INDEX IF NOT EXISTS adsl_connection_idx
        ON adsl_connection(date, event)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS adsl_state (
        date TEXT,
        atm_bw_down INT,
        atm_bw_up INT,
        noise_margin_down FLOAT,
        noise_margin_up FLOAT,
        att_down FLOAT,
        att_up FLOAT,
        fec_down INT,
        fec_up INT,
        crc_down INT,
        crc_up INT,
        hec_down INT,
        hec_up INT
    )""")

    cur.execute("""CREATE INDEX IF NOT EXISTS adsl_state_idx
        ON adsl_state(date)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS netlinks (
        date TEXT,
        link TEXT,
        state TEXT,
        usage_down INT,
        usage_up INT
    )""")

    cur.execute("""CREATE INDEX IF NOT EXISTS netlinks_idx
        ON netlinks(date, link, state)""")
