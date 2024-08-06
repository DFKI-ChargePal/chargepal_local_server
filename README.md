# ChargePal Local Server software

This repository contains software for database access, planning and fleet control, as well as robot-server communication.

## Server and planner

Entry point to this component in the ChargePal application is the `server.py` script, which imports the `planner.py` script.

- The `server.py` script uses grpc to communicate with the robots and continuously runs the planner.
- The `planner.py` script runs a loop consisting of:
  - fetching all relevant data from robot databases (rdb) and local server database (lsv / ldb) in the planning database (pdb),
  - processing all current and new bookings, i.e. charging requests, as well as jobs, i.e. robot action sequences,
  - updating server and planning databases accordingly.

To run the server:

- go into folder `src/chargepal_local_server`
- make sure the gRPC files `communication_pb2_grpc.py`, `communication_pb2.py`, and `communication_pb2.pyi` exist
  - if not, generate them from the `src` folder above with the `./generate-proto` script (or with
    `python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. chargepal_local_server/communication.proto`
    directly)
- `python server.py`
- use client scripts from https://git.ni.dfki.de/chargepal/system-integration/robot-packages/chargepal_client

## Databases

The database architecture of ChargePal servers and robots consists of several database types due to the distributed system
and due to the different responsibilites of components in the ChargePal consortium:

- the server's mysql database (lsv), owned and maintained by our partners
- the server's sqlite3 databases for fleet control and communication (ldb) as well as for planning (pdb)
- the robots' sqlite3 databases (rdb), see `chargepal_client` for details

Database access and usage is handled by various scripts:

- `ldb_interfaces.py` and `pdb_interfaces.py` describe the ldb and pdb interfaces, respectively, using [sqlmodel](https://sqlmodel.tiangolo.com/).
- `create_ldb.py`, `create_ldb_orders.py`, `create_pdb.py`, and `reset_dbs` are used to initialize the databases.
- `access_ldb`, `update_ldb.py`, and `update_pdb.py` contain utility function to the databases.
