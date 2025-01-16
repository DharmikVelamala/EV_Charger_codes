import smbus2
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CoralEnvSensor:
    I2C_BUS = 1  # Default I2C bus on Raspberry Pi

    # I2C addresses
    
    RESULT_REGISTER = 0x00
    CONFIG_REGISTER = 0x01
    LOW_LIMIT_REGISTER = 0x02
    HIGH_LIMIT_REGISTER = 0x03
    MANUFACTURER_ID_REGISTER = 0x7E
    
    ADDRESSES = {
        "HUMIDITY_TEMP": 0x40,
        "AMBIENT_LIGHT": 0x45,
        "BAROMETRIC_PRESSURE": 0x76,
        "ANALOG_ADC": 0x49,
        "CRYPTOPROCESSOR": 0x30,
    }

    def __init__(self, i2c_bus=None):
        """Initialize I2C connection with default or user-specified bus."""
        try:
            self.bus = smbus2.SMBus(i2c_bus if i2c_bus is not None else self.I2C_BUS)
            logging.info("Initialized I2C bus %d", i2c_bus if i2c_bus is not None else self.I2C_BUS)
        except Exception as e:
            logging.error("Failed to initialize I2C bus: %s", e)
            raise RuntimeError("I2C initialization failed") from e

    # Humidity and Temperature Sensor (HDC2010)
    def read_humidity_temperature(self):
        """Read humidity and temperature from HDC2010."""
        try:
            address = self.ADDRESSES["HUMIDITY_TEMP"]
            # Trigger measurement
            self.bus.write_byte_data(address, 0x0F, 0x01)  # Trigger temperature/humidity measurement
            time.sleep(0.1)  # Wait for the measurement to complete

            # Read temperature and humidity
            temp_raw = self.bus.read_word_data(address, 0x00)  # Temperature register (0x00)
            humidity_raw = self.bus.read_word_data(address, 0x02)  # Humidity register (0x02)

            # Convert raw data to meaningful values
            temperature = ((temp_raw / 65536.0) * 165.0) - 40.0
            humidity = (humidity_raw / 65536.0) * 100.0

            logging.info("Humidity: %.2f %% | Temperature: %.2f °C", humidity, temperature)
            return humidity, temperature
        except Exception as e:
            logging.error("Failed to read humidity and temperature: %s", e)
            raise RuntimeError("Humidity/Temperature read failed") from e

    def read_all_registers_hdc2010(self):
        """Read all registers of the HDC2010 sensor."""
        try:
            address = self.ADDRESSES["HUMIDITY_TEMP"]
            for reg in [0x00, 0x02, 0x0F, 0x10, 0x11, 0x12]:
                data = self.bus.read_word_data(address, reg)
                logging.info("Register 0x%02X: %d", reg, data)
        except Exception as e:
            logging.error("Failed to read HDC2010 registers: %s", e)

    # Ambient Light Sensor (OPT3002)
    def read_ambient_light(self, address=None):
        """Read ambient light intensity from OPT3002."""
        try:
            address = address if address is not None else self.ADDRESSES["AMBIENT_LIGHT"]
            # Read raw light intensity
            light_raw = read_register(address, self.RESULT_REGISTER)  # Light result register (0x00)
            # Convert raw data to lux using datasheet scaling
            result = ((raw & 0xFF) << 8) | (raw >> 8) # Replace with actual scaling factor
            exponent = (result >> 12) & 0x0F
            mantissa = result & 0x0FFF
            lsb_size = 1.2 * (2 ** exponent)
            light_intensity = mantissa * lsb_size
            logging.info("Light Intensity: %.2f lux", light_intensity)
            #logging.info("Ambient Light: %.2f lux", light_intensity)
            return light_intensity
        except Exception as e:
            logging.error("Failed to read ambient light: %s", e)
            raise RuntimeError("Ambient Light read failed") from e

    def read_all_registers_opt3002(self):
        """Read all registers of the OPT3002 sensor."""
        try:
            address = self.ADDRESSES["AMBIENT_LIGHT"]
            for reg in [0x00, 0x01, 0x02, 0x03, 0x04, 0x0E, 0x0F]:
                data = self.bus.read_word_data(address, reg)
                logging.info("Register 0x%02X: %d", reg, data)
        except Exception as e:
            logging.error("Failed to read OPT3002 registers: %s", e)

    # Barometric Pressure Sensor (BMP280)
    def read_barometric_pressure(self, address=None):
        """Read barometric pressure from BMP280."""
        try:
            address = address if address is not None else self.ADDRESSES["BAROMETRIC_PRESSURE"]
            # Read raw pressure data
            pressure_raw = self.bus.read_word_data(address, 0xF7)  # Pressure data register (0xF7)
            # Convert raw data to hPa using datasheet scaling
            pressure = pressure_raw / 256.0  # Replace with actual scaling factor
            logging.info("Barometric Pressure: %.2f hPa", pressure)
            return pressure
        except Exception as e:
            logging.error("Failed to read barometric pressure: %s", e)
            raise RuntimeError("Barometric Pressure read failed") from e

    def read_all_registers_bmp280(self):
        """Read all registers of the BMP280 sensor."""
        try:
            address = self.ADDRESSES["BAROMETRIC_PRESSURE"]
            for reg in [0xF7, 0xF8, 0xF4, 0xF5, 0xD0, 0xD1, 0xD3]:
                data = self.bus.read_word_data(address, reg)
                logging.info("Register 0x%02X: %d", reg, data)
        except Exception as e:
            logging.error("Failed to read BMP280 registers: %s", e)

    # ADC (Analog to Digital Converter)
    def read_adc(self, address=None):
        """Read ADC values from ADC device."""
        try:
            address = address if address is not None else self.ADDRESSES["ANALOG_ADC"]
            # Read raw ADC value
            adc_raw = self.bus.read_word_data(address, 0x00)  # ADC result register (0x00)
            logging.info("ADC Value: %d", adc_raw)
            return adc_raw
        except Exception as e:
            logging.error("Failed to read ADC: %s", e)
            raise RuntimeError("ADC read failed") from e

    def read_all_registers_adc(self):
        """Read all registers of the ADC device."""
        try:
            address = self.ADDRESSES["ANALOG_ADC"]
            for reg in [0x00, 0x01, 0x02, 0x03]:
                data = self.bus.read_word_data(address, reg)
                logging.info("Register 0x%02X: %d", reg, data)
        except Exception as e:
            logging.error("Failed to read ADC registers: %s", e)

    # Cryptoprocessor
    def read_cryptoprocessor(self, address=None):
        """Read cryptoprocessor status or data."""
        try:
            address = address if address is not None else self.ADDRESSES["CRYPTOPROCESSOR"]
            # Example: Read a status register or some other register
            data = self.bus.read_word_data(address, 0x00)  # Example register (0x00)
            logging.info("Cryptoprocessor Data: %d", data)
            return data
        except Exception as e:
            logging.error("Failed to read cryptoprocessor: %s", e)
            raise RuntimeError("Cryptoprocessor read failed") from e

    def read_all_registers_cryptoprocessor(self):
        """Read all registers of the Cryptoprocessor."""
        try:
            address = self.ADDRESSES["CRYPTOPROCESSOR"]
            for reg in [0x00, 0x01, 0x02, 0x03, 0x10, 0x11]:
                data = self.bus.read_word_data(address, reg)
                logging.info("Register 0x%02X: %d", reg, data)
        except Exception as e:
            logging.error("Failed to read Cryptoprocessor registers: %s", e)
            
    def read_limits(self):
        """Read the low and high limit registers."""
        low_limit = self.read_register(self.LOW_LIMIT_REGISTER)
        high_limit = self.read_register(self.HIGH_LIMIT_REGISTER)
        logging.info("Low Limit: 0x%04X, High Limit: 0x%04X", low_limit, high_limit)
        return low_limit, high_limit

    def read_manufacturer_id(self):
        """Read the manufacturer ID."""
        manufacturer_id = self.read_register(self.MANUFACTURER_ID_REGISTER)
        logging.info("Manufacturer ID: 0x%04X", manufacturer_id)
        return manufacturer_id

            
    def read_result(self):
        """Read the light intensity result."""
        result = self.read_register(self.RESULT_REGISTER)
        exponent = (result >> 12) & 0x0F
        mantissa = result & 0x0FFF
        lsb_size = 1.2 * (2 ** exponent)
        light_intensity = mantissa * lsb_size
        logging.info("Light Intensity: %.2f lux", light_intensity)
        return light_intensity

    def configure_sensor(self, range_mode=0x0C, conversion_time=0x01, mode=0x03):
        """
        Configure the sensor.
        - range_mode: Auto range (0x0C) or manual (0x00 to 0x0B).
        - conversion_time: 800 ms (0x01) or 100 ms (0x00).
        - mode: Continuous (0x03), single-shot (0x02), or shutdown (0x00).
        """
        config = (range_mode << 12) | (conversion_time << 11) | (mode << 9)
        self.write_register(self.ADDRESSES["AMBIENT_LIGHT"], self.CONFIG_REGISTER, config)
        logging.info("Sensor configured with range 0x%02X, conversion time %d ms, mode 0x%02X",
                     range_mode, 800 if conversion_time else 100, mode)

    def set_limits(self, low_limit, high_limit):
        """Set the low and high threshold limits."""
        self.write_register(self.LOW_LIMIT_REGISTER, low_limit)
        self.write_register(self.HIGH_LIMIT_REGISTER, high_limit)
        logging.info("Low Limit set to 0x%04X, High Limit set to 0x%04X", low_limit,high_limit)


            
    def read_register(self, address, register):
        """Read a 16-bit register."""
        try:
            raw = self.bus.read_word_data(address, register)
            # Swap bytes (MSB and LSB are reversed in I2C word reads)
            value = ((raw & 0xFF) << 8) | (raw >> 8)
            logging.debug("Read 0x%04X from register 0x%02X", value, register)
            return value
        except Exception as e:
            logging.error("Failed to read register 0x%02X: %s", register, e)
            raise

    def write_register(self, address, register, value):
        """Write a 16-bit value to a register."""
        try:
            # Swap bytes to match I2C word format
            swapped = ((value & 0xFF) << 8) | (value >> 8)
            self.bus.write_word_data(address, register, swapped)
            logging.debug("Wrote 0x%04X to register 0x%02X", value, register)
        except Exception as e:
            logging.error("Failed to write 0x%04X to register 0x%02X: %s", value, register,e)
            raise

    def close(self):
        """Close the I2C connection."""
        try:
            self.bus.close()
            logging.info("I2C bus closed.")
        except Exception as e:
            logging.error("Failed to close I2C bus: %s", e)
            raise RuntimeError("Failed to close I2C connection") from e


# Main function for testing
if __name__ == "__main__":
    try:
        sensor = CoralEnvSensor()

        # Test readings with default values
        logging.info("Reading Humidity and Temperature:")
        humidity, temperature = sensor.read_humidity_temperature()
        print(f"Humidity: {humidity:.2f}% | Temperature: {temperature:.2f}°C")

        logging.info("Reading Ambient Light:")
        sensor.configure_sensor()
        #sensor.read_result()
        light = sensor.read_ambient_light()
        print(f"Ambient Light: {light:.2f} lux")

        logging.info("Reading Barometric Pressure:")
        pressure = sensor.read_barometric_pressure()
        print(f"Barometric Pressure: {pressure:.2f} hPa")

        # Read all registers for each sensor
        sensor.read_all_registers_hdc2010()

        sensor.read_all_registers_opt3002()
        sensor.read_all_registers_bmp280()
        sensor.read_all_registers_adc()
        sensor.read_all_registers_cryptoprocessor()

    except Exception as e:
        logging.error("Error occurred: %s", e)
    finally:
        sensor.close()
