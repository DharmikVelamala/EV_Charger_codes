import spidev
import time

# Initialize SPI
spi = spidev.SpiDev()
spi.open(0, 0)  # SPI bus 0, device 0 (update as needed)
spi.max_speed_hz = 2000000  # 2 MHz max speed for ATM90E32AS
spi.mode = 0b11  # SPI Mode 0 (CPOL = 0, CPHA = 0)

# Function to read a 16-bit register
def read_register(address):
    # Construct the read command: MSB = 1 for read
    command = [(address | 0x80) & 0xFF, 0x00]  # Address | 0x80 sets read bit
    response = spi.xfer2(command)
    # Combine the response bytes into a 16-bit value
    return (response[0] << 8) | response[1]

# Function to write a 16-bit value to a register
def write_register(address, value):
    # Construct the write command: MSB = 0 for write
    command = [(address & 0x7F) & 0xFF, (value >> 8) & 0xFF, value & 0xFF]
    spi.xfer2(command)

# Read voltage, current, and power
def get_measurements():
    voltage = read_register(0xD9)  # Urms register
    current = read_register(0xDD)  # Irms register
    power = read_register(0xB0)    # Pmean register
    return voltage, current, power

try:
    while True:
        voltage, current, power = get_measurements()
        print(f"Voltage: {voltage} (raw), Current: {current} (raw), Power: {power} (raw)")
        # Apply scaling factors from the datasheet to get real-world units
        # Example: scaled_voltage = voltage * VOLTAGE_SCALE
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")
    spi.close()
