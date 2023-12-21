### Fleet control consisting of planning and commmunication

To test,

- go into folder `src\chargepal_local_server`
- make sure the gRPC files exist
  - to generate: `python -m grpc_tools.protoc -Iprotos --python_out=. --pyi_out=. --grpc_python_out=. protos/local_server.proto`
- `python text_server_example.py`
- use client scripts from https://git.ni.dfki.de/chargepal/system-integration/robot-packages/chargepal_client
