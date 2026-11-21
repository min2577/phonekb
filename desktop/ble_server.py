#!/usr/bin/env python3
"""ble_server.py - PhoneKB BLE Central client (GATT Client).

Phone = Peripheral (broadcasts "PhoneKB").
PC = Central (scans, connects, subscribes Notify to receive commands).

Usage:
  1. Library (main.py embeds):
     from ble_server import start_ble_central, write_to_phone_async
     handles = await start_ble_central(on_msg_bytes_coro, name="PhoneKB", loop=loop)
     await write_to_phone_async(handles, b'...')

  2. CLI (Phase 0 demo):
     python ble_server.py
     -> scan, find PhoneKB, connect, print received bytes

UUID spec:
  Service         a1b2c3d4-0001-4000-8000-00805f9b34fb
  Notify char     a1b2c3d4-0002-4000-8000-00805f9b34fb  (phone -> pc, commands)
  Write char      a1b2c3d4-0003-4000-8000-00805f9b34fb  (pc -> phone, responses)
"""
import asyncio
import ctypes
import logging
import subprocess
import sys
from typing import Awaitable, Callable, Optional, Union

from winrt.windows.devices.bluetooth import (
    BluetoothAdapter,
    BluetoothLEDevice,
)
from winrt.windows.devices.bluetooth.advertisement import (
    BluetoothLEAdvertisementWatcher,
)
from winrt.windows.devices.bluetooth.genericattributeprofile import (
    GattCharacteristicProperties,
    GattClientCharacteristicConfigurationDescriptorValue,
    GattCommunicationStatus,
)
from winrt.windows.storage.streams import DataReader, DataWriter

log = logging.getLogger("phonekb.ble")

SERVICE_UUID = 'a1b2c3d4-0001-4000-8000-00805f9b34fb'
NOTIFY_CHAR_UUID = 'a1b2c3d4-0002-4000-8000-00805f9b34fb'
WRITE_CHAR_UUID = 'a1b2c3d4-0003-4000-8000-00805f9b34fb'


def _bytes_from_buffer(buf):
    reader = DataReader.from_buffer(buf)
    n = reader.unconsumed_buffer_length
    if n <= 0:
        return b''
    return bytes(reader.read_bytes(n))


def _ensure_bt_user_service():
    try:
        qout = subprocess.run(['sc', 'query', 'state=', 'all'], capture_output=True, text=True, timeout=5).stdout
    except Exception as e:
        log.warning('sc query failed: ' + str(e))
        return False, None
    for line in qout.splitlines():
        if 'SERVICE_NAME: BluetoothUserService_' in line:
            svc = line.split(': ', 1)[1].strip()
            try:
                r = subprocess.run(['sc', 'start', svc], capture_output=True, text=True, timeout=10)
                return r.returncode == 0, svc
            except Exception as e:
                log.warning('sc start failed: ' + str(e))
                return False, svc
    return False, None


