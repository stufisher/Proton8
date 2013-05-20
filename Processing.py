import wx
import wx.aui
import wx.lib.scrolledpanel as scrolled
import math
import time
import glob
import os
import re
import pickle
import shutil

from iotbx.shelx import hklf, crystal_symmetry_from_ins
from mmtbx import polygon
from iotbx import pdb, phil
from wxtbx import polygon as pgn, polygon_db_viewer, metallicbutton, bitmaps
from cctbx.array_family import flex

from Constants import *
from Refinement import Refinement
from Project import Project
from Shelx import Shelx
import ShelxData
from Tab import Tab
from Validation import Validation
from BondLengths import BondLengths
from AutoProcess import AutoProcessManager, AutoProcess
from Controls import FileBrowser

import matplotlib
matplotlib.use('WXAgg', False)

from matplotlib.figure import Figure
from matplotlib.ticker import FormatStrFormatter
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas

DEBUG = 1

def debug_print(text):
    if DEBUG:
        print text

# ----------------------------------------------------------------------------
# The Process Manager
class ProcessManager(Tab):

    def __init__(self, nb):
        Tab.__init__(self, nb)
        
        Holder.set_finished_callback(self._job_finished)
                
        self._tabs = wx.aui.AuiNotebook(self, -1, size=(700,750))
        
        self.main = wx.BoxSizer(wx.HORIZONTAL)
        self.main.Add(self._tabs, 1 , wx.EXPAND)
        self.SetSizer(self.main)

        self._auto_manager = AutoProcessManager()
        AutoProcess.set_start_refinement(self.start_new_refinement)
        
        self._running = 0

    def _r_act(self, event):
        id = event.GetId()
        fns = ['abort', 'view_log', 'load_coot']
        
        if id < len(fns):
            pid = self._tabs.GetSelection()
            
            if pid > -1:
                page = self._tabs.GetPage(pid)
                getattr(page, fns[id])()

        
    def _job_finished(self, id, status):
        self._auto_manager.refinement_finished(id, status)
        self.refresh_tabs()
                  
        self._running -= 1
        
        if self._running == 0:
            self.set_status('All Jobs Finished')
        else:
            self.set_status(str(self._running) + ' Job(s) Running')
        
        
    def _load_refinement(self, event):
        inputs, files = self._get_inputs('dat')
        dlg = wx.SingleChoiceDialog(self, 'Select a refinement to load:', 'Load Refinement', inputs, wx.CHOICEDLG_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            file = files[dlg.GetSelection()]
            
            tab = Holder(self._tabs)
            tab.load_refinement(file)
            self._tabs.AddPage(tab, inputs[dlg.GetSelection()], True)
            tab.SetFocus()
            
        dlg.Destroy() 

    
    def load_refinement(self, file, title):
        tab = Holder(self._tabs)
        tab.load_refinement(file)
        self._tabs.AddPage(tab, title, True)
        tab.SetFocus()
        self.GetParent().SetSelection(1)
    
    def new_refinement(self):
        self._new_refinement('')
    
    def auto_refinement(self):
        pass
    
    def _new_refinement(self, event):
        inputs, files = self._get_inputs()
        inputs2, files2 = self._get_root_files('ins')
        reflns, files3 = self._get_root_files()
        
        inputs = inputs2 + inputs
        files  = files2 + files
    
        dlg = NewRefinement(self, -1, 'New Refinement', inputs, reflns, files, files3)
        val = dlg.ShowModal()
        
        if val == 1:
            title, refln, input, type, cycles, res, resl, options = dlg.get_values()
            
            if options['auto']:
                self._auto_manager.new(title, files3[refln], files[input], type, cycles, res, resl, options)
            else:
                self.start_new_refinement(title, files3[refln], files[input], type, cycles, res, resl, options)

        dlg.Destroy()
            
            
    def start_new_refinement(self, title, refln, input, type, cycles, res, resl, options):
        id = self._get_next_jobid()
        
        os.mkdir(self._project.root() + '/' + str(id) + '_' + REFINEMENT_TYPES[type])
        #root = self._project.root() + '/' + str(id) + '_' + REFINEMENT_TYPES[type] + '/'+ str(id) + '_' + REFINEMENT_TYPES[type].lower()
        root = './' + str(id) + '_' + REFINEMENT_TYPES[type] + '/'+ str(id) + '_' + REFINEMENT_TYPES[type].lower()
        file = root + '.ins'
        
        print os.getcwd()
        
        shutil.copy2(input, file)
        shutil.copy2(refln, root + '.hkl')
        
        if type == FULL_MATRIX:
            shutil.copy2(input.replace('.res', '.pdb'), root + '_start.pdb')
        
        print input, file
        ins = Shelx(file)
        ins.set_type(type, cycles, options)
        ins.set_res(res, resl)
        ins.set_hklf(refln.find('_F.hkl') > -1)
        ins.write()
        
        self._running += 1
        self.set_status(str(self._running) + ' Job(s) Running')
        
        self._project.action(REFINEMENT_TYPES[type])
        
        tab = Holder(self._tabs)
        tab.start_refinement(type, root, title, res, resl, cycles, input, refln, id, options)
        
        self._tabs.AddPage(tab, str(id) + '_' + REFINEMENT_TYPES[type], True)
        tab.SetFocus()
        self.GetParent().SetSelection(1)
            
        return id, root
    
    def _get_next_jobid(self):
        last = 0
        for f in os.listdir(self._project.root()):
            m = re.match('(\d+)_', f)
            if m:
                if int(m.group(1)) > last:
                    last = int(m.group(1))
                
        return last + 1
            
    
    def _get_inputs(self, type='res'):
        inputs = []
        files = []
    
        for f in sorted(os.listdir(self._project.root()), key=self.sort_dirs):
            m = re.match('(\d+)_', f)
            if m:
                types = ['res', 'ins'] if type == 'res' else [type]
                for t in types:
                    res = glob.glob(self._project.root() + os.sep + f + os.sep + '*.' + t)
                    for fl in res:
                        if os.path.basename(fl) == (f.lower() + '.ins'):
                            inputs.append(f+'/Input')
                        elif os.path.basename(fl) == (f.lower() + '.res'):
                            inputs.append(f+'/Output')
                        else:
                            inputs.append(fl.replace(self._project.root() + os.sep, ''))
                    
                        files.append(fl)
                
        return inputs, files
    
    def sort_dirs(self, item):
        l = item.split('_')
        if l[0].isdigit():
            i = int(l[0])
        else:
            i = item
        return i
    
    def _get_root_files(self, type='hkl'):
        res = glob.glob(self._project.root() + '/*.' + type)
        names = [ os.path.basename(r) for r in res]
        
        return names, res


# ----------------------------------------------------------------------------
# A Process Tab
class Process(Tab): 
    
    _finished_callback = None
    
    def __init__(self, nb):
        Tab.__init__(self, nb)
        
        Refinement.set_proot(self.s.proot)
        
        # plot
        self.dpi = 100
        self.fig = Figure((5.0, 4.0), dpi=self.dpi)
        col = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND)
        self.fig.patch.set_facecolor((col[0]/255.0, col[1]/255.0, col[2]/255.0))
        self.canvas = FigCanvas(self, -1, self.fig)
        self.ax1 = self.fig.add_subplot(111)
        self.ax1.set_position([0.115,0.17,0.80,0.79])
        self.ax2 = self.ax1.twinx()
        self.ax2.set_position([0.115,0.17,0.80,0.79])
        self._clear_figure()
                
        # stats
        self.stats_sizer = wx.FlexGridSizer(cols=2, rows=9, hgap=5, vgap=5)
        self._labels = [
            wx.StaticText(self, -1, 'Title'),
            wx.StaticText(self, -1, 'Status'),
            wx.StaticText(self, -1, 'Cycle'),
            wx.StaticText(self, -1, 'Resolution (A)'),
            wx.StaticText(self, -1, 'R-work (%)'),
            wx.StaticText(self, -1, 'R-free (%)'),
            wx.StaticText(self, -1, '# of Reflections'),
            wx.StaticText(self, -1, 'Parameters'),
            wx.StaticText(self, -1, 'Data:Parameter')
        ]
        
        self._labels[0].Wrap(200)
        self._values = [ wx.StaticText(self, -1, '') for x in range(len(self._labels)) ]
        
        rows = [1,2,3,4,6]
        for i in range(len(self._labels)):
            self.stats_sizer.Add(self._labels[i], 0, wx.EXPAND|wx.TOP, i in rows and 15 or 5)
            self.stats_sizer.Add(self._values[i], 0, wx.EXPAND|wx.TOP, i in rows and 15 or 5)
        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.stats_sizer, 0, wx.ALL, 10)
                
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.vbox.Add(self.button_sizer, 0, wx.EXPAND|wx.CENTER, 10)
                
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox.Add(self.vbox, 1, wx.EXPAND|wx.ALL, 10)
        self.hbox.Add(self.canvas, 4, wx.EXPAND|wx.ALL, 10)
    
        self.SetSizer(self.hbox)
        self.hbox.Fit(self)
        
        self._refinement = None
    
    def set_finished_callback(self, func):
        self._finished_callback = func
    
    def view_log(self, event):
        if self._refinement is not None:
            p = self._refinement.parameters()
            log = p['input'] + '.log'
            
            if os.path.exists(log):
                dlg = LogFile(self, -1, 'Log File Output for Job ' + str(p['id']), log)
                dlg.Show(True)
            
    def load_coot(self, event):
        if self._refinement is not None:
            p = self._refinement.parameters()        
            if 'input' in p:
                self._coot_client.load_refinement(p['input'])
    
    def _clear_figure(self):
        self.ax1.cla()
        self.ax2.cla()
            
        self.ax1.set_ylabel('wR2', fontsize=9)
        self.ax1.tick_params(labelsize=8)
        self.ax1.yaxis.set_major_formatter(FormatStrFormatter('%5.3f'))
        
        self.ax2.tick_params(labelsize=8)
        self.ax2.yaxis.set_major_formatter(FormatStrFormatter('%4.1f'))

        self.ax2.set_ylabel('GooF', fontsize=9)        
    
    def load_refinement(self, file):
        self._refinement = pickle.load(open(file))
        self._clear_figure()
        self._refinement_cycle()
    
        log = metallicbutton.MetallicButton(self, -1, 'View Log', '', bitmaps.fetch_icon_bitmap("mimetypes", "log"), size=(105, 34))
        coot = metallicbutton.MetallicButton(self, -1, 'View In Coot', '', bitmaps.fetch_icon_bitmap("custom", "coot"), size=(105, 34))
        
        self.Bind(wx.EVT_BUTTON, self.view_log, log)
        self.Bind(wx.EVT_BUTTON, self.load_coot, coot)
        self.button_sizer.Add(log, 0, wx.EXPAND|wx.ALL, 2)
        self.button_sizer.Add(coot, 0, wx.EXPAND|wx.ALL, 2)
    
        self.Fit()
    
    def start_refinement(self, type, root, title, res, resl, cycles, ins, hkl, id, options):
        abort = metallicbutton.MetallicButton(self, -1, 'Abort', '', bitmaps.fetch_icon_bitmap("actions", "stop"), size=(105, 34))
        self.Bind(wx.EVT_BUTTON, self.abort, abort)
        self.button_sizer.Add(abort, 0, wx.EXPAND|wx.ALL, 2)
        self.Fit()
        
        self._refinement = Refinement(self, type, root, title, res, resl, cycles, ins, hkl, id, options)
        self._refinement.set_callbacks(self._refinement_started, self._refinement_running, self._refinement_cycle, self._refinement_finished, self._error_dialog)
    
    def abort(self, event=''):
        if self._refinement:
            self._refinement.abort()
    
    def _error_dialog(self, log):
        #dlg = wx.MessageDialog(self, 'Shelx failed with the following message:\n' + str(log), 'Shelxl Error', wx.OK|wx.ICON_ERROR)
        dlg = ShelxError(self, log)
        dlg.ShowModal()
        #dlg.Destroy()
            
    def _refinement_started(self):
        debug_print('starting shelx...')
        self._refinement_cycle()
        
    def _refinement_running(self, text):
        pass
        #self._set_sb(text)
        
    def _refinement_finished(self):
        self._refinement_cycle()
        debug_print('process finished...')
        
        #if hasattr(self, '_finished_callback'):
        if self._finished_callback is not None:
            self._finished_callback()
        
    def _refinement_cycle(self):
        p = self._refinement.parameters()
        l = p['last_cycle']
        
        debug_print('new cycle...')
        self._values[0].SetLabel(p['title'])
        self._values[1].SetLabel(p['status'])
        self._values[2].SetLabel(str(l) + ' of ' + str(p['total_cycles'] + 1))
        self._values[3].SetLabel(str(p['res']) + ' - ' + (str(p['resl'])  if 'resl' in p else '10'))
        self._values[5].SetLabel(str('' if p['rfree'] == -1 else "%.4f" % p['rfree']))
        self._values[4].SetLabel(str(p['r'] if type(p['r']) == type(str()) else "%.4f" % p['r']))
        
        if l > 0:
            self._values[6].SetLabel(str(p['cycles'][l][2]))
            self._values[7].SetLabel(str(p['cycles'][l][3]))
            self._values[8].SetLabel(str(round(float(p['cycles'][l][2])/float(p['cycles'][l][3]),2)))
            
            x  = range(len(p['cycles'].keys()))
            y  = [ p['cycles'][i+1][0] for i in x ]
            y2 = [ p['cycles'][i+1][1] for i in x ]
        
            self.ax1.plot(x, y, 'r^-')
            self.ax2.plot(x,y2, 'bo-')
            
            self.ax1.set_xticks(x)
            self.ax1.set_xticklabels([ 'Cycle ' + str(i+1) for i in x ], rotation='vertical', size=8)
            
            self.canvas.draw()

    def has_finished(self):
        ret = False

        if self._refinement is not None:
            p = self._refinement.parameters()
            ret = p['status'] == 'Finished'

        return ret

    def parameters(self):
        if self._refinement is not None:
            return self._refinement.parameters()


