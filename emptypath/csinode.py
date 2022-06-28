
import logging
from multiprocessing.sharedctypes import Value
import os
from pathlib import Path
import subprocess
import shutil

import grpc

from . import csi_pb2
from . import csi_pb2_grpc

logger = logging.getLogger('__name__')

PLUGIN_NAME = 'emptypath.tdihp.github.io'
VENDOR_VERSION = '0.0.1'
CSI_PATH = '/csi/csi.sock'


class Node(csi_pb2_grpc.NodeServicer, csi_pb2_grpc.IdentityServicer):
    def __init__(self, node_id, path='/data', ):
        logger.info('Node(%r, %r) initializing', node_id, path)
        self.node_id = node_id
        path = Path(path)
        if not path.is_dir():
            raise FileNotFoundError('path %s not found' % path)

        self.path = path

    def GetPluginInfo(self, request, context):
        logger.debug('GetPluginInfo called')
        return csi_pb2.GetPluginInfoResponse(
            name=PLUGIN_NAME,
            vendor_version=VENDOR_VERSION,
        )

    def GetPluginCapabilities(self, request, context):
        logger.debug('GetPluginCapabilities called')
        return csi_pb2.GetPluginCapabilitiesResponse(capabilities=[])

    def Probe(self, request, context):
        logger.debug('Probe called')
        return csi_pb2.ProbeResponse(ready=True)

    def NodeGetCapabilities(self, request, context):
        logger.debug('NodeGetCapabilities called')
        return csi_pb2.NodeGetCapabilitiesResponse(capabilities=[])

    def NodeGetInfo(self, request, context):
        logger.debug('NodeGetInfo called')
        return csi_pb2.NodeGetInfoResponse(node_id=self.node_id)

    def NodePublishVolume(self, request, context):
        logger.debug('NodeGetInfo called')
        volume_id = request.volume_id
        if not volume_id:
            raise ValueError('VolumeID must be non-empty')

        ephemeral = request.volume_context.get('csi.storage.k8s.io/ephemeral')
        if not ephemeral:
            raise ValueError(
                'We only support ephemeral volume.non-ephemeral requested'
            )

        if request.readonly:
            raise ValueError('Why do you need readonly huh?')

        target_path = Path(request.target_path)
        if target_path.exists():
            raise FileExistsError('Target path %s exists' % target_path)

        logger.info('NodeGetInfo(volume_id=%s, target_path=%s)',
            volume_id, target_path)

        volume_path = self.path / volume_id
        if volume_path.exists():
            raise FileExistsError ('requesting to publish volume for id %s'
                'but file already there' % volume_id)

        volume_path.mkdir()
        target_path.mkdir()
        args = ['mount', '--bind', volume_path, target_path]
        logger.debug('mount args: %r', args)
        subprocess.run(args, check=True)
        return csi_pb2.NodePublishVolumeResponse()

    def NodeUnpublishVolume(self, request, context):
        logger.debug('NodeUnpublishVolume called')
        volume_id = request.volume_id
        if not volume_id:
            raise ValueError('VolumeID must be non-empty')

        target_path = Path(request.target_path)

        logger.info('NodeUnpublishVolume(volume_id=%s, target_path=%s)',
            volume_id, target_path)

        if target_path.exists():
            if target_path.is_mount():
                logger.info('unmounting target path %s', target_path)
                subprocess.run(['umount', target_path])
            else:
                logger.warning('target path %s is not mount', target_path)

            logger.debug('removing target path %s', target_path)
            target_path.rmdir()
        else:
            logger.warning('target path %s not exist', target_path)

        volume_path = self.path / volume_id
        if volume_path.exists():
            logger.debug('recursively removing volume path %s', volume_path)
            shutil.rmtree(volume_path)
        else:
            logger.warning('volume path %s not exist', volume_path)

        return csi_pb2.NodeUnpublishVolumeResponse()

    def prepare_server(self, server):
        csi_pb2_grpc.add_IdentityServicer_to_server(self, server)
        # csi_pb2_grpc.add_ControllerServicer_to_server(self, server)
        csi_pb2_grpc.add_NodeServicer_to_server(self, server)



