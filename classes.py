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

    def __init__(self, coin_name, amount, fee_coin_name, fee_amount):
        self.timestamp = datetime.now()
        self.amount = float(amount)
        self.fee_amount = float(fee_amount) if fee_amount != "" else ""

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
    
    def __init__(self, coin_name, amount, fee_coin_name, fee_amount):
        """ Creates an entry in Wallet """
        super().__init__(coin_name, amount, fee_coin_name, fee_amount)

        # Creation of a Wallet entry given the information of the transaction
        WalletEntry(self.coin_id, str(self.timestamp), self.amount, self.price)

        # Fee consideration
        func.if_fee(fee_coin_name, self.fee_amount)

class SellTransaction(Transactions):
    """ Contains the logic of a sell transaction """

    def __init__(self, coin_name, amount, fee_coin_name, fee_amount):
        """ Close entries and create new ones with the left amount """
        super().__init__(coin_name, amount, fee_coin_name, fee_amount)

        # Check open entries in the Wallet
        result = func._open_normal_entries_check(coin_name)

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

class DexPool:
    """ Register dex and pool that appears for the first time """

    def __init__(self, dexpool_name):
        self.dexpool_name = dexpool_name

        func.insert_query_connection("dex_pools", ["dexpool_name"], [self.dexpool_name])

class Stake(Transactions):
    """ Cointains the logic to stake coins """

    def __init__(self, coin_name, amount, dex_pool, fee_coin_name, fee_amount):
        super().__init__(coin_name, amount, fee_coin_name, fee_amount)
        self.dex_pool = dex_pool

        # Find open entries that share coin and aren´t staked yet
        dbQueryEntries = f"""SELECT w.entry_id, w.amount FROM wallet as w JOIN 
        coins AS c ON w.coin_id=c.coin_id WHERE c.coin_id='{self.coin_id}' 
        AND w.dexpool_id IS NULL AND w.total_benefit IS NULL"""
        result = func.database_connection(dbQueryEntries)

        # Check dex pool
        func.check_dexpool_in_database(dex_pool)
        dbQueryDexPool = f"""SELECT dexpool_id FROM dex_pools WHERE 
        dexpool_name='{dex_pool}'"""
        dex_pool_id = func.database_connection(dbQueryDexPool)[0][0]

        # Loop between entries
        am_to_be_staked = self.amount
        for entry in result:
            if am_to_be_staked >= entry[1]:
                dbQueryUpdateEntry = f"""UPDATE wallet SET 
                stake_date='{self.timestamp}', dexpool_id={dex_pool_id}
                WHERE entry_id={entry[0]}"""
                func.database_connection(dbQueryUpdateEntry)
                if am_to_be_staked == entry[1]:
                    break
                am_to_be_staked -= entry[1]
            
            else:
                # Leave the actual entry with the no stake amount
                new_amount = entry[1] - am_to_be_staked
                dbQueryUpdate = f"""UPDATE wallet SET amount={new_amount} WHERE 
                entry_id={entry[0]}"""
                func.database_connection(dbQueryUpdate)

                # Create a new entry with the same information but staked
                dbQuerySelect = f"""SELECT coin_id, buy_date, price_buy FROM 
                wallet WHERE entry_id={entry[0]}"""
                sol = func.database_connection(dbQuerySelect)[0]
                func.insert_query_connection("wallet", ["coin_id", "buy_date", 
                        "amount", "price_buy", "dexpool_id", "stake_date"], 
                        [sol[0], sol[1], am_to_be_staked, sol[2], dex_pool_id, 
                        self.timestamp])
            
        func.if_fee(fee_coin_name, fee_amount)

class HarvestBuy(Transactions):
    """ Buy transaction but comming from a Stake/Farm pool """

    def __init__(self, coin_name, amount, fee_coin_name, fee_amount, dexpool_id):
        super().__init__(coin_name, amount, fee_coin_name, fee_amount)
        self.dexpool_id = dexpool_id

        # Update benef_harvested with the dolar amount of the harvested coin
        benef_harvested = self.amount * self.price
        dbQuery = f"""SELECT w.entry_id, w.benef_harvested FROM wallet AS w JOIN
        dex_pools AS dx ON w.dexpool_id=dx.dexpool_id WHERE w.dexpool_id=
        {self.dexpool_id} ORDER BY w.entry_id ASC LIMIT 1"""
        entry = func.database_connection(dbQuery)[0]
        dbQueryUpdate = f"""UPDATE wallet SET 
        benef_harvested={0 if entry[1]==None else float(entry[1]) + benef_harvested} 
        WHERE entry_id={entry[0]}"""
        func.database_connection(dbQueryUpdate)

        # Create a new entry
        func.insert_query_connection("wallet", ["coin_id", "buy_date", "amount", 
                "price_buy"], [self.coin_id, self.timestamp, self.amount, self.price])


class Destake(Transactions):
    """ How the program manages the exit from a stake pool """

    def __init__(self, coin_name, amount, fee_coin_name, fee_amount, dexpool_id):
        super().__init__(coin_name, amount, fee_coin_name, fee_amount)
        self.dexpool = dexpool_id

        dbQuery = f"""SELECT w.entry_id, w.amount, w.price_buy FROM wallet AS w JOIN dex_pools 
        AS dx ON w.dexpool_id=dx.dexpool_id"""
        result = func.database_connection(dbQuery)
        am_destake = self.amount
        for entry in result:
            if am_destake >= entry[1]:
                # Close the entry and open a new one with no stake label
                func.benefit_sell_submission(self.price, entry[2], entry[1], 
                        entry[0], self.timestamp)
                func.insert_query_connection("wallet", ["coin_id", "buy_date", 
                        "amount", "price_buy"], [self.coin_id, self.timestamp, 
                        entry[1], self.price])
                if am_destake == entry[1]:
                    break
                am_destake -= entry[1]
            
            else:
                # Modify the actual entry amount and calculate benefit
                dbQueryUpdate = f"""UPDATE wallet SET amount={am_destake} WHERE 
                entry_id={entry[0]}"""
                func.database_connection(dbQueryUpdate)
                func.benefit_sell_submission(self.price, entry[2], am_destake, 
                        entry[0], self.timestamp)

                # Open a new entry with a reduced amount
                func.insert_query_connection("wallet", ["coin_id", "buy_date", 
                        "amount", "price_buy"], [self.coin_id, self.timestamp, 
                        am_destake, self.price])
