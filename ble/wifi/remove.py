import subprocess
import re

def remove_all_wifi_networks():
    """Remove all saved Wi-Fi networks using connmanctl."""
    try:
        # List all services
        result = subprocess.run(
            ['connmanctl', 'services'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        services = result.stdout

        # Find all Wi-Fi services
        wifi_services = re.findall(r"(wifi_\S+_managed_psk)", services)

        if not wifi_services:
            print("No saved Wi-Fi networks found.")
            return

        # Iterate and remove each Wi-Fi service
        for service in wifi_services:
            print(f"Removing: {service}")
            subprocess.run(
                ['connmanctl', 'remove', service],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
        print("All saved Wi-Fi networks have been removed.")

    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e.stderr}")

# Execute the function
remove_all_wifi_networks()
