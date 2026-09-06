# SPDX-License-Identifier: Apache-2.0
"""Run the C++ checks against a private mock bus; never access real disks."""
import os
import subprocess
import sys
import tempfile
import threading

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
name = dbus.service.BusName('org.freedesktop.UDisks2', bus)
base = '/org/freedesktop/UDisks2/block_devices/mmcblk1'
block = 'org.freedesktop.UDisks2.Block'
partition = 'org.freedesktop.UDisks2.Partition'
filesystem = 'org.freedesktop.UDisks2.Filesystem'
calls = []


class Manager(dbus.service.Object):
    @dbus.service.method('org.freedesktop.DBus.ObjectManager', out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        return {
            base: {block: {'DeviceNumber': dbus.UInt64(101)}},
            base + 'p1': {partition: {'Table': dbus.ObjectPath(base)}, filesystem: {}},
            base + 'p2': {partition: {'Table': dbus.ObjectPath(base)}, filesystem: {}},
            base + '0': {block: {'DeviceNumber': dbus.UInt64(110)}, filesystem: {}},
        }


class Device(dbus.service.Object):
    @dbus.service.method(block, in_signature='sa{sv}', out_signature='h')
    def OpenDevice(self, mode, options):
        assert mode == 'rw'
        assert options['flags'] & os.O_EXCL
        assert options['flags'] & os.O_CLOEXEC
        assert not options['flags'] & os.O_ACCMODE
        if self._object_path == base + '0':
            raise dbus.exceptions.DBusException('Cancelled', name='org.freedesktop.UDisks2.Error.NotAuthorizedDismissed')
        with tempfile.TemporaryFile() as file:
            file.write(b'x')
            file.seek(0)
            return dbus.types.UnixFd(file.fileno())

    @dbus.service.method(filesystem, in_signature='a{sv}')
    def Unmount(self, options):
        calls.append(self._object_path)
        if self._object_path.endswith('p2'):
            raise dbus.exceptions.DBusException('Not mounted', name='org.freedesktop.UDisks2.Error.NotMounted')
        if self._object_path == base + '0':
            raise dbus.exceptions.DBusException('Busy', name='org.freedesktop.UDisks2.Error.DeviceBusy')


class Control(dbus.service.Object):
    @dbus.service.method('org.example.Test', out_signature='as')
    def Calls(self):
        return calls


objects = [Manager(bus, '/org/freedesktop/UDisks2'), Control(bus, '/test')]
objects += [Device(bus, base + suffix) for suffix in ('', 'p1', 'p2', '0')]
loop = GLib.MainLoop()
result = [1]


def run_tests():
    try:
        env = dict(os.environ, DBUS_SYSTEM_BUS_ADDRESS=os.environ['DBUS_SESSION_BUS_ADDRESS'],
                   RPI_IMAGER_MOCK_UDISKS='1')
        result[0] = subprocess.run(sys.argv[1:], env=env).returncode
    finally:
        GLib.idle_add(loop.quit)


threading.Thread(target=run_tests).start()
loop.run()
sys.exit(result[0])
