#!/usr/bin/env python3
import sqlite3
import communication_pb2


def read_serialize() -> communication_pb2.Response_UpdateRDB:
    ldb_data = communication_pb2.Response_UpdateRDB()

    conn_ldb = sqlite3.connect("db/ldb.db")
    cur_ldb = conn_ldb.cursor()

    # Get list of tables
    cur_ldb.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur_ldb.fetchall()

    # Iterate over tables
    for table_row in tables:
        table_name = table_row[0]

        # Read data from table
        cur_ldb.execute(f"SELECT ROWID,* FROM {table_name};")
        rows = cur_ldb.fetchall()

        # Create TableData message
        table_data = communication_pb2.TableData()
        for row in rows:
            row_msg = communication_pb2.Row()
            row_msg.row_identifier = row[0]
            row_msg.column_values = str(row[1:])
            table_data.rows.append(row_msg)
        table_data.table_name = table_name

        # Add table_data to DBData
        ldb_data.tables.append(table_data)

    # Close connection
    conn_ldb.close()

    return ldb_data
