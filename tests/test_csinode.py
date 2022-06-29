import pytest
import grpc
import uuid
from emptypath.csinode import *
from concurrent import futures
from unittest.mock import patch


@pytest.fixture
def server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    yield server
    server.stop(grace=1)

@pytest.fixture
def datadir(tmp_path_factory):
    return tmp_path_factory.mktemp("data")

@pytest.fixture
def node_id():
    return str(uuid.uuid4())

@pytest.fixture
def csinode(node_id, datadir):
    return Node(node_id, datadir)

@pytest.fixture
def csipath(tmp_path_factory):
    return 'unix://' + str(tmp_path_factory.mktemp("data") / 'csi.sock')

@pytest.fixture(autouse=True)
def runnodeserver(server, csinode, csipath):
    csinode.prepare_server(server)  
    server.add_insecure_port(csipath)
    server.start()

@pytest.fixture
def channel(csipath):
    channel = grpc.insecure_channel(csipath)
    yield channel
    channel.close()


def testpublish(channel, tmp_path_factory, datadir):
    target_root = tmp_path_factory.mktemp("target")
    target_path = target_root / 'mount'
    stub = csi_pb2_grpc.NodeStub(channel, )
    volume_id = "dummy-volume-id-" + str(uuid.uuid4())
    # we need to use mock as the mount needs root,
    # and we don't want that in test
    with patch('subprocess.run') as run:
        stub.NodePublishVolume(csi_pb2.NodePublishVolumeRequest(
                volume_id=volume_id,
                target_path=str(target_path),
                volume_context={
                    'csi.storage.k8s.io/ephemeral': '1',
                }
            ),
            timeout=1
        )
        assert run.called == 1
        call_args, call_kwargs = run.call_args
        assert call_args[0] == \
            ['mount', '--bind',  datadir / volume_id, target_path]
    assert target_path.exists()
    # we simply test whether driver has created the path


def testunpublish(channel, tmp_path_factory, datadir):
    target_root = tmp_path_factory.mktemp("target")
    target_path = target_root / 'mount'
    target_path.mkdir()
    volume_id = "dummy-volume-id"
    volume_path = datadir / volume_id
    volume_path.mkdir()
    # write something to volume path to make sure it can delete things
    (volume_path / 'foobar').write_text('some testing text')

    stub = csi_pb2_grpc.NodeStub(channel, )

    with patch('subprocess.run') as run:
        stub.NodeUnpublishVolume(csi_pb2.NodeUnpublishVolumeRequest(
                volume_id=volume_id,
                target_path=str(target_path),
            ),
            timeout=1
        )
        assert run.called == 1
        call_args, call_kwargs = run.call_args
        assert call_args[0] == ['umount', target_path]

    assert not volume_path.exists()
    assert not target_path.exists()


def test_nodegetinfo(channel, node_id):
    stub = csi_pb2_grpc.NodeStub(channel, )

    info = stub.NodeGetInfo(csi_pb2.NodeGetInfoRequest())
    assert info.node_id == node_id
