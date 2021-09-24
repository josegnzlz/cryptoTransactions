import sec_functions as sfunc

table_name = "coins"
values = ["DAG"]
columns = ["coin_name"]

sfunc.insert_query_connection(table_name, columns, values)
