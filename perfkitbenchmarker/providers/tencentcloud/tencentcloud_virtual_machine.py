# Copyright 2017 PerfKitBenchmarker Authors. All rights reserved.
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
"""Class to represent a GCE Virtual Machine object.

All VM specifics are self-contained and the class provides methods to
operate on the VM: boot, shutdown, etc.
"""

import base64
import collections
import json
import logging
import threading
from absl import flags
from PerfKitBenchmarker.perfkitbenchmarker.providers import tencentcloud
from perfkitbenchmarker import disk
from perfkitbenchmarker import linux_virtual_machine
from perfkitbenchmarker import providers
from perfkitbenchmarker import virtual_machine
from perfkitbenchmarker import vm_util
from perfkitbenchmarker.providers.tencentcloud import tencentcloud_disk
from perfkitbenchmarker.providers.tencentcloud import tencentcloud_network
from perfkitbenchmarker.providers.tencentcloud import util

FLAGS = flags.FLAGS

class TencentCloudVirtualMachine(virtual_machine.BaseVirtualMachine):
  """Object representing an Tencent Cloud Virtual Machine(CVM)."""

  CLOUD = providers.TENCENTCLOUD

  _host_lock = threading.Lock()
  deleted_hosts = set()
  host_map = collections.defaultdict(list)

  def __init__(self, vm_spec):
    """Initialize a Tencent Cloud virtual machine.

    Args:
      vm_spec: virtual_machine.BaseVirtualMachineSpec object of the VM.

    Raises:
      errors.Config.MissingOption: If the spec does not include a "machine_type"
          or both "cpus" and "memory".
      errors.Config.InvalidValue: If the spec contains both "machine_type" and
          at least one of "cpus" or "memory".
    """

    super(TencentCloudVirtualMachine, self).__init__(vm_spec)
    self.user_name = FLAGS.user_name
    self.region = util.GetRegionFromZone(self.zone)
    self.network = tencentcloud_network.TencentNetwork.GetNetwork(self)
    self.firewall = tencentcloud_network.TencentFirewall.GetFirewall()
    pass

  @vm_util.Retry(poll_interval=1, log_errors=False)
  def _WaitForInstanceStatus(self, status_list):
    """Waits until the instance's status is in status_list."""
    pass

  @vm_util.Retry(poll_interval=5, max_retries=30, log_errors=False)
  def _WaitForEipStatus(self, status_list):
    """Waits until the instance's status is in status_list."""
    pass

  def _AllocatePubIp(self, region, instance_id):
    """Allocate a public ip address and associate it to the instance."""
    pass

  @vm_util.Retry()
  def _PostCreate(self):
    """Get the instance's data and tag it."""
    pass


  def _CreateDependencies(self):
    """Create VM dependencies."""
    # Calls tccli
    self.image = self.image or util.GetDefaultImage(self.machine_type,
                                                    self.region)

    # Create user and add SSH key
    with open(self.ssh_public_key) as f:
      self.public_key = f.read().rstrip('\n')
      self.key_pair_name, self.key_id = TencentKeyFileManager.ImportKeyfile(
                                                    self.region, self.public_key)

    self.AllowRemoteAccessPorts()
    pass

  def _DeleteDependencies(self):
    """Delete VM dependencies."""
    pass

  @classmethod
  def _GetDefaultImage(cls, region):
    """Returns the default image given the machine type and region.

    If no default is configured, this will return None.
    """

    pass

  def _GenerateLoginSettings() -> str:
    """Returns:
      LoginSettings. Use this parameter to set the login method,
      password, and key of the instance or keep the login settings
      of the original image.

      In this case, this value should be the ssh public key.
    """

    return ''

  def _GenerateCreateCommand(self):
    """Generates a command to create the VM instance.

    Returns:
      TccliCommand. Command to issue in order to create the VM instance.
    """
    args = ['cvm', 'RunInstances']
    cmd = util.TccliCommand(self, args)

    cmd.flags['Placement.Zone'] = self.zone
    cmd.flags['ImageId'] = self.image
    cmd.flags['InstanceType'] = self.machine_type
    cmd.flags['InstanceName'] = self.name
    cmd.flags['SecurityGroupIds'] = self.network.security_group.group_id
    cmd.flags['LoginSettings'] = self.key_id
    cmd.flags['SystemDisk.DiskType'] = self.disk.disk_type
    cmd.flags['SystemDisk.DiskSize'] = self.disk.disk_size

    return cmd


  def _Create(self):
    """Create a VM instance."""
    create_cmd = self._GenerateCreateCommand(self)
    _, stderr, retcode = create_cmd.Issue()

    pass


  def _Delete(self):
    """Delete a VM instance."""
    pass


  def _Exists(self):
    """Returns true if the VM exists."""
    pass


  def CreateScratchDisk(self, disk_spec):
    """Create a VM's scratch disk.

    Args:
      disk_spec: virtual_machine.BaseDiskSpec object of the disk.
    """
    pass


  def AddMetadata(self, **kwargs):
    """Adds metadata to the VM."""
    pass


class TencentKeyFileManager(object):
  """Object for managing Tencent Cloud Keyfiles."""
  _lock = threading.Lock()
  imported_keyfile_set = set()
  deleted_keyfile_set = set()


  @classmethod
  def ImportKeyfile(cls, region, public_key):
    """Imports the public keyfile to Tencent Cloud.

       Returns:
    """
    with cls._lock:
      if (region, FLAGS.run_uri) in cls.imported_keyfile_set:
        return
      key_name = cls.GetKeyNameForRun()

      args = ['ecs', 'ImportKeyPair']
      import_cmd = util.TccliCommand(cls, args)
      import_cmd.flags['Reigon'] = region
      import_cmd.flags['KeyName'] = key_name
      import_cmd.flags['ProjectId'] = 0
      import_cmd.flags['PublicKey'] = public_key

      stdout, _, _ = import_cmd.Issue()
      key_id = json.loads(stdout)

      cls.run_uri_key_names[FLAGS.run_uri] = key_name
      return key_name, key_id

  @classmethod
  def DeleteKeyfile(cls, region, key_name):
    """Deletes the imported KeyPair for a run_uri."""
    pass

  @classmethod
  def GetKeyNameForRun(cls):
    return 'perfkit-key-{0}'.format(FLAGS.run_uri)
