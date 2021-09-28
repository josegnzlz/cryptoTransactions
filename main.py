import classes as c
import psycopg2 as pg
from apikey import key
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import date, datetime
import functions as func

while True:
    op = int(input("""Si quieres hacer una COMPRA pulsa 1, si quieres hacer una venta pulsa 2, 
    reiniciar la base de datos 3, si quieres hacer un stake de una moneda pulsa 4,
    si quieres retirar beneficios de una pool pulsa 5, ver las entradas activas 6,
    para sacar monedas de una stake pool pulsa 7, salir del bucle 8: """))

    if op == 1:
        print("Operación de compra")
        coin_name = input("Moneda transaccionada: ")
        amount = input("Cantidad de moneda transaccionada: ")
        fee_coin_name = input("Moneda usada para pagar las fees: ")
        fee_amount = input("Cantidad de moneda usada en fees: ")

        func.check_coin_name_input(coin_name)
        func.check_coin_name_input(fee_coin_name)

        c.BuyTransaction(coin_name.upper(), amount, fee_coin_name.upper(), fee_amount)
        func.show_wallet()

    elif op == 2:
        print("Operación de venta")
        coin_name = input("Moneda transaccionada: ")
        amount = input("Cantidad de moneda transaccionada: ")
        fee_coin_name = input("Moneda usada para pagar las fees: ")
        fee_amount = input("Cantidad de moneda usada en fees: ")

        func.check_coin_name_input(coin_name)
        func.check_coin_name_input(fee_coin_name)

        c.SellTransaction(coin_name.upper(), amount, fee_coin_name.upper(), fee_amount)
        func.show_wallet()

    elif op == 3:
        print("Reinicio de la base de datos")
        func.reboot_database()

    elif op == 4:
        print("Operación de stake")
        coin_name = input("Moneda transaccionada: ")
        amount = input("Cantidad de moneda transaccionada: ")
        dex_pool = input("DEX-pool en la que se ha invertido: ")
        fee_coin_name = input("Moneda usada para pagar las fees: ")
        fee_amount = input("Cantidad de moneda usada en fees: ")

        func.check_coin_name_input(coin_name)
        func.check_coin_name_input(fee_coin_name)

        c.Stake(coin_name.upper(), amount, dex_pool, fee_coin_name.upper(), fee_amount)
        func.show_wallet()

    elif op == 5:
        print("Operación de compra harvested")
        coin_name = input("Moneda transaccionada: ")
        amount = input("Cantidad de moneda transaccionada: ")
        fee_coin_name = input("Moneda usada para pagar las fees: ")
        fee_amount = input("Cantidad de moneda usada en fees: ")
        print(func.dexpools_database())
        dexpool_id = int(input("Selecciona el id de la pool: "))

        if func.check_coin_name_input(coin_name) == False:
            continue
        if func.check_coin_name_input(fee_coin_name) == False:
            continue

        c.HarvestBuy(coin_name.upper(), amount, fee_coin_name.upper(), fee_amount, 
                dexpool_id)
        func.show_wallet()

    elif op == 6:
        print("Entradas activas en la base de datos")
        func.show_wallet()

    elif op == 7:
        print("Operación de destake")
        coin_name = input("Moneda transaccionada: ")
        amount = input("Cantidad de moneda transaccionada: ")
        fee_coin_name = input("Moneda usada para pagar las fees: ")
        fee_amount = input("Cantidad de moneda usada en fees: ")
        print(func.dexpools_database())
        dexpool_id = int(input("Selecciona el id de la pool: "))

        if func.check_coin_name_input(coin_name) == False:
            continue
        if func.check_coin_name_input(fee_coin_name) == False:
            continue

        c.Destake(coin_name, amount, fee_coin_name, fee_amount, dexpool_id)
        func.show_wallet()

    else:
        break
