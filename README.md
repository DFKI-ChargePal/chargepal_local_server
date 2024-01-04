### Fleet control consisting of planning and commmunication

To test,

- go into folder `src\chargepal_local_server`
- make sure the gRPC files exist, if not
  - to generate: `python -m grpc_tools.protoc -Iprotos --python_out=. --pyi_out=. --grpc_python_out=. communication.proto`
- `python text_server_example.py`
- use client scripts from https://git.ni.dfki.de/chargepal/system-integration/robot-packages/chargepal_client (branch: expreiment/client)
