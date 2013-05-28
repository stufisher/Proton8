import inspect

import wx
import wx.aui
import wx.html
import matplotlib
matplotlib.use('WXAgg')

import os
import subprocess
import xmlrpclib

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
from Controls import FileBrowser
from LigandGL import Ligand

#from Shelx import PDBImporter

import wxtbx.bitmaps

# ----------------------------------------------------------------------------
# Proton8 Main Frame
class MainFrame(wx.Frame):
    def __init__(self, parent, id, title):
        self._settings = Settings()
        
        if self._settings.val('phenix'):
            import sys
                
            p = self._settings.val('phenix')
            base = p + '/Contents/' + os.path.basename(p).lower()
            sys.path.append(base + '/elbow')
            sys.path.append(base)
            libtbx.env.add_repository(base)
            libtbx.env.process_module(None, 'elbow', False)
        
        CootClient.set_start_coot(self.start_coot)
        SettingsDialog.set_settings(self._settings)
        HelpDialog.set_settings(self._settings)
        
        wx.Frame.__init__(self, parent, id, title, size=(850,540))
        self.Bind(wx.EVT_CLOSE, self._on_close)
        
        self.toolbar = wx.ToolBar(self, style=wx.TB_3DBUTTONS|wx.TB_TEXT)
        quit = self.toolbar.AddLabelTool(wx.ID_ANY, 'Quit', wxtbx.bitmaps.fetch_icon_bitmap('actions', 'exit'))
        settings = self.toolbar.AddLabelTool(wx.ID_ANY, 'Settings', wxtbx.bitmaps.fetch_icon_bitmap('actions', 'configure'))
        about = self.toolbar.AddLabelTool(wx.ID_ANY, 'About', wxtbx.bitmaps.fetch_icon_bitmap('actions', 'info'))
        help = self.toolbar.AddLabelTool(wx.ID_ANY, 'Help', wxtbx.bitmaps.fetch_icon_bitmap('actions', 'agt_support'))
        self.toolbar.AddSeparator()
        coot = self.toolbar.AddLabelTool(wx.ID_ANY, 'Coot', wx.Bitmap(self._settings.proot + 'Resources/gui_resources/coot.png'))
        ligand = self.toolbar.AddLabelTool(wx.ID_ANY, 'Ligands', wx.Bitmap(self._settings.proot + 'Resources/gui_resources/ligand_32.png'))
        self.SetToolBar(self.toolbar)
        self.toolbar.Realize()
        
        self.Bind(wx.EVT_TOOL, self._on_close, quit)
        self.Bind(wx.EVT_TOOL, self.start_coot, coot)
        self.Bind(wx.EVT_TOOL, self._show_settings, settings)
        self.Bind(wx.EVT_TOOL, self._show_about, about)
        self.Bind(wx.EVT_TOOL, self._show_help, help)
        self.Bind(wx.EVT_TOOL, self._view_ligand, ligand)
        
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

        nb.AddPage(self.sheet1, 'Manage')
        nb.AddPage(self.sheet2, 'Process')
        nb.AddPage(self.sheet3, 'Compare')

        self.sb = self.CreateStatusBar()
        self.sb.SetFieldsCount(2)
        self.sb.SetStatusWidths([-4, -1])
        self.sheet2.SetFocus()

        self.sheet1.load_project()
        self.sheet1.refresh_tabs()
        #self.sheet1.sheet2._test()
    
    def _view_ligand(self, event):
        dlg = wx.FileDialog(self, 'Select a PDB file to load', defaultDir=os.getcwd(), wildcard='PDB File|*.pdb')
    
        if dlg.ShowModal() == wx.ID_OK:
            lig = Ligand(str(dlg.GetPath()), os.path.basename(str(dlg.GetPath())))
            lig.Show(True)

        dlg.Destroy()
    
    
    def _show_settings(self, event):
        dlg = SettingsDialog(self)
        dlg.Show(True)
    
    def _show_about(self, event):
        dlg = AboutDialog(self)
        dlg.Show(True)
    
    
    def _show_help(self, event):
        dlg = HelpDialog(self)
        dlg.Show(True)
    
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


# ----------------------------------------------------------------------------
# Proton8 App
class Proton8(wx.App):
    outputWindowClass = ErrorHandler
    
    def OnInit(self):
         frame = MainFrame(None, -1, 'Proton8')
         #ErrorHandler.set_parent(frame)         
         frame.Show(True)
         frame.Centre()
         
         return True


