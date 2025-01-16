import smbus
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FanController:
    DEFAULT_PWM_VALUE = 127  # Default PWM value (50% duty cycle)
    DEFAULT_FAN_SPEED = 50  # Default fan speed (50%)
    DEFAULT_ERROR_BIT = 0x01  # Example default error bit for status register
    DEFAULT_TEMP_THRESHOLDS = [30, 60]  # Default temperature thresholds (low, medium)

    def __init__(self, i2c_bus, fan_addresses):
        """
        Initialize the Fan Controller.

        :param i2c_bus: I2C bus number.
        :param fan_addresses: List of I2C addresses for fan controllers.
        """
        self.bus = smbus.SMBus(i2c_bus)
        self.fan_addresses = fan_addresses
        self.fan_status = {addr: {'speed': 0, 'error': False} for addr in fan_addresses}

    def write_register(self, address, reg, value):
        """Write a value to a register."""
        try:
            self.bus.write_byte_data(address, reg, value)
        except Exception as e:
            logging.error(f"Failed to write to {hex(address)} register {hex(reg)}: {e}")

    def read_register(self, address, reg):
        """Read a value from a register."""
        try:
            return self.bus.read_byte_data(address, reg)
        except Exception as e:
            logging.error(f"Failed to read from {hex(address)} register {hex(reg)}: {e}")
            return None

    def set_fan_speed(self, fan_address, speed=None):
        """
        Set the fan speed.

        :param fan_address: Address of the fan controller.
        :param speed: Speed as a percentage (0-100). Defaults to 50%.
        """
        speed = speed if speed is not None else self.DEFAULT_FAN_SPEED

        if speed < 0 or speed > 100:
            logging.error("Speed must be between 0 and 100.")
            return

        pwm_value = int((speed * 255) / 100)  # Convert percentage to PWM value (0-255)
        self.write_register(fan_address, 0x30, pwm_value)  # Example PWM register
        self.fan_status[fan_address]['speed'] = speed
        logging.info(f"Set fan at {hex(fan_address)} to {speed}% speed.")

    def get_fan_rpm(self, fan_address):
        """
        Get the fan's RPM.

        :param fan_address: Address of the fan controller.
        :return: RPM value or None if an error occurs.
        """
        rpm_lsb = self.read_register(fan_address, 0x40)  # Example RPM LSB register
        rpm_msb = self.read_register(fan_address, 0x41)  # Example RPM MSB register

        if rpm_lsb is None or rpm_msb is None:
            self.fan_status[fan_address]['error'] = True
            return None

        rpm = (rpm_msb << 8) | rpm_lsb
        return rpm

    def check_errors(self, fan_address):
        """
        Check for errors in the fan.

        :param fan_address: Address of the fan controller.
        :return: True if an error is detected, False otherwise.
        """
        status_reg = self.read_register(fan_address, 0x20)  # Example status register

        if status_reg is None:
            self.fan_status[fan_address]['error'] = True
            return True

        error_detected = bool(status_reg & self.DEFAULT_ERROR_BIT)  # Default error bit

        if error_detected:
            logging.warning(f"Error detected for fan at {hex(fan_address)}.")
        else:
            logging.info(f"No errors for fan at {hex(fan_address)}.")

        self.fan_status[fan_address]['error'] = error_detected
        return error_detected

    def control_fans_based_on_temperature(self, temperature_data, thresholds=None):
        """
        Control fan speeds based on temperature data.

        :param temperature_data: List of temperatures corresponding to each fan controller.
        :param thresholds: List of temperature thresholds (low, medium). Defaults to [30, 60].
        """
        thresholds = thresholds if thresholds is not None else self.DEFAULT_TEMP_THRESHOLDS

        for addr, temp in zip(self.fan_addresses, temperature_data):
            if temp < thresholds[0]:
                self.set_fan_speed(addr, 20)  # Low speed
            elif temp < thresholds[1]:
                self.set_fan_speed(addr, 50)  # Medium speed
            else:
                self.set_fan_speed(addr, 100)  # High speed

    def monitor_fans(self):
        """Monitor fan speeds and check for faults."""
        for addr in self.fan_addresses:
            rpm = self.get_fan_rpm(addr)
            if rpm is not None:
                logging.info(f"Fan at {hex(addr)} is running at {rpm} RPM.")
            else:
                logging.error(f"Failed to read RPM for fan at {hex(addr)}.")

            self.check_errors(addr)

# Example usage
if __name__ == "__main__":
    fan_addresses = [0x2F, 0x3E]  # Replace with your fan controller I2C addresses
    controller = FanController(i2c_bus=1, fan_addresses=fan_addresses)

    # Example: Control fans based on temperature
    temperature_readings = [25, 55]  # Example temperatures
    controller.control_fans_based_on_temperature(temperature_readings)

    # Monitor fans in a loop
    try:
        while True:
            controller.monitor_fans()
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("Exiting fan controller.")
