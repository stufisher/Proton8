import os
import json
import inspect
import wx

from Tab import Tab
from Project import Project

class Settings:
    def __init__(self):
        self._settings = { 'project_roots': [], 'current_root': None }
        self._root = os.path.expanduser('~/.proton8')

        os.environ['PATH'] = os.environ['PATH'] + ':' + os.getcwd() + '/Resources'
        self._p8_root = os.getcwd() + '/'
        
        self._restore()

    @property
    def proot(self):
        #return self._p8_root
        return inspect.getfile(inspect.currentframe()).replace('Settings.py', '')
                
    def save(fn):
        def _decorated(self,*args):
            val = fn(self,*args)
            self._save()
            return val
            
        return _decorated
                
    def _save(self):
        if not os.path.exists(self._root):
            os.mkdir(self._root)
            
        file = open(self._root + '/settings.json', 'w')
        file.write(json.dumps(self._settings))
        file.close()
        
    def _restore(self):
        if os.path.exists(self._root + '/settings.json'):
            file = open(self._root + '/settings.json')
            self._settings = json.load(file)
            file.close()
          
    @property
    def projects(self):
        return self._settings['project_roots']
          
    @property
    def current(self):
            return self._settings['current_root']
    
    @current.setter
    @save
    def current(self, current):
        self._settings['current_root'] = current
    
    @save
    def load_project(self, root):
        if root != self.current:
            if os.path.exists(root + os.sep + '.proton8' + os.sep + 'project.json'):
                Tab._project = Project(root)
                self._settings['current_root'] = root
    
    @save
    def add_project(self, root, title):
        if not root in self.projects:
            upd = False
            if os.path.exists(root + os.sep + '.proton8' + os.sep + 'project.json'):
                ret = wx.MessageBox('The selected folder looks like an existing Proton8 project. Do you wish to import it?', 'Project Exists', style=wx.YES_NO | wx.CENTRE)
                print ret
                if ret == wx.YES:
                    #print 'YES1'
                    Tab._project = Project(root)
                    upd = True
            else:
                Tab._project = Project(root,title)
                upd = True
                
            if upd:
                self.projects.append(root)
                self._settings['current_root'] = root
            
    @save
    def del_project(self, root):
        if root in self.projects:
            self._settings['project_roots'].remove(root)
        
    
    @save
    def val(self, key, value=None):
        if value is None:
            if key in self._settings:
                return self._settings[key]
            else:
                raise Exception, 'No such setting'
                
        else:
            self._settings[key] = value