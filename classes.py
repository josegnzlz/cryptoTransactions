import psycopg2 as pg
from apikey import key
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import datetime
from tabulate import tabulate
import functions as func

class Coins:
    """ Class used when a new coin has been transacted. It's a lookup table """

    def __init__(self, coin):
        """ Creates the entry in database when the object is defined """
        self.coin = coin
        dbQuery = f"""INSERT INTO coins (coin_name) VALUES ('{self.coin}')"""
        func.database_connection(dbQuery)

class Transactions:
    """ Adds a transaction to the database """

    def __init__(self, coin_name, amount, fee_coin_name, fee_amount, operation):
        self.timestamp = datetime.now()
        self.amount = amount
        self.fee_amount = fee_amount
        self.operation = operation

        # Check if coin exists in the actual database, if it doesn´t, adds it
        func.check_coin_in_database(coin_name)

        # Define properties: coin_id and price
        dbCoinQuery = f"""SELECT coin_id FROM coins WHERE coin_name='{coin_name}'"""
        coin_list = func.database_connection(dbCoinQuery)
        self.coin_id = coin_list[0][0]

        self.price = func.cmc_price_consult(coin_name)

        # Check fee coin and submitting the transaction
        if fee_coin_name != "":
            func.check_coin_in_database(fee_coin_name)

            dbFeeCoinQuery = f"""SELECT coin_id FROM coins WHERE coin_name='{fee_coin_name}'"""
            coin_list = func.database_connection(dbFeeCoinQuery)
            self.fee_coin_id = coin_list[0][0]
            # Crear def _coin_id_lookup para estas dos busquedas

            dbQuery = f"""INSERT INTO transactions (trx_timestamp, coin_id, amount, 
            price, fee_coin_id, fee_amount, operation_type) VALUES 
            ('{self.timestamp}', '{self.coin_id}', '{self.amount}', 
            '{self.price}', '{self.fee_coin_id}', '{self.fee_amount}', 
            '{self.operation}')"""
            func.database_connection(dbQuery)

        else:
            dbQuery = f"""INSERT INTO transactions (trx_timestamp, coin_id, amount, 
            price, operation_type) VALUES 
            ('{self.timestamp}', '{self.coin_id}', '{self.amount}', 
            '{self.price}', '{self.operation}')"""
            func.database_connection(dbQuery)


class Treasury:
    """ Registration of possessed coins and old ones """
    def __init__(self, staked="False"):
        self.staked = staked

        # Submitting the entry
        dbQuery = f"""INSERT INTO treasury (staked) VALUES ('{self.staked}')"""
        func.database_connection(dbQuery)


class Transaction_treasury:
    """ Table to relate treasury entries with the transactions that influence it """
    def __init__(self, transaction_id, treasury_entry_id, action):
        self.transaction_id = transaction_id
        self.treasury_entry_id = treasury_entry_id
        if action == "creation":
            self.action_id = 1
        elif action == "modification":
            self.action_id = 2
        elif action == "close":
            self.action_id = 3
        elif action == "partial close":
            self.action_id = 4



        dbQuery = f"""INSERT INTO trx_treasury (trx_id, treasury_id, action_id) 
        VALUES ('{self.transaction_id}', '{self.treasury_entry_id}', {self.action_id})"""
        func.database_connection(dbQuery)


class BuyTransaction(Transactions):
    """ Contains the logic of a buy transaction """
    
    def __init__(self, coin_name, amount, fee_coin_name, fee_amount, operation):
        """ Creates an entry in Treasury, and associates it with the Transaction """
        super().__init__(coin_name, amount, fee_coin_name, fee_amount, operation)

        # Search the transaction id
        dbTrxQuery = f"""SELECT trx_id FROM transactions 
        WHERE trx_timestamp='{self.timestamp}'"""
        result = func.database_connection(dbTrxQuery)
        trx_id = result[0][0]

        # Creation of Treasury entry
        Treasury()

        # Selection of Treasury entry id
        dbTreasuryQuery = f"""SELECT treasury_id FROM treasury 
        ORDER BY treasury_id DESC LIMIT 1"""
        sol = func.database_connection(dbTreasuryQuery)
        treasury_id = sol[0][0]

        # Creation of the association in Trx_treasury table
        Transaction_treasury(trx_id, treasury_id, "creation")

        # Fee consideration
        func.if_fee(fee_coin_name, self.fee_amount)

