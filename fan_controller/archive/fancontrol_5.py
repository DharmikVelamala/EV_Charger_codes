import smbus
import logging
import time

logging.basicConfig(level=logging.DEBUG)

class FanController:
    def __init__(self, bus_number, address):
        self.bus = smbus.SMBus(bus_number)
        self.address = address
        self.fan_registers = {
            1: {"rpm_high": 0x10, "rpm_low": 0x11, "pwm": 0x20},
            2: {"rpm_high": 0x12, "rpm_low": 0x13, "pwm": 0x21},
        }

    def write_register(self, reg, value):
        try:
            self.bus.write_byte_data(self.address, reg, value)
            logging.debug(f"Wrote value {value} to register {reg}")
        except Exception as e:
            logging.error(f"Failed to write to register {reg}: {e}")

    def read_register(self, reg):
        try:
            value = self.bus.read_byte_data(self.address, reg)
            logging.debug(f"Read value {value} from register {reg}")
            return value
        except Exception as e:
            logging.error(f"Failed to read from register {reg}: {e}")
            return None

    def set_fan_speed(self, fan_number, speed_percentage):
        if fan_number not in self.fan_registers:
            logging.error("Invalid fan number")
            return
        pwm_value = int((speed_percentage / 100) * 255)
        self.write_register(self.fan_registers[fan_number]["pwm"], pwm_value)

    def get_fan_rpm(self, fan_number):
        if fan_number not in self.fan_registers:
            logging.error("Invalid fan number")
            return None
        rpm_high = self.read_register(self.fan_registers[fan_number]["rpm_high"])
        rpm_low = self.read_register(self.fan_registers[fan_number]["rpm_low"])
        if rpm_high is None or rpm_low is None:
            return None
        return (rpm_high << 8) | rpm_low

    def monitor_fans(self):
        for fan_number in self.fan_registers:
            rpm = self.get_fan_rpm(fan_number)
            if rpm is None:
                logging.warning(f"Fan {fan_number} RPM read failed")
            elif rpm == 0:
                logging.warning(f"Fan {fan_number} is stalled")
            else:
                logging.info(f"Fan {fan_number} RPM: {rpm}")

    def adjust_fan_speeds_based_on_temp(self, temperature):
        speed = min(max((temperature - 20) * 5, 0), 100)  # Linear mapping
        for fan_number in self.fan_registers:
            self.set_fan_speed(fan_number, speed)

    def check_status(self):
        status_reg = 0x00
        status = self.read_register(status_reg)
        if status is not None:
            logging.info(f"Status register: {bin(status)}")
        return status

    # New functions added below

    def retry_write_register(self, reg, value, retries=3):
        for attempt in range(retries):
            try:
                self.write_register(reg, value)
                return True
            except Exception as e:
                logging.error(f"Attempt {attempt + 1}: Failed to write register {reg}: {e}")
        return False

    def retry_read_register(self, reg, retries=3):
        for attempt in range(retries):
            try:
                value = self.read_register(reg)
                if value is not None:
                    return value
            except Exception as e:
                logging.error(f"Attempt {attempt + 1}: Failed to read register {reg}: {e}")
        return None

    def dynamic_add_fan(self, fan_number, rpm_high, rpm_low, pwm):
        if fan_number in self.fan_registers:
            logging.warning(f"Fan {fan_number} already exists")
            return False
        self.fan_registers[fan_number] = {"rpm_high": rpm_high, "rpm_low": rpm_low, "pwm": pwm}
        logging.info(f"Fan {fan_number} added dynamically")
        return True

    def save_configuration(self, filepath):
        try:
            with open(filepath, "w") as file:
                file.write(str(self.fan_registers))
                logging.info(f"Configuration saved to {filepath}")
        except Exception as e:
            logging.error(f"Failed to save configuration: {e}")

    def load_configuration(self, filepath):
        try:
            with open(filepath, "r") as file:
                self.fan_registers = eval(file.read())
                logging.info(f"Configuration loaded from {filepath}")
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")

    def set_fan_off(self, fan_number):
        if fan_number not in self.fan_registers:
            logging.error("Invalid fan number")
            return
        self.set_fan_speed(fan_number, 0)
        logging.info(f"Fan {fan_number} turned off")

    def map_speed_to_curve(self, fan_number, temperature):
        if temperature < 20:
            speed = 0
        elif temperature > 80:
            speed = 100
        else:
            speed = (temperature - 20) * (100 / 60)
        self.set_fan_speed(fan_number, speed)
        logging.info(f"Fan {fan_number} speed set to {speed}% for temperature {temperature}")

    def asynchronous_monitoring(self):
        import threading

        def monitor_loop():
            while True:
                self.monitor_fans()
                time.sleep(5)

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logging.info("Asynchronous fan monitoring started")

# Example usage
if __name__ == "__main__":
    controller = FanController(bus_number=1, address=0x1A)
    controller.adjust_fan_speeds_based_on_temp(temperature=30)
    controller.asynchronous_monitoring()
    controller.save_configuration("fan_config.txt")

