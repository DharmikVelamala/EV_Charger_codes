import spidev
import time
import logging
import RPi.GPIO as GPIO

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Pin Definitions for GPIO
PINS = {
    'GND': "GND",
    'ZX0': 4,
    'ZX1': 17,
    'ZX2': 27,
    'CF1': 22,
    'CF2': 23,
    'CF3': 24,
    'CF4': 25,
    'WarnOut': 5,
    'IRQ0': 6,
    'IRQ1': 12,
    'PM0': 13,
    'PM1': 19,
    'DMA': 16,
    'SDI': 10,
    'CS': 8,
    'SCLK': 11,
    'SDO': 9,
    'EXT_VDD': "POWER",  # 3.3V power pin
    'RST': 26
}

# Register Definitions from Datasheet
REGISTERS = {
    'MeterEn': 0x00,
    'ChannelMapI': 0x01,
    'ChannelMapU': 0x02,
    'SagPeakDetCfg': 0x05,
    'OVth': 0x06,
    'ZXConfig': 0x07,
    'SagTh': 0x08,
    'PhaseLossTh': 0x09,
    'InWarnTh': 0x0A,
    'OIth': 0x0B,
    'FreqLoTh': 0x0C,
    'FreqHiTh': 0x0D,
    'DetectCtrl': 0x10,
    'DetectTh1': 0x11,
    'UgainA': 0x61,
    'IgainA': 0x62,
    'UrmsA': 0xD9,
    'IrmsA': 0xDD,
    'SoftReset': 0x70,
    'Freq': 0xF8
    # Add all other registers here as needed
}

class ATM90E3x:
    # Default SPI and calibration values
    DEFAULT_SPI_BUS = 0
    DEFAULT_SPI_DEVICE = 0
    DEFAULT_SPEED_HZ = 100000
    DEFAULT_VOLTAGE_CAL = 0x1000
    DEFAULT_CURRENT_CAL = 0x1000

    def __init__(self, spi_bus=DEFAULT_SPI_BUS, spi_device=DEFAULT_SPI_DEVICE, speed_hz=DEFAULT_SPEED_HZ):
        """
        Initialize the SPI connection and GPIO pin assignments.
        """
        try:
            self.reset_device()
            self.spi = spidev.SpiDev()
            self.spi.open(spi_bus, spi_device)
            self.spi.max_speed_hz = speed_hz
            self.spi.mode = 0b00  # SPI Mode 0
            logging.info("ATM90E3x initialized with SPI bus %d, device %d, speed %d Hz", spi_bus, spi_device, speed_hz)
            self.init_gpio()
        except Exception as e:
            logging.error("Failed to initialize SPI connection: %s", e)
            raise RuntimeError("SPI initialization failed") from e

    def init_gpio(self):
        """Initialize GPIO pins."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PINS['RST'], GPIO.OUT)
        GPIO.setup([PINS['ZX0'], PINS['ZX1'], PINS['ZX2']], GPIO.IN)
        GPIO.setup(PINS['IRQ0'], GPIO.IN)
        GPIO.add_event_detect(PINS['ZX0'], GPIO.RISING, callback=self.on_zero_crossing)
        GPIO.add_event_detect(PINS['IRQ0'], GPIO.FALLING, callback=self.on_interrupt_request)

    def reset_device(self):
        """Reset the ATM90E3x device."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PINS['RST'], GPIO.OUT)
        GPIO.output(PINS['RST'], GPIO.LOW)
        time.sleep(0.2)
        GPIO.output(PINS['RST'], GPIO.HIGH)
        time.sleep(0.1)
        logging.info("Device has been reset.")

    def _spi_transfer(self, data):
        """Perform an SPI transfer."""
        try:
            response = self.spi.xfer2(data)
            logging.debug("SPI transfer: Sent %s, Received %s", data, response)
            return response
        except Exception as e:
            logging.error("SPI transfer failed: %s", e)
            raise RuntimeError("SPI transfer failed") from e

    def _read_register(self, register_address):
        """Read data from a register."""
        try:
            cmd = [0x80 | (register_address >> 8), register_address & 0xFF, 0x00, 0x00]
            response = self._spi_transfer(cmd)
            value = (response[2] << 8) | response[3]
            logging.debug("Read register 0x%04X: 0x%04X", register_address, value)
            return value
        except Exception as e:
            logging.error("Error reading register 0x%04X: %s", register_address, e)
            raise RuntimeError(f"Failed to read register 0x{register_address:04X}") from e

    def _write_register(self, register_address, value):
        """Write data to a register."""
        try:
            cmd = [register_address >> 8, register_address & 0xFF, value >> 8, value & 0xFF]
            self._spi_transfer(cmd)
            logging.debug("Wrote 0x%04X to register 0x%04X", value, register_address)
        except Exception as e:
            logging.error("Error writing to register 0x%04X: %s", register_address, e)
            raise RuntimeError(f"Failed to write to register 0x{register_address:04X}") from e

    def _read_register_named(self, register_name):
        """Read a register by its name."""
        register_address = REGISTERS.get(register_name)
        if register_address is None:
            raise ValueError(f"Register {register_name} is not defined.")
        return self._read_register(register_address)

    def _write_register_named(self, register_name, value):
        """Write to a register by its name."""
        register_address = REGISTERS.get(register_name)
        if register_address is None:
            raise ValueError(f"Register {register_name} is not defined.")
        self._write_register(register_address, value)

    def on_zero_crossing(self, channel):
        """Handle zero-crossing event."""
        logging.info("Zero Crossing Detected on Pin %d", channel)

    def on_interrupt_request(self, channel):
        """Handle interrupt request event."""
        logging.info("Interrupt Request Detected on Pin %d", channel)

    def close(self):
        """Close SPI connection and cleanup GPIO."""
        self.spi.close()
        GPIO.cleanup()

    def initialize_defaults(self):
        """Initialize default register values."""
        self._write_register_named('MeterEn', 0x01)
        self._write_register_named('ChannelMapI', 0x0F)
        self._write_register_named('ChannelMapU', 0x07)

    def read_voltage(self):
        """Read RMS Voltage."""
        return self._read_register_named('UrmsA') * 0.01

    def read_current(self):
        """Read RMS Current."""
        return self._read_register_named('IrmsA') * 0.001

    def read_frequency(self):
        """Read Frequency."""
        return self._read_register_named('Freq') * 0.01

# Example Usage
def main():
    meter = ATM90E3x()
    try:
        meter.initialize_defaults()
        voltage = meter.read_voltage()
        current = meter.read_current()
        frequency = meter.read_frequency()
        print(f"Voltage: {voltage} V")
        print(f"Current: {current} A")
        print(f"Frequency: {frequency} Hz")
    finally:
        meter.close()

if __name__ == "__main__":
    main()

