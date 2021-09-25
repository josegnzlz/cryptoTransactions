import psycopg2 as pg
from apikey import key
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import datetime
import functions as func

class Coins:
    """ Register coins that appears for the first time """
    def __init__(self, coin_name):
        self.coin_name = coin_name
        func.insert_query_connection(table_name = "coins", 
                columns=["coin_name"], values=[self.coin_name])

class WalletEntry:
    """ Contains everything needed to create, modify or delete a entry """

    def __init__(self, coin_id, buy_date, amount, price_buy):
        # This are the basics, the other things can be done with methods
        func.insert_query_connection("wallet",columns=["coin_id", "buy_date", 
                "amount", "price_buy"], values=[coin_id, buy_date, 
                amount, price_buy])

class Transactions:
    """ Contains the logic to modify the database when a transaction takes place """

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

        if coin_name.startswith("LP"):
            print("You have transacted a LP token, please answer the following:")
            lp_value = float(input("Total Value of the Liquidity Pool: "))
            lp_token_supply = float(input("Circulating supply of the LP token: "))
            self.price = lp_value / lp_token_supply
        else:
            self.price = func.cmc_price_consult(coin_name)

class BuyTransaction(Transactions):
    """ Contains the logic of a buy transaction """
    
    def __init__(self, coin_name, amount, fee_coin_name, fee_amount, operation):
        """ Creates an entry in Wallet """
        super().__init__(coin_name, amount, fee_coin_name, fee_amount, operation)

        # Creation of a Wallet entry given the information of the transaction
        WalletEntry(self.coin_id, str(self.timestamp), self.amount, self.price)

        # Fee consideration
        func.if_fee(fee_coin_name, self.fee_amount)

class SellTransaction(Transactions):
    """ Contains the logic of a sell transaction """

    def __init__(self, coin_name, amount, fee_coin_name, fee_amount, operation):
        """ Close entries and create new ones with the left amount """
        super().__init__(coin_name, amount, fee_coin_name, fee_amount, operation)

        # Check open entries in the Wallet
        result = func._open_entries_check(coin_name)

        # Loop entries comparing the transaction´s amount with the entry's amount
        remaining_amount = float(self.amount)
        print(f"Amount of the sell transaction: {remaining_amount}")
        for entry in result:
            if entry[1] < remaining_amount:
                # Close entry by calculating benefits
                func.benefit_sell_submission(self.price, entry[2], entry[1], 
                        entry[0], self.timestamp)
                remaining_amount -= entry[1]

            elif entry[1] == remaining_amount:
                func.benefit_sell_submission(self.price, entry[2], entry[1], 
                        entry[0], self.timestamp)
                break
            
            else:
                # Close the actual entry for the transaction amount, and create
                # a new entry with the remaining amount of the old entry
                dbQueryUpdate = f"""UPDATE wallet SET amount={remaining_amount} 
                WHERE entry_id={entry[0]}"""
                print(dbQueryUpdate)
                func.database_connection(dbQueryUpdate)
                print(self.price)
                func.benefit_sell_submission(self.price, entry[2], 
                        remaining_amount, entry[0], self.timestamp)

                new_entry_amount = entry[1] - remaining_amount
                func.insert_query_connection("wallet", columns=["coin_id", 
                        "buy_date", "amount", "price_buy"], values=[self.coin_id, 
                        entry[3], new_entry_amount, entry[2]])
                break
        
        func.if_fee(fee_coin_name, fee_amount)
