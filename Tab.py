import wx

class Tab(wx.Panel):
    _registry = []

    @staticmethod
    def set_settings(settings):
        Tab._settings = settings

        
    @staticmethod
    def set_update_sb(func):
        Tab._update_sb = func

    @staticmethod
    def set_coot_client(serv):
        Tab._coot_client = serv

    @staticmethod
    def set_start_coot(func):
        Tab._start_coot = func    
    
    
    @staticmethod
    def wproj(fn):
        def _decorated(self, *args):
            if self._project is not None:
                return fn(self, *args)
            else:
                wx.MessageBox('Please select or create a project before starting any jobs', 'No Project Selected', style=wx.OK | wx.CENTRE)
                
        return _decorated
    
    _project = None
    
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        if not self in Tab._registry:
            Tab._registry.append(self)
            
            
    def refresh_tabs(self):
       if self._project is not None:
            for tab in Tab._registry:
                if tab:
                    tab.refresh()
                else:
                    Tab._registry.remove(tab)
            
            
    # abstract
    def refresh(self):
        pass
        
        
    def set_status(self, text):
        if hasattr(self, '_update_sb'):
            self._update_sb(text)
        
                
        
    @property
    def s(self):
        return self._settings
        