# ----------------------------------------------------------------------------
# About Dialog
class AboutDialog(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, 'About')

        credits = """When using Proton8 please reference: Fisher et al., Acta Dxx, 20xx, xxx

Dependencies
------------
cctbx - http://cctbx.sourceforge.org
matplotlib - http://matplotlib.org
wxpython - http://wxpython.org

polygon - 
phenix.elbow
reduce
probe

Thanks
------
Nat Echols"""
            
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.sizer.Add(wx.StaticText(self, -1, 'Proton8 is developed by Stu Fisher'), 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(wx.StaticText(self, -1, 'fisher@ill.fr'), 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(wx.TextCtrl(self, -1, credits, style=wx.TE_MULTILINE, size=(450, 200)), 0, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(self.sizer)
        self.Fit()


# ----------------------------------------------------------------------------
# Settings Dialog
class SettingsDialog(wx.Dialog):

    @staticmethod
    def set_settings(s):
        SettingsDialog.s = s
    
    
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, 'Settings')

        self.sizer = wx.FlexGridSizer(cols=2, rows=0, hgap=5, vgap=5)

        self.sizer.Add(wx.StaticText(self, -1, 'Coot Path'), 0, wx.EXPAND)
        self._coot = FileBrowser(self, self.s.val('coot'), 'Select your COOT directory')
        self.sizer.Add(self._coot.sizer(), 0, wx.EXPAND)
            
        self.sizer.Add(wx.StaticText(self, -1, 'PHENIX Path'), 0, wx.EXPAND)
        self._phenix = FileBrowser(self, self.s.val('phenix'), 'Select your PHENIX directory', dir=True)
        self.sizer.Add(self._phenix.sizer(), 0, wx.EXPAND)
        
        self._ok = wx.Button(self, -1, 'Save')
        self._cb = wx.Button(self, -1, 'Close')
        self._cb.Bind(wx.EVT_BUTTON, self._on_close)
        self._ok.Bind(wx.EVT_BUTTON, self._save)
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_sizer.Add(self._ok)
        self.button_sizer.Add(self._cb)
            
            
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer.Add(self.sizer, 1, wx.EXPAND|wx.ALL, 5)
        self.main_sizer.Add(self.button_sizer, 0, wx.EXPAND|wx.ALL, 5)
        
        self.SetSizer(self.main_sizer)
        self.Fit()


    def _on_close(self, event):
        self.EndModal(0)
        self.Destroy()


    def _save(self, event):
        self.s.val('coot', self._coot.file())
        self.s.val('phenix', self._phenix.file())

        self._on_close()


# ----------------------------------------------------------------------------
# Help Dialog
class HelpDialog(wx.Frame):
    
    @staticmethod
    def set_settings(s):
        HelpDialog.s = s
    
    
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, 'Help', size=(700,500))

        self.toolbar = wx.ToolBar(self, style=wx.TB_3DBUTTONS|wx.TB_TEXT)
        close = self.toolbar.AddLabelTool(wx.ID_ANY, 'Close', wxtbx.bitmaps.fetch_icon_bitmap('actions', 'no'))
        self.toolbar.AddSeparator()
        home = self.toolbar.AddLabelTool(wx.ID_ANY, 'Home', wxtbx.bitmaps.fetch_icon_bitmap('apps', 'home'))
        back = self.toolbar.AddLabelTool(wx.ID_ANY, 'Back', wxtbx.bitmaps.fetch_icon_bitmap('actions', '1leftarrow'))
        forward = self.toolbar.AddLabelTool(wx.ID_ANY, 'Forward', wxtbx.bitmaps.fetch_icon_bitmap('actions', '1rightarrow'))
        
        self.Bind(wx.EVT_TOOL, self._on_close, close)
        self.Bind(wx.EVT_TOOL, self._home, home)
        self.Bind(wx.EVT_TOOL, self._back, back)
        self.Bind(wx.EVT_TOOL, self._forward, forward)
        
        
        self.SetToolBar(self.toolbar)
        self.toolbar.Realize()

        self.html = wx.html.HtmlWindow(self)
        self._home('')
        
    
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.html, 1, wx.EXPAND)
            
        self.SetSizer(self.sizer)


    def _on_close(self, event):
        self.Destroy()

    def _home(self, event):
        self.html.LoadPage(self.s.proot + 'Resources/help/index.html')

    def _back(self, event):
        self.html.HistoryBack()

    def _forward(self, event):
        self.html.HistoryForward()


# ----------------------------------------------------------------------------
# Coot Client and Magic Method
class CootClient:
    
    @staticmethod
    def set_p8(path):
        CootClient._p8p = path
    
    @staticmethod
    def set_start_coot(func):
        CootClient._start_coot = func
    
    def __init__(self):
        self._server = xmlrpclib.Server('http://localhost:41734')

    def __getattr__(self, name):
        if self._start_coot is not None:
            self._start_coot('')
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