async def start_ble_central(
    on_message: Callable[[bytes], Union[None, Awaitable[None]]],
    name: str = 'PhoneKB',
    loop: Optional[asyncio.AbstractEventLoop] = None,
    on_connected: Optional[Callable] = None,
    on_disconnected: Optional[Callable] = None,
):
    """Start BLE Central scanner. Find phone 'PhoneKB', connect, subscribe Notify.

    on_message(bytes): called per Notify frame from phone
    on_connected(): called after GATT connected + Notify subscribed
    on_disconnected(): called on disconnect (best-effort)

    Returns dict {watcher, state, ...}. Caller keeps it alive.
    """
    if loop is None:
        loop = asyncio.get_running_loop()

    adapter = await BluetoothAdapter.get_default_async()
    if adapter is None:
        raise RuntimeError('no bluetooth adapter')
    log.info('BLE adapter: ' + str(adapter.device_id))

    ok, svc_name = _ensure_bt_user_service()
    if ok:
        log.info('BluetoothUserService started: ' + svc_name)
    else:
        log.warning('BluetoothUserService not running, some Win10 may not work')

    state = {
        'device': None,
        'service': None,
        'notify_char': None,
        'write_char': None,
        'connected': False,
    }

    async def _connect_to_phone(bt_addr: int):
        if state['connected']:
            return
        log.info('BLE Central connecting to phone: ' + hex(bt_addr))
        try:
            device = await BluetoothLEDevice.from_bluetooth_address_async(bt_addr)
        except Exception as e:
            log.warning('from_bluetooth_address_async failed: ' + str(e))
            return
        if device is None:
            log.warning('device is None')
            return
        state['device'] = device
        try:
            services_result = await device.get_gatt_services_async()
        except Exception as e:
            log.warning('get_gatt_services_async failed: ' + str(e))
            return
        if services_result.status != GattCommunicationStatus.SUCCESS:
            log.warning('GATT services enum failed status=' + str(services_result.status))
            return
        target_service = None
        for svc in services_result.services:
            try:
                if str(svc.uuid).lower() == SERVICE_UUID:
                    target_service = svc
                    break
            except Exception:
                continue
        if target_service is None:
            log.warning('service ' + SERVICE_UUID + ' not found')
            return
        state['service'] = target_service
        try:
            chars_result = await target_service.get_characteristics_async()
        except Exception as e:
            log.warning('get_characteristics_async failed: ' + str(e))
            return
        if chars_result.status != GattCommunicationStatus.SUCCESS:
            log.warning('GATT chars enum failed status=' + str(chars_result.status))
            return
        notify_char = None
        write_char = None
        for ch in chars_result.characteristics:
            try:
                u = str(ch.uuid).lower()
                if u == NOTIFY_CHAR_UUID:
                    notify_char = ch
                elif u == WRITE_CHAR_UUID:
                    write_char = ch
            except Exception:
                continue
        if notify_char is None or write_char is None:
            log.warning('Notify/Write chars not found')
            return
        state['notify_char'] = notify_char
        state['write_char'] = write_char

        def on_notify_sync(sender, args):
            try:
                data = _bytes_from_buffer(args.value)
            except Exception as e:
                log.exception('on_notify decode failed: ' + str(e))
                return
            if not data:
                return
            log.info('BLE recv ' + str(len(data)) + ' bytes hex=' + data[:32].hex(' '))
            try:
                result = on_message(data)
            except Exception as e:
                log.exception('on_message callback failed: ' + str(e))
                return
            if asyncio.iscoroutine(result):
                asyncio.run_coroutine_threadsafe(result, loop)

        notify_char.add_value_changed(on_notify_sync)

        try:
            status = await notify_char.write_client_characteristic_configuration_descriptor_async(
                GattClientCharacteristicConfigurationDescriptorValue.NOTIFY
            )
            if status != GattCommunicationStatus.SUCCESS:
                log.warning('subscribe Notify failed status=' + str(status))
                return
        except Exception as e:
            log.warning('write CCCD exception: ' + str(e))
            return

        state['connected'] = True
        log.info('BLE GATT connected  Notify=' + NOTIFY_CHAR_UUID + '  Write=' + WRITE_CHAR_UUID)
        if on_connected is not None:
            try:
                on_connected()
            except Exception:
                pass

    def on_advertisement_sync(sender, args):
        try:
            adv = args.advertisement
            local_name = ''
            if adv and adv.local_name:
                local_name = str(adv.local_name)
            if local_name != name:
                return
            bt_addr = int(args.bluetooth_address)
            log.info('BLE scan found ' + name + ' @ ' + hex(bt_addr))
            asyncio.run_coroutine_threadsafe(_connect_to_phone(bt_addr), loop)
        except Exception as e:
            log.exception('on_advertisement failed: ' + str(e))

    watcher = BluetoothLEAdvertisementWatcher()
    watcher.add_received(on_advertisement_sync)
    watcher.start()
    log.info('BLE scan started, waiting for ' + name + '...')

    return {
        'watcher': watcher,
        'state': state,
        'service_uuid': SERVICE_UUID,
        'notify_char_uuid': NOTIFY_CHAR_UUID,
        'write_char_uuid': WRITE_CHAR_UUID,
    }


async def write_to_phone_async(handles, payload: bytes):
    """PC -> phone: write bytes to phone's Write characteristic. Returns True on success."""
    state = handles.get('state') if isinstance(handles, dict) else None
    if state is None or not state.get('connected'):
        return False
    write_char = state.get('write_char')
    if write_char is None:
        return False
    dw = DataWriter()
    dw.write_bytes(payload)
    buf = dw.detach_buffer()
    try:
        result = await write_char.write_value_with_result_async(buf)
        return result.status == GattCommunicationStatus.SUCCESS
    except Exception as e:
        log.exception('write_to_phone failed: ' + str(e))
        return False


async def _phase0_main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
    adapter = await BluetoothAdapter.get_default_async()
    if adapter is None:
        print('error: no bluetooth adapter')
        sys.exit(1)
    print('adapter: ' + str(adapter.device_id))

    def on_msg(data: bytes):
        print('')
        print('[recv] ' + str(len(data)) + ' bytes hex=' + data.hex(' '))
        try:
            t = data.decode('utf-8')
            print('       text: ' + repr(t))
        except Exception:
            pass
        return None

    def on_connected():
        print('[connected PhoneKB]')

    handles = await start_ble_central(on_msg, name='PhoneKB', on_connected=on_connected)
    print('[3/3] waiting for phone to broadcast... (Ctrl+C to quit)')
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print('quit')


if __name__ == '__main__':
    if ctypes.windll.shell32.IsUserAnAdmin() == 0:
        print('need admin (BLE GATT client requires)')
        print('requesting UAC...')
        rc = ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, ' '.join(sys.argv), None, 1)
        if int(rc) > 32:
            print('new window started, use that')
            sys.exit(0)
        else:
            print('UAC cancelled or failed rc=' + str(rc))
    asyncio.run(_phase0_main())
