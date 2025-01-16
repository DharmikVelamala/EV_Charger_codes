# -*- coding: utf-8 -*-
import sys
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
from example_advertisement import Advertisement, register_ad_cb, register_ad_error_cb
from example_gatt_server import Service, Characteristic, register_app_cb, register_app_error_cb
import subprocess
from wifi1 import WifiManager
import dataHandler
import apiHandler

BLUEZ_SERVICE_NAME = 'org.bluez'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'

UART_SERVICE_UUID = '5D4ABCF8-9EB6-4B0F-94D9-D9CECF1D18ED'
UART_RX_CHARACTERISTIC_UUID = '5D4ABCF9-9EB6-4B0F-94D9-D9CECF1D18ED'
UART_TX_CHARACTERISTIC_UUID = '5D4ABCFA-9EB6-4B0F-94D9-D9CECF1D18ED'
LOCAL_NAME = 'rpi-gatt-server'
mainloop = None
a = []
Wifi = WifiManager()


class TxCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, UART_TX_CHARACTERISTIC_UUID, ['notify'], service)
        self.notifying = False
        GLib.io_add_watch(sys.stdin, GLib.IO_IN, self.on_console_input)
        self.predefined_value = "Predefined message"

    def on_console_input(self, fd, condition):
        s = fd.readline()
        if s.isspace():
            return True
        if s.strip() == "specific message":
            self.send_tx(self.predefined_value.encode())
        else:
            self.send_tx(s.encode())
        return True

    def send_tx(self, msg_bytes):
        if not self.notifying:
            return
        value = [dbus.Byte(b) for b in msg_bytes]
        self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': value}, [])

    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True

    def StopNotify(self):
        if not self.notifying:
            return
        self.notifying = False


class RxCharacteristic(Characteristic):
    def __init__(self, bus, index, service, tx_characteristic):
        super().__init__(bus, index, UART_RX_CHARACTERISTIC_UUID, ['write'], service)
        self.tx_characteristic = tx_characteristic

    def WriteValue(self, value, options):
        data = bytearray(value)
        print(f'Received: {data}')
        a.append(data)
        
        is_valid, message = apiHandler.validate_packet(data)
        if is_valid:
            print("is_valid")
            extracted_data, extraction_message = apiHandler.extract_data(data)
            print(extracted_data, extraction_message)
            data_response = dataHandler.Authorization(extracted_data)
            print("response_data_packet", data_response)
            self.send_predefined_response(data_response)
        else:
            print(message)

        with open('received_data.txt', 'a') as file:
            file.write(data.hex() + '\n')
        
        if len(a) == 17:
            process_received_data(a)

    def send_predefined_response(self, msg):
        try:
            msg_bytes = bytes.fromhex(msg)
            print(f"Sending predefined response: {msg_bytes}")
            self.tx_characteristic.send_tx(msg_bytes)
        except ValueError as e:
            print(f"Failed to convert message to bytes: {e}")


'''def process_received_data(data):
    fields = a
    device_pin = fields[0]
    wifi_ssid = fields[11]
    wifi_password = fields[12]

    wifi_flag = Wifi.connect_wifi(wifi_ssid.split("\r")[0], wifi_password.split("\r")[0])
    print(wifi_flag)
    a.clear()
    
    with open('formatted_data.txt', 'a') as file:
        file.write(f"Device PIN: {device_pin}\nWi-Fi SSID: {wifi_ssid}\nWi-Fi Password: {wifi_password}\n")'''


def process_received_data(data):
    # Split the data into individual fields
    #fields = data.split(';')
    fields=a
    #print(fields)
    # Extract information from the fields
    device_pin = fields[0]
    user_id = fields[1]
    user_rights = fields[2]
    user_name = fields[3]
    user_email = fields[4]
    device_mac = fields[5]
    vehicle_manufacturer = fields[6]
    vehicle_model = fields[7]
    vehicle_class = fields[8]
    vehicle_variant = fields[9]
    vehicle_color = fields[10]
    wifi_ssid = fields[11]
    wifi_password = fields[12]
    timestamp = fields[13]
    battery_capacity = fields[14]
    vehicle_image = fields[15]
    efficiency_mileage = fields[16]
    Bluetooth_Mac_address=fields[17]
    
    wifi_flag=Wifi.connect_wifi(wifi_ssid.split("\r")[0],wifi_password.split("\r")[0])
    print(wifi_flag)
    a.clear()
    # Format the information and store it in a specific format
    Bluetooth_mac_data = f"Saved bluetooth Mac address: {Bluetooth_Mac_address}"
    with open('mac_data.txt', 'a') as file:
        file.write(Bluetooth_mac_data + '\n')
        
        
    formatted_data = f"Device PIN: {device_pin}\n" \
                     f"User ID: {user_id}\n" \
                     f"User Rights: {user_rights}\n" \
                     f"User Name: {user_name}\n" \
                     f"User Email: {user_email}\n" \
                     f"Device MAC Address: {device_mac}\n" \
                     f"Vehicle Manufacturer: {vehicle_manufacturer}\n" \
                     f"Vehicle Model: {vehicle_model}\n" \
                     f"Vehicle Class: {vehicle_class}\n" \
                     f"Vehicle Variant: {vehicle_variant}\n" \
                     f"Vehicle Color: {vehicle_color}\n" \
                     f"Wi-Fi SSID: {wifi_ssid}\n" \
                     f"Wi-Fi Password: {wifi_password}\n" \
                     f"Timestamp: {timestamp}\n" \
                     f"Battery Capacity: {battery_capacity}\n" \
                     f"Vehicle Image: {vehicle_image}\n" \
                     f"Efficiency/Mileage: {efficiency_mileage}\n"
    
    # Store the formatted data in a separate file
    with open('formatted_data.txt', 'a') as file:
        file.write(formatted_data + '\n')
        
    return wifi_flag


class UartService(Service):
    def __init__(self, bus, index):
        super().__init__(bus, index, UART_SERVICE_UUID, True)
        tx_characteristic = TxCharacteristic(bus, 0, self)
        self.add_characteristic(tx_characteristic)
        self.add_characteristic(RxCharacteristic(bus, 1, self, tx_characteristic))


class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        super().__init__(bus, self.path)

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


class UartApplication(Application):
    def __init__(self, bus):
        super().__init__(bus)
        self.add_service(UartService(bus, 0))


class UartAdvertisement(Advertisement):
    def __init__(self, bus, index):
        super().__init__(bus, index, 'peripheral')
        self.add_service_uuid(UART_SERVICE_UUID)
        self.add_local_name(LOCAL_NAME)
        self.include_tx_power = True


def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for o, props in objects.items():
        if LE_ADVERTISING_MANAGER_IFACE in props and GATT_MANAGER_IFACE in props:
            return o
        print(f'Skip adapter: {o}')
    return None


def main():
    global mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    adapter = find_adapter(bus)
    if not adapter:
        print('BLE adapter not found')
        return

    service_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter), GATT_MANAGER_IFACE)
    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter), LE_ADVERTISING_MANAGER_IFACE)

    app = UartApplication(bus)
    adv = UartAdvertisement(bus, 0)

    mainloop = GLib.MainLoop()

    service_manager.RegisterApplication(app.get_path(), {}, reply_handler=register_app_cb, error_handler=register_app_error_cb)
    ad_manager.RegisterAdvertisement(adv.get_path(), {}, reply_handler=register_ad_cb, error_handler=register_ad_error_cb)
    try:
        mainloop.run()
    except KeyboardInterrupt:
        adv.Release()


if __name__ == '__main__':
    main()
