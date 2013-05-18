import wx


class FileBrowser:

    def __init__(self, parent, mask):

        self._browse = wx.Button(self, -1, 'Browse', size=(70,25))
        self._browse.Bind(wx.EVT_BUTTON, self._get_cif)
        self._label = wx.TextCtrl(self, -1, size=(250,25))
        
        self._browse_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._browse_sizer.Add(self._label)
        self._browse_sizer.Add(self._browse, wx.EXPAND)

    def get_file(self):
        return self._browse.GetValue()