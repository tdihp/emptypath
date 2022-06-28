#!/bin/bash
set -e
TAG=tdihp/emptypath:$(date -u +%Y%m%d%H%M)

python -m grpc_tools.protoc -Iprotos --python_out=. --grpc_python_out=. emptypath/csi.proto
docker build . -t "$TAG"
docker push "$TAG"
