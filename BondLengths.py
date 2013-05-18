import re
import os
import glob
import math
import wx
import pickle

import iotbx.pdb
from wxtbx import metallicbutton, bitmaps

import matplotlib
matplotlib.use('WXAgg', False)

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas

from Project import Project
from Tab import Tab
from Ligand import Ligand
from Constants import *
from PDBTools import PDBTools

DEBUG = 1

def debug_print(text):
    if DEBUG:
        print text

class BondLengths(Tab):

    def __init__(self, nb):
        Tab.__init__(self, nb)

        self._pdbt = PDBTools()
        
        self._res_size = (200,170)
        self._to_save = []
        
        self.fig = Figure((5.0, 4.0), dpi=100)
        col = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND)
        self.fig.patch.set_facecolor((col[0]/255.0, col[1]/255.0, col[2]/255.0))
        self.canvas = FigCanvas(self, -1, self.fig)

        self.res = wx.StaticBitmap(self, size=self._res_size)
        self.res.SetBitmap(wx.EmptyImage(self._res_size[0], self._res_size[1]).ConvertToBitmap())

        self._rtypes = ['Aspartate', 'Glutamate', 'Histidine', 'Arginine']
        self._rtypess = ['Asp', 'Glu', 'His', 'Arg']
        
        self.ax1 = self.fig.add_subplot(111)
        self.ax1.set_position([0.10,0.153,0.80,0.81])
        self.ax2 = self.ax1.twinx()
        self.ax2.set_position([0.10,0.153,0.80,0.81])
        self.ax1.tick_params(labelsize=8)
        self.ax2.tick_params(labelsize=8)   
        
        self._highlight = 0
        
        self._bond_lengths = ''
        self._std_devs = ''
        self._residue_selection = []
        self._chain_lookup = {}
        
        self._residue_type = 0
        
        self._residues = {'asp': {}, 'glu': {}, 'his': {}, 'arg': {}}
        self._omitted = {'asp': [], 'glu': [], 'his': [], 'arg': []}
        
        self.omitted_title = wx.StaticBox( self, -1, "Omitted" ) 
        self.omitted_sizer = wx.StaticBoxSizer( self.omitted_title, wx.HORIZONTAL)        
        
        self.selected_title = wx.StaticBox( self, -1, "Displayed" ) 
        self.selected_sizer = wx.StaticBoxSizer( self.selected_title, wx.HORIZONTAL)        
        
        self.residue_info_title = wx.StaticBox( self, -1, "Residue Info: " ) 
        self.residue_info_sizer = wx.StaticBoxSizer( self.residue_info_title, wx.VERTICAL)
        
        #self.residue_info = wx.FlexGridSizer(rows=0, cols=2, vgap=5, hgap=5)
        
        #self.residue_info.Add(wx.StaticText(self, -1, 'D(C-O)'))
        #self._dco = wx.StaticText(self, -1, '')
        #self.residue_info.Add(self._dco)

        #self.residue_info.Add(wx.StaticText(self, -1, 'S(D(C-O))'))
        #self._sdco = wx.StaticText(self, -1, '')
        #self.residue_info.Add(self._sdco)
            
        #self.residue_info.Add(wx.StaticText(self, -1, 'Level'))
        #self._lev = wx.StaticText(self, -1, '')
        #self.residue_info.Add(self._lev)
        
        #self.residue_info_sizer.Add(self.residue_info, 0)
        self.residue_info_sizer.Add(self.res, 0)        
        
        self.residue_sel = wx.ListBox(self, 26, wx.DefaultPosition, (70, 80), [], wx.LB_MULTIPLE)
        self.residue_sel.Bind(wx.EVT_LISTBOX, self._update_sel)
        self.omitted_res = wx.ListBox(self, 26, wx.DefaultPosition, (70, 80), [], wx.LB_SINGLE)
        self.omitted_res.Bind(wx.EVT_LISTBOX, self._goto_omitted)

        self.data_box = wx.BoxSizer(wx.HORIZONTAL)
        self.data_box.Add(wx.StaticText(self, -1, 'Residue Type'), 0, wx.EXPAND|wx.ALL, 5)

        self.res_type = wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY)
        self.res_type.Bind(wx.EVT_COMBOBOX, self._set_residue_type)
        self.data_box.Add(self.res_type, 0, wx.EXPAND|wx.ALL, 5)

        self.omitted_sizer.Add(self.omitted_res, 1, wx.EXPAND|wx.ALL, 0)
        self.selected_sizer.Add(self.residue_sel, 1, wx.EXPAND|wx.ALL, 0)
                                                 
        self.ressel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ressel_sizer.Add(self.omitted_sizer, 1, wx.EXPAND|wx.ALL, 5)
        self.ressel_sizer.Add(self.selected_sizer, 1, wx.EXPAND|wx.ALL, 5)
        
        lig = metallicbutton.MetallicButton(self, -1, 'Ligands', '', bitmaps.fetch_icon_bitmap("actions", "viewmag", scale=(16,16)), size=(75, 25))
        save = metallicbutton.MetallicButton(self, -1, 'Figure', '', bitmaps.fetch_icon_bitmap("actions", "save_all", scale=(16,16)), size=(65, 25))
        tab = metallicbutton.MetallicButton(self, -1, 'Data', '', bitmaps.fetch_icon_bitmap("actions", "save_all", scale=(16,16)), size=(65, 25))
        self.Bind(wx.EVT_BUTTON, self._view_ligands, lig)
        self.Bind(wx.EVT_BUTTON, self._save_figure, save)
        self.Bind(wx.EVT_BUTTON, self._save_data, tab)
        
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_sizer.Add(save, 0, wx.LEFT, 5)
        self.button_sizer.Add(tab, 0, wx.LEFT, 5)
        self.button_sizer.Add(lig, 0, wx.LEFT, 5)
        
        self.residue_box = wx.BoxSizer(wx.VERTICAL)
        self.residue_box.Add(self.data_box, 0)
        self.residue_box.Add(self.residue_info_sizer, 0, wx.EXPAND, 10)
        self.residue_box.Add(self.ressel_sizer, 0)
        self.residue_box.Add(self.button_sizer, 0)
        
        self.main = wx.BoxSizer(wx.HORIZONTAL)
        self.main.Add(self.residue_box, 1, wx.EXPAND|wx.ALL, 5)
        
        self.averages = wx.StaticText(self, -1, '', style=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        #self.bottom_sizer.Add(self.button_sizer, 0)
        self.bottom_sizer.Add(self.averages, 1, wx.EXPAND)
        
        self.canvas_sizer = wx.BoxSizer(wx.VERTICAL)
        self.canvas_sizer.Add(self.canvas, 1, wx.EXPAND|wx.ALL)
        self.canvas_sizer.Add(self.bottom_sizer, 0, wx.EXPAND)
                
        self.main.Add(self.canvas_sizer, 3, wx.EXPAND|wx.ALL, 5)
        
        self.SetSizer(self.main)
        self.main.Fit(self)
        
        self.canvas.mpl_connect('button_press_event', self._on_click)
    
    def _save_data(self, e):
        dlg = wx.FileDialog(self, "Save Data as CSV", os.getcwd(), "", "*.csv", wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            
            out = open(path, 'w')
            for l in self._to_save:
                print >> out, ','.join(map(str, l))
            
            out.close()
        
        dlg.Destroy()
    
    def _view_ligands(self, event):
        if self._bond_lengths is not None:
            frame = Ligand(self._bond_lengths, self._bond_lengths.replace('_start.pdb', '').replace(self._project.root(), ''))
            frame.Show(True)

        
    def load_refinement(self, ref, type):
        if type == FULL_MATRIX:
            self._bond_lengths = ref.replace('.dat', '_start.pdb')
            self._std_devs = ref.replace('.dat', '.cif')
        else:
            self._bond_lengths = ref.replace('.dat', '.pdb')
        
        self.analyse()
    
        if os.path.exists(self._bond_lengths):
            self._chain_lookup = self._pdbt.get_chains(self._bond_lengths)
        
        self.res_type.Clear()
        for t in sorted(self._residues.keys()):
            if t != 'avg':
                if len(self._residues[t].keys()) > 0:
                    self.res_type.Append(self._rtypes[[x.lower() for x in self._rtypess].index(t)])
        
        self.res_type.SetSelection(0)
        self._set_residue_type('')
        
        self.draw()

    def refresh(self):
        pass


    def _save_figure(self, event):
        dlg = wx.FileDialog(self, "Save Image", os.getcwd(), "", "*.png", wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.fig.savefig(path, dpi=300, transparent=True)

        dlg.Destroy()



    def _update_sel(self, event):
        t = self._rtypess[self._residue_type].lower()
        x = self._residues[t].keys()
        x.sort()        
    
        n = list(self.residue_sel.GetSelections())
        n.sort()
        
        self._residue_selection = [ x[i] for i in n ]
        self.draw()
        

    def _set_data(self, new = False):
        #t, stdevs = self._get_inputs('cif')
        #std = self._data_widgets[1].GetCurrentSelection()
        
        #if std < len(stdevs) and std > -1:
        #    if stdevs[std] != self._std_devs:
        #        self._std_devs = stdevs[std]
        #        new = True
        
        if new:
            self.analyse()
            
            self.res_type.Clear()
            for t in sorted(self._residues.keys()):
                if t != 'avg':
                    if len(self._residues[t].keys()) > 0:
                        self.res_type.Append(self._rtypes[[x.lower() for x in self._rtypess].index(t)])
                
            self.res_type.SetSelection(0)
            self._set_residue_type('')
                
            self.draw()
    
    
    def _set_residue_type(self, event):
        self._residue_type = self._rtypes.index(self.res_type.GetValue())
        self._update_lists()
        self._highlight = -1
        
        self.draw()
        
        self.res_im = wx.Image(self.s.proot + 'Resources/gui_resources/'+self._rtypess[self._residue_type].lower()+'.png', wx.BITMAP_TYPE_PNG).Scale(self._res_size[0], self._res_size[1]).ConvertToBitmap()
        self.res.SetBitmap(self.res_im)
        
            #if 'avg' in self._residues:
            #sn = self._rtypess[self._residue_type].lower()
            #if sn in self._residues['avg']:
            #    s = self._residues['avg'][sn]
            #    self._values[3].SetLabel(str(round(s, 2)))
            #self._values[4].SetLabel(str(round(self._residues['avg']['b'], 2)))

    def _show_residue(self):
        if self._highlight == -1:
            return
    
        t  = self._rtypess[self._residue_type].lower()
        tu = self._rtypess[self._residue_type]  
    
        r = self._residues[t][self._residue_selection[self._highlight]]
        rid = self._residue_selection[self._highlight]
    
        self.residue_info_title.SetLabel('Residue Info: ' + tu + '-' + str(rid))
       
        self.res_im = wx.Image(self.s.proot + 'Resources/gui_resources/'+self._rtypess[self._residue_type].lower()+'.png', wx.BITMAP_TYPE_PNG).Scale(self._res_size[0], self._res_size[1]).ConvertToBitmap()
        memDC = wx.MemoryDC()
        #memDC.SetTextForeground((0,0,0));
        memDC.SetFont( wx.Font( 10, wx.DEFAULT, wx.NORMAL, wx.NORMAL) )
        memDC.SelectObject(self.res_im)
        
        labels = {0: [[1,115,10,20],[2,5,85,95]], 
                  1: [[1,115,10,20],[2,5,85,95]], 
                  2: [[1,80,8,20],[2,0,132,142],[3,5,40,50],[4,130,138,148],[5,147,90,100]],
                  3: [[1,115,135,145],[2,42,65,75],[2,70,2,12]]}
        
        temp1 = '%.1f' if self._residue_type == 2 else '%.3f'
        temp2 = '%.1f+%.1f' if self._residue_type == 2 else '%.3f+%.3f'
                      
        for l in labels[self._residue_type]:
            
            if len(r[l[0]]) > 3:
                str1 = temp2 % (r[l[0]][0], r[l[0]][3])
            else:
                str1 = temp1 % r[l[0]][0]
            memDC.DrawText(str1, l[1], l[2])
            memDC.DrawText('(' + '%.1f' % r[l[0]][2] + ')', l[1], l[3])
            
        if 'r' in r.keys():
            memDC.DrawText('Level: %.2f' % r['r'][2], 5, 155)
                
        memDC.SelectObject(wx.NullBitmap)
        self.res.SetBitmap(self.res_im)
        
        #if 'r' in r.keys():
            #self._dco.SetLabel(str(round(r['r'][0],3)))
            #self._sdco.SetLabel(str(round(r['r'][1],3)))
            #self._lev.SetLabel(str(round(r['r'][2],2)))
        #else:
            #self._dco.SetLabel('')
            #self._sdco.SetLabel('')
            #self._lev.SetLabel('')
    
        atoms = ['CG', 'CD', 'CG', 'CZ']
        self._coot_client.centre_residue(self._chain_lookup[rid], rid, atoms[self._residue_type])
    
    def _goto_omitted(self, event):
        selected = self._omitted[self._rtypess[self._residue_type].lower()][self.omitted_res.GetSelections()[0]]
        self._coot_client.centre_residue(selected, 'CA')
            
    
    def _on_click(self,event):
        if event.xdata:
            self._highlight = int(round(event.xdata, 0))
        else:
            self._highlight = -1
        self._show_residue()
        #self.draw()
        

    def _get_inputs(self, type='res'):
        inputs = []
        files = []
    
        for f in os.listdir(self._project.root()):
            m = re.match('(\d+)_', f)
            if m:
                res = glob.glob(self._project.root() + '/' + f + '/*.' + type)
                if len(res) > 0:
                    if res[0].find('.fcf.cif') == -1:
                        inputs.append(f)
                        files.append(res[0])
                
        return inputs, files
    

    def analyse(self):
        self._highlight = -1
        self._omitted, self._residues = self._pdbt.get_bond_lengths(self._bond_lengths)

        if os.path.exists(self._std_devs):
            print 'stds exist'
            devs = open(self._std_devs)
            asp_re = re.compile(r'CG_(\d+) OD(1|2)_\1 (\d+\.\d+)\((\d+)\)')
            glu_re = re.compile(r'CD_(\d+) OE(1|2)_\1 (\d+\.\d+)\((\d+)\)')
        
            his_re = [re.compile(r'CG_(\d+) CD2_\1 NE2_\1 (\d+.\d+)\((\d+)\)'),
                      re.compile(r'ND1_(\d+) CE1_\1 NE2_\1 (\d+.\d+)\((\d+)\)'),
                      re.compile(r'CE1_(\d+) NE2_\1 CD2_\1 (\d+.\d+)\((\d+)\)'),
                      re.compile(r'CG_(\d+) ND1_\1 CE1_\1 (\d+.\d+)\((\d+)\)'),
                      re.compile(r'CD2_(\d+) CG_\1 ND1_\1 (\d+.\d+)\((\d+)\)'),
                      re.compile(r'NE2_(\d+) CD2_\1 CG_\1 (\d+.\d+)\((\d+)\)'),
                      re.compile(r'NE2_(\d+) CE1_\1 ND1_\1 (\d+.\d+)\((\d+)\)'),
                      re.compile(r'CD2_(\d+) NE2_\1 CE1_\1 (\d+.\d+)\((\d+)\)'),
                      re.compile(r'CE1_(\d+) ND1_\1 CG_\1 (\d+.\d+)\((\d+)\)'),
                      re.compile(r'ND1_(\d+) CG_\1 CD2_\1 (\d+.\d+)\((\d+)\)'),
                      ]
                      
            arg_re = [re.compile(r'CZ_(\d+) NH2_\1 (\d+\.\d+)\((\d+)\)'),
                      re.compile(r'CZ_(\d+) NE_\1 (\d+\.\d+)\((\d+)\)'),
                      re.compile(r'CZ_(\d+) NH1_\1 (\d+\.\d+)\((\d+)\)'),
                      re.compile(r'NH2_(\d+) CZ_\1 (\d+\.\d+)\((\d+)\)'),
                      re.compile(r'NE_(\d+) CZ_\1 (\d+\.\d+)\((\d+)\)'),
                      re.compile(r'NH1_(\d+) CZ_\1 (\d+\.\d+)\((\d+)\)')
                     ]
            for s in devs:
                for t,rex in {'asp': asp_re, 'glu': glu_re}.items():
                    a = rex.match(s)
                    
                    if a:
                        if int(a.group(1)) in self._residues[t]:
                            if len(self._residues[t][int(a.group(1))][int(a.group(2))]) < 4:
                                d = pow(10, len((a.group(3).split('.'))[1]))
                                self._residues[t][int(a.group(1))][int(a.group(2))].append(float(a.group(4))/d)
                                
                for id,rex in enumerate(his_re):
                    a = rex.match(s)
                    
                    if a:
                        if int(a.group(1)) in self._residues['his']:
                            if len(a.group(2).split('.')) > 1:
                                d = pow(10, len((a.group(2).split('.'))[1]))
                            else:
                                d = 1
                        
                            self._residues['his'][int(a.group(1))][(id%5)+1].append(float(a.group(3))/d)
                            
                for id,rex in enumerate(arg_re):
                    a = rex.match(s)
                    if a:
                        if int(a.group(1)) in self._residues['arg']:
                            d = pow(10, len((a.group(2).split('.'))[1]))
                            self._residues['arg'][int(a.group(1))][(id%3)+1].append(float(a.group(3))/d)
            
            devs.close()
            
        for type in self._residues.keys():
            std_arr = []
            for res in self._residues[type]:
                if type == 'asp'or type == 'glu' or type == 'his':
                    r = self._residues[type][res]
                                        
                    if len(r[1]) == 4 and len(r[2]) == 4:
                        std_arr.append(r[1][3])
                        std_arr.append(r[2][3])
                    
                        delta = abs(r[1][0] - r[2][0])
                        sigdel = math.sqrt(pow(r[1][3],2)+pow(r[2][3],2))
                        siglev = delta/sigdel
                        bavg = (r[1][2]+r[2][2])/2
                        
                        self._residues[type][res]['r'] = [delta, sigdel, siglev, r[1][1], bavg]
            
            if len(std_arr) > 0:
                self._residues['avg'][type] = sum(std_arr)/len(std_arr)
        
        self._update_lists()
        self._show_residue()

        
    def _update_lists(self):
        t  = self._rtypess[self._residue_type].lower()
        tu = self._rtypess[self._residue_type]
                
        x   = self._residues[t].keys()
        x.sort()        
        self._residue_selection = [ k for k in x ]

        self.omitted_res.Clear()
        for i in range(len(self._omitted[t])):
            self.omitted_res.Append(tu + '-' + str(self._omitted[t][i]))
            
        self.residue_sel.Clear()
        all = self._residues[t].keys()
        all.sort()
        for id,i in enumerate(all):
            self.residue_sel.Append(tu + '-' + str(i))
            self.residue_sel.SetSelection(id, True)
                

    def draw(self):
        self.ax1.cla()
        self.ax2.cla()
    
        self.ax2.set_ylabel('B Factor ($A^2$)', fontsize=9)  

        t  = self._rtypess[self._residue_type].lower()
        tu = self._rtypess[self._residue_type]

        x = self._residue_selection
        
        xs  = [ tu + '-' + str(k) for k in x ]
        xa  = range(len(self._residue_selection))
        
        l1  = [self._residues[t][k][1][0] for k in x ]
        l2  = [self._residues[t][k][2][0] for k in x ]
        
        if len(x) > 0:
            if len(self._residues[t][k][1]) == 4:
                el1 = [self._residues[t][k][1][3] for k in x ]
            else:
                el1 = [ 0 for k in x ]
                
            if len(self._residues[t][k][2]) == 4:
                el2 = [self._residues[t][k][2][3] for k in x ]
            else:
                el2 = [ 0 for k in x ]

            b1  = [self._residues[t][k][1][2] for k in x ]
            b2  = [self._residues[t][k][2][2] for k in x ]
            
            if self._residue_type == 0 or self._residue_type == 1:
                dg = 'C-O$\gamma$' if self._residue_type == 0 else 'C-O$\delta$'
               
                self.ax1.errorbar(xa, l1, yerr=el1, fmt='ro', label=dg+'1')
                self.ax1.errorbar(xa, l2, yerr=el2, fmt='b^', label=dg+'2')
                self.ax2.plot(xa, b1, 'go', label='B('+dg+'1)'), 
                self.ax2.plot(xa, b2, 'y^', label='B('+dg+'2)')
                self.ax1.axhline(y=1.21, color='0.7')
                self.ax1.axhline(y=1.31, color='0.7')
                self.ax1.axhspan(1.327, 1.293, alpha=0.6, color='0.9')
                self.ax1.axhspan(1.194, 1.226, alpha=0.6, color='0.9')
                self.ax1.set_ylim(min(l1+l2+[1.2])-0.2, max(l1+l2+[1.32])+0.05)
                self.ax1.set_ylabel('C-O (A)', fontsize=9)
            
                self._to_save = [['Residue', 'C-OD1', 'ESDS(C-OD1)', 'B(C-OD1)', 'C-OD2', 'ESDS(C-OD2)', 'B(C-OD2)', 'D(C-O)', 'S(D(C-O)', 'Level']]
                for i,k in enumerate(x):
                    diff = abs(l2[i]-l1[i])
                    sig = math.sqrt(math.pow(el1[i],2) + math.pow(el1[i],2))
                    
                    if sum(el1) == 0 and sum(el2) == 0:
                        self._to_save.append([k, l1[i], 'N/A', b1[i], l2[i], 'N/A', b2[i], diff, 'N/A', 'N/A'])
                    else:
                        self._to_save.append([k, l1[i], el1[i], b1[i], l2[i], el2[i], b2[i], diff, sig, diff/sig])
        
        
            # his CG CD2 NE2, ND1 CE1 NE2
            elif self._residue_type == 2:
                self.ax1.errorbar(xa, l1, yerr=el1, fmt='ro', label='CG-CD2-NE2')
                self.ax1.errorbar(xa, l2, yerr=el2, fmt='b^', label='ND1-CE1-NE2')
                
                l3  = [self._residues[t][k][3][0] for k in x ]
                b3  = [self._residues[t][k][3][2] for k in x ]
                l4  = [self._residues[t][k][4][0] for k in x ]
                b4  = [self._residues[t][k][4][2] for k in x ]
                l5  = [self._residues[t][k][5][0] for k in x ]
                b5  = [self._residues[t][k][5][2] for k in x ]
                
                if len(self._residues[t][k][3]) == 4:
                    el3 = [self._residues[t][k][3][3] for k in x ]
                else:
                    el3 = [ 0 for k in x ]
        
                if len(self._residues[t][k][4]) == 4:
                    el4 = [self._residues[t][k][5][3] for k in x ]
                else:
                    el4 = [ 0 for k in x ]

                if len(self._residues[t][k][5]) == 4:
                    el5 = [self._residues[t][k][5][3] for k in x ]
                else:
                    el5 = [ 0 for k in x ]
                
                self.ax1.errorbar(xa, l3, yerr=el3, fmt='g^', label='CD2-NE2-CE1')
                self.ax1.errorbar(xa, l4, yerr=el4, fmt='c^', label='CE1-ND1-CG')
                self.ax1.errorbar(xa, l5, yerr=el5, fmt='m^', label='CD2-CG-ND1')
                
                self.ax2.plot(xa, b1, 'go', xa, b2, 'y^')
                self.ax1.axhline(y=111.2, color='0.7')
                self.ax1.axhline(y=109.3, color='0.7')
                self.ax1.axhline(y=107.5, color='0.7')
                self.ax1.axhline(y=107.2, color='0.7')
                self.ax1.set_ylim(95, 115)
                self.ax1.set_ylabel('Angle ($^\circ$)', fontsize=9)
            
                angles = ['CG-CD2-NE2', 'ND1-CE1-NE2', 'CD2-NE2-CE1', 'CE1-ND1-CG', 'CD2-CG-ND1']
                cols = [ [ x, 'ESDS('+x+')', 'B('+x+')'] for x in angles ]
                    
                self._to_save = [['Residue', 'D(ang)', 'S(D(ang))', 'Level']]
                self._to_save[0][1:1] = cols
                for i,k in enumerate(xs):
                    diff = abs(l2[i]-l1[i])
                    sig = math.sqrt(math.pow(el1[i],2) + math.pow(el1[i],2))
                    
                    if sum(el1) == 0 and sum(el2) == 0:
                        self._to_save.append([k, l1[i], 'N/A', b1[i], l2[i], 'N/A', b2[i], l3[i], 'N/A', b3[i], l4[i], 'N/A', b4[i], l5[i], 'N/A', b5[i], diff, 'N/A', 'N/A'])
                    else:
                        self._to_save.append([k, l1[i], el1[i], b1[i], l2[i], el2[i], b2[i], l3[i], el3[i], b3[i], l4[i], el4[i], b4[i], l5[i], el5[i], b5[i], diff, sig, diff/sig])
                    
            # arg CZ NH2, CZ NE, CZ NH1, CD NE?        
            elif self._residue_type == 3:
                l3  = [self._residues[t][k][3][0] for k in x ]
                b3  = [self._residues[t][k][3][2] for k in x ]
                
                if len(self._residues[t][k][3]) == 4:
                    el3 = [self._residues[t][k][3][3] for k in x ]
                else:
                    el3 = [ 0 for k in x ]
                
                self.ax1.errorbar(xa, l1, yerr=el1, fmt='bo', label='CZ-NH2')
                self.ax1.errorbar(xa, l2, yerr=el2, fmt='r^', label='CZ-NE')
                self.ax1.errorbar(xa, l3, yerr=el3, fmt='ms', label='CZ-NH1')                
                self.ax2.plot(xa, b1, 'go', label='B(CZ-NH2)')
                self.ax2.plot(xa, b2, 'y^', label='B(CZ-NE)')
                self.ax2.plot(xa, b3, 'cs', label='B(CZ-NH1)')
                self.ax1.set_ylim(min(l1+l2)-0.2, max(l1+l2)+0.05)
                self.ax1.set_ylabel('CZ-X (A)', fontsize=9)
                self.ax1.axhline(y=1.326, color='0.7')
                self.ax1.axhline(y=1.41, color='0.7')

                self._to_save = [['Residue', 'CZ-NH2', 'ESDS(CZ-NH2)', 'B(CZ-NH2)', 'CZ-NE', 'ESDS(CZ-NE)', 'B(CZ-NE)', 'CZ-NH1', 'ESDS(CCZ-NH1)', 'B(CZ-NH1)', 'D(CZ-NH2 - CZ-NE)', 'S(D(CZ-NH2 - CZ-NE))', 'Level']]
                for i,k in enumerate(xs):
                    diff = abs(l2[i]-l1[i])
                    sig = math.sqrt(math.pow(el1[i],2) + math.pow(el1[i],2))
                    
                    if sum(el1) == 0 and sum(el2) == 0:
                        self._to_save.append([k, l1[i], 'N/A', b1[i], l2[i], 'N/A', b2[i], l3[i], 'N/A', b3[i], diff, 'N/A', 'N/A'])
                    else:
                        self._to_save.append([k, l1[i], el1[i], b1[i], l2[i], el2[i], b2[i], l3[i], el3[i], b3[i], diff, sig, diff/sig])

            if sum(el1) == 0 and sum(el2) == 0:
                txt = 'Average B factor: %.1f' % (self._residues['avg']['b'])
            else:
                txt = 'Average B factor: %.1f, Average sigma: %.3f' % (self._residues['avg']['b'],sum(el1+el2)/(len(el1)+len(el2)))
            
            self.averages.SetLabel(txt)
            self.ax2.axhline(y=self._residues['avg']['b'], color=(0.5,0.5,0), ls='--')
            self.ax2.set_ylim(min(b1+b2)-2, max(b1+b2)+20)
            
            #self.ax2.set_xlim(-1, len(x))
            self.ax1.set_xlim(-1, len(x))
            self.ax1.set_xticks(xa)
            self.ax1.set_xticklabels(xs, rotation='vertical', size=8)        


            self.ax1.tick_params(labelsize=8)
            self.ax2.tick_params(labelsize=8)

            if self._highlight > -1:
                self.ax1.axvspan(self._highlight-0.5, self._highlight+0.5, alpha=0.3, color='0.9')

            handles, labels = self.ax1.get_legend_handles_labels()
            handles2, labels2 = self.ax2.get_legend_handles_labels()
            leg = self.ax2.legend(handles+handles2, labels+labels2, prop={'size':8}, numpoints=1, loc='best', fancybox=True)
            leg.get_frame().set_alpha(0.5)

        self.canvas.draw()
        