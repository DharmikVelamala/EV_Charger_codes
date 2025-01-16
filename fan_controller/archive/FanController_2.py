import smbus
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class FanController:
    # Static fan addresses based on hardcoded values
    REG_FAN_SETTING = {
        "fan1": 0x30,
        "fan2": 0x40,
        "fan3": 0x50,
        "fan4": 0x60,
        "fan5": 0x70
    }
    REG_TACH_READING_HIGH = {
        "fan1": 0x3E,
        "fan2": 0x4E,
        "fan3": 0x5E,
        "fan4": 0x6E,
        "fan5": 0x7E
    }
    REG_TACH_READING_LOW = {
        "fan1": 0x3F,
        "fan2": 0x4F,
        "fan3": 0x5F,
        "fan4": 0x6F,
        "fan5": 0x7F
    }
    REG_CONFIGURATION = 0x20
    REG_FAN_STATUS = 0x24
    REG_FAN_STALL_STATUS = 0x25
    REG_DRIVE_FAIL_STATUS = 0x27

    DEFAULT_PWM_VALUE = 127  # Default PWM value (50% duty cycle)
    DEFAULT_FAN_SPEED = 50  # Default fan speed (50%)
    DEFAULT_ERROR_BIT = 0x01  # Default error bit for status register
    DEFAULT_NUM_FANS = 5  # Default number of fans
    DEFAULT_TEMP_MIN = 25  # Default minimum temperature (°C)
    DEFAULT_TEMP_MAX = 85  # Default maximum temperature (°C)

    def __init__(self, i2c_bus, address=0x4D, num_fans=DEFAULT_NUM_FANS, temperature_limits=None):
        """
        Initialize the Fan Controller.

        :param i2c_bus: I2C bus number.
        :param address: I2C address of the fan controller.
        :param num_fans: Number of fans to control (default is 5).
        :param temperature_limits: Dictionary of temperature limits for each fan (e.g., {"fan1": (25, 85)}).
        """
        self.bus = smbus.SMBus(i2c_bus)
        self.address = address
        self.num_fans = num_fans  # Set the number of fans to control
        self.fan_settings = {}
        self.fan_tach_readings = {}
        self.fan_status = {}
        self.temperature_limits = temperature_limits or {
            f"fan{i+1}": (self.DEFAULT_TEMP_MIN, self.DEFAULT_TEMP_MAX) for i in range(num_fans)
        }

        # Initialize only the selected fans
        self.initialize_fans()

        # Calculate the min and max RPMs for each fan before starting
        self.calculate_min_max_rpm()
        
        # Turn on only the selected fans
        self.turn_on_selected_fans()

    def update_fan_variables(self, fan_setting=None, tach_high=None, tach_low=None, pwm_value=None,fan_speed=None, error_bit=None, num_fans=None, temp_min=None, temp_max=None):
        """
        Update the static fan-related variables.

        :param fan_setting: Dictionary to update fan settings (e.g., {"fan1": 0x31}).
        :param tach_high: Dictionary to update tachometer high readings.
        :param tach_low: Dictionary to update tachometer low readings.
        :param pwm_value: PWM value to update.
        :param fan_speed: Fan speed to update.
        :param error_bit: Error bit to update.
        :param num_fans: Number of fans.
        :param temp_min: Minimum temperature limit.
        :param temp_max: Maximum temperature limit.
        """
        if fan_setting:
            FanController.REG_FAN_SETTING.update(fan_setting)
        if tach_high:
            FanController.REG_TACH_READING_HIGH.update(tach_high)
        if tach_low:
            FanController.REG_TACH_READING_LOW.update(tach_low)
        if pwm_value:
            FanController.DEFAULT_PWM_VALUE = pwm_value
        if fan_speed:
            self.fan_speed = fan_speed
        if error_bit:
            FanController.DEFAULT_ERROR_BIT = error_bit
        if num_fans:
            FanController.DEFAULT_NUM_FANS = num_fans
        if temp_min:
            self.temp_min = temp_min
        if temp_max:
            self.temp_max = temp_max

        # Logging changes for confirmation
        print(f"Updated Fan Settings: {FanController.REG_FAN_SETTING}")
        print(f"Updated Tachometer High: {FanController.REG_TACH_READING_HIGH}")
        print(f"Updated Tachometer Low: {FanController.REG_TACH_READING_LOW}")
        print(f"Updated PWM Value: {FanController.DEFAULT_PWM_VALUE}")
        print(f"Updated Fan Speed: {self.fan_speed}")
        print(f"Updated Minimum Temperature: {self.temp_min}")
        print(f"Updated Maximum Temperature: {self.temp_max}")


    def set_temperature_limits(self, fan_name, min_temp, max_temp):
        """
        Set custom temperature limits for a specific fan.
    
        :param fan_name: Name of the fan (e.g., "fan1").
        :param min_temp: Minimum temperature in degrees Celsius.
        :param max_temp: Maximum temperature in degrees Celsius.
        """
        if fan_name not in self.fan_status:
            logging.error(f"Invalid fan name: {fan_name}")
            return
    
        self.temperature_limits[fan_name] = (min_temp, max_temp)
        logging.info(f"Set temperature limits for {fan_name}: {min_temp}°C - {max_temp}°C.")



    def write_register(self, reg, value):
        """Write a value to a register."""
        try:
            self.bus.write_byte_data(self.address, reg, value)
            logging.info(f"Written {value:#04x} to register {reg:#04x}.")
        except Exception as e:
            logging.error(f"Failed to write to register {reg:#04x}: {e}")

    def read_register(self, reg):
        """Read a value from a register."""
        try:
            value = self.bus.read_byte_data(self.address, reg)
            logging.info(f"Read {value:#04x} from register {reg:#04x}.")
            return value
        except Exception as e:
            logging.error(f"Failed to read from register {reg:#04x}: {e}")
            return None 

    def configure(self):
        """Configure the device for normal operation."""
        self.write_register(self.REG_CONFIGURATION, 0x40)  # Enable watchdog and configure default settings

    def set_fan_speed(self, fan_name, speed=None):
        """
        Set the fan speed using PWM based on the provided speed percentage.

        :param fan_name: Name of the fan (e.g., "fan1").
        :param speed: Speed as a percentage (0-100). Defaults to 50%.
        """
        if fan_name not in self.fan_settings:
            logging.error(f"Invalid fan name: {fan_name}")
            return

        speed = speed if speed is not None else self.DEFAULT_FAN_SPEED

        if speed < 0 or speed > 100:
            logging.error("Speed must be between 0 and 100.")
            return

        pwm_value = int((speed / 100) * 255)  # Convert percentage to PWM value (0-255)
        reg = self.fan_settings[fan_name]
        self.write_register(reg, pwm_value)
        self.fan_status[fan_name]['speed'] = speed
        logging.info(f"Set {fan_name} to {speed}% speed (PWM value: {pwm_value}).")

    def adjust_fan_speed(self, fan_name, temperature):
        """
        Adjust the fan speed dynamically based on the temperature.

        :param fan_name: Name of the fan (e.g., "fan1").
        :param temperature: Current temperature in degrees Celsius.
        """
        if fan_name not in self.fan_status:
            logging.error(f"Invalid fan name: {fan_name}")
            return

        min_temp, max_temp = self.temperature_limits.get(fan_name, (self.DEFAULT_TEMP_MIN, self.DEFAULT_TEMP_MAX))
        
        # Clamp temperature within the set limits
        temperature = max(min(temperature, max_temp), min_temp)
        
        # Scale temperature to PWM value (0-255)
        pwm_value = int(min(max((temperature - min_temp) * 255 / (max_temp - min_temp), 0), 255))
        reg = self.fan_settings[fan_name]
        self.write_register(reg, pwm_value)
        speed=int((pwm_value/255)*100)
        self.fan_status[fan_name]['speed'] = speed
        logging.info(f"Set {fan_name} to {speed}% speed (PWM value: {pwm_value}).")

    def get_fan_rpm(self, fan_name):
        """
        Get the fan's RPM.

        :param fan_name: Name of the fan (e.g., "fan1").
        :return: RPM value or None if an error occurs.
        """
        if fan_name not in self.fan_status:
            logging.error(f"Invalid fan name: {fan_name}")
            return None

        reg_high = self.fan_tach_readings[fan_name]['high']
        reg_low = self.fan_tach_readings[fan_name]['low']

        high_byte = self.read_register(reg_high)
        low_byte = self.read_register(reg_low)

        if high_byte is None or low_byte is None:
            self.fan_status[fan_name]['error'] = True
            return None

        rpm = (high_byte << 8) | low_byte
        self.fan_status[fan_name]['rpm'] = rpm
        logging.info(f"{fan_name} RPM: {rpm}")
        return rpm

    def compare_rpm_with_target(self, fan_name):
        """
        Compare the current RPM with a target RPM and log the result.
        :param fan_name: Name of the fan (e.g., "fan1").
        """
        target_rpm = self.calculate_target_rpm(fan_name)
        current_rpm = self.fan_status[fan_name]['rpm']

        if current_rpm is None:
            logging.warning(f"RPM for {fan_name} could not be read. Unable to compare with target.")
            return

        if current_rpm < target_rpm:
            logging.warning(f"{fan_name} RPM ({current_rpm}) is below the target RPM ({target_rpm}).")
        elif current_rpm > target_rpm:
            logging.warning(f"{fan_name} RPM ({current_rpm}) exceeds the target RPM ({target_rpm}).")
        else:
            logging.info(f"{fan_name} RPM is on target: {current_rpm} RPM.")
    
    
    def calculate_min_max_rpm(self):
        """Calculate the min and max RPMs based on initial diagnostics."""
        min_rpm = float('inf')
        max_rpm = 0

        # Perform diagnostic on each fan to get the RPM readings
        for fan_name in self.fan_settings.keys():
            # Read the tachometer values
            high_byte = self.read_register(self.fan_tach_readings[fan_name]['high'])
            low_byte = self.read_register(self.fan_tach_readings[fan_name]['low'])

            if high_byte is not None and low_byte is not None:
                rpm = (high_byte << 8) | low_byte
                logging.info(f"Initial RPM for {fan_name}: {rpm}")

                # Update min and max RPM values
                min_rpm = min(min_rpm, rpm)
                max_rpm = max(max_rpm, rpm)

            # Save the calculated RPM values in the fan status for later use
            self.fan_status[fan_name]['min_rpm'] = min_rpm
            self.fan_status[fan_name]['max_rpm'] = max_rpm

        logging.info(f"Min RPM across all fans: {min_rpm}")
        logging.info(f"Max RPM across all fans: {max_rpm}")
    
    def compare_rpm_with_target(self, fan_name):
        """
        Compare the current RPM with a dynamically calculated target RPM and log the result.
        The target RPM is calculated based on the fan's initial RPM and current PWM value.
        
        :param fan_name: Name of the fan (e.g., "fan1").
        """
        target_rpm = self.calculate_target_rpm(fan_name)
        current_rpm = self.fan_status[fan_name]['rpm']

        if current_rpm is None:
            logging.warning(f"RPM for {fan_name} could not be read. Unable to compare with target.")
            return

        # Dynamically calculate the tolerance as a percentage of the target RPM
        min_rpm = self.fan_status[fan_name]['min_rpm']
        max_rpm = self.fan_status[fan_name]['max_rpm']

        # Adjust the tolerance based on the actual observed min/max RPMs
        tolerance = 0.10  # Allow for ±10% tolerance by default

        if current_rpm < target_rpm * (1 - tolerance):
            logging.warning(f"{fan_name} RPM ({current_rpm}) is below the target RPM ({target_rpm}) by more than 10%.")
        elif current_rpm > target_rpm * (1 + tolerance):
            logging.warning(f"{fan_name} RPM ({current_rpm}) exceeds the target RPM ({target_rpm}) by more than 10%.")
        else:
            logging.info(f"{fan_name} RPM is within the acceptable range.")

    def calculate_target_rpm(self, fan_name):
        """
        Calculate the target RPM dynamically based on the initial RPMs (min/max) and the current PWM value.
        
        :param fan_name: Name of the fan (e.g., "fan1").
        :return: The target RPM for the fan based on the current PWM.
        """
        min_rpm = self.fan_status[fan_name]['min_rpm']
        max_rpm = self.fan_status[fan_name]['max_rpm']
        speed = self.fan_status[fan_name]['speed']

        # Scale the target RPM proportionally based on PWM
        target_rpm = min_rpm + ((max_rpm - min_rpm) * (speed / 100))
        logging.info(f"Target RPM for {fan_name} based on current speed {speed}: {target_rpm}")
        return target_rpm
    
    def check_errors(self, fan_name):
        """
        Check for errors in the fan.

        :param fan_name: Name of the fan (e.g., "fan1").
        :return: True if an error is detected, False otherwise.
        """
        if fan_name not in self.fan_status:
            logging.error(f"Invalid fan name: {fan_name}")
            return True

        status_reg = self.read_register(self.REG_FAN_STATUS)
        if status_reg is None:
            self.fan_status[fan_name]['error'] = True
            return True

        error_detected = bool(status_reg & self.DEFAULT_ERROR_BIT)

        if error_detected:
            logging.warning(f"Error detected for {fan_name}.")
        else:
            logging.info(f"No errors for {fan_name}.")

        self.fan_status[fan_name]['error'] = error_detected
        return error_detected

    def control_fans_based_on_temperature(self, temperature_data):
        """
        Control fan speeds dynamically based on temperature data.

        :param temperature_data: Dictionary with fan names as keys and temperatures as values.
        """
        for fan_name, temp in temperature_data.items():
            if fan_name in self.fan_status:
                self.adjust_fan_speed(fan_name, temp)

    def check_fan_status(self):
        """Check the overall fan status and report any issues."""
        status = self.read_register(self.REG_FAN_STATUS)
        if status is not None:
            logging.info(f"Fan Status: {status:#04x}")
        else:
            logging.error("Failed to read fan status register.")
        return self.read_register(self.REG_FAN_STATUS)

    def check_stall_status(self):
        """Check for any fan stalls."""
        stall_status = self.read_register(self.REG_FAN_STALL_STATUS)
        if stall_status is not None:
            if stall_status:
                logging.warning(f"Fan Stall Detected: {stall_status:#04x}")
            else:
                logging.info("No fan stall detected.")
        else:
            logging.error("Failed to read fan stall status register.")
        

    def check_drive_fail_status(self):
        """Check for any drive failures."""
        drive_fail_status = self.read_register(self.REG_DRIVE_FAIL_STATUS)
        if drive_fail_status is not None:
            if drive_fail_status:
                logging.warning(f"Drive Fail Detected: {drive_fail_status:#04x}")
            else:
                logging.info("No drive fail detected.")
        else:
            logging.error("Failed to read drive fail status register.")
            
    def monitor_fans(self):
    """
    Monitor fan speeds, check for faults, and return a list of fault codes for each fan.
    
    :return: A list of fault codes, one for each fan.
             0 means no faults, non-zero values represent specific faults.
    """
    fault_codes = []

    # Retrieve status from individual functions
    fan_status = self.check_fan_status()
    stall_status = self.check_stall_status()
    drive_fail_status = self.check_drive_fail_status()

    # Iterate over each fan and calculate fault codes
    for i, fan_name in enumerate(self.fan_settings, start=1):
        fault_code = 0

        # Check general fan status
        if fan_status & (1 << (i - 1)):
            fault_code |= 0x01  # Bit 0: General fan status fault

        # Check for stall status
        if stall_status & (1 << (i - 1)):
            fault_code |= 0x02  # Bit 1: Stall detected

        # Check for drive failure
        if drive_fail_status & (1 << (i - 1)):
            fault_code |= 0x04  # Bit 2: Drive failure detected

        # Check RPM
        rpm = self.get_fan_rpm(fan_name)
        if rpm is None:
            fault_code |= 0x08  # Bit 3: RPM read failure
        elif not self.compare_rpm_with_target(fan_name):
            fault_code |= 0x10  # Bit 4: RPM out of target range

        # Add fault code for this fan to the list
        fault_codes.append(fault_code)

    return fault_codes

    def initialize_fans(self):
        """Initialize the fan settings and tachometer readings."""
        number=0
        for fan_name in self.REG_FAN_SETTING.keys():
            if number<self.num_fans:
                self.fan_settings[fan_name] = self.REG_FAN_SETTING[fan_name]
                self.fan_tach_readings[fan_name] = {
                    "high": self.REG_TACH_READING_HIGH[fan_name],
                    "low": self.REG_TACH_READING_LOW[fan_name]
                }
                self.fan_status[fan_name] = {"speed": self.DEFAULT_FAN_SPEED, "rpm": None, "min_rpm": None, "max_rpm": None, "error": False}
                number+=1

    def turn_on_selected_fans(self):
        """Activate the fans based on the selected fan settings."""
        for fan_name in self.fan_settings.keys():
            self.set_fan_speed(fan_name, self.fan_status[fan_name]["speed"])
    

# Example usage
if __name__ == "__main__":
    # Example initialization with custom temperature limits for each fan
    temp_limits = {
        "fan1": (30, 70),
        "fan2": (25, 85),
        "fan3": (20, 80),
    }
    
    controller = FanController(i2c_bus=1, num_fans=3, temperature_limits=temp_limits)

    # Example: Control fans based on current temperatures (arbitrary example)
    temperature_data = {
        "fan1": 65,
        "fan2": 72,
        "fan3": 55,
    }

    controller.control_fans_based_on_temperature(temperature_data)
    controller.monitor_fans()