# ----------------------------------------------------------------------------
# Modified cctbx PolygonPanel
class P8PolygonPanel(pgn.PolygonPanel):
    _callback = None
    
    def __init__(self, parent, renderer):
        self.h = 300
        self._last = 0
        pgn.PolygonPanel.__init__(self, parent, renderer)
        #self.Bind(wx.EVT_LEFT_DOWN, self._clicked)
        self.Bind(wx.EVT_MOTION, self._clicked)

    def set_callback(self, cb):
        self._callback = cb
    
    def _clicked(self, e):
        x,y = self.GetSize()
        c = min((x,y))/2.0
        
        ang = round((180/math.pi)*math.atan2(y-e.GetY()-c, e.GetX()-c)+30) % 360 / 60
        
        if self._callback and self._last != ang:
            self._last = ang
            self._callback(int(ang))


# ----------------------------------------------------------------------------
# Polygon / Histogram Panel
class Compare(Tab):
    @staticmethod
    def set_stats(func):
        Compare._stats = func
    
    def __init__(self, nb):
        Tab.__init__(self, nb)
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
    
    def load_refinement(self, ref, stats):
        pdb_file = ref.replace('.dat', '.pdb')
        pdb_io = pdb.input(file_name=pdb_file)
        
        m_stats = self._stats()
        
        self.model_stats = {
            "r_work" : stats['r'],
            "r_free" : stats['rfree'],
            "adp_mean_all" : flex.mean_default(pdb_io.xray_structure_simple().extract_u_iso_or_u_equiv()*(math.pi**2*8), None),
            "bond_rmsd" : m_stats[1][0],
            "angle_rmsd" : m_stats[1][1],
            "clashscore" : m_stats[0]
        }
                
        self.hist_data = polygon.output.get_basic_histogram_data(d_min=stats['res'])
        self.renderer = pgn.wx_renderer(self.hist_data, self.model_stats)
    
        self.polygon_panel = P8PolygonPanel(self, self.renderer)
        self.polygon_panel.set_callback(self._on_click)
                
        self.histogram = polygon_db_viewer.HistogramPlot(self, figure_size=(5,4), font_size=6, title_font_size=6)
        col = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND)
        self.histogram.figure.patch.set_facecolor((col[0]/255.0, col[1]/255.0, col[2]/255.0))
        self.histogram.show_histogram(data=self.hist_data[0][1],
                                      n_bins=10,
                                      reference_value=self.model_stats['r_work'],
                                      xlabel='r_work')
    
        self.pg_sizer = wx.BoxSizer(wx.VERTICAL)
        self.pg_sizer.Add(self.histogram, 1, wx.ALL, 10)
        self.pg_sizer.Add(self.draw_color_key())
                
        self.sizer.Add(self.pg_sizer, 1)                
        self.sizer.Add(self.polygon_panel, 2, wx.ALL, 10)
    
    def _on_click(self, qd):
        lkup = { 0:1, 1:3, 2:5, 3:0, 4:4, 5:2 }
        self.histogram.show_histogram(data=self.hist_data[lkup[qd]][1],
                                      n_bins=10,
                                      reference_value=self.model_stats[self.hist_data[lkup[qd]][0]],
                                      xlabel=self.hist_data[lkup[qd]][0])
    
    def draw_color_key (self) :
        lower_sizer = wx.BoxSizer(wx.VERTICAL)
        if self.renderer.relative_scale_colors :
            caption = wx.StaticText(self, -1,
            """Histogram bins are colored based on the ratio of the number of structures \
                in each bin to the average number per bin:""")
        else :
            caption = wx.StaticText(self, -1,
            """Histogram bins are colored by the number of structures in each bin.""")
        caption.Wrap(320)
        lower_sizer.Add(caption, 0, wx.ALL, 5)
        key_sizer = wx.BoxSizer(wx.HORIZONTAL)
        key_sizer = wx.FlexGridSizer(rows=1, cols=0)
        lower_sizer.Add(key_sizer)
        colors, cutoffs = self.renderer.get_color_key()
        for i, color in enumerate(colors) :
            color_widget = pgn.ColorBox(self, -1, "", color, size=(24,24))
            key_sizer.Add(color_widget, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
            if i < len(cutoffs) :
                if self.renderer.relative_scale_colors :
                    label = wx.StaticText(self, -1, "=< %s" % str(cutoffs[i]))
                else :
                    label = wx.StaticText(self, -1, "= %s" % str(cutoffs[i]))
                key_sizer.Add(label, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)

        return lower_sizer


# ----------------------------------------------------------------------------
# Main Process Holder
class Holder(Tab):

    @staticmethod
    def set_finished_callback(func):
        Holder._finished_callback = func

    def __init__(self, nb):
        Tab.__init__(self, nb)

        #Process.set_finished_callback(self.refinement_finished)
        
        self._tabs = wx.aui.AuiNotebook(self, -1, style=wx.NB_TOP, size=(850,750))
        self._tab_list = []
        
        self._stats = Process(self)
        self._stats.set_finished_callback(self.refinement_finished)
        self._tabs.AddPage(self._stats, 'Refinement')

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self._tabs, 1, wx.EXPAND)
            
        self.SetSizer(self.sizer)

    def start_refinement(self, type, root, title, res, resl, cycles, ins, hkl, id, options):
        self._stats.start_refinement(type, root, title, res, resl, cycles, ins, hkl, id, options)

    def load_refinement(self, ref):
        self._stats.load_refinement(ref)

        if self._stats.has_finished():
            self.load_analysis(ref) 
    
    def refinement_finished(self):
        p = self._stats.parameters()
        
        if hasattr(self, '_finished_callback'):
            self._finished_callback(p['id'], p['status'])

        if self._stats.has_finished():
            self.load_analysis(p['input'] + '.dat')
        
            
    def load_analysis(self, ref):
        self._tab_list.append(Validation(self))
        self._tab_list[-1].load_refinement(ref)
        self._tabs.AddPage(self._tab_list[-1], 'Validation')

        Compare.set_stats(self._tab_list[-1].stats)
        
        self._tab_list.append(Compare(self))
        self._tab_list[-1].load_refinement(ref, self._stats.parameters())
        self._tabs.AddPage(self._tab_list[-1], 'Compare')
    
        self._tab_list.append(BondLengths(self))
        self._tab_list[-1].load_refinement(ref, self._stats.parameters()['type'])
        self._tabs.AddPage(self._tab_list[-1], 'Bond Lengths')
    

    def load_coot(self):
        self._stats.load_coot()

