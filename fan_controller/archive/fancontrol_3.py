import smbus
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FanController:
    # Static fan addresses based on hardcoded values
    FAN_ADDRESSES = {
        "fan1": 0x2F,
        "fan2": 0x3E,
        "fan3": 0x4A,
        "fan4": 0x5C
    }

    DEFAULT_PWM_VALUE = 127  # Default PWM value (50% duty cycle)
    DEFAULT_FAN_SPEED = 50  # Default fan speed (50%)
    DEFAULT_ERROR_BIT = 0x01  # Default error bit for status register

    def __init__(self, i2c_bus):
        """
        Initialize the Fan Controller.

        :param i2c_bus: I2C bus number.
        """
        self.bus = smbus.SMBus(i2c_bus)
        self.fan_status = {
            name: {'speed': 0, 'error': False, 'rpm': 0} for name in self.FAN_ADDRESSES
        }

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

    def set_fan_speed(self, fan_name, speed=None):
        """
        Set the fan speed using PWM based on the provided speed percentage.

        :param fan_name: Name of the fan (e.g., "fan1").
        :param speed: Speed as a percentage (0-100). Defaults to 50%.
        """
        if fan_name not in self.FAN_ADDRESSES:
            logging.error(f"Invalid fan name: {fan_name}")
            return

        speed = speed if speed is not None else self.DEFAULT_FAN_SPEED

        if speed < 0 or speed > 100:
            logging.error("Speed must be between 0 and 100.")
            return

        pwm_value = int((speed * 255) / 100)  # Convert percentage to PWM value (0-255)
        fan_address = self.FAN_ADDRESSES[fan_name]
        self.write_register(fan_address, 0x30, pwm_value)  # Example PWM register
        self.fan_status[fan_name]['speed'] = speed
        logging.info(f"Set {fan_name} at {hex(fan_address)} to {speed}% speed.")

    def adjust_fan_speed(self, fan_name, temperature):
        """
        Adjust the fan speed dynamically based on the temperature.

        :param fan_name: Name of the fan (e.g., "fan1").
        :param temperature: Current temperature in degrees Celsius.
        """
        if fan_name not in self.FAN_ADDRESSES:
            logging.error(f"Invalid fan name: {fan_name}")
            return

        fan_address = self.FAN_ADDRESSES[fan_name]
        pwm_value = int(min(max(temperature * 2.55, 0), 255))  # Scale 0-100 to 0-255
        self.write_register(fan_address, 0x30, pwm_value)
        self.fan_status[fan_name]['speed'] = int(pwm_value / 255 * 100)
        logging.info(f"Adjusted {fan_name} speed based on temperature: {temperature}C -> {self.fan_status[fan_name]['speed']}% PWM.")

    def get_fan_rpm(self, fan_name):
        """
        Get the fan's RPM.

        :param fan_name: Name of the fan (e.g., "fan1").
        :return: RPM value or None if an error occurs.
        """
        if fan_name not in self.FAN_ADDRESSES:
            logging.error(f"Invalid fan name: {fan_name}")
            return None

        fan_address = self.FAN_ADDRESSES[fan_name]
        rpm_lsb = self.read_register(fan_address, 0x40)  # Example RPM LSB register
        rpm_msb = self.read_register(fan_address, 0x41)  # Example RPM MSB register

        if rpm_lsb is None or rpm_msb is None:
            self.fan_status[fan_name]['error'] = True
            return None

        rpm = (rpm_msb << 8) | rpm_lsb
        self.fan_status[fan_name]['rpm'] = rpm
        return rpm

    def check_errors(self, fan_name):
        """
        Check for errors in the fan.

        :param fan_name: Name of the fan (e.g., "fan1").
        :return: True if an error is detected, False otherwise.
        """
        if fan_name not in self.FAN_ADDRESSES:
            logging.error(f"Invalid fan name: {fan_name}")
            return True

        fan_address = self.FAN_ADDRESSES[fan_name]
        status_reg = self.read_register(fan_address, 0x20)  # Example status register

        if status_reg is None:
            self.fan_status[fan_name]['error'] = True
            return True

        error_detected = bool(status_reg & self.DEFAULT_ERROR_BIT)  # Default error bit

        if error_detected:
            logging.warning(f"Error detected for {fan_name} at {hex(fan_address)}.")
        else:
            logging.info(f"No errors for {fan_name} at {hex(fan_address)}.")

        self.fan_status[fan_name]['error'] = error_detected
        return error_detected

    def control_fans_based_on_temperature(self, temperature_data):
        """
        Control fan speeds dynamically based on temperature data.

        :param temperature_data: Dictionary with fan names as keys and temperatures as values.
        """
        for fan_name, temp in temperature_data.items():
            if fan_name not in self.FAN_ADDRESSES:
                logging.error(f"Invalid fan name: {fan_name}")
                continue

            self.adjust_fan_speed(fan_name, temp)

    def monitor_fans(self):
        """Monitor fan speeds and check for faults."""
        for fan_name in self.FAN_ADDRESSES:
            rpm = self.get_fan_rpm(fan_name)
            if rpm is not None:
                logging.info(f"{fan_name} is running at {rpm} RPM.")
            else:
                logging.error(f"Failed to read RPM for {fan_name}.")

            self.check_errors(fan_name)

# Example usage
if __name__ == "__main__":
    controller = FanController(i2c_bus=1)

    # Example: Control fans based on temperature
    temperature_readings = {
        "fan1": 25,
        "fan2": 55,
        "fan3": 65
    }
    controller.control_fans_based_on_temperature(temperature_readings)

    # Monitor fans in a loop
    try:
        while True:
            controller.monitor_fans()
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("Exiting fan controller.")
