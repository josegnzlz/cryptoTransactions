import classes as c
import psycopg2 as pg
from apikey import key
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import date, datetime
import functions as func

op = int(input("""Si quieres hacer una COMPRA pulsa 1, si quieres hacer una venta pulsa 2, 
reiniciar la base de datos 3, ver las entradas activas 4: """))
if op == 1:
    print("Operación de compra")
    coin_name = input("Moneda transaccionada: ")
    amount = input("Cantidad de moneda transaccionada: ")
    fee_coin_name = input("Moneda usada para pagar las fees: ")
    fee_amount = input("Cantidad de moneda usada en fees: ")
    operation = "buy"

    c.BuyTransaction(coin_name, amount, fee_coin_name, fee_amount, operation)
    func.show_wallet()

elif op == 2:
    print("Operación de venta")
    coin_name = input("Moneda transaccionada: ")
    amount = input("Cantidad de moneda transaccionada: ")
    fee_coin_name = input("Moneda usada para pagar las fees: ")
    fee_amount = input("Cantidad de moneda usada en fees: ")
    operation = "sell"

    c.SellTransaction(coin_name, amount, fee_coin_name, fee_amount, operation)
    func.show_wallet()

elif op == 3:
    print("Reinicio de la base de datos")
    func.reboot_database()

else:
    print("Entradas activas en la base de datos")
