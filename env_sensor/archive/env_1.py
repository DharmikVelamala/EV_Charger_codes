import smbus2
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class CoralEnvSensor:
    I2C_BUS = 1  # Default I2C bus on Raspberry Pi

    # I2C addresses
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
            self.bus.write_byte_data(address, 0x0F, 0x01)  # Example register command
            time.sleep(0.1)  # Wait for the measurement to complete

            # Read temperature and humidity
            temp_raw = self.bus.read_word_data(address, 0x00)  # Example register
            humidity_raw = self.bus.read_word_data(address, 0x02)  # Example register

            # Convert raw data to meaningful values
            temperature = ((temp_raw / 65536.0) * 165.0) - 40.0
            humidity = (humidity_raw / 65536.0) * 100.0

            logging.info("Humidity: %.2f %% | Temperature: %.2f °C", humidity, temperature)
            return humidity, temperature
        except Exception as e:
            logging.error("Failed to read humidity and temperature: %s", e)
            raise RuntimeError("Humidity/Temperature read failed") from e

    # Ambient Light Sensor (OPT3002)
    def read_ambient_light(self, address=None):
        """Read ambient light intensity from OPT3002."""
        try:
            address = address if address is not None else self.ADDRESSES["AMBIENT_LIGHT"]
            # Read raw light intensity
            light_raw = self.bus.read_word_data(address, 0x00)  # Example register
            # Convert raw data to lux using datasheet scaling
            light_intensity = light_raw * 0.01  # Replace with actual scaling factor
            logging.info("Ambient Light: %.2f lux", light_intensity)
            return light_intensity
        except Exception as e:
            logging.error("Failed to read ambient light: %s", e)
            raise RuntimeError("Ambient Light read failed") from e

    # Barometric Pressure Sensor (BMP280)
    def read_barometric_pressure(self, address=None):
        """Read barometric pressure from BMP280."""
        try:
            address = address if address is not None else self.ADDRESSES["BAROMETRIC_PRESSURE"]
            # Read raw pressure data
            pressure_raw = self.bus.read_word_data(address, 0xF7)  # Example register
            # Convert raw data to hPa using datasheet scaling
            pressure = pressure_raw / 256.0  # Replace with actual scaling factor
            logging.info("Barometric Pressure: %.2f hPa", pressure)
            return pressure
        except Exception as e:
            logging.error("Failed to read barometric pressure: %s", e)
            raise RuntimeError("Barometric Pressure read failed") from e

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
        light = sensor.read_ambient_light()
        print(f"Ambient Light: {light:.2f} lux")

        logging.info("Reading Barometric Pressure:")
        pressure = sensor.read_barometric_pressure()
        print(f"Barometric Pressure: {pressure:.2f} hPa")

    except Exception as e:
        logging.error("Error during sensor operations: %s", e)
    finally:
        sensor.close()
