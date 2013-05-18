import wx
import wx.aui
import pickle
import os
import re
import glob
import time
import urllib
import shutil
import gzip
import json

from wxtbx import bitmaps, metallicbutton, icons
from iotbx import mtz, cif, reflection_file_reader

from Constants import *
from Shelx import MTZImporter, CIFImporter, PDBImporter
from Refinement import Refinement
from Project import Project
from Tab import Tab
from Processing import Summary

class Manager(Tab): 

    def __init__(self, nb):
        Tab.__init__(self, nb)

        self._tabs = wx.aui.AuiNotebook(self, -1, style=wx.NB_TOP, size=(850,750))
        self.sheet1 = Projects(self._tabs)
        
                
        self.sheet2 = Jobs(self._tabs)

        self._tabs.AddPage(self.sheet1, "Projects")
        self._tabs.AddPage(self.sheet2, "Job List")
            
        self.main = wx.BoxSizer(wx.HORIZONTAL)
        self.main.Add(self._tabs, 1, wx.EXPAND)
        
        self.SetSizer(self.main)
        
    def get_project(self):
        return self._project

    
    def load_project(self):
        self.sheet1.retrieve()
        
# ---------------------------------------------------------------------------
# Current Project Job List
class Jobs(Tab):
    
    @staticmethod
    def set_load_refinement(func):
        Jobs.load_refinement = func
    
    @staticmethod
    def set_new_refinement(func):
        Jobs.new_refinement = func

    @staticmethod
    def set_auto_refinement(func):
        Jobs.auto_refinement = func

    def __init__(self, nb):
        Tab.__init__(self, nb)
        
        self.job_list = wx.ListCtrl(self, -1, style=wx.LC_REPORT|wx.LC_SINGLE_SEL, size=(700, 400))
        self.job_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._load_job)
        
        titles = ['ID', 'Date', 'Title', 'Type', 'Status', 'R']
        sizes = [65,135,225,130,80,60]
        for i,t in enumerate(titles):
            self.job_list.InsertColumn(i, t, width=sizes[i])

        new = metallicbutton.MetallicButton(self, -1, 'New', '', bitmaps.fetch_icon_bitmap("actions", "window_new"), size=(120,40))
        load = metallicbutton.MetallicButton(self, -1, 'Load', '', bitmaps.fetch_icon_bitmap("actions", "fileopen"), size=(120,40))
        delete = metallicbutton.MetallicButton(self, -1, 'Delete', '', bitmaps.fetch_icon_bitmap("actions", "fileclose"), size=(120,40))
        sum = metallicbutton.MetallicButton(self, -1, 'Summary', '', bitmaps.fetch_icon_bitmap("actions", "info"), size=(120,40))
                
        self.Bind(wx.EVT_BUTTON, self._new_job, new)
        self.Bind(wx.EVT_BUTTON, self._load_job, load)
        self.Bind(wx.EVT_BUTTON, self._delete_job, delete)
        self.Bind(wx.EVT_BUTTON, self._show_summary, sum)
                
        import_cif = metallicbutton.MetallicButton(self, -1, 'Import HKL', '', icons.hkl_file.GetBitmap(), size=(120,40))
        import_pdb = metallicbutton.MetallicButton(self, -1, 'Import PDB', '', icons.pdb_file.GetBitmap(), size=(120,40))
        rcsb_dl = metallicbutton.MetallicButton(self, -1, 'RCSB PDB', '', bitmaps.fetch_icon_bitmap("actions", "down"), size=(120,40))
        self.Bind(wx.EVT_BUTTON, self._import_pbd, import_pdb)
        self.Bind(wx.EVT_BUTTON, self._import_cif, import_cif)
        self.Bind(wx.EVT_BUTTON, self._download_files, rcsb_dl)
        
        self.sidebar = wx.BoxSizer(wx.VERTICAL)
        self.sidebar.Add(new, 0, wx.EXPAND | wx.ALL, 5)
        self.sidebar.Add(load, 0, wx.EXPAND | wx.ALL, 5)
        self.sidebar.Add(sum, 0, wx.EXPAND | wx.ALL, 5)
        self.sidebar.Add(delete, 0, wx.EXPAND | wx.ALL, 5)
        self.sidebar.AddSpacer(20)
                
        self.sidebar.Add(import_cif, 0, wx.EXPAND | wx.ALL, 5)
        self.sidebar.Add(import_pdb, 0, wx.EXPAND | wx.ALL, 5)
        self.sidebar.AddSpacer(10)
        self.sidebar.Add(rcsb_dl, 0, wx.EXPAND | wx.ALL, 5)
                
        self.main = wx.BoxSizer(wx.HORIZONTAL)
        self.main.Add(self.job_list, 0, wx.EXPAND|wx.ALL, 5)
        self.main.Add(self.sidebar, 0, wx.EXPAND|wx.ALL, 5)
        
        self.SetSizer(self.main)
    
    
    @Tab.wproj
    def _show_summary(self, event):
        ids, files, dirs = self._get_inputs()
        sel = self.job_list.GetFirstSelected()
        dlg = Summary(files[sel], dirs[sel], self._project.root())
        
        dlg.Show()
            
    def _test(self):       
        self.job_list.SetItemState(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        self._load_job('')    

    @Tab.wproj
    def _delete_job(self, event):
        ids, files, dirs = self._get_inputs()

        sel = self.job_list.GetFirstSelected()
        if sel > -1:
            shutil.rmtree(self._project.root() + '/' + dirs[sel])
            
        self._project.job_count(-1)
            
        self.refresh_tabs()
    
    @Tab.wproj
    def _load_job(self, event):
        if hasattr(self, 'load_refinement'):
            ids, files, dirs = self._get_inputs()
            sel = self.job_list.GetFirstSelected()
            
            if sel > -1:
                self.load_refinement(str(files[sel]), dirs[sel])

    @Tab.wproj
    def _new_job(self, event):
        if hasattr(self, 'new_refinement'):
            self.new_refinement()

    @Tab.wproj
    def _auto_job(self, event):
        if hasattr(self, 'auto_refinement'):
            self.auto_refinement()

    @Tab.wproj
    def refresh(self):
        #print 'refreshing job list...'
            
        self.job_list.DeleteAllItems()
        
        ids, files, dirs = self._get_inputs()
        for i,d in enumerate(files):
            r = pickle.load(open(d, 'rb'))
            p = r.parameters()
            
            self.job_list.InsertStringItem(i, str(ids[i]))
            
            p['time'] = time.strftime('%H:%M %d-%m-%Y', time.localtime(p['time']))
            self.job_list.SetStringItem(i, 1, p['time'])
            self.job_list.SetStringItem(i, 2, p['title'])
            self.job_list.SetStringItem(i, 3, REFINEMENT_TYPES[p['type']])
            self.job_list.SetStringItem(i, 4, p['status'])
            
            p['r'] = 'N/A' if p['r'] == -1 else (p['r'] if type(p['r']) == type(str()) else str('%.4f' % p['r']))
            self.job_list.SetStringItem(i, 5, p['r'])
        
    #@Tab.wproj
    #def _import_mtz(self, event):
    #    dlg = NewMTZ(self, -1, 'Import MTZ File')
    #    val = dlg.ShowModal()
        
    #    if val == 1:
    #        mtz, f, sigf, rfree = dlg.get_values()
            
    #        if f and sigf and rfree:
    #            MTZImporter(mtz, f, sigf, rfree, self._project.root())
            
    #    dlg.Destroy()
        
    @Tab.wproj
    def _import_pbd(self, event):
        dlg = NewPDB(self, -1, 'Import PDB File')
        dlg.CentreOnParent()
        val = dlg.ShowModal()
        
        if val == 1:
            print dlg.get_file(), self._project.root()
            p = PDBImporter(dlg.get_file(), self._project.root(), self)
        
            if p.finished():
                self.set_status('PDB file sucessfully imported')
        
        dlg.Destroy()

    @Tab.wproj
    def _import_cif(self, event):
        dlg = NewCIF(self, -1, 'Import CIF File')
        val = dlg.ShowModal()
        
        if val == 1:
            cif, f_lab, r_lab = dlg.get_values()
            if cif and f_lab and r_lab:
                c = CIFImporter(cif, f_lab, r_lab, self._project.root())

                if c.finished():
                    self.set_status('Reflection file successfully imported')
            
        dlg.Destroy()

    @Tab.wproj
    def _download_files(self, events):
        dlg = Retrieve(self, -1, 'Download from RCSB', self._project.root())
        val = dlg.ShowModal()
        dlg.Destroy()

    def _get_inputs(self):
        id = []
        files = []
        dirs = []
    
        for f in sorted(os.listdir(self._project.root()), key=self.sort_dirs):
            m = re.match('(\d+)_', f)
            if m:
                res = sorted(glob.glob(self._project.root() + os.sep + f + os.sep + '*.dat'))
                if len(res) > 0:
                    id.append(m.group(1))
                    files.append(res[0])
                    dirs.append(f)
                
        return id, files, dirs
        
    def sort_dirs(self, item):
        l = item.split('_')
        if l[0].isdigit():
            i = int(l[0])
        else:
            i = item
        return i
        

# ----------------------------------------------------------------------------
# Project Manager
class Projects(Tab):

    def __init__(self, nb):
        Tab.__init__(self, nb)
        self.project_list = wx.ListCtrl(self, -1, style=wx.LC_REPORT, size=(700, 400))
        self.project_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._load_project)
        
        self._il = wx.ImageList(16,16)
        self._il.Add(bitmaps.fetch_icon_bitmap("actions", "agt_action_success", scale=(16,16)))
        self.project_list.SetImageList(self._il, wx.IMAGE_LIST_SMALL)        

        titles = ['', 'Title', '# Jobs', 'Last Action']
        sizes = [20,400, 100,140]
        for i,t in enumerate(titles):
            self.project_list.InsertColumn(i, t)
            self.project_list.SetColumnWidth(i, sizes[i])
        
        self.sidebar = wx.BoxSizer(wx.VERTICAL)
        
        new = metallicbutton.MetallicButton(self, -1, 'New', '', bitmaps.fetch_icon_bitmap("actions", "folder_new"), size=(120,40))
        delete = metallicbutton.MetallicButton(self, -1, 'Delete', '', bitmaps.fetch_icon_bitmap("actions", "fileclose"), size=(120,40))
        load = metallicbutton.MetallicButton(self, -1, 'Load', '', bitmaps.fetch_icon_bitmap("actions", "folder"), size=(120,40))
         
        self.Bind(wx.EVT_BUTTON, self._new_project, new)
        self.Bind(wx.EVT_BUTTON, self._load_project, load)
        self.Bind(wx.EVT_BUTTON, self._delete_project, delete)
                
        self.sidebar.Add(new, 0, wx.EXPAND|wx.ALL, 5)
        self.sidebar.Add(load, 0, wx.EXPAND|wx.ALL, 5)
        self.sidebar.Add(delete, 0, wx.EXPAND|wx.ALL, 5)
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.project_list, 0, wx.EXPAND | wx.ALL, 5)
        self.sizer.Add(self.sidebar, 0, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(self.sizer)
        
        
        
    def retrieve(self):
        print self.s.current
        if self.s.current is not None:
            if os.path.exists(self.s.current):
                #Tab._project = pickle.load(open(self.s.current + '/.proton8/project.pkl', 'rb'))
                Tab._project = Project(self.s.current)
                self._update_sb('Project: ' + Tab._project.title(), 1)
            else:
                self._update_sb('Project: None', 1)
                self.refresh()
        else:
            self._update_sb('Project: None', 1)
            self.refresh()


    def get_project(self):
        return self._project

    def _delete_project(self, event):
        pass

    def _new_project(self, event):
        dlg = NewProject(self, -1, 'New Project')
        v = dlg.ShowModal()
        
        if v:
            title, root = dlg.vals()
            self.s.add_project(root, title)
            self.refresh_tabs()

    def _load_project(self, event):
        sel = self.project_list.GetFirstSelected()
    
        print self.s.projects, sel, self.s.current
        
        if sel < len(self.s.projects):
            self.s.load_project(self.s.projects[sel])
            self.refresh_tabs()
            self._update_sb('Project: ' + Tab._project.title(), 1)
        
    def refresh(self):
        print 'refreshing project list...'
            
        self.project_list.DeleteAllItems()
       
        
        i = 0
        for r in self.s.projects:
            if os.path.exists(r + '/.proton8/project.json'):
                proj = Project(r) 

                t = time.strftime('%H:%M %d-%m-%Y', time.localtime(proj.last_time())) if proj.last_time() > -1 else 'N/A'
                self.project_list.InsertStringItem(i, '')
                self.project_list.SetStringItem(i, 1, str(proj.title()))
                self.project_list.SetStringItem(i, 2, str(proj.job_count()))
                self.project_list.SetStringItem(i, 3, t)
                if self.s.current == r:
                    self.project_list.SetItemImage(i, 0)
                i +=1


class NewProject(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title)

        self._root = None
        
        self.input_sizer = wx.FlexGridSizer(cols=2, rows=0, vgap=5, hgap=5)
            
        self.input_sizer.Add(wx.StaticText(self, -1, 'Title'), 0, wx.EXPAND)
        self._title = wx.TextCtrl(self, -1, '')
        self.input_sizer.Add(self._title, 0, wx.EXPAND)
            
        self.input_sizer.Add(wx.StaticText(self, -1, 'Project Root'), 0, wx.EXPAND)
        self._root_sizer = wx.BoxSizer(wx.HORIZONTAL)
        browse = wx.Button(self, -1, 'Browse')
        browse.Bind(wx.EVT_BUTTON, self._get_root)
        self._root_lab = wx.TextCtrl(self, -1, '', size=(200,20))
        self._root_sizer.Add(self._root_lab, 0, wx.EXPAND)
        self._root_sizer.Add(browse, 0, wx.EXPAND)
        
        self.input_sizer.Add(self._root_sizer, 0, wx.EXPAND)
            
        self._buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._buttons.Add(wx.Button(self, 0, 'Create'), 0, wx.EXPAND|wx.ALL, 5)
        self._buttons.Add(wx.Button(self, 1, 'Cancel'), 0, wx.EXPAND|wx.ALL, 5)
                
        self.Bind(wx.EVT_BUTTON, self._create, id=0)
        self.Bind(wx.EVT_BUTTON, self._cancel, id=1)    
            
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.input_sizer, 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(self._buttons, 0, wx.EXPAND|wx.ALL, 5)
        
        self.SetSizer(self.sizer)
        self.Fit()
        
    def vals(self):
        return self._title.GetValue(), self._root

    def _get_root(self, event):
        dlg = wx.DirDialog(self, "Select a Project Directory", os.getcwd())
        if dlg.ShowModal() == wx.ID_OK:
            self._root = str(dlg.GetPath())
            
            self._root_lab.SetLabel(self._root)
            
        dlg.Destroy()
        
    def _create(self, event):
        self.EndModal(1)
        
    def _cancel(self, event):
        self.EndModal(0)
        
# ----------------------------------------------------------------------------
# Retrieve PDB/SF from PDB Dialog
class Retrieve(wx.Dialog):
    def __init__(self, parent, id, title, root):
        wx.Dialog.__init__(self, parent, id, title)
        
        self._root = str(root)
        
        self._pdb_label = wx.StaticText(self, -1, 'PDB Code')
        self._pdb_entry = wx.TextCtrl(self, -1)
        
        self._pdb_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._pdb_sizer.Add(self._pdb_label, 0, wx.EXPAND|wx.ALL, 5)
        self._pdb_sizer.Add(self._pdb_entry, 0, wx.EXPAND|wx.ALL, 5)
        
        self._gauge_label = wx.StaticText(self, -1, '')
        self._gauge = wx.Gauge(self, -1, 9)
        
        self._gauge.Hide()
        self._gauge_label.Hide()
        
        self._buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._buttons.Add(wx.Button(self, 0, 'Import'), 0, wx.EXPAND|wx.ALL, 5)
        self._buttons.Add(wx.Button(self, 1, 'Close'), 0, wx.EXPAND|wx.ALL, 5)
                
        self.Bind(wx.EVT_BUTTON, self._import, id=0)
        self.Bind(wx.EVT_BUTTON, self._close, id=1)      
        
        self.main = wx.BoxSizer(wx.VERTICAL)
        self.main.Add(self._pdb_sizer, 0, wx.EXPAND|wx.ALL, 5)
        self.main.Add(self._gauge_label, 0, wx.EXPAND|wx.ALL, 5)
        self.main.Add(self._gauge, 0, wx.EXPAND|wx.ALL, 5)
        self.main.Add(self._buttons, 0, wx.EXPAND|wx.ALL, 5)
        
        self.SetSizer(self.main)
        self.Fit()
        
        
    def _import(self, event):
        self._gauge.Show()
        self._gauge_label.Show()
        self.Fit()
        
        pdb = str(self._pdb_entry.GetValue())
        
        if not os.path.exists(self._root + '/temp'):
            os.mkdir(self._root + '/temp')
        
        self._set_status(0, 'Downloading PDB')
        urllib.urlretrieve('http://www.rcsb.org/pdb/files/' + pdb.lower() + '.pdb.gz', self._root + '/temp/' + pdb.lower() + '.pdb.gz')
        self._set_status(1, 'Uncompressing PDB')
        out = open(self._root + '/temp/' + pdb.lower() + '.pdb', 'wb')
        out.write(gzip.open(self._root + '/temp/' + pdb.lower() + '.pdb.gz', 'rb').read())
        out.close()
        self._set_status(2, 'Converting PDB to INS')
        PDBImporter(self._root + '/temp/' + pdb.lower() + '.pdb', self._root)
                
        self._set_status(3, 'Downloading SFs')
        urllib.urlretrieve('http://www.rcsb.org/pdb/files/r' + pdb.upper() + 'sf.ent.gz', self._root + '/temp/r' + pdb.upper() + 'sf.ent.gz')
        self._set_status(4, 'Uncompressing SFs')
        sff = self._root + '/temp/' + pdb.lower() + '.cif'
                
        out = open(sff, 'wb')
        out.write(gzip.open(self._root + '/temp/r' + pdb.upper() + 'sf.ent.gz', 'rb').read())
        out.close()
        
        self._set_status(5, 'Finding Columns')
        if os.path.exists(sff):
            m = reflection_file_reader.any_reflection_file(sff)
            fs = []
            rs = []
            for col in m.as_miller_arrays():
                if (col.is_xray_intensity_array() or col.is_xray_amplitude_array()) and not col.anomalous_flag():
                    fs.append(col.info().label_string())
                elif col.info().label_string().find('status') > -1:
                    rs.append(col.info().label_string())
        
            self._set_status(6, 'Converting CIF to HKL')

            if len(fs) > 0:
                for f in fs:
                    if len(rs) > 0:
                        CIFImporter(sff, f, rs[0], self._root)
                    else:
                        CIFImporter(sff, f, '', self._root, True)

        self._set_status(7, 'Cleaning Up...')
        os.remove(self._root + '/temp/' + pdb.lower() + '.pdb.gz')
        os.remove(self._root + '/temp/' + pdb.lower() + '.pdb')
        os.remove(self._root + '/temp/r' + pdb.upper() + 'sf.ent.gz')
        os.remove(self._root + '/temp/' + pdb.lower() + '.cif')
            
        self._set_status(8, 'Finished')
        self._close('')
        
    
    def _close(self, event):
        self.EndModal(1)
        
    def _set_status(self, point, text):
        self._gauge_label.SetLabel(text)
        self._gauge.SetValue(point)

        
# ----------------------------------------------------------------------------
# Import MTZ Dialog
class NewMTZ(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title)#, size=(330,340))
        
        self._mtz = None
        
        self._input_sizer = wx.GridSizer(cols=2, rows=5, hgap=5, vgap=5)
        self._inputs = [
            wx.StaticText(self, -1, 'MTZ File'),
            wx.Button(self, -1, 'Browse'),
            wx.StaticText(self, -1, ''),
            wx.StaticText(self, -1, ''),                        
            wx.StaticText(self, -1, 'Reflections'),
            wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY),
            wx.StaticText(self, -1, 'Std Deviations'),
            wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY),            
            wx.StaticText(self, -1, 'FreeR Set'),
            wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY),
        ]
        
        self._inputs[1].Bind(wx.EVT_BUTTON, self._get_mtz)
        
        for i in range(len(self._inputs)):
            self._input_sizer.Add(self._inputs[i], 0, wx.EXPAND|wx.TOP|wx.LEFT, 5)

        self._buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._buttons.Add(wx.Button(self, 0, 'Import'), 0, wx.EXPAND|wx.ALL, 5)
        self._buttons.Add(wx.Button(self, 1, 'Cancel'), 0, wx.EXPAND|wx.ALL, 5)
                
        self.Bind(wx.EVT_BUTTON, self._import, id=0)
        self.Bind(wx.EVT_BUTTON, self._close, id=1)          
        
        self.main = wx.BoxSizer(wx.VERTICAL)
        self.main.Add(self._input_sizer)
        self.main.Add(self._buttons)        
        
        self.SetSizer(self.main)
        

    def _close(self, event):
        self.EndModal(0)

    def _import(self, event):
        self.EndModal(1)
        
    def get_values(self):
        return self._mtz, self._inputs[5].GetValue(), self._inputs[7].GetValue(), self._inputs[9].GetValue()
        
    def _get_mtz(self, event):
        dlg = wx.FileDialog(self, "Select an MTZ File", os.getcwd(), "", "*.mtz", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self._mtz = str(dlg.GetPath())
            self._inputs[3].SetLabel(self._mtz)
            #self._inputs[13].SetLabel(self._mtz)
            
            m = mtz.object(self._mtz)
            
            self._inputs[5].Clear()
            self._inputs[7].Clear()
            self._inputs[9].Clear()
            
            for col in m.columns():
                if col.type() == 'J' or col.type() == 'F':
                    self._inputs[5].Append(col.label())

                if col.type() == 'Q':
                    self._inputs[7].Append(col.label())
                
                if col.type() == 'I':
                    self._inputs[9].Append(col.label())
            
        dlg.Destroy()
        

# ----------------------------------------------------------------------------
# Import Reflections Dialog
class NewCIF(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title)#, size=(330,340))
        
        self._cif = None
        
        self._browse = wx.Button(self, -1, 'Browse', size=(70,25))
        self._browse.Bind(wx.EVT_BUTTON, self._get_cif)
        self._label = wx.TextCtrl(self, -1, size=(250,25))
        
        self._browse_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._browse_sizer.Add(self._label)
        self._browse_sizer.Add(self._browse, wx.EXPAND)
        
        self._input_sizer = wx.FlexGridSizer(cols=2, rows=3, hgap=5, vgap=5)
        self._inputs = [
            wx.StaticText(self, -1, 'Reflection'),
            self._browse_sizer,
            wx.StaticText(self, -1, 'F, SigF'),
            wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY),
            wx.StaticText(self, -1, 'FreeR'),
            wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY),
        ]
        
        for i in range(len(self._inputs)):
            self._input_sizer.Add(self._inputs[i], 0, wx.EXPAND)

        self._buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._buttons.Add(wx.Button(self, 0, 'Import'), 0, wx.EXPAND|wx.ALL, 5)
        self._buttons.Add(wx.Button(self, 1, 'Cancel'), 0, wx.EXPAND|wx.ALL, 5)
                
        self.Bind(wx.EVT_BUTTON, self._import, id=0)
        self.Bind(wx.EVT_BUTTON, self._close, id=1)          
        
        self.main = wx.BoxSizer(wx.VERTICAL)
        self.main.Add(self._input_sizer, 0, wx.EXPAND|wx.ALL, 5)
        self.main.Add(self._buttons, 0, wx.EXPAND|wx.LEFT, 65)
        
        self.SetSizer(self.main)
        self.Fit()
        

    def _close(self, event):
        self.EndModal(0)

    def _import(self, event):
        self.EndModal(1)
        
    def get_values(self):
        return self._cif, self._inputs[3].GetValue(), self._inputs[5].GetValue()
        
    def _get_cif(self, event):
        dlg = wx.FileDialog(self, "Select a Reflection File", os.getcwd(), "", "CIF File (*.cif)|*.cif|MTZ File (*.mtz)|*.mtz", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self._cif = str(dlg.GetPath())
            self._label.SetLabel(self._cif)
            
            #m = cif.reader(self._cif)
            print self._cif, type(self._cif)
            m = reflection_file_reader.any_reflection_file(self._cif)
            
            self._inputs[3].Clear()
            self._inputs[5].Clear()
            
            for col in m.as_miller_arrays():
                if col.is_xray_intensity_array() or col.is_xray_amplitude_array():
                    self._inputs[3].Append(col.info().label_string())
                else:
                    self._inputs[5].Append(col.info().label_string())
            
        dlg.Destroy()


# ----------------------------------------------------------------------------
# Import PDB File  
class NewPDB(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title)#, size=(330,340))
        
        self._mtz = None
        
        self._inputs = [
            wx.StaticText(self, -1, 'PDB File'),
            wx.Button(self, -1, 'Browse'),
            wx.TextCtrl(self, -1, '', size=(200,20)),
        ]
        
        self._inputs[1].Bind(wx.EVT_BUTTON, self._get_pdb)
        
        self.file_box = wx.BoxSizer(wx.HORIZONTAL)
        self.file_box.Add(self._inputs[2], 0, wx.EXPAND)
        self.file_box.Add(self._inputs[1], 0, wx.EXPAND)

        self._input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._input_sizer.Add(self._inputs[0], 0, wx.EXPAND|wx.TOP|wx.LEFT, 5)
        self._input_sizer.Add(self.file_box, 0, wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, 5)

        self._buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._buttons.Add(wx.Button(self, 0, 'Import'), 0, wx.EXPAND|wx.ALL, 5)
        self._buttons.Add(wx.Button(self, 1, 'Cancel'), 0, wx.EXPAND|wx.ALL, 5)
                
        self.Bind(wx.EVT_BUTTON, self._import, id=0)
        self.Bind(wx.EVT_BUTTON, self._close, id=1)          
        
        self.main = wx.BoxSizer(wx.VERTICAL)
        self.main.Add(self._input_sizer, 0, wx.EXPAND|wx.ALL, 5)
        self.main.Add(self._buttons, 0, wx.EXPAND|wx.LEFT, 70)
        
        self.SetSizer(self.main)
        self.Fit()
        
    def _get_pdb(self, event):
        dlg = wx.FileDialog(self, "Select a PDB File", os.getcwd(), "", "*.pdb", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self._pdb = str(dlg.GetPath())
            self._inputs[2].SetLabel(self._pdb)
            
        dlg.Destroy()


    def _close(self, event):
        self.EndModal(0)

    def _import(self, event):
        self.EndModal(1)
        
    def get_file(self):
        return self._pdb
 