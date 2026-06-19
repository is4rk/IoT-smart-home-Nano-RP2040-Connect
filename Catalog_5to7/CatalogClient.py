import requests
#not much to say tbh, just adds /catalog to the base url
class CatalogClient:
    def __init__(self, url):
        self.url = url
        
    def get_catalog(self):
        return (requests.get(self.url)).json()

    def get_devices(self):
        url = self.url+"/catalog/devices"
        return (requests.get(url)).json()

    def get_device(self, id):
        url = self.url+"/catalog/devices/"+str(id)
        return (requests.get(url)).json()
    
    def get_services(self):
        url = self.url + "/catalog/services"
        return requests.get(url).json()

    def get_service(self, id):
        url = self.url + "/catalog/services/" + str(id)
        return requests.get(url).json()

    def get_broker(self):
        url = self.url+"/catalog/broker"
        return (requests.get(url)).json()

    def register_device(self, payload):
        url = self.url+"/catalog/devices"
        return (requests.post(url, json=payload)).json()
    
    def register_service(self,payload):
        url = self.url+"/catalog/services"
        return (requests.post(url, json=payload)).json()

    def refresh_device(self, id, payload):
        url = self.url+"/catalog/devices/"+str(id)
        return (requests.put(url, json=payload)).json()
 
    def refresh_service(self, id, payload):
        url = self.url+"/catalog/services/"+str(id)
        return (requests.put(url, json=payload)).json()