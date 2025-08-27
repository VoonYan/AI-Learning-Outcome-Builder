import json
import threading

class ConfigManager:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self._AIParams = self._retrieveAIParams()

    def _retrieveAIParams(self):
        with open(self.path) as file:
            return json.load(file)
    
    def getCurrentParams(self):
        with self.lock:
            return self._AIParams.copy()
        
    def replaceCurrentParameter(self, key, newValue):
        with self.lock:
            self._AIParams.update({key: newValue})
        with open(self.path, 'w') as file:
            json.dump(self._AIParams, file)
        pass
