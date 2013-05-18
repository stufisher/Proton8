import inspect

import wx
import wx.aui
import matplotlib
matplotlib.use('WXAgg')

import subprocess
import xmlrpclib
import os

#root = '/Applications/Proton8/Contents/Proton8/source'
root = inspect.getfile(inspect.currentframe()).replace('Proton8.py', '')

os.environ['BOOST_ADAPTBX_FPE_DEFAULT'] = '1'
os.environ['BOOST_ADAPTBX_SIGNALS_DEFAULT'] = '1'
os.environ['REDUCE_HET_DICT'] = root + '/Resources/reduce_het_dict.txt'

import libtbx
from libtbx import load_env

libtbx.env.add_repository(root + '/Resources/')
libtbx.env.process_module(None, 'probe', False)
libtbx.env.process_module(None, 'reduce', False)

from Processing import ProcessManager, Process
from Compare import Compare
from Manager import Manager, Jobs
from Error import ErrorHandler
from Tab import Tab
from Settings import Settings

#from Shelx import PDBImporter

import wxtbx.bitmaps

class MainFrame(wx.Frame):
    def __init__(self, parent, id, title):
        self._settings = Settings()
        
        #PDBImporter('./test/3HLX.pdb', '.')
        #exit(1)
        
        wx.Frame.__init__(self, parent, id, title, size=(850,540))
        self.Bind(wx.EVT_CLOSE, self._on_close)
        
        self.toolbar = wx.ToolBar(self, style=wx.TB_3DBUTTONS|wx.TB_TEXT)
        quit = self.toolbar.AddLabelTool(wx.ID_ANY, 'Quit', wxtbx.bitmaps.fetch_icon_bitmap("actions", "exit"))
        settings = self.toolbar.AddLabelTool(wx.ID_ANY, 'Settings', wxtbx.bitmaps.fetch_icon_bitmap("actions", "configure"))
        about = self.toolbar.AddLabelTool(wx.ID_ANY, 'About', wxtbx.bitmaps.fetch_icon_bitmap("actions", "info"))
        coot = self.toolbar.AddLabelTool(wx.ID_ANY, 'Start Coot', wx.Bitmap(self._settings.proot + 'Resources/gui_resources/coot.png'))
        self.SetToolBar(self.toolbar)
        self.toolbar.Realize()
        
        self.Bind(wx.EVT_TOOL, self._on_close, quit)
        self.Bind(wx.EVT_TOOL, self.start_coot, coot)
        
        self._coot_timer = None
        self._coot_process = None
        self._coot_client = CootClient()

        nb = wx.aui.AuiNotebook(self, -1, style=wx.NB_TOP)
        self.sheet1 = Manager(nb)
        
        Tab.set_settings(self._settings)
        CootClient.set_p8(self._settings.proot)
        
        Tab.set_coot_client(self._coot_client)
        Tab.set_start_coot(self.start_coot)
        Tab.set_update_sb(self.set_status)
        
        self.sheet2 = ProcessManager(nb)
        self.sheet3 = Compare(nb)
        
        Jobs.set_new_refinement(self.sheet2.new_refinement)
        Jobs.set_load_refinement(self.sheet2.load_refinement)
        Jobs.set_auto_refinement(self.sheet2.auto_refinement)

        nb.AddPage(self.sheet1, "Manager")
        nb.AddPage(self.sheet2, "Process")
        nb.AddPage(self.sheet3, "Compare")

        self.sb = self.CreateStatusBar()
        self.sb.SetFieldsCount(2)
        self.sb.SetStatusWidths([-4, -1])
        self.sheet2.SetFocus()

        self.sheet1.load_project()
        self.sheet1.refresh_tabs()
        
        #self.sheet1.sheet2._test()
        
        
        
    def set_status(self, text, fld =0):
        self.sb.SetStatusText(text, fld)

    def set_project(self, project):
        self._project = project
        
    def start_coot(self, event):
        print self._coot_process
        if self._coot_process is not None:
            print self._coot_process.poll()
        
        if self._coot_process == None:
            self._coot_timer = wx.Timer(self, 201)
            wx.EVT_TIMER(self, 201, self.check_coot)
            self._coot_timer.Start(250, False)

            try:
                # need to reset env to get coot to load
                self._coot_process = subprocess.Popen(['/Applications/coot.app/Contents/MacOS/coot', '--script='+self._settings.proot+'Coot.py'], shell=False, env={'DISPLAY': os.environ['DISPLAY'], 'HOME': os.environ['HOME']})
            except:
                wx.MessageBox('Couldnt Start Coot', 'Proton8 couldnt find coot', style=wx.OK | wx.CENTRE)

    
    def check_coot(self, event):
        if self._coot_process is not None:
            if self._coot_process.poll() is not None:
                self._coot_process = None
                self._coot_timer = None
        else:
            self._coot_timer = None
            
    def _on_close(self, event):
        if self._coot_process is not None:
            if self._coot_process.poll() is None:
                self._coot_process.terminate()
        self.Destroy()

class Proton8(wx.App):
    #outputWindowClass = ErrorHandler
    
    def OnInit(self):
         frame = MainFrame(None, -1, 'Proton8')
         #ErrorHandler.set_parent(frame)         
         frame.Show(True)
         frame.Centre()
         
         return True



class CootClient:
    
    @staticmethod
    def set_p8(path):
        CootClient._p8p = path
    
    def __init__(self):
        self._server = xmlrpclib.Server('http://localhost:41734')

    def __getattr__(self, name):
        return _Method(self._server, name)


class _Method:
    def __init__(self, send, name):
        self.__send = send
        self.__name = name
    def __getattr__(self, name):
        return _Method(self.__send, "%s.%s" % (self.__name, name))
    def __call__(self, *args):
        try:
            fn = self.__send.__getattr__(self.__name)
            return fn(*args)
        except:
            pass
    

if __name__ == '__main__':
    app = Proton8(0)
    app.MainLoop()