# ----------------------------------------------------------------------------
# New Refinement Dialog
class NewRefinement(wx.Dialog):

    def __init__(self, parent, id, title, inputs, refls, in_files, ref_files):
        wx.Dialog.__init__(self, parent, id, title)

        self._in_files = in_files
        self._ref_files = ref_files
        self._residue_list = []
        
        self.input_sizer = wx.FlexGridSizer(rows=0, cols=2, vgap=5, hgap=5)
        self.input_sizer.Add(wx.StaticText(self, -1, 'Title'))

        self._title = wx.TextCtrl(self, -1, '', (30, 200))
        self.input_sizer.Add(self._title, 0, wx.EXPAND)
            
        self.input_sizer.Add(wx.StaticText(self, -1, 'Reflections'))
        self._reflections = wx.ComboBox(self, -1, choices=refls, style=wx.CB_READONLY)
        self._reflections.Bind(wx.EVT_COMBOBOX, self._set_res)
        self.input_sizer.Add(self._reflections, 0, wx.EXPAND)

        self.input_sizer.Add(wx.StaticText(self, -1, 'Structure'))
        self._structure = wx.ComboBox(self, -1, choices=inputs, style=wx.CB_READONLY)
        self._structure.Bind(wx.EVT_COMBOBOX, self._set_res)
        self.input_sizer.Add(self._structure, 0, wx.EXPAND)

        self.input_sizer.Add(wx.StaticText(self, -1, 'Type'))
        self._refinement_type = wx.ComboBox(self, -1, REFINEMENT_TYPES[0], choices=REFINEMENT_TYPES, style=wx.CB_READONLY)
        self._refinement_type.Bind(wx.EVT_COMBOBOX, self._set_type)
        self.input_sizer.Add(self._refinement_type, 0, wx.EXPAND)

        self.input_sizer.Add(wx.StaticText(self, -1, 'Cycles'))
        self._cycles = wx.SpinCtrl(self, -1, value='10')
        self.input_sizer.Add(self._cycles, 0)
            
        self.input_sizer.Add(wx.StaticText(self, -1, 'Resolution'))
        self._res_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._res_high = wx.TextCtrl(self, -1, '')
        self._res_low = wx.TextCtrl(self, -1, '')
        self._res_sizer.Add(self._res_high)
        self._res_sizer.Add(self._res_low)
        self.input_sizer.Add(self._res_sizer, 0)
            
        self.input_sizer.Add(wx.StaticText(self, -1, 'Options'))
        self._opt_sizer = wx.BoxSizer(wx.VERTICAL)

        self._auto = wx.CheckBox(self, -1, 'Auto Refinement', (10, 10))
        self._opt_sizer.Add(self._auto)
        self._auto.Bind(wx.EVT_CHECKBOX, self._set_auto)
        
        self._hydrogens = wx.CheckBox(self, -1, 'Add Hydrogens', (10, 10))
        self._opt_sizer.Add(self._hydrogens)

        self._anis = wx.CheckBox(self, -1, 'Anisotropic', (10, 10))
        self._opt_sizer.Add(self._anis)
        
        self._bloc = wx.CheckBox(self, -1, 'BLOC Refinement', (10, 10))
        self._opt_sizer.Add(self._bloc)
                             
        self._rfree = wx.CheckBox(self, -1, 'Include Rfree Set', (10, 10))
        self._opt_sizer.Add(self._rfree, 0)
        
        self.input_sizer.Add(self._opt_sizer, 0, wx.EXPAND)
        
        self._residues_title = wx.StaticText(self, -1, 'Unrestrained Residues')
        self._residues_title.Wrap(100)
        self.input_sizer.Add(self._residues_title)
        self._residues = wx.ListBox(self, 26, wx.DefaultPosition, (40, 100), [], wx.LB_MULTIPLE)

        self.input_sizer.Add(self._residues, 0, wx.EXPAND)
        
        self._ur_title = wx.StaticText(self, -1, 'Un-/Restrained Cycles')
        self._ur_title.Wrap(100)
        self._ur_cycles = wx.SpinCtrl(self, -1, value='5')
        self.input_sizer.Add(self._ur_title, 0, wx.EXPAND)
        self.input_sizer.Add(self._ur_cycles, 0)
        
        self._total_title = wx.StaticText(self, -1, 'Total Cycles')
        self._total_cycles = wx.SpinCtrl(self, -1, value='1')
        self.input_sizer.Add(self._total_title, 0, wx.EXPAND)
        self.input_sizer.Add(self._total_cycles, 0)
    
        self._custom_file = FileBrowser(self, 'Text File (*.txt)|*.txt', 'Select a text file containing custom shelx commands')
        self.input_sizer.Add(wx.StaticText(self, -1, 'Custom Command / Restraints'), 0, wx.EXPAND)
        self.input_sizer.Add(self._custom_file.sizer(), 0, wx.EXPAND)
        
        self._button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._startb = wx.Button(self, 0, 'Start')
        self._startb.Bind(wx.EVT_BUTTON, self._start)
        self._button_sizer.Add(self._startb, 1, wx.EXPAND|wx.ALL, 5)
        self._cancel = wx.Button(self, 1, 'Cancel')
        self._cancel.Bind(wx.EVT_BUTTON, self._close)
        self._button_sizer.Add(self._cancel, 1, wx.EXPAND|wx.ALL, 5)
        
        self.input_sizer.Add((10,10))
        self.input_sizer.Add(self._button_sizer, 0, wx.EXPAND)
        
        
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer.Add(self.input_sizer, 0, wx.EXPAND|wx.ALL, 5)
        #self.main_sizer.Add(self._button_sizer, 0, wx.EXPAND|wx.CENTER, 10)
        
        self.SetSizer(self.main_sizer)

        for c in [self._residues, self._residues_title, self._rfree, self._bloc, self._ur_title, self._ur_cycles, self._total_title, self._total_cycles]:
            c.Hide()

        self.Fit()
        self._set_res('')
        self._hydrogens.SetValue(0)

    def _set_auto(self, event):
        v = self._auto.GetValue() == 1
        self._ur_title.Show(v)
        self._ur_cycles.Show(v)
        self._total_title.Show(v)
        self._total_cycles.Show(v)
    
        self.Fit()
    
    def _set_type(self, event):
        if self._refinement_type.GetCurrentSelection() == FULL_MATRIX:
            self._cycles.SetValue(1)
            
            self._bloc.Show()
            self._rfree.Show()
        else:
            self._cycles.SetValue(10)
            
            self._bloc.Hide()
            self._rfree.Hide()
        
        if self._refinement_type.GetCurrentSelection() == PART_UNRESTRAINED:
            self._residues_title.Show()
            self._residues.Show()
        else:
            self._residues_title.Hide()
            self._residues.Hide()

        self.main_sizer.Layout()
        self.Fit()
                
    def _set_res(self, event):
        ref = self._ref_files[self._reflections.GetCurrentSelection()]
        ins = self._in_files[self._structure.GetCurrentSelection()]
        
        
        if os.path.exists(ref) and os.path.exists(ins):
            hkl = hklf.reader(open(ref))
            try:
                ma = hkl.as_miller_arrays(crystal_symmetry=crystal_symmetry_from_ins.extract_from(ins))
            except:
                return
                
            rr = ma[0].resolution_range()
            
            self._res_high.SetValue(str(round(rr[1], 2)))
            self._res_low.SetValue(str(round(rr[0], 2)))
            
            ins_obj = Shelx(ins)
            self._hydrogens.SetValue(ins_obj.has_hydrogen())
            
            self._residues.Clear()
            self._residue_list = []
            for r in sorted(ins_obj.residue_list()):
                if r not in (ShelxData._r + ['HOH', 'DOD', 'CL', 'MG']) or (r in ['ASP', 'GLU', 'HIS', 'ARG']):
                    self._residues.Append(r)
                    self._residue_list.append(r)

    
    def _close(self, event):
        self.EndModal(0)
    
    def _start(self, event):
        self.EndModal(1)

    def get_values(self):
        ty = self._refinement_type.GetCurrentSelection()
        if ty == -1:
            ty = 0
        
        residues = []
        selected = self._residues.GetSelections()
        for s in selected:
            residues.append(self._residue_list[s])
        
        #title, refln, input, type, cycles, res, resl, residues
        return self._title.GetValue(),self._reflections.GetCurrentSelection(),self._structure.GetCurrentSelection(),ty,self._cycles.GetValue(),float(self._res_high.GetValue()),float(self._res_low.GetValue()),{'residues': residues,'hydrogens': self._hydrogens.GetValue(),'bloc': self._bloc.GetValue(),'rfree': self._rfree.GetValue(), 'auto': self._auto.GetValue(), 'ur_cycles': self._ur_cycles.GetValue(), 'total_cycles': self._total_cycles.GetValue(), 'anis': self._anis.GetValue(), 'custom': self._custom_file.file()}

                
