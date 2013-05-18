import wx

class ErrorHandler:
    def __init__(self):
        self._parent = None
        self._dialog = None
        
    def SetParent(self, parent):
        self._parent = parent
        
    def _create_dialog(self):
        if self._dialog is None:
            self._dialog = ErrorDialog(self._parent)
            self._dialog.Show()
            self._dialog.SetFocus()      
        
    def write(self, text):
        self._create_dialog()
        self._dialog.append(text)


class ErrorDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, 0, 'Proton8 Python Error', size=(350,400))
        self.Bind(wx.EVT_CLOSE, self._on_close)
        
        self._text = ''
        
        self.label = wx.StaticText(self, -1, 'Proton8 seems to have encountered an error, press send to email this log to the developer', size=(350,50))
        self.text = wx.TextCtrl(self, -1, size=(350, 300), style=wx.TE_MULTILINE)
        self.text.SetFont(wx.Font(12, wx.MODERN, wx.NORMAL, wx.NORMAL))
        
        send = wx.Button(self, 0, 'Send Report')
        close = wx.Button(self, 1, 'Close')
        
        close.Bind(wx.EVT_BUTTON, self._on_close)
        send.Bind(wx.EVT_BUTTON, self._send_report)
        
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_sizer.Add(send)
        self.button_sizer.Add(close)
        
        self.main = wx.BoxSizer(wx.VERTICAL)
        self.main.Add(self.label)
        self.main.Add(self.text)
        self.main.Add(self.button_sizer)
        
        self.SetSizer(self.main)
        
        
    def _on_close(self, event):
        self.Destroy()
        
    def _send_report(self, event):
        pass
    
    def append(self, text):
        self._text += text + '\n'
        self.text.SetValue(self._text)
        