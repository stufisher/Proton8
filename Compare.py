import matplotlib
matplotlib.use('WXAgg', False)

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas

import wx
import os
import pickle
import re
import glob
import math

from Tab import Tab
from PDBTools import PDBTools

class Compare(Tab):

    def __init__(self, nb):
        Tab.__init__(self, nb)

        self.fig = Figure((5.0, 4.0), dpi=100)
        col = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND)
        self.fig.patch.set_facecolor((col[0]/255.0, col[1]/255.0, col[2]/255.0))
        self.canvas = FigCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('button_press_event', self._on_click)
        self.ax1 = self.fig.add_subplot(111)
        self.ax1.set_position([0.10,0.153,0.80,0.81])
        #self.ax2 = self.ax1.twinx()
        self.ax1.tick_params(labelsize=8)
        #self.ax2.tick_params(labelsize=8)   
        
        self.hist_fig = Figure((2,1.5), dpi=100)
        self.hist_fig.set_facecolor((col[0]/255.0, col[1]/255.0, col[2]/255.0))
        self.hist_canvas = FigCanvas(self, -1, self.hist_fig)
        self.hist_ax1 = self.hist_fig.add_subplot(111)
        
        self.shist_fig = Figure((2,1.5), dpi=100)
        self.shist_fig.set_facecolor((col[0]/255.0, col[1]/255.0, col[2]/255.0))
        self.shist_canvas = FigCanvas(self, -1, self.shist_fig)
        self.shist_ax1 = self.shist_fig.add_subplot(111)
        
        self.refinements = wx.ListBox(self, 26, wx.DefaultPosition, (60, 100), [], wx.LB_MULTIPLE)
        self.refinements.Bind(wx.EVT_LISTBOX, self._set_refinements)
        
        self.res_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.res_sizer.Add(wx.StaticText(self, -1, 'Residue Type'), 0, wx.EXPAND)
        self.res_type = wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY)
        self.res_type.Bind(wx.EVT_COMBOBOX, self._set_residue_type)
        self.res_sizer.Add(self.res_type, 0, wx.EXPAND)

        self._flds = [ wx.StaticText(self, -1, '') for i in range(4) ]
        
        self.avg_info = wx.FlexGridSizer(rows=0, cols=2, vgap=5, hgap=5)
        self.avg_info.Add(wx.StaticText(self, -1, 'Average Std Dev'), 0, wx.EXPAND)
        self.avg_info.Add(self._flds[0], 0, wx.EXPAND)
        #self.avg_info.Add(wx.StaticText(self, -1, 'Number of Vals'), wx.EXPAND|wx.ALL, 5)
        #self.avg_info.Add(self._flds[1], wx.EXPAND|wx.ALL, 5)
        
        self.res_info = wx.FlexGridSizer(rows=0, cols=2, vgap=5, hgap=5)
        self.res_info.Add(wx.StaticText(self, -1, 'Average Values'), 0, wx.EXPAND)
        self.res_info.Add(self._flds[1], 0, wx.EXPAND)
        self.res_info.Add(wx.StaticText(self, -1, 'Standard Dev'), 0, wx.EXPAND)
        self.res_info.Add(self._flds[2], 0, wx.EXPAND)
        #self.res_info.Add(wx.StaticText(self, -1, 'Number of Vals'), wx.EXPAND|wx.ALL, 5)
        #self.res_info.Add(self._flds[3], wx.EXPAND|wx.ALL, 5)
        
        self.side_sizer = wx.BoxSizer(wx.VERTICAL)
        self.side_sizer.Add(wx.StaticText(self, -1, 'Refinements'), 0, wx.EXPAND|wx.LEFT, 5)
        self.side_sizer.Add(self.refinements, 0, wx.EXPAND|wx.LEFT, 5)
        self.side_sizer.Add(self.res_sizer, 0, wx.EXPAND|wx.LEFT, 5)
        self.side_sizer.Add(self.avg_info, 0, wx.EXPAND|wx.LEFT, 5)
        self.side_sizer.Add(self.shist_canvas, 1, wx.EXPAND|wx.LEFT, 5)
        self.side_sizer.Add(self.res_info, 0, wx.EXPAND|wx.LEFT, 5)
        self.side_sizer.Add(self.hist_canvas, 1, wx.EXPAND|wx.LEFT, 5)
        
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.sizer.Add(self.side_sizer, 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(self.canvas, 1, wx.EXPAND|wx.ALL, 5)
        
        self._rtypes = ['Aspartate', 'Glutamate', 'Histidine', 'Arginine']
        self._rtypess = ['Asp', 'Glu', 'His', 'Arg']
        
        self._residue_type = 0
        self._highlight = -1
        self._selected_residue = -1
        self._residue_types = []
        self._all_data = []
        self._averaged = []
        self._files = []
                            
        self.SetSizer(self.sizer)
        self.Fit()

    def _on_click(self,event):
        self._highlight = -1
        if event.xdata:
            self._highlight = int(round(event.xdata, 0))
            t  = self._rtypess[self._residue_type].lower()
            x = sorted(self._averaged[t].keys())
            if self._highlight < len(x):
                self._selected_residue = x[self._highlight]
            
            
        self._plot()
        self._show_residue()

    def _set_residue_type(self, event):
        self._residue_type = self._rtypes.index(self.res_type.GetValue())
        self._plot()


    def _set_refinements(self, event):
        refs = list(self.refinements.GetSelections())
        self._pdbs = [ self._files[i].replace('.dat', '.pdb') for i in refs ]
        
        print self._pdbs
        self.analyse()
        self._plot()
        self._show_residue()
        
    def refresh(self):
        self.refinements.Clear()
        
        ids, files, dirs = self._get_inputs()
        self._files = []
        for i,d in enumerate(files):
            r = pickle.load(open(d))
            p = r.parameters()
            
            if p['type'] in (1,2,3):
                self._files.append(files[i])
                self.refinements.Append(dirs[i])


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


    def analyse(self):
        pdbt = PDBTools()
    
        self._bond_lengths = []
        for f in self._pdbs:
            om, res = pdbt.get_bond_lengths(str(f))
            self._bond_lengths.append(res)
            
        combined = {}
        for ty in self._bond_lengths[0].keys():
            combined[ty] = {}
            
            for pid,p in enumerate(self._bond_lengths):
                for rid,r in p[ty].iteritems():
                    if not rid in combined[ty]:
                        combined[ty][rid] = {}
                
                    if type(r) == type({}):
                        for bl,v in r.iteritems():
                            #print pid, ty, rid, bl, v
                            if not bl in combined[ty][rid]:
                                combined[ty][rid][bl] = [[v[0]], [v[1]], [v[2]]]
                            else:
                                for i in range(3):
                                    combined[ty][rid][bl][i].append(v[i])

        self._all_data = dict(combined)
        
        self._averaged = {}
        for tid,res in combined.iteritems():
            self._averaged[tid] = {}
            for rid,r in res.iteritems():
                if not rid in self._averaged[tid]:
                    self._averaged[tid][rid] = {}
                for n,bl in r.iteritems():
                    tmp = []
                    for i in range(3):
                        tmp.append(self._stat(bl[i]))
                
                    self._averaged[tid][rid][n] = tmp
        
        self._residue_types = []
        self.res_type.Clear()
        for k in sorted(self._averaged.keys()):
            if k != 'avg' and len(self._averaged[k]) > 0:
                self.res_type.Append(self._rtypes[[ x.lower() for x in self._rtypess].index(k)])
        self._residue_types.append(k)
        
            
    def _stat(self, list):
        ret = [0,0]
        if len(list) > 0:
            avg = sum(list)/len(list)
            
            var = []
            for i in list:
                var.append(pow(abs(i-avg),2))
                
            ret = [avg, 1/float(len(list))*math.sqrt(sum(var))]
          
        return ret
        
    def _plot(self):
        self.ax1.cla()
        #self.ax2.cla()
    
        #self.ax2.set_ylabel('B Factor ($A^2$)', fontsize=9)  

        t  = self._rtypess[self._residue_type].lower()
        tu = self._rtypess[self._residue_type]

        x = sorted(self._averaged[t].keys())
        
        xs  = [ tu + '-' + str(k) for k in x ]
        xa  = range(len(x))
        
        l1  = [self._averaged[t][k][1][0][0] for k in x ]
        l2  = [self._averaged[t][k][2][0][0] for k in x ]
        el1 = [self._averaged[t][k][1][0][1] for k in x ]
        el2 = [self._averaged[t][k][2][0][1] for k in x ]
        
        if len(x) > 0:
            b1  = [self._averaged[t][k][1][2][0] for k in x ]
            be1 = [self._averaged[t][k][2][2][1] for k in x ]
            b2  = [self._averaged[t][k][1][2][0] for k in x ]
            be2 = [self._averaged[t][k][2][2][1] for k in x ]
            
            if self._residue_type == 0 or self._residue_type == 1:
                self.ax1.errorbar(xa, l1, yerr=el1, fmt='ro', label='$C-O\gamma1')
                self.ax1.errorbar(xa, l2, yerr=el2, fmt='b^', label='$C-O\gamma2')
                #self.ax2.plot(xa, b1, 'go', xa, b2, 'y^')
                
                #self.ax2.errorbar(xa, b1, yerr=be1, fmt='go')
                #self.ax2.errorbar(xa, b2, yerr=be2, fmt='y^')
                
                self.ax1.axhline(y=1.21, color='0.7')
                self.ax1.axhline(y=1.31, color='0.7')
                self.ax1.axhspan(1.327, 1.293, alpha=0.6, color='0.9')
                self.ax1.axhspan(1.194, 1.226, alpha=0.6, color='0.9')
                #self.ax1.set_ylim(min(l1+l2+[1.2])-0.2, max(l1+l2+[1.32])+0.05)
                self.ax1.set_ylabel('C-O (A)', fontsize=9)
                                      
            # his CG CD2 NE2, ND1 CE1 NE2
            elif self._residue_type == 2:
                self.ax1.errorbar(xa, l1, yerr=el1, fmt='ro', label='CG-CD2-NE2')
                self.ax1.errorbar(xa, l2, yerr=el2, fmt='b^', label='ND1-CE1-NE2')
                #self.ax2.plot(xa, b1, 'go', xa, b2, 'y^')
                self.ax1.axhline(y=111.2, color='0.7')
                self.ax1.axhline(y=109.3, color='0.7')
                self.ax1.axhline(y=107.5, color='0.7')
                self.ax1.axhline(y=107.2, color='0.7')
                #self.ax1.set_ylim(95, 115)
                self.ax1.set_ylabel('Angle', fontsize=9)
            
            # arg CZ NH2, CZ NE, CZ NH1, CD NE?        
            elif self._residue_type == 3:
                l3  = [self._averaged[t][k][3][0][0] for k in x ]
                #b3  = [self._residues[t][k][3][2] for k in x ]
                el3 = [self._averaged[t][k][3][0][1] for k in x ]
                
                self.ax1.errorbar(xa, l1, yerr=el1, fmt='ro', label='CZ-NH2')
                self.ax1.errorbar(xa, l2, yerr=el2, fmt='b^', label='CZ-NE')
                self.ax1.errorbar(xa, l3, yerr=el3, fmt='b^', label='CZ-NH1')                
                #self.ax2.plot(xa, b1, 'go', xa, b2, 'y^', xa, b3)
                #self.ax1.set_ylim(min(l1+l2)-0.2, max(l1+l2)+0.05)
                self.ax1.set_ylabel('NZ-X (A)', fontsize=9)
                self.ax1.axhline(y=1.326, color='0.7')
                self.ax1.axhline(y=1.41, color='0.7')            
            
            #self.ax2.axhline(y=self._averaged['avg']['b'], color=(0.5,0.5,0), ls='--')
            #self.ax2.set_ylim(min(b1+b2)-2, max(b1+b2)+20)
            
            self.ax1.set_xlim(-1, len(x))
            self.ax1.set_xticks(xa)
            self.ax1.set_xticklabels(xs, rotation='vertical', size=8)        

            self.ax1.tick_params(labelsize=8)
            #self.ax2.tick_params(labelsize=8)

            if self._highlight > -1:
                self.ax1.axvspan(self._highlight-0.5, self._highlight+0.5, alpha=0.3, color='0.9')

            #handles, labels = self.ax1.get_legend_handles_labels()
            #handles2, labels2 = self.ax2.get_legend_handles_labels()
            #self.ax2.legend(handles+handles2, labels+labels2)

        self.canvas.draw()
        self._hist_stds()
        
            
    def _hist_stds(self):
        t  = self._rtypess[self._residue_type].lower()
        tu = self._rtypess[self._residue_type]
        
        #print self._averaged[t]
        
        l1  = [ self._averaged[t][rid][1][0][1] for rid in self._averaged[t].keys() ] + [ self._averaged[t][rid][2][0][1] for rid in self._averaged[t].keys() ]
      
        #print l1
        
        self.shist_ax1.cla()
        
        if len(l1) > 0:
            avg = sum(l1)/len(l1)
            self.shist_ax1.axvline(x=avg, color='blue')
        
            self._flds[0].SetLabel('%.3f' % avg)
            #self._flds[1].SetLabel(str(len(l1)))
        
        self.shist_ax1.tick_params(labelsize=8)
        self.shist_ax1.hist(l1, 10, normed=1, facecolor='green', alpha=0.75)
        self.shist_canvas.draw()
    
            
    def _show_residue(self):
        if self._highlight > -1:
            t  = self._rtypess[self._residue_type].lower()
            tu = self._rtypess[self._residue_type]
            
            l1 = self._all_data[t][self._selected_residue][1][0]
            l2 = self._all_data[t][self._selected_residue][2][0]
            
            vals = [ '%.3f' % x[0] for x in [self._stat(l1), self._stat(l2)] ]
            stds = [ '%.3f' % x[1] for x in [self._stat(l1), self._stat(l2)] ]   
                
            self._flds[1].SetLabel(' '.join(vals))
            self._flds[2].SetLabel(' '.join(stds))
            
            self.hist_ax1.cla()
            self.hist_ax1.tick_params(labelsize=8)
            self.hist_ax1.hist(l1, 5, normed=0, facecolor='red', alpha=0.75)
            self.hist_ax1.hist(l2, 5, normed=0, facecolor='blue', alpha=0.75)
            self.hist_canvas.draw()
        
