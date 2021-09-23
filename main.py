import classes as c
import functions as func
import psycopg2 as pg
from apikey import key
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import date, datetime

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
    func.show_trx_treasury_table()

elif op == 2:
    print("Operación de venta")
    coin_name = input("Moneda transaccionada: ")
    amount = input("Cantidad de moneda transaccionada: ")
    fee_coin_name = input("Moneda usada para pagar las fees: ")
    fee_amount = input("Cantidad de moneda usada en fees: ")
    operation = "sell"

    c.SellTransaction(coin_name, amount, fee_coin_name, fee_amount, operation)
    func.show_trx_treasury_table()

elif op == 3:
    print("Reinicio de la base de datos")
    func.reboot_database()
    func.show_trx_treasury_table()

else:
    print("Entradas activas en la base de datos")
    func.show_active_treasury()




# dbAmountQuery = f"""SELECT amount FROM transactions WHERE trx_id='9'"""
# amount_trx = database_connection(dbAmountQuery)[0][0]
# print(type(amount_trx))

# dictionary = {
#     "Comida": [["Pollo", "Patatas"], ["Lechuga", "Tomate"]],
#     "Coches": ["Chevrolet", "Peugeot"],
#     "Familia": ["Hijo", "Hermana"]
# }
# for entry in dictionary:
#     print(entry)
#     for lt in dictionary[entry]:
#         print(dictionary[entry][0][0])
        
#     print("BREAK")

# coin_name = input("Moneda transaccionada: ")
# amount = input("Cantidad de moneda transaccionada: ")
# fee_coin_name = input("Moneda usada para pagar las fees: ")
# fee_amount = input("Cantidad de moneda usada en fees: ")
# operation = input("Operacion realizada: ")

# BuyTransaction(coin_name, amount, fee_coin_name, fee_amount, operation)

# dbCoinCheck = f"""SELECT coin_name FROM coins WHERE EXISTS (SELECT 
#         coin_name FROM coins WHERE coin_name='{coin_name}')"""
# result = database_connection(dbCoinCheck)
# if result == []:
#     request = False
# else:
#     request = True
# print(request)

# func.show_treasury()


# print(datetime.now())

# coin = input("Moneda: ")
# dbQuery = f"""SELECT coin_id FROM coins WHERE coin_name='{coin}'"""

# conn = pg.connect(
#             host="localhost",
#             database="cryptotransactions",
#             user="postgres",
#             password="18p05tgr3sQL89*")

# cur = conn.cursor()
# try:
#     cur.execute(dbQuery)
# except (pg.DatabaseError, pg.InternalError, pg.OperationalError,
#         pg.DataError, pg.IntegrityError, pg.ProgrammingError) as e:
#     raise e
# finally:
#     array = []

#     if dbQuery.startswith("SELECT"):
#         for row in cur:
#             array.append(row)

#     if conn is not None:
#         conn.commit()
#         cur.close()
#         conn.close()
#         print("Database conection was successful")

# print(array[0][0])







