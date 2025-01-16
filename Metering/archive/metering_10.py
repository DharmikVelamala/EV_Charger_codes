import spidev
import time
import logging
import RPi.GPIO as GPIO

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Pin Definitions for GPIO
PINS = {
    'RST': 25,  # Reset Pin
    'CS': 8,    # Chip Select
}

class ATM90E3x:
    # Register Addresses for All Phases (from datasheet)
    REGISTERS = {
        'VoltageA': 0xD9,
        'VoltageB': 0xDB,
        'VoltageC': 0xDD,
        'CurrentA': 0xDD,
        'CurrentB': 0xDE,
        'CurrentC': 0xDF,
        'PowerA': 0xD1,
        'PowerB': 0xD2,
        'PowerC': 0xD3,
        'Frequency': 0xB8,
        'PhaseAngleA': 0xF9,
        'PhaseAngleB': 0xFA,
        'PhaseAngleC': 0xFB,
        # Add additional registers as needed
    }

    DEFAULT_SPI_BUS = 0
    DEFAULT_SPI_DEVICE = 0
    DEFAULT_SPEED_HZ = 2000000

    def __init__(self, spi_bus=DEFAULT_SPI_BUS, spi_device=DEFAULT_SPI_DEVICE, speed_hz=DEFAULT_SPEED_HZ):
        """Initialize the SPI connection and GPIO pin assignments."""
        self.spi_bus = spi_bus
        self.spi_device = spi_device
        self.speed_hz = speed_hz

        try:
            self.spi = spidev.SpiDev()
            self.spi.open(spi_bus, spi_device)
            self.spi.max_speed_hz = speed_hz
            self.spi.mode = 0b11  # SPI Mode 0
            logging.info("ATM90E3x initialized with SPI bus %d, device %d, speed %d Hz", spi_bus, spi_device, speed_hz)

            self._init_gpio()
            self.reset_device()
        except Exception as e:
            logging.error("Initialization failed: %s", e)
            raise RuntimeError("Initialization failed") from e

    def _init_gpio(self):
        """Initialize GPIO pins for the ATM90E3x."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PINS['RST'], GPIO.OUT)
        GPIO.output(PINS['RST'], GPIO.HIGH)  # Set reset pin high initially
        logging.info("GPIO initialized.")

    def reset_device(self):
        """Reset the ATM90E3x device."""
        try:
            GPIO.output(PINS['RST'], GPIO.LOW)
            time.sleep(0.1)  # Hold reset for 100ms
            GPIO.output(PINS['RST'], GPIO.HIGH)
            time.sleep(0.1)  # Allow the device to stabilize
            logging.info("Device reset complete.")
        except Exception as e:
            logging.error("Device reset failed: %s", e)
            raise RuntimeError("Device reset failed") from e

    def _spi_transfer(self, data):
        """Perform an SPI transfer."""
        try:
            #logging.debug("Sending SPI data: %s", data)
            response = self.spi.xfer2(data)
            #logging.debug("SPI transfer: Sent %s, Received %s", data, response)
            return response
        except Exception as e:
            logging.error("SPI transfer failed: %s", e)
            raise RuntimeError("SPI transfer failed") from e

    def _read_register(self, register_name):
        """Read data from a register."""
        if register_name not in self.REGISTERS:
            raise ValueError(f"Unknown register: {register_name}")

        reg_address = self.REGISTERS[register_name]
        cmd = [0x80 | (reg_address >> 8), reg_address & 0xFF, 0x00, 0x00]
        response = self._spi_transfer(cmd)

        if len(response) != 4:
            raise RuntimeError("Invalid response length")

        result = (response[2] << 8) | response[3]
        #logging.debug("Read register %s (0x%04X): 0x%04X", register_name, reg_address, result)
        return result

    def _read_scaled_value(self, register_name, scale):
        """Read a scaled value from a register."""
        try:
            raw_value = self._read_register(register_name)
            print(register_name," : ", raw_value ,"\n","Scale :",scale)
            return raw_value * scale
        except Exception as e:
            logging.error("Failed to read %s: %s", register_name, e)
            return None

    def read_voltage(self, phase):
        """Read RMS Voltage for a given phase."""
        register = f"Voltage{phase}"
        return self._read_scaled_value(register, 0.01)

    def read_current(self, phase):
        """Read RMS Current for a given phase."""
        register = f"Current{phase}"
        return self._read_scaled_value(register, 0.001)

    def read_power(self, phase):
        """Read Active Power for a given phase."""
        register = f"Power{phase}"
        return self._read_scaled_value(register, 0.00032)

    def read_phase_angle(self, phase):
        """Read Phase Angle for a given phase."""
        register = f"PhaseAngle{phase}"
        return self._read_scaled_value(register, 0.01)

    def read_frequency(self):
        """Read Frequency."""
        return self._read_scaled_value('Frequency', 0.01)

    def close(self):
        """Close the SPI connection and reset GPIO pins."""
        try:
            self.spi.close()
            GPIO.cleanup()
            logging.info("SPI connection closed and GPIO cleaned up.")
        except Exception as e:
            logging.error("Error closing resources: %s", e)
            raise RuntimeError("Failed to close resources") from e

# Example Usage
def main():
    meter = ATM90E3x()
    try:
        for phase in ['A', 'B', 'C']:
            print(f"Phase {phase} Voltage: {meter.read_voltage(phase)} V")
            print(f"Phase {phase} Current: {meter.read_current(phase)} A")
            print(f"Phase {phase} Power: {meter.read_power(phase)} W")
            print(f"Phase {phase} Phase Angle: {meter.read_phase_angle(phase)} degrees")
        
        print(f"Frequency: {meter.read_frequency()} Hz")
    finally:
        meter.close()

if __name__ == "__main__":
    main()

