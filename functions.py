import psycopg2 as pg
from apikey import key
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import datetime
from tabulate import tabulate
import classes as cl

def database_insert_connection(dbQuery): # Puedo eliminarla, la otra hace lo mismo y solo cambia si cojo o no el resultado
    """ Makes a connection with the database given a database query """

    conn = pg.connect(
            host="localhost",
            database="cryptotransactions",
            user="postgres",
            password="18p05tgr3sQL89*")

    cur = conn.cursor()
    try:
        cur.execute(dbQuery)
    except (pg.DatabaseError, pg.InternalError, pg.OperationalError,
            pg.DataError, pg.IntegrityError, pg.ProgrammingError) as e:
        raise e
    finally:
        if conn is not None:
            conn.commit()
            cur.close()
            conn.close()

def database_connection(dbQuery):
    """ Makes a connection with the database given a database query
            and returns data from database """

    conn = pg.connect(
            host="localhost",
            database="cryptotransactions",
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

def check_coin_in_database(coin):
    """ If coin doesn´t exist, create it. If exists, do nothing """
    
    dbCoinCheck = f"""SELECT coin_name FROM coins WHERE EXISTS (SELECT 
    coin_name FROM coins WHERE coin_name='{coin}')"""
    result = database_connection(dbCoinCheck)
    if result == []:
        cl.Coins(coin)

def show_last_ten_trxs():
    """ Shows the last 10 transactions done """

    dbQuery = """SELECT trx_id, trx_timestamp, cns.coin_name, amount, price, cs.coin_name, fee_amount, operation_type 
    FROM ((transactions LEFT JOIN coins AS cns ON transactions.coin_id = cns.coin_id)
    LEFT JOIN coins AS cs ON transactions.fee_coin_id = cs.coin_id) 
    ORDER BY trx_id ASC LIMIT 10"""
    result = database_connection(dbQuery)
    trx_id, timestamp, coin, amount = [], [], [], []
    price, fee_coin, fee_amount, op_type = [], [], [], []
    titles = ("ID", "Timestamp", "Coin", "Amount", "Price", "Fee Coin", 
            "Fee Amount", "Operation")
    result.insert(0, titles)

    for i, row in enumerate(result):
        trx_id.append(row[0])
        timestamp.append(row[1].strftime("%d-%b-%Y %H:%M:%S") if i != 0 else row[1])
        coin.append(row[2])
        amount.append(row[3])
        price.append(row[4])
        fee_coin.append(row[5] if row[5] is not None else 'None')
        fee_amount.append(row[6] if row[6] is not None else '0')
        op_type.append(row[7])
    
    solution = [trx_id, timestamp, coin, amount, price, fee_coin, fee_amount, op_type]

    print(tabulate(solution))

# Coge mucho código de la clase de transaccion de venta
def show_active_treasury():
    """ Shows the coins I own and the actual benefit/loss """
    # Look for active treasury entries
    dbQueryActiveEntries = """SELECT treasury_id FROM treasury WHERE 
    total_benefit IS NULL"""
    res = list(sol[0] for sol in database_connection(dbQueryActiveEntries))
    
    # Check their relations
    string = f"treasury_id={res[0]}"
    for i, r in enumerate(res):
        if i != 0:
            string = string + f" OR treasury_id={r}"
    dbQueryCheckRelations = f"""SELECT treasury_id, trx_id, action_id FROM 
    trx_treasury WHERE {string}"""
    print(dbQueryCheckRelations)
    solution = database_connection(dbQueryCheckRelations)
    trsy_trx_dict = {}
    for j, s in enumerate(solution):
        keys = trsy_trx_dict.keys()
        if s[0] not in keys:
            trsy_trx_dict[s[0]] = [[s[1], s[2]]]
        else:
            trsy_trx_dict[s[0]].append([s[1], s[2]])

    # Calculate the amount in the entries, and the transacted coin
    entries_data = []
    for entry in trsy_trx_dict:
        amount_entry = 0
        dbQuery = f"""SELECT coin_name FROM coins JOIN transactions ON 
        coins.coin_id=transactions.coin_id WHERE trx_id={trsy_trx_dict[entry][0][0]}"""
        coin = database_connection(dbQuery)[0][0]
        for lt in trsy_trx_dict[entry]:
            # Select the amount of each transaction and coin transacted
            dbQuery = f"""SELECT amount, price, trx_timestamp FROM transactions WHERE 
            trx_id={lt[0]}"""
            result = database_connection(dbQuery)
            am = result[0][0]
            if lt[1] == 1:
                """ Creation action """
                amount_entry += am
                price_buy = result[0][1]
                timestamp = result[0][2].strftime("%d-%b-%Y %H:%M:%S")
            else:
                """ Modification action """
                amount_entry -= amount_modification_trxs(lt[0], entry)
        entries_data.append([timestamp, coin, amount_entry, price_buy])

    # Calculate the benefits but without entering them in the database
    # And show the timestamp of the buy trx, coin, amount, price_buy,
    # actual_price, actual_total_benefit, actual_perc_benefit
    headers = ["Buy Date", "Coin", "Amount", "Buy Price", "Actual Price",
            "Actual Total Benefit", "Percentaje Benefit"]

    for i, item in enumerate(entries_data):
        actual_price = cmc_price_consult(item[1])
        benefit = calculate_benefit(actual_price, price_buy=item[3], amount=item[2])

        item.append(actual_price)
        item.append(benefit[0])
        item.append("{:.2f}%".format(round(benefit[1], 2)))

    print(tabulate(entries_data, headers=headers))

    # dbQuery = """SELECT trx_id, trx_timestamp, cns.coin_name, amount, price, cs.coin_name, fee_amount, operation_type 
    # FROM ((transactions LEFT JOIN coins AS cns ON transactions.coin_id = cns.coin_id)
    # LEFT JOIN coins AS cs ON transactions.fee_coin_id = cs.coin_id) 
    # ORDER BY trx_id ASC LIMIT 10"""
    
    # result = database_connection(dbQuery)
    # trx_id, timestamp, coin, amount = [], [], [], []
    # price, fee_coin, fee_amount, op_type = [], [], [], []
    # titles = ("ID", "Timestamp", "Coin", "Amount", "Price", "Fee Coin", 
    #         "Fee Amount", "Operation")
    # result.insert(0, titles)

    # for i, row in enumerate(result):
    #     trx_id.append(row[0])
    #     timestamp.append(row[1].strftime("%d-%b-%Y %H:%M:%S") if i != 0 else row[1])
    #     coin.append(row[2])
    #     amount.append(row[3])
    #     price.append(row[4])
    #     fee_coin.append(row[5] if row[5] is not None else 'None')
    #     fee_amount.append(row[6] if row[6] is not None else '0')
    #     op_type.append(row[7])
    
    # solution = [trx_id, timestamp, coin, amount, price, fee_coin, fee_amount, op_type]

    # print(tabulate(solution))

def calculate_benefit(price_sell, price_buy=None, amount=None, trx_id=None):
    """ Calculate the benefits """

    if trx_id != None:
        dbQuery = f"""SELECT amount, price FROM transactions WHERE 
        trx_id={trx_id}"""
        info = database_connection(dbQuery)
        amount = info[0][0]
        price_buy = info[0][1]
    
    total_benefit = amount * price_sell - amount * price_buy
    if price_sell >= price_buy:
        perc_benefit = (price_sell / price_buy - 1) * 100
    else:
        perc_benefit = -(price_buy / price_sell - 1) * 100
    
    return [total_benefit, perc_benefit]

def amount_modification_trxs(trx_id, treasury_id):
    """ Calculate the amount of the transaction modification in the actual entry """
    # Amount of the transaction that is been studied
    dbAmountQuery = f"""SELECT amount FROM transactions WHERE trx_id={trx_id}"""
    amount_trx = database_connection(dbAmountQuery)[0][0]

    # Entries afected by the transaction and action in them
    dbQuery = f"""SELECT treasury_id, action_id FROM trx_treasury WHERE 
    trx_id={trx_id} AND treasury_id<{treasury_id}"""
    treasury_action_array = []
    entry_act = database_connection(dbQuery)
    for j in entry_act:
        treasury_action_array.append([j[0], j[1]])

    for i in treasury_action_array:
        # For each row, look up for all transactions related to the entry
        amount_entry = 0
        dbQueryTrxEntries = f"""SELECT trx_id, action_id FROM trx_treasury WHERE 
        treasury_id={i[0]}"""
        resp = database_connection(dbQueryTrxEntries)
        trx_action_array = []
        for x in resp:
            trx_action_array.append([x[0], x[1]])
            if x[1] == 1:
                dbAmQuery = f"""SELECT amount FROM transactions WHERE 
                trx_id={x[0]}"""
                amount_entry += database_connection(dbAmQuery)[0][0]
            elif x[1] == 2:
                amount_entry -= amount_modification_trxs(x[0], i[0])
            elif x[1] == 3:
                amount_trx -= amount_entry
            elif x[1] == 4:
                pass # Modification amount is the same amount than for partial close
    
    print(f"Cantidad modificada en la entrada '{treasury_id}' por la transacción '{trx_id}': '{amount_trx}'")
    return amount_trx

def benefit_sell_submission(price_sell, price_buy, coin_amount_entry, entry):
    benefits = calculate_benefit(price_sell, price_buy=price_buy, 
            amount=coin_amount_entry)
    dbSubmitQuery = f"""UPDATE treasury SET 
    total_benefit={benefits[0]}, perc_benefit={benefits[1]} 
    WHERE treasury_id={entry}"""
    database_connection(dbSubmitQuery)

    print("Beneficios calculados e incluidos en la base de datos")

def if_fee(fee_coin_name, fee_amount):
    if fee_coin_name != "":
        # Select open entries
        dbQuery = f"""SELECT treasury.treasury_id FROM treasury JOIN trx_treasury ON 
        treasury.treasury_id=trx_treasury.treasury_id JOIN transactions ON 
        trx_treasury.trx_id=transactions.trx_id JOIN coins ON coins.coin_id=
        transactions.coin_id WHERE coins.coin_name='{fee_coin_name}' AND 
        treasury.total_benefit IS NULL"""
        result = database_connection(dbQuery)
        entries = []
        for r in result:
            entries.append(r if r not in entries else "")
        string = f"(treasury_id={entries[0][0]}"

        # Buy transactions of the entries
        for i, entry in enumerate(entries):
            if i != 0 and entry != "":
                string = string + f" OR treasury_id={entry}"
        string = string + ")"
        dbQuery = f"""SELECT trx_id FROM trx_treasury WHERE {string} AND 
        action_id=1 ORDER BY trx_id ASC LIMIT 1"""
        trx_id = database_connection(dbQuery)[0][0]
        dbQuery = f"""SELECT amount FROM transactions WHERE trx_id={trx_id}"""
        amount = database_connection(dbQuery)[0][0]
        new_amount = amount - float(fee_amount)
        print(f"Nueva cantidad: {new_amount}, para la transaccion: {trx_id}")
        dbQuery = f"""UPDATE transactions SET amount='{new_amount}' WHERE trx_id='{trx_id}'"""
        database_connection(dbQuery)

# Debbug functions

def reboot_database():
    dbQuery = """DELETE FROM trx_treasury"""
    database_connection(dbQuery)
    dbQuery = """DELETE FROM treasury"""
    database_connection(dbQuery)
    dbQuery = """DELETE FROM transactions"""
    database_connection(dbQuery)
    dbQuery = """DELETE FROM coins"""
    database_connection(dbQuery)
    dbQuery = """ALTER SEQUENCE transactions_trx_id_seq RESTART WITH 1"""
    database_connection(dbQuery)
    dbQuery = """ALTER SEQUENCE treasury_treasury_id_seq RESTART WITH 1"""
    database_connection(dbQuery)
    dbQuery = """ALTER SEQUENCE coins_coin_id_seq RESTART WITH 1"""
    database_connection(dbQuery)

def show_trx_treasury_table():
    dbQuery = """SELECT trx_id, treasury_id, action_id FROM trx_treasury """
    resp = database_connection(dbQuery)
    for i, r in enumerate(resp):
        print(f"Fila {i}: transacción '{r[0]}' y entrada '{r[1]}': acción '{r[2]}'")