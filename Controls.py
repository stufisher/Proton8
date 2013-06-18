import wx
import os

import wxtbx.bitmaps

# File browser control
class FileBrowser:

    def __init__(self, parent, mask, title, *args, **kwargs):
        self._callback = None
        self._dir = False
        
        if 'dir' in kwargs:
            self._dir = True
        
        if 'callback' in kwargs:
            self._callback = kwargs['callback']
    
        val = ''
        if 'val' in kwargs:
            val = kwargs['val']
        
    
        self._parent = parent
        self._mask = mask
        self._title = title
        
        self._browse = wx.Button(parent, -1, 'Browse')#, size=(50,25))
        self._browse.Bind(wx.EVT_BUTTON, self._get_file)
        self._file = wx.TextCtrl(parent, -1, val)#, size=(250,25))
        
        self._browse_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._browse_sizer.Add(self._file, 3, wx.EXPAND)
        self._browse_sizer.Add(self._browse, 1, wx.EXPAND|wx.ALL, 2)

    def _get_file(self, event):
        if self._dir:
            dlg = wx.DirDialog(self._parent, self._title, os.getcwd())
        else:
            dlg = wx.FileDialog(self._parent, self._title, os.getcwd(), "", self._mask, wx.OPEN)
        
        if dlg.ShowModal() == wx.ID_OK:
            self._file.SetLabel(dlg.GetPath())
            if self._callback is not None:
                self._callback()
            

        dlg.Destroy()


    def file(self):
        return str(self._file.GetValue())
    
    def sizer(self):
        return self._browse_sizer


class ValidFileBrowser(FileBrowser):
    def __init__(self, *args, **kwargs):
        FileBrowser.__init__(self, *args, **kwargs)

        self._path = kwargs['path']
        
        self._valid = wx.StaticBitmap(self._parent, size=(16,16))
        self._browse_sizer.Add(self._valid, 0, wx.EXPAND|wx.ALL, 2)
    
        self._validate()


    def _get_file(self, event):
        FileBrowser._get_file(self, event)
        self._validate()

        
    def _validate(self):
        path = self._path.replace('[P]', self.file()).replace('[p]', self.file().lower())
        path = path.replace('[B]', os.path.basename(self.file())).replace('[b]', os.path.basename(self.file()).lower())
        
        print path
        if os.path.exists(path):
            self._valid.SetBitmap(wxtbx.bitmaps.fetch_icon_bitmap('actions', 'ok', scale=(16,16)))
        else:
            self._valid.SetBitmap(wxtbx.bitmaps.fetch_icon_bitmap('actions', 'no', scale=(16,16)))

