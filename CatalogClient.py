import requests

class CatalogClient:
    def __init__(self, url):
        self.url = url
        
    def get_catalog(self):
        return (requests.get(self.url)).json()

    def get_devices(self):
        url = self.url+"/devices"
        return (requests.get(url)).json()

    def get_device(self, id):
        url = self.url+"/devices/"+str(id)
        return (requests.get(url)).json()

    def get_broker(self):
        url = self.url+"/broker"
        return (requests.get(url)).json()

    def register_device(self, payload):
        url = self.url+"/devices"
        return (requests.post(url, json=payload)).json()
    
    def register_service(self,payload):
        url = self.url+"/services"
        return (requests.post(url, json=payload)).json()

    def refresh_device(self, id):
        url = self.url+"/devices/"+str(id)
        return (requests.put(url)).json()
 
    def refresh_service(self, id):
        url = self.url+"/services/"+str(id)
        return (requests.put(url)).json()