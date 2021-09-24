import psycopg2 as pg
from apikey import key
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import datetime
import new_classes as cls

def database_connection(dbQuery):
    """ Makes a connection with the database given a database query
            and returns data from database """

    conn = pg.connect(
            host="localhost",
            database="cryptoWallet",
            user="postgres",
            password="18p05tgr3sQL89*")

    cur = conn.cursor()
    try:
        cur.execute(dbQuery)
    except (pg.DatabaseError, pg.InternalError, pg.OperationalError,
            pg.DataError, pg.IntegrityError, pg.ProgrammingError) as e:
        raise e
    finally:
        result = []

        if dbQuery.startswith("SELECT"):
            for row in cur:
                result.append(row)

        if conn is not None:
            conn.commit()
            cur.close()
            conn.close()
        
        return result

def insert_query_connection(table_name, columns, values):
    columns_array = f"({columns[0]}"
    for i, col in enumerate(columns):
        if i != 0:
            columns_array += f", {col}"
    columns_array += ")"

    values_array = f"('{values[0]}'"
    for j, val in enumerate(values):
        if j != 0:
            values_array += f", {val}"
    values_array += ")"

    dbQuery = f"""INSERT INTO {table_name} {columns_array} VALUES {values_array}"""

    database_connection(dbQuery)

def check_coin_in_database(coin):
    """ If coin doesn´t exist, create it. If exists, do nothing """
    
    dbCoinCheck = f"""SELECT coin_name FROM coins WHERE EXISTS (SELECT 
    coin_name FROM coins WHERE coin_name='{coin}')"""
    result = database_connection(dbCoinCheck)
    if result == []:
        cls.Coins(coin)