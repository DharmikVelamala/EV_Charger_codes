import sys
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
from example_advertisement import Advertisement, register_ad_cb, register_ad_error_cb
from example_gatt_server import Service, Characteristic, register_app_cb, register_app_error_cb
from wifi1 import WifiManager
import dataHandler
import apiHandler

# Constants for BLE UUIDs and other configurations
UART_SERVICE_UUID = '5D4ABCF8-9EB6-4B0F-94D9-D9CECF1D18ED'
UART_RX_CHARACTERISTIC_UUID = '5D4ABCF9-9EB6-4B0F-94D9-D9CECF1D18ED'
UART_TX_CHARACTERISTIC_UUID = '5D4ABCFA-9EB6-4B0F-94D9-D9CECF1D18ED'
LOCAL_NAME = 'rpi-gatt-server'
BLUETOOTH_SERVICE_NAME = 'org.bluez'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'

class BLEDriver:
    """
    Driver class for handling BLE communication.
    """
    def __init__(self, service_uuid, local_name, rx_uuid, tx_uuid):
        self.service_uuid = service_uuid
        self.local_name = local_name
        self.rx_uuid = rx_uuid
        self.tx_uuid = tx_uuid
        self.bus = None
        self.mainloop = None
        self.wifi_manager = WifiManager()

    def find_adapter(self):
        """Find a suitable BLE adapter."""
        remote_om = dbus.Interface(self.bus.get_object(BLUETOOTH_SERVICE_NAME, '/'), DBUS_OM_IFACE)
        objects = remote_om.GetManagedObjects()
        for obj, props in objects.items():
            if LE_ADVERTISING_MANAGER_IFACE in props and GATT_MANAGER_IFACE in props:
                return obj
        return None

    def run(self):
        """Initialize and start the BLE main loop."""
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        adapter = self.find_adapter()
        if not adapter:
            print('BLE adapter not found')
            return

        service_manager = dbus.Interface(self.bus.get_object(BLUETOOTH_SERVICE_NAME, adapter), GATT_MANAGER_IFACE)
        ad_manager = dbus.Interface(self.bus.get_object(BLUETOOTH_SERVICE_NAME, adapter), LE_ADVERTISING_MANAGER_IFACE)

        app = UartApplication(self.bus, self.service_uuid, self.rx_uuid, self.tx_uuid)
        adv = UartAdvertisement(self.bus, 0, self.service_uuid, self.local_name)

        self.mainloop = GLib.MainLoop()

        service_manager.RegisterApplication(app.get_path(), {}, reply_handler=register_app_cb, error_handler=register_app_error_cb)
        ad_manager.RegisterAdvertisement(adv.get_path(), {}, reply_handler=register_ad_cb, error_handler=register_ad_error_cb)
        
        try:
            self.mainloop.run()
        except KeyboardInterrupt:
            adv.Release()

class TxCharacteristic(Characteristic):
    def __init__(self, bus, index, service, uuid):
        super().__init__(bus, index, uuid, ['notify'], service)
        self.notifying = False
        GLib.io_add_watch(sys.stdin, GLib.IO_IN, self.on_console_input)

    def on_console_input(self, fd, condition):
        s = fd.readline()
        if not s.strip():
            return True
        self.send_tx(s.encode())
        return True

    def send_tx(self, msg_bytes):
        if not self.notifying:
            return
        value = [dbus.Byte(b) for b in msg_bytes]
        self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': value}, [])

    def StartNotify(self):
        self.notifying = True

    def StopNotify(self):
        self.notifying = False

class RxCharacteristic(Characteristic):
    def __init__(self, bus, index, service, uuid, tx_characteristic):
        super().__init__(bus, index, uuid, ['write'], service)
        self.tx_characteristic = tx_characteristic

    def WriteValue(self, value, options):
        data = bytearray(value)
        print(f'Received: {data}')
        is_valid, message = apiHandler.validate_packet(data)
        if is_valid:
            extracted_data, extraction_message = apiHandler.extract_data(data)
            data_response = dataHandler.Authorization(extracted_data)
            self.tx_characteristic.send_tx(bytes.fromhex(data_response))
        else:
            print(f"Invalid data: {message}")

class UartService(Service):
    def __init__(self, bus, index, service_uuid, rx_uuid, tx_uuid):
        super().__init__(bus, index, service_uuid, True)
        tx_characteristic = TxCharacteristic(bus, 0, self, tx_uuid)
        self.add_characteristic(tx_characteristic)
        self.add_characteristic(RxCharacteristic(bus, 1, self, rx_uuid, tx_characteristic))

class UartApplication(dbus.service.Object):
    def __init__(self, bus, service_uuid, rx_uuid, tx_uuid):
        self.path = '/'
        self.services = []
        super().__init__(bus, self.path)
        self.add_service(UartService(bus, 0, service_uuid, rx_uuid, tx_uuid))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            for chrc in service.get_characteristics():
                response[chrc.get_path()] = chrc.get_properties()
        return response

class UartAdvertisement(Advertisement):
    def __init__(self, bus, index, service_uuid, local_name):
        super().__init__(bus, index, 'peripheral')
        self.add_service_uuid(service_uuid)
        self.add_local_name(local_name)
        self.include_tx_power = True

if __name__ == '__main__':
    driver = BLEDriver(
        service_uuid=UART_SERVICE_UUID,
        local_name=LOCAL_NAME,
        rx_uuid=UART_RX_CHARACTERISTIC_UUID,
        tx_uuid=UART_TX_CHARACTERISTIC_UUID
    )
    driver.run()
