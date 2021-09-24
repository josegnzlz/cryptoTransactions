import psycopg2 as pg
from apikey import key
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import datetime
import functions as func
import sec_functions as sfunc

class Coins:
    """ Register coins that appears for the first time """
    def __init__(self, coin_name):
        self.coin_name = coin_name
        sfunc.insert_query_connection(table_name = "coins", 
                columns=["coin_name"], values=[self.coin_name])

class WalletEntry:
    """ Contains everything needed to create, modify or delete a entry """

    def __init__(self, coin_id, buy_date, amount, price_buy):
        # This are the basics, the other things can be done with methods
        pass

class Transactions:
    """ Contains the logic to modify the database when a transaction takes place """

    def __init__(self, coin_name, amount, fee_coin_name, fee_amount, operation):
        self.timestamp = datetime.now()
        self.amount = amount
        self.fee_amount = fee_amount
        self.operation = operation

        # Check if coin exists in the actual database, if it doesn´t, adds it
        sfunc.check_coin_in_database(coin_name)

        # Define properties: coin_id and price
        dbCoinQuery = f"""SELECT coin_id FROM coins WHERE coin_name='{coin_name}'"""
        coin_list = sfunc.database_connection(dbCoinQuery)
        self.coin_id = coin_list[0][0]

        if coin_name.startswith("LP"):
            print("You have transacted a LP token, please answer the following:")
            lp_value = float(input("Total Value of the Liquidity Pool: "))
            lp_token_supply = float(input("Circulating supply of the LP token: "))
            self.price = lp_value / lp_token_supply
        else:
            self.price = func.cmc_price_consult(coin_name)

class BuyTransactions(Transactions):
    """ Contains the logic of a buy transaction """
    
    def __init__(self, coin_name, amount, fee_coin_name, fee_amount, operation):
        """ Creates an entry in Treasury, and associates it with the Transaction """
        super().__init__(coin_name, amount, fee_coin_name, fee_amount, operation)

        # Creation of a Wallet entry given the information of the transaction

        # Fee consideration
        func.if_fee(fee_coin_name, self.fee_amount)