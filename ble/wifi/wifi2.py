import subprocess

class WifiManager:
    def modprobe_wifi(self, module_name="moal", config_file="nxp/wifi_mod_para.conf"):
        """Load Wi-Fi module using modprobe."""
        try:
            subprocess.run(['modprobe', module_name, f'mod_para={config_file}'], check=True)
            print(f"Module {module_name} loaded with config {config_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error loading module: {e}")
            return False
        return True

    def enable_wifi(self):
        """Enable Wi-Fi using connmanctl."""
        try:
            subprocess.run(['connmanctl', 'enable', 'wifi'], check=True)
            print("Wi-Fi enabled")
        except subprocess.CalledProcessError as e:
            print(f"Error enabling Wi-Fi: {e}")
            return False
        return True

    def scan_wifi(self):
        """Scan for available Wi-Fi networks."""
        try:
            subprocess.run(['connmanctl', 'scan', 'wifi'], check=True)
            print("Scanning for Wi-Fi networks...")
        except subprocess.CalledProcessError as e:
            print(f"Error scanning for networks: {e}")
            return False
        return True

    def list_services(self, ssid):
        """List available Wi-Fi services and remove a service if already saved."""
        try:
            result = subprocess.run(['connmanctl', 'services'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            services = result.stdout.decode('utf-8').strip().split("\n")
            print("Available services:")
            for service in services:
                print(service)
                service_parts = [item for item in service.split(" ") if item]  # Clean empty strings
                if len(service_parts) > 2 and service_parts[-2] == ssid:  # Match SSID
                    service_name = service_parts[-1]
                    # Remove the saved network if it exists
                    try:
                        subprocess.run(['connmanctl', 'remove', service_name], check=True)
                        print(f"Removed saved network: {service_name}")
                    except subprocess.CalledProcessError as e:
                        print(f"Error removing saved network: {e}")
                    return service_name  # Return the service name for connecting
            print(f"SSID '{ssid}' not found.")
            return None
        except subprocess.CalledProcessError as e:
            print(f"Error listing services: {e}")
            return None

    def connect_to_network(self, service_name, passphrase):
        """Connect to a specific Wi-Fi network."""
        try:
            subprocess.run(['connmanctl', 'agent', 'on'], check=True)
            connect_process = subprocess.run(
                ['connmanctl', 'connect', service_name],
                input=f"Passphrase = {passphrase}\n",
                text=True,
                check=True
            )
            print(f"Connected to {service_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error connecting to {service_name}: {e}")
            return False

    def connect_wifi(self, ssid, passphrase):
        """Complete Wi-Fi connection procedure."""
        if self.modprobe_wifi() and self.enable_wifi() and self.scan_wifi():
            service_name = self.list_services(ssid)
            if service_name:
                return self.connect_to_network(service_name, passphrase)
            else:
                print(f"Network with SSID '{ssid}' not found in available services.")
                return False
        return False

# Example Usage
wifi_manager = WifiManager()
result = wifi_manager.connect_wifi(ssid="PSTI", passphrase="psti@123")
print(f"Connection result: {result}")
