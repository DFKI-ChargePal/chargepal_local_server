### Fleet control consisting of planning and commmunication

To run the server:

- go into folder `src\chargepal_local_server`
- make sure the gRPC files `communication_pb2.*` exist
  - if not, generate them with `python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. communication.proto`
- `python server.py`
- use client scripts from https://git.ni.dfki.de/chargepal/system-integration/robot-packages/chargepal_client