# ----------------------------------------------------------------------------
# Error Dialog
class ShelxError(wx.Dialog):
    def __init__(self, parent, log):
        wx.Dialog.__init__(self, parent, -1, 'Shelxl Error', size=(590,250))
        self.Bind(wx.EVT_CLOSE, self._on_close)
    
        self.text = wx.TextCtrl(self, -1, log, style=wx.TE_MULTILINE)
        self.text.SetFont(wx.Font(12, wx.MODERN, wx.NORMAL, wx.NORMAL))
    
        self._ok = wx.Button(self, -1, 'Ok')
        self._ok.Bind(wx.EVT_BUTTON, self._on_close)
            
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(wx.StaticText(self, -1, 'Shelxl encountered an error:'), 0, wx.ALL, 5)
        self.sizer.Add(self.text, 1, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(self._ok, 0, wx.ALL, 5)
        
        self.SetSizer(self.sizer)
        #self.Fit()
    
    def _on_close(self, event):
        self.EndModal(1)
        self.Destroy()


# ----------------------------------------------------------------------------
# Log File Dialog
class LogFile(wx.Dialog):
    def __init__(self, parent, id, title, log):
        wx.Dialog.__init__(self, parent, id, title, size=(590,400))
        self.Bind(wx.EVT_CLOSE, self._on_close)
        
        self.text = wx.TextCtrl(self, -1, open(log).read(), style=wx.TE_MULTILINE)
        self.text.SetFont(wx.Font(12, wx.MODERN, wx.NORMAL, wx.NORMAL))
        
        self._close = wx.Button(self, -1, 'Close')
        self._close.Bind(wx.EVT_BUTTON, self._on_close)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.text, 1, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(self._close, 0, wx.EXPAND|wx.ALL, 5)
        
        self.SetSizer(self.sizer)
        #self.Fit()
        
    def _on_close(self, event):
        self.EndModal(1)
        self.Destroy()

# ----------------------------------------------------------------------------
# Job Summary
class Summary(wx.Frame):
    
    def __init__(self, job, title, root):
        wx.Frame.__init__(self,None,-1,'Job Summary', size=(500,300))
        
        self.toolbar = wx.ToolBar(self, style=wx.TB_3DBUTTONS|wx.TB_TEXT)
        close = self.toolbar.AddLabelTool(wx.ID_ANY, 'Close', bitmaps.fetch_icon_bitmap("actions", "no"))
        self.Bind(wx.EVT_TOOL, self._close, close)
        self.toolbar.AddSeparator()
        self.toolbar.AddControl(wx.StaticText(self.toolbar, -1, title))
        self.SetToolBar(self.toolbar)
        self.toolbar.Realize()
        
        self.table = wx.FlexGridSizer(cols=2, rows=0, hgap=5, vgap=5)
        
        if os.path.exists(job):
            r = pickle.load(open(job, 'rb'))
            p = r.parameters()
            
            #self.table.Add(wx.StaticText(self, -1, 'Job:'))
            #self.table.Add(wx.StaticText(self, -1, title))
            self.table.Add(wx.StaticText(self, -1, 'Title:'))
            self.table.Add(wx.StaticText(self, -1, p['title']), 0, wx.EXPAND|wx.BOTTOM, 10)
            
            self.table.Add(wx.StaticText(self, -1, 'Started:'))
            self.table.Add(wx.StaticText(self, -1, time.strftime("%H:%M %d-%m-%Y", time.localtime(p['time']))))
            self.table.Add(wx.StaticText(self, -1, 'Time Taken:'))
            self.table.Add(wx.StaticText(self, -1, str(round((p['timef']-p['time'])/60,1)) + ' mins'), 0, wx.EXPAND|wx.BOTTOM, 10)
            
            self.table.Add(wx.StaticText(self, -1, 'Input HKL:'))
            self.table.Add(wx.StaticText(self, -1, p['hkl'].replace(root, '')))
            self.table.Add(wx.StaticText(self, -1, 'Input INS:'))
            self.table.Add(wx.StaticText(self, -1, p['ins'].replace(root, '')), 0, wx.EXPAND|wx.BOTTOM, 10)
            
            self.table.Add(wx.StaticText(self, -1, 'Status:'))
            self.table.Add(wx.StaticText(self, -1, p['status']))
            self.table.Add(wx.StaticText(self, -1, 'Type:'))
            self.table.Add(wx.StaticText(self, -1, REFINEMENT_TYPES[p['type']]))
            
            if p['type'] == PART_UNRESTRAINED:
                self.table.Add(wx.StaticText(self, -1, 'Unrestrained Residues:'))
                self.table.Add(wx.StaticText(self, -1, ', '.join(p['options']['residues'])), 0, wx.EXPAND|wx.BOTTOM, 10)
            
            if p['type'] == FULL_MATRIX:
                self.table.Add(wx.StaticText(self, -1, 'BLOC 1:'))
                self.table.Add(wx.StaticText(self, -1, 'Yes' if p['options']['bloc'] else 'No'))
                self.table.Add(wx.StaticText(self, -1, 'Include Rfree:'))
                self.table.Add(wx.StaticText(self, -1, 'Yes' if p['options']['rfree'] else 'No'), 0, wx.EXPAND|wx.BOTTOM, 10)
            
            self.table.Add(wx.StaticText(self, -1, 'Cycles:'))
            self.table.Add(wx.StaticText(self, -1, str(p['total_cycles'])))
            self.table.Add(wx.StaticText(self, -1, 'Resolution'))
            self.table.Add(wx.StaticText(self, -1, '%.2f - %.2f' % (p['res'], p['resl'])))
            
            self.table.Add(wx.StaticText(self, -1, 'R:'))
            self.table.Add(wx.StaticText(self, -1, '%.4f' % p['r']))
            self.table.Add(wx.StaticText(self, -1, 'Rfree:'))
            self.table.Add(wx.StaticText(self, -1, '%.4f' % p['rfree']), 0, wx.EXPAND|wx.BOTTOM, 10)
            
            self.table.Add(wx.StaticText(self, -1, 'Hydrogens:'))
            self.table.Add(wx.StaticText(self, -1,'Yes' if p['options']['hydrogens'] else 'No'))
            self.table.Add(wx.StaticText(self, -1, 'Anistropic:'))
            self.table.Add(wx.StaticText(self, -1,'Yes' if p['options']['anis'] else 'No'))

            self.table.Add(wx.StaticText(self, -1, 'Custom Commands:'))
        
            cust = 'N/A'
            if 'custom' in p['options']:
                if p['options']['custom']:
                    cust = p['options']['custom']
        
            self.table.Add(wx.StaticText(self, -1, cust))
        
        self.fig = Figure((3.0, 2.0), dpi=100)
        col = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND)
        self.fig.patch.set_facecolor((col[0]/255.0, col[1]/255.0, col[2]/255.0))
        self.canvas = FigCanvas(self, -1, self.fig)
        self.ax1 = self.fig.add_subplot(111)
        self.ax2 = self.ax1.twinx()
        
        self.ax1.set_ylabel('wR2', fontsize=9)
        self.ax1.tick_params(labelsize=8)
        self.ax1.yaxis.set_major_formatter(FormatStrFormatter('%5.3f'))
        
        self.ax2.tick_params(labelsize=8)
        self.ax2.yaxis.set_major_formatter(FormatStrFormatter('%4.1f'))
        
        self.ax2.set_ylabel('GooF', fontsize=9)
        
        x  = range(len(p['cycles'].keys()))
        y  = [ p['cycles'][i+1][0] for i in x ]
        y2 = [ p['cycles'][i+1][1] for i in x ]
        
        self.ax1.plot(x, y, 'r^-')
        self.ax2.plot(x,y2, 'bo-')
        
        self.ax1.set_xticks(x)
        self.ax1.set_xticklabels([ str(i+1) for i in x ], rotation='vertical', size=8)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.table, 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(self.canvas, 0, wx.EXPAND|wx.ALL, 5)
        
        self.SetSizer(self.sizer)
        self.Fit()
    
    def _close(self, e):
        self.Destroy()