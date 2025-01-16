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

    def list_services(self,ssid):
        """List available Wi-Fi services."""
        try:
            result = subprocess.run(['connmanctl', 'services'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            services = result.stdout.decode('utf-8').strip().split("\n")
            print("Available services:")
            for service in services:
                print(service)
                my_list = service.split(" ")
                SSID = [item for item in my_list if item]
                print(SSID)
                if (SSID[-2]==ssid):
                    print(SSID)
                    #if SSID[-3]:
                    #    print("Dharmik")
                    #    subprocess.run(['connmanctl', 'remove', SSID[2]], check=True)
                    print(SSID)
                    return services , SSID
            return services , SSID
        except subprocess.CalledProcessError as e:
            print(f"Error listing services: {e}")
            return []

    def connect_to_network(self, service_name, passphrase):
        """Connect to a specific Wi-Fi network."""
        try:
            subprocess.run(['connmanctl', 'agent', 'on'], check=True)
            subprocess.run(['connmanctl', 'connect', service_name], input=f"Passphrase = {passphrase}\n", text=True, check=True)
            print(f"Connected to {service_name}")
            subprocess.run(['connmanctl', 'quit'])
        except subprocess.CalledProcessError as e:
            print(f"Error connecting to {service_name}: {e}")
            return False
        return True

    def connect_wifi(self, ssid, passphrase):
        """Complete Wi-Fi connection procedure."""
        if self.modprobe_wifi() and self.enable_wifi() and self.scan_wifi():
            services,SSID = self.list_services(ssid)
            #print(services,"/n")
            # Filter services to find the one that matchexs the SSID (e.g., 'PSTI')
            service_name = None
            #for service in services:
                #if ssid in service:
                    # If 'PSTI' is found, use the service identifier (e.g., 'wifi_a841f4f2c841_50535449_managed_psk')
                    #service_name = service.strip().split(' ')[1]  # Extracting service name from the line
                    #break
            service_name = SSID[-1]
            if service_name:
                return self.connect_to_network(service_name, passphrase)
            else:
                print(f"Network with SSID '{ssid}' not found in available services.")
                return False
        return False

# Example Usage
wifi_manager = WifiManager()
result = wifi_manager.connect_wifi(ssid="PSTI", passphrase="psti@123")
#result = wifi_manager.connect_wifi(ssid="dhanu", passphrase="dhanu.pc")
print(f"Connection result: {result}")
