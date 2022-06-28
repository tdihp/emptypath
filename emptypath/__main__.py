import os
import logging

import grpc
from concurrent import futures
from emptypath.csinode import Node

csi_path = os.environ.get('EMPTHPATH_CSI_BIND', 'unix:///csi/csi.sock')
csi_threads = int(os.environ.get('EMPTHPATH_CSI_THREADS', '4'))
volume_path = os.environ.get('EMPTYPATH_VOLUME_PATH', '/data')
verbosity = os.environ.get('EMPTYPATH_VERBOSITY', 'INFO')
node_id = os.environ.get('EMPTYPATH_NODE_ID', 'dummy_id')

logging.basicConfig(level=getattr(logging, verbosity))

server = grpc.server(futures.ThreadPoolExecutor(max_workers=csi_threads))
node = Node(node_id, volume_path)
node.prepare_server(server)
server.add_insecure_port(csi_path)
server.start()
server.wait_for_termination()
