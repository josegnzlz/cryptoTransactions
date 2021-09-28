import psycopg2 as pg
from apikey import key
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import datetime
import classes as cls

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

def cmc_price_consult(coin):
    """ Makes a consult to CoinMarketCap given a crypto symbol """

    url = 'https://pro-api.coinmarketcap.com/v1/tools/price-conversion'
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': key,
    }      
    params = {
        'amount': '1',
        'symbol': coin,
        'convert': 'USD',
    }
    session = Session()
    session.headers.update(headers)
    try:
        response = session.get(url, params=params)
        data = json.loads(response.text)
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(e)
    finally:
        price = float(data['data']['quote']['USD']['price'])
    
    return price

def insert_query_connection(table_name, columns, values):
    columns_array = f"({columns[0]}"
    for i, col in enumerate(columns):
        if i != 0:
            columns_array += f", {col}"
    columns_array += ")"

    values_array = f"('{values[0]}'"
    for j, val in enumerate(values):
        if j != 0:
            values_array += f", '{val}'"
    values_array += ")"

    dbQuery = f"""INSERT INTO {table_name} {columns_array} VALUES {values_array}"""
    print(dbQuery)
    database_connection(dbQuery)

def check_coin_in_database(coin):
    """ If coin doesn´t exist, create it. If exists, do nothing """
    
    dbCoinCheck = f"""SELECT coin_name FROM coins WHERE EXISTS (SELECT 
    coin_name FROM coins WHERE coin_name='{coin}')"""
    result = database_connection(dbCoinCheck)
    if result == []:
        cls.Coins(coin)

def if_fee(fee_coin_name, fee_amount):
    if fee_coin_name != "":
        # Select open entries
        result = _open_normal_entries_check(fee_coin_name)

        for entry in result:
            if float(fee_amount) < entry[1]:
                dbQueryUpdate = f"""UPDATE wallet SET amount=
                {entry[1]-float(fee_amount)} WHERE entry_id={entry[0]}"""
                database_connection(dbQueryUpdate)
            else:
                # Close the entry and if fee is still positive, substract from the next entry
                pass

def _open_normal_entries_check(coin):
    dbQuery = f"""SELECT wallet.entry_id, wallet.amount, wallet.price_buy, 
    wallet.buy_date FROM wallet JOIN coins ON wallet.coin_id=coins.coin_id 
    WHERE coins.coin_name='{coin}' AND wallet.total_benefit IS NULL AND 
    wallet.dexpool_id IS NULL"""
    result = database_connection(dbQuery)
    return result

def calculate_benefit(price_sell, price_buy, amount):
    """ Calculate the benefits """
    print(f"En calculo de beneficios: Precio de compra: {price_buy} Precio de venta: {price_sell} Cantidad: {amount}")
    total_benefit = amount * price_sell - amount * price_buy
    if price_sell >= price_buy:
        perc_benefit = (price_sell / price_buy - 1) * 100
    else:
        perc_benefit = -(price_buy / price_sell - 1) * 100
    
    return [total_benefit, perc_benefit]

def benefit_sell_submission(price_sell, price_buy, coin_amount_entry, entry, 
        sell_date):
    """ Calculate the benefits and makes the closure of the entry """

    benefits = calculate_benefit(price_sell, price_buy, coin_amount_entry)
    dbSubmitQuery = f"""UPDATE wallet SET sell_date='{sell_date}', 
    price_sell={price_sell}, total_benefit={benefits[0]}, 
    perc_benefit={benefits[1]} WHERE entry_id={entry}"""
    print(dbSubmitQuery)
    database_connection(dbSubmitQuery)

def reboot_database():
    dbQuery = """DELETE FROM wallet"""
    database_connection(dbQuery)
    dbQuery = """DELETE FROM coins"""
    database_connection(dbQuery)
    dbQuery = """DELETE FROM dex_pool"""
    database_connection(dbQuery)
    dbQuery = """DELETE FROM fiat_trxs"""
    database_connection(dbQuery)
    
    dbQuery = """ALTER SEQUENCE coins_coin_id_seq RESTART WITH 1"""
    database_connection(dbQuery)
    dbQuery = """ALTER SEQUENCE dex_pool_dexpool_id_seq RESTART WITH 1"""
    database_connection(dbQuery)
    dbQuery = """ALTER SEQUENCE fiat_trxs_fiat_trx_id_seq RESTART WITH 1"""
    database_connection(dbQuery)
    dbQuery = """ALTER SEQUENCE wallet_entry_id_seq RESTART WITH 1"""
    database_connection(dbQuery)

def show_wallet():
    dbQuery="""SELECT w.entry_id, c.coin_name, w.buy_date, w.amount, w.price_buy, 
    w.stake_date, dx.dexpool_name, w.benef_harvested, w.sell_date, w.price_sell, 
    w.total_benefit, w.perc_benefit FROM wallet AS w JOIN coins AS c ON w.coin_id=
    c.coin_id LEFT JOIN dex_pools AS dx ON w.dexpool_id=dx.dexpool_id ORDER BY 
    w.entry_id ASC"""
    result = database_connection(dbQuery)
    for entry in result:
        print(f"""Entrada {entry[0]}: Moneda: {entry[1]}, Fecha compra: {entry[2]},
        cantidad: {entry[3]}, Precio compra: {entry[4]}, Fecha de stake: {entry[5]},
        Dex/pool: {entry[6]}, Beneficios recogidos: {entry[7]}$, Fecha venta: {entry[8]}, 
        Precio venta: {entry[9]}, Beneficios totales: {entry[10]}, 
        Beneficios en porcentaje: {entry[11]}%\n""")

def check_dexpool_in_database(dexpool_name):
    """ If coin doesn´t exist, create it. If exists, do nothing """
    
    dbDexpoolCheck = f"""SELECT dexpool_name FROM dex_pools WHERE EXISTS (SELECT 
    dexpool_name FROM dex_pools WHERE dexpool_name='{dexpool_name}')"""
    result = database_connection(dbDexpoolCheck)
    dexpool_id = 0
    if result == []:
        cls.DexPool(dexpool_name)
        dbQuery = f"""SELECT dexpool_id FROM dex_pools WHERE dexpool_name=
        '{dexpool_name}'"""
        dexpool_id = database_connection(dbQuery)[0][0]
    return dexpool_id

def check_coin_name_input(coin_name):
    """ Returns True if everything is fine, False if a mistake has ocurred """
    try:
        float(coin_name)
        print("El nombre de la moneda no puede ser un número")
        back = False
    except:
        back = True
    return back

def dexpools_database():
    dbQuery = """SELECT dexpool_id, dexpool_name FROM dex_pools"""
    dexpools = database_connection(dbQuery)
    solution = [["Dexpool id", "Dexpool name"]]
    select = """Dexpool id      Dexpool name\n"""
    for dexpool in dexpools:
        select += f"""{dexpool[0]}          {dexpool[1]}"""
    return select
