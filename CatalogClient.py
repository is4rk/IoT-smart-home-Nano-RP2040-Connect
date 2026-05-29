import requests

# TODO: dobbiamo usare i path del url per dire se /device o /service, non un booleano e poi un dict
class CatalogClient:
    def __init__(self, url):
        self.url = url

    def get_catalog(self):
        respose = requests.get(self.url)
        return respose.json()

    def get_devices(self): 
        respose = requests.get(self.url)
        data = respose.json()
        return data["devices"]

    def get_device(self, id): 
        respose = requests.get(self.url)
        data = respose.json()
        return data["devices"]["id"]

    def get_broker(self):
        respose = requests.get(self.url)
        data = respose.json()
        return data["broker"]

    def register_device(self, payload):
        url = self.url + "/devices"
        body={
            "type": False,
            "element": payload,
        }
        response = requests.post(url, json=body)
        return response.json()
    
    def register_service(self,payload):
        url = self.url + "/services"
        body={
            "type": True,
            "element": payload,
        }
        requests.post()

    def refresh_device(self, id):
        url = self.catalog_url + "/devices/" + id
        body = {
            "id": id
        }
        response = requests.put(url, body)
        return response.json()

        
    # TODO: 
    def refresh_device(self, id):
        url = self.catalog_url + "/services/" + id
        body = {
            "id": id
        }
        response = requests.put(url, body)
        return response.json()