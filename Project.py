import os
import pickle
import json
from time import time

class Project:
    
    def __init__(self, root, title=None, **kwargs):
        self._data = { 'root': root, 'title': title, 'job_count': 0, 'last_action': '', 'last_time': -1}
    
        if title is None:
            self._load()
            if self._data['root'] != root:
                self._data['root'] = root
                self._save()
            
            if 'cwd' in kwargs:
                    os.chdir(self._data['root'])
    
        else:
            self._save()
            if 'cwd' in kwargs:
                os.chdir(root)
    
            
    
    
    def root(self):
        return str(self._data['root'])
    
    def title(self):
        return self._data['title']
    

    def job_count(self, pm = None):
        return len([name for name in os.listdir(self.root()) if os.path.isdir(self.root()+os.sep+name) and name.split('_')[0].isdigit()])
        
        if pm is None:
            return self._data['job_count']
        else:
            self._data['job_count'] += pm
            self._save()
        
    def action(self, action):
        self._data['last_time'] = time()
        self._data['last_action'] = action
        #self._data['job_count'] += 1
        self._save()
        
    def last_time(self):
        return self._data['last_time']
        
    def _save(self):
        if not os.path.exists(self.root() + os.sep + '.proton8'):
            os.mkdir(self.root() + os.sep + '.proton8')

        #pickle.dump(self, open(self._root + '/.proton8/project.pkl', 'wb'))
        json.dump(self._data, open(self.root() + os.sep + '.proton8' + os.sep + 'project.json', 'w'))
        
    def _load(self):
        if os.path.exists(self.root() + os.sep + '.proton8' + os.sep + 'project.json'):
            self._data = json.load(open(self.root() + os.sep + '.proton8' + os.sep + 'project.json'))
        
    def _sync(self):
        pass