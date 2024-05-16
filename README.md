### Fleet control consisting of planning and commmunication

To run the server:

- go into folder `src/chargepal_local_server`
- make sure the gRPC files `communication_pb2.*` exist
  - if not, generate them from the `src` folder above with the `./generate-proto` script (or with
    `python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. chargepal_local_server/communication.proto`
    directly)
- `python server.py`
- use client scripts from https://git.ni.dfki.de/chargepal/system-integration/robot-packages/chargepal_client