class SellTransaction(Transactions):
    """ Contains the logic of a sell transaction """

    def __init__(self, coin_name, amount, fee_coin_name, fee_amount, operation):
        """ Iniciate a transaction and make all procedures to stablish a sell """
        super().__init__(coin_name, amount, fee_coin_name, fee_amount, operation)

        # Search the sell transaction id (trx_id), and stablish de amount_trx_sell
        dbTrxQuery = f"""SELECT trx_id FROM transactions 
        WHERE trx_timestamp='{self.timestamp}'"""
        result = func.database_connection(dbTrxQuery)
        trx_id = result[0][0]

        amount_trx_sell = float(self.amount)

        print(f"El id de la transacción es {trx_id}, la cantidad vendida es: {amount_trx_sell}")

        # Select trx_ids of transactions that have transacted the same coin
        dbSameCoinQuery = f"""SELECT trx_id FROM transactions WHERE 
        coin_id='{self.coin_id}'"""
        transaction_array = func.database_connection(dbSameCoinQuery)
        string = ""
        for i, trx in enumerate(transaction_array):
            transact = trx[0]
            if i == 0:
                string = string + f"trx_id='{transact}'"
            else:
                string = string + f" OR trx_id='{transact}'"

        # Select treasury_ids related to the transactions
        dbTrxTreasuryQuery = f"""SELECT trx_id, treasury_id, action_id FROM trx_treasury 
        WHERE {string}"""
        rp = func.database_connection(dbTrxTreasuryQuery)
        # Diccionary to save the relationships between transactions and entries in the treasury
        # Treasury_id: [[trx_id, action_id], [trx_id, action_id]]
        original_trsy_trxs_dict = {}
        trstring = ""
        for i, tr in enumerate(rp):
            keys = original_trsy_trxs_dict.keys()
            if tr[1] not in keys:
                original_trsy_trxs_dict[tr[1]] = [[tr[0], tr[2]]]
                if i == 0:
                    trstring = trstring + f"(treasury_id='{tr[1]}'"
                else:
                    trstring = trstring + f" OR treasury_id='{tr[1]}'"
            else:
                original_trsy_trxs_dict[tr[1]].append([tr[0], tr[2]])

        trstring = trstring + ")"

        print("Diccionario de tesoro_transacciones sin limpiar: ")
        print(original_trsy_trxs_dict)
        
        # Select the treasury entries that aren´t closed
        dbTreasuryQuery = f"""SELECT treasury_id FROM treasury WHERE 
        {trstring} AND total_benefit IS NULL"""
        response = func.database_connection(dbTreasuryQuery)
        treasury_array = [] # Contains treasury entries ids
        for tup in response:
            treasury_array.append(tup[0])

        # Take out from trsy_trx_dict the closed transactions
        trsy_trxs_dict = original_trsy_trxs_dict.copy()
        for entry in original_trsy_trxs_dict:
            if entry not in treasury_array:
                trsy_trxs_dict.pop(entry)
        
        print("Diccionario de tesoro_transacciones limpio de las entradas cerradas:")
        print(trsy_trxs_dict)

        # Calculate the amount in the entries
        for entry in trsy_trxs_dict:
            coin_amount_entry = 0
            for lt in trsy_trxs_dict[entry]:
                # Select the amount of each transaction
                dbQuery = f"""SELECT amount FROM transactions WHERE 
                trx_id={lt[0]}"""
                am = func.database_connection(dbQuery)[0][0]
                # If entries are not closed, there is imposible a close or
                # partial close action
                if lt[1] == 1:
                    """ Creation action """
                    coin_amount_entry += am
                else:
                    """ Modification action """
                    coin_amount_entry -= func.amount_modification_trxs(lt[0], entry)
                    print("Modificacion encontrada y manejada con exito")

            print(f"Cantidad de moneda en la entrada '{entry}': {coin_amount_entry}")

            dbBenefitQuery = f"""SELECT price FROM transactions 
            WHERE trx_id={trx_id}"""
            price_sell = func.database_connection(dbBenefitQuery)[0][0]
            dbBuyPriceQuery = f"""SELECT price FROM transactions 
            WHERE trx_id='{trsy_trxs_dict[entry][0][0]}'"""
            price_buy = func.database_connection(dbBuyPriceQuery)[0][0]

            if float(self.amount) >= coin_amount_entry:
                # Close entry and continue. To close, benefits must be calculate
                func.benefit_sell_submission(price_sell, price_buy, 
                        coin_amount_entry, entry)
                
                Transaction_treasury(trx_id, entry, "close")
                print("Unión trx y entry creada: close y sigue")
                amount_trx_sell -= coin_amount_entry
                print(f"Cantidad de moneda aún no asignada en la transaccion de venta: {amount_trx_sell}")
                if float(self.amount) == coin_amount_entry:
                    # Close entry and finish
                    print("Unión trx y entry creada: close y finalizacion")
                    break
                
            elif float(self.amount) < coin_amount_entry:
                # Partial close the entry, create a new one and modify it
                func.benefit_sell_submission(price_sell, price_buy, 
                        coin_amount_entry, entry)
                        
                Transaction_treasury(trx_id, entry, "partial close")
                # Create a new one, after the last one, of course
                Treasury()
                dbQueryLastEntry = f"""SELECT treasury_id FROM treasury ORDER 
                BY treasury_id DESC LIMIT 1"""
                last_entry = func.database_connection(dbQueryLastEntry)[0][0]
                Transaction_treasury(trsy_trxs_dict[entry][0][0], last_entry, "creation")
                # Modify it
                treas_array = list(arr for arr in trsy_trxs_dict[entry])
                
                print("ARRAY DE LA ENTRADA DEL TESORO")
                print(treas_array)
                
                for ar in treas_array:
                    if(ar[1] == 2):
                        Transaction_treasury(ar[0], last_entry, "modification")
                
                Transaction_treasury(trx_id, last_entry, "modification")

                print("Se ha cerrado la entrada, se ha creado una nueva, y se ha modificado")
                break
        
        # Fee consideration
        func.if_fee(fee_coin_name, self.fee_amount)


