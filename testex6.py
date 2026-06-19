import time
import threading
from CatalogClient import CatalogClient

def start_heartbeat_loop(client, service_id):
    print(f"Starting background heartbeat thread for {service_id}...")
    while True:
        try:
            time.sleep(60) # Send heartbeat every 60 seconds 
            print(f"Sending heartbeat for {service_id}...")
            # Use PUT to refresh registration lease 
            response = client.refresh_service(service_id)
            print("Heartbeat ACK:", response)
        except Exception as e:
            print(f"Connection warning: {e}. Retrying on next cycle...") # 

if __name__ == "__main__":
    # 1. Initialize client pointing to your local Catalog registry
    client = CatalogClient(CATALOG_URL)
    
    # 2. Define a fake service payload to register 
    my_service_id = "thermostat_service_01"
    mock_payload = {
        "id": my_service_id,
        "description": "Smart Home Thermostat Controller",
        "endpoints": {"url": "http://localhost:9000"},
        "resources": ["temperature", "thermostat"]
    }
    
    # 3. Test service auto-registration on startup 
    print(f"Registering service: {my_service_id}...")
    reg_response = client.register_service(mock_payload)
    print("Registration Response from Catalog:", reg_response)
    
    # 4. Spin up the background thread loop to handle periodic refreshes [cite: 148, 149]
    bg_thread = threading.Thread(target=start_heartbeat_loop, args=(client, my_service_id), daemon=True)
    bg_thread.start()
    
    # Keep main script alive to watch execution logs
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping simulation client.")