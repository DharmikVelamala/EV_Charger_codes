# -*- coding: utf-8 -*-
import sys
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
from example_advertisement import Advertisement, register_ad_cb, register_ad_error_cb
from example_gatt_server import Service, Characteristic, register_app_cb, register_app_error_cb
import dataHandler
import apiHandler
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class BluetoothGATTServer:
    def __init__(self):
        self._BLUEZ_SERVICE_NAME = 'org.bluez'
        self._DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
        self._LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
        self._GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
        self._GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'

        self._UART_SERVICE_UUID = '5D4ABCF8-9EB6-4B0F-94D9-D9CECF1D18ED'
        self._UART_RX_CHARACTERISTIC_UUID = '5D4ABCF9-9EB6-4B0F-94D9-D9CECF1D18ED'
        self._UART_TX_CHARACTERISTIC_UUID = '5D4ABCFA-9EB6-4B0F-94D9-D9CECF1D18ED'
        self._LOCAL_NAME = 'PI-Charge'

        self._data_buffer = []
        self._mainloop = None

    class TxCharacteristic(Characteristic):
        def __init__(self, bus, index, service):
            super().__init__(bus, index, server._UART_TX_CHARACTERISTIC_UUID, ['notify'], service)
            self._notifying = False
            GLib.io_add_watch(sys.stdin, GLib.IO_IN, self._on_console_input)
            self._predefined_value = "Predefined message"

        def _on_console_input(self, fd, condition):
            s = fd.readline()
            if s.isspace():
                return True
            if s.strip() == "specific message":
                self._send_tx(self._predefined_value.encode())
            else:
                self._send_tx(s.encode())
            return True

        def _send_tx(self, msg_bytes):
            if not self._notifying:
                return
            value = [dbus.Byte(b) for b in msg_bytes]
            try:
                self.PropertiesChanged(self._GATT_CHRC_IFACE, {'Value': value}, [])
            except dbus.DBusException as e:
                logging.error(f"Failed to send notification: {e}")

        def StartNotify(self):
            if self._notifying:
                return
            self._notifying = True

        def StopNotify(self):
            if not self._notifying:
                return
            self._notifying = False

    class RxCharacteristic(Characteristic):
        def __init__(self, bus, index, service, tx_characteristic, data_buffer):
            super().__init__(bus, index, server._UART_RX_CHARACTERISTIC_UUID, ['write'], service)
            self._tx_characteristic = tx_characteristic
            self._data_buffer = data_buffer

        def WriteValue(self, value, options):
            data = bytearray(value)
            logging.info(f'Received: {data}')
            self._data_buffer.append(data)

            try:
                is_valid, message = apiHandler.validate_packet(data)
                if is_valid:
                    extracted_data, extraction_message = apiHandler.extract_data(data)
                    logging.info(f"Extracted data: {extracted_data}, Message: {extraction_message}")
                    data_response = dataHandler.Authorization(extracted_data)
                    self._send_predefined_response(data_response)
                else:
                    logging.warning(f"Invalid packet: {message}")

                with open('received_data.txt', 'a') as file:
                    file.write(data.hex() + '\n')

                if len(self._data_buffer) == 17:
                    self._process_received_data()

            except Exception as e:
                logging.error(f"Error processing received data: {e}")

        def _send_predefined_response(self, msg):
            try:
                msg_bytes = bytes.fromhex(msg)
                logging.info(f"Sending predefined response: {msg_bytes}")
                self._tx_characteristic._send_tx(msg_bytes)
            except ValueError as e:
                logging.error(f"Failed to convert message to bytes: {e}")

    def process_received_data(self, data):
        try:
            fields = server._data_buffer
            # Extract and save information from the fields
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
            Bluetooth_Mac_address = fields[17]
            
            server._data_buffer.clear()
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

            with open('formatted_data.txt', 'a') as file:
                file.write(formatted_data + '\n')

        except Exception as e:
            logging.error(f"Error processing received data: {e}")

    class UartService(Service):
        def __init__(self, bus, index, data_buffer):
            super().__init__(bus, index, server._UART_SERVICE_UUID, True)
            try:
                tx_characteristic = BluetoothGATTServer.TxCharacteristic(bus, 0, self)
                self.add_characteristic(tx_characteristic)
                self.add_characteristic(BluetoothGATTServer.RxCharacteristic(bus, 1, self, tx_characteristic, data_buffer))
            except Exception as e:
                logging.error(f"Failed to initialize UART service: {e}")

    class Application(dbus.service.Object):
        def __init__(self, bus):
            self._path = '/'
            self._services = []
            super().__init__(bus, self._path)

        def get_path(self):
            return dbus.ObjectPath(self._path)

        def add_service(self, service):
            self._services.append(service)

        @dbus.service.method('org.freedesktop.DBus.ObjectManager', out_signature='a{oa{sa{sv}}}')
        def GetManagedObjects(self):
            response = {}
            for service in self._services:
                response[service.get_path()] = service.get_properties()
                for chrc in service.get_characteristics():
                    response[chrc.get_path()] = chrc.get_properties()
            return response

    def _find_adapter(self, bus):
        try:
            remote_om = dbus.Interface(bus.get_object(self._BLUEZ_SERVICE_NAME, '/'), self._DBUS_OM_IFACE)
            objects = remote_om.GetManagedObjects()
            for o, props in objects.items():
                if self._LE_ADVERTISING_MANAGER_IFACE in props and self._GATT_MANAGER_IFACE in props:
                    return o
                logging.debug(f'Skip adapter: {o}')
            return None
        except dbus.DBusException as e:
            logging.error(f"Failed to find Bluetooth adapter: {e}")
            return None

    def run(self):
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            bus = dbus.SystemBus()
            adapter = self._find_adapter(bus)
            if not adapter:
                logging.error('BLE adapter not found')
                return

            service_manager = dbus.Interface(bus.get_object(self._BLUEZ_SERVICE_NAME, adapter), self._GATT_MANAGER_IFACE)
            ad_manager = dbus.Interface(bus.get_object(self._BLUEZ_SERVICE_NAME, adapter), self._LE_ADVERTISING_MANAGER_IFACE)

            app = self.Application(bus)
            service = self.UartService(bus, 0, self._data_buffer)
            app.add_service(service)

            adv = Advertisement(bus, 0, 'peripheral')
            adv.add_service_uuid(self._UART_SERVICE_UUID)
            adv.add_local_name(self._LOCAL_NAME)
            adv.include_tx_power = True

            self._mainloop = GLib.MainLoop()

            service_manager.RegisterApplication(app.get_path(), {}, reply_handler=register_app_cb, error_handler=register_app_error_cb)
            ad_manager.RegisterAdvertisement(adv.get_path(), {}, reply_handler=register_ad_cb, error_handler=register_ad_error_cb)

            try:
                self._mainloop.run()
            except KeyboardInterrupt:
                logging.info("Exiting due to keyboard interrupt")
                adv.Release()

        except Exception as e:
            logging.error(f"Error in run method: {e}")
            if self._mainloop:
                self._mainloop.quit()

if __name__ == '__main__':
    try:
        server = BluetoothGATTServer()
        server.run()
    except Exception as e:
        logging.error(f"Error starting BluetoothGATTServer: {e}")
