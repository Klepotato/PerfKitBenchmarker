# Copyright 2014 PerfKitBenchmarker Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Module containing classes related to Tencent Cloud disks.

Disks can be created, deleted, attached to VMs, and detached from VMs.
Use 'DescribeDisks' to determine valid disk types.
"""

import json
import logging
import string
import threading
from absl import flags
from perfkitbenchmarker import disk
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.providers.tencentcloud import tencentcloud_network
from perfkitbenchmarker.providers.tencentcloud import util

FLAGS = flags.FLAGS
#???具体的参数不确定,看什么地方？
#猜测是descride返回的东西
T_STANDARD = 'pd-standard'
T_REMOTE_SSD = 'CLOUD_HSSD'
T_REMOTE_ESSD = 'CLOUD_HSSD'
T_LOCAL= 'cloud_efficiency'
T_PIOPS = 'pd-extreme'

DISK_TYPE = {
  disk.STANDARD: T_STANDARD,
  disk.REMOTE_SSD: T_REMOTE_SSD,
  disk.PIOPS: T_PIOPS,
  disk.LOCAL: T_LOCAL,
  disk.REMOTE_ESSD: T_REMOTE_ESSD,
}

class TencentDisk(disk.BaseDisk):
  """Object representing an TencentCloud Disk."""

  _lock = threading.Lock()
  vm_devices = {}

  def __init__(self, disk_spec, zone):
    super(TencentDisk, self).__init__(disk_spec)
    self.id = None
    self.Count= '1'
    self.region = util.GetRegionFromZone(self.zone)#get还没补充完
    self.attached_vm_id = None
    self.disk_type= 'CLOUD_HSSD'
    self.disk_size= '500'

  def _Create(self):
    """Creates the disk."""
    #查找cli命令用字符串输入腾讯云的接口命令
    create_cmd = util.Tencent_PREFIX +[
      'ecm',
      'CreateDisk',
      '--DiskType %s' % self.disk_type,
      '--DiskCount %s' % self.Count,
      '--DiskSize %s' % self.disk_size,
      #'--DiskCategory %s' % DISK_TYPE[self.disk_type]
    ]
    create_cmd = util.TccliCommand(create_cmd)  #获取命令行工具得到的东西
    stdout, _, _ = vm_util.IssueCommand(create_cmd, raise_on_failure=False)
    response = json.loads(stdout)   #解析返回地json数据
    self.id = response['DiskId']

  def _Delete(self):
    """Deletes the disk."""
    #cmd
    delete_cmd = util.Tencent_PREFIX + [
        'ecm',
        'TerminateDisks',
        '--DiskId %s' % self.id]
    logging.info('Deleting Tencent Cloud disk %s. This may fail if the disk is not '
                 'yet detached, but will be retried.', self.id)
    delete_cmd = util.GetEncodedCmd(delete_cmd)
    vm_util.IssueRetryableCommand(delete_cmd)

  def Attach(self, vm):
    """Attaches the disk to a VM.

    Args:
      vm: The TencentVirtualMachine instance to which the disk will be attached.
    """
    with self._lock:
      self.attached_vm_id = vm.id
      if self.attached_vm_id not in TencentDisk.vm_devices:
        TencentDisk.vm_devices[self.attached_vm_id] = set(
            string.ascii_lowercase[1:])
      self.device_letter = min(TencentDisk.vm_devices[self.attached_vm_id])
      TencentDisk.vm_devices[self.attached_vm_id].remove(self.device_letter)

    attach_cmd = util.Tencent_PREFIX + [
        'ecm',
        'AttachDisks',
        '--DiskId %s' % self.id,
        '--InstanceId %s' % self.attached_vm_id,
        '--Device %s' % self.GetVirtualDevicePath()]
    attach_cmd = util.GetEncodedCmd(attach_cmd)
    vm_util.IssueRetryableCommand(attach_cmd)

  def Detach(self): #卸载主机上的云盘
    """Detaches the disk from a VM."""
    #cmd
    detach_cmd = util.Tencent_PREFIX + [
      'ecm',
      'DetachDisks',
      '--InstanceId %s' % self.attached_vm_id,
      '--DiskId %s' % self.id]
    detach_cmd = util.GetEncodedCmd(detach_cmd)
    vm_util.IssueRetryableCommand(detach_cmd)

    with self._lock:
      assert self.attached_vm_id in TencentDisk.vm_devices
      TencentDisk.vm_devices[self.attached_vm_id].add(self.device_letter)
      self.attached_vm_id = None
      self.device_letter = None

  def GetDevicePath(self):
    """Returns the path to the device inside the VM."""
    return '/dev/vd%s' % self.device_letter

  def GetVirtualDevicePath(self):
    """Returns the path to the device visible to console users."""
    return '/dev/xvd%s' % self.device_letter

  @vm_util.Retry(poll_interval=5, max_retries=30, log_errors=False)
  def WaitForDiskStatus(self, status_list):
    """Waits until disk is attach to the instance"""
    logging.info('Waits until the disk\'s status is one of statuses: %s',
                 status_list)
    #cmd
    describe_cmd = util.Tencent_PREFIX + [
        'ecm',
        'DescribeDisks']
    attach_cmd = util.GetEncodedCmd(describe_cmd)
    stdout, _ = vm_util.IssueRetryableCommand(attach_cmd)
    response = json.loads(stdout)
    disk = response['Disks']['Disk']
    assert len(disk) == 1
    status = disk[0]['Status']
    assert status in status_list
