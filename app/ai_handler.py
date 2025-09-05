import json
import threading

#this manager handles the config_manager in __init__ as a flask is multithreaded, the config_manager resource could encounter race conditions
#this manager locks the resources to mitigate them, and can get, load, edit and reset the AI params as needed 
class ConfigManager:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self._AIParams = self._retrieveAIParams()

    def _retrieveAIParams(self):
        try:
            with open(self.path) as file:
                return json.load(file)
        except:
            with open('app/AIConfigDefault.json') as file:
                return json.load(file)
    
    def getCurrentParams(self):
        with self.lock:
            return self._AIParams.copy()
        
    def replaceCurrentParameter(self, key, newValue):
        with self.lock:
            self._AIParams.update({key: newValue})
            with open(self.path, 'w') as file:
                json.dump(self._AIParams, file)

    def resetParamsToDefault(self):
        with open('app/AIConfigDefault.json') as file:
            self._AIParams = json.load(file)
