import re
import os
import glob
from Project import Project
from Tab import Tab
import iotbx.pdb

import matplotlib
matplotlib.use('WXAgg', False)

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas
import matplotlib.pyplot as plt

import math
import wx

DEBUG = 1

def debug_print(text):
    if DEBUG:
        print text

class Analyse(Tab): 

    def __init__(self, nb):
        Tab.__init__(self, nb)

        self.fig = Figure((5.0, 4.0), dpi=100)
        col = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND)
        self.fig.patch.set_facecolor((col[0]/255.0, col[1]/255.0, col[2]/255.0))
        self.canvas = FigCanvas(self, -1, self.fig)             

        self.res = wx.StaticBitmap(self, size=(200,237))
        self.res.SetBitmap(wx.EmptyImage( 200,237 ).ConvertToBitmap())

        self._rtypes = ['Aspartate', 'Glutamate', 'Histidine', 'Arginine']
        self._rtypess = ['Asp', 'Glu', 'His', 'Arg']
        
        self.ax1 = self.fig.add_subplot(111)
        self.ax1.set_position([0.10,0.153,0.80,0.81])
        self.ax2 = self.ax1.twinx()
        self.ax1.tick_params(labelsize=8)
        self.ax2.tick_params(labelsize=8)   
        
        self._highlight = 0
        
        self._bond_lengths = ''
        self._std_devs = ''
        self._residue_selection = []
        
        self._residue_type = 0
        
        self._residues = {'asp': {}, 'glu': {}, 'his': {}, 'arg': {}}
        self._omitted = {'asp': [], 'glu': [], 'his': [], 'arg': []}
        
        self.omitted_title = wx.StaticBox( self, -1, "Omitted" ) 
        self.omitted_sizer = wx.StaticBoxSizer( self.omitted_title, wx.HORIZONTAL)        
        
        self.selected_title = wx.StaticBox( self, -1, "Displayed" ) 
        self.selected_sizer = wx.StaticBoxSizer( self.selected_title, wx.HORIZONTAL)        
        
        self.residue_info_title = wx.StaticBox( self, -1, "Residue Info: " ) 
        self.residue_info_sizer = wx.StaticBoxSizer( self.residue_info_title, wx.HORIZONTAL)        
        
        self._labels = [ 
                        wx.StaticText(self, -1, 'D(C-O)'),
                        wx.StaticText(self, -1, 'S(D(C-O))'),
                        wx.StaticText(self, -1, 'Level'),
                        
                        wx.StaticText(self, -1, 'Avg S'),
                        wx.StaticText(self, -1, 'Avg B'),
                      ]
                      
        self._values = [ wx.StaticText(self, -1, '') for x in range(len(self._labels)) ]
                              
                              
        self.residue_info = wx.GridSizer(rows=5, cols=2, vgap=5, hgap=5)
        for i in range(len(self._labels)):
            self.residue_info.Add(self._labels[i], 0, wx.EXPAND)
            self.residue_info.Add(self._values[i], 0, wx.EXPAND)
        
        self.residue_info_sizer.Add(self.residue_info, 0)
        self.residue_info_sizer.Add(self.res, 0)        
        
        self.residue_sel = wx.ListBox(self, 26, wx.DefaultPosition, (80, 100), [], wx.LB_MULTIPLE)
        self.residue_sel.Bind(wx.EVT_LISTBOX, self._update_sel)
        self.omitted_res = wx.ListBox(self, 26, wx.DefaultPosition, (80, 100), [], wx.LB_SINGLE)
        self.omitted_res.Bind(wx.EVT_LISTBOX, self._goto_omitted)
                
        self._data_widgets = [ wx.StaticText(self, -1, 'Bond Lengths'),
                               wx.ComboBox(self, -1, '', choices=[], style=wx.CB_READONLY),
                               wx.StaticText(self, -1, 'Standard Deviations'),
                               wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY),
                               wx.StaticText(self, -1, 'Residue Type'),
                               wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY)]

        self._data_widgets[1].Bind(wx.EVT_COMBOBOX, self._set_data)
        self._data_widgets[3].Bind(wx.EVT_COMBOBOX, self._set_data)
        self._data_widgets[5].Bind(wx.EVT_COMBOBOX, self._set_residue_type)
        self._data_widgets[5].SetStringSelection('Aspartate')

        self.data_box = wx.GridSizer(rows=3, cols=2, vgap=5, hgap=5)
        for i in range(len(self._data_widgets)):
            self.data_box.Add(self._data_widgets[i], 0, wx.EXPAND)  
        
        self.omitted_sizer.Add(self.omitted_res)
        self.selected_sizer.Add(self.residue_sel)
        
        self.button_sizer = wx.BoxSizer(wx.VERTICAL)
        
        coot = wx.BitmapButton(self, 1, wx.Image('Resources/Icons/coot_logo.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap())
        pymol = wx.BitmapButton(self, 2, wx.Image('Resources/Icons/pymol.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap())
        plot = wx.BitmapButton(self, 3, wx.Image('Resources/Icons/plot_tiny.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap())        
        self.button_sizer.Add(coot, 0, wx.EXPAND)
        self.button_sizer.Add(pymol, 0, wx.EXPAND)                        
        self.button_sizer.Add(plot, 0, wx.EXPAND)                      
        plot.Bind(wx.EVT_BUTTON, self._save_figure)
                                                 
        self.ressel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ressel_sizer.Add(self.omitted_sizer)
        self.ressel_sizer.Add(self.selected_sizer)
        self.ressel_sizer.Add(self.button_sizer)
                                            
        self.residue_box = wx.BoxSizer(wx.VERTICAL)
        self.residue_box.Add(self.data_box)
        self.residue_box.Add(self.residue_info_sizer, 0, wx.EXPAND | wx.TOP, 10)
        self.residue_box.Add(self.ressel_sizer)
        
        self.main = wx.BoxSizer(wx.HORIZONTAL)
        self.main.Add(self.residue_box, 0, wx.ALL, 10)
        self.main.Add(self.canvas, 0, wx.ALL, 5)
        
        self.SetSizer(self.main)
        self.main.Fit(self)
        
        self.canvas.mpl_connect('button_press_event', self._on_click)
        self.update_inputs()


    def refresh(self):
        self.update_inputs()
        

    def update_inputs(self):
        bls,t = self._get_inputs('pdb')
        stdevs,t = self._get_inputs('cif')
        
        self._data_widgets[1].Clear()
        for b in bls:
            self._data_widgets[1].Append(b)
            
        self._data_widgets[3].Clear()
        for s in stdevs:
            self._data_widgets[3].Append(s)

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
        

    def _set_data(self, event):
        t, bls = self._get_inputs('pdb')
        t, stdevs = self._get_inputs('cif')    
        
        bl = self._data_widgets[1].GetCurrentSelection()
        std = self._data_widgets[3].GetCurrentSelection()
        
        new = False
        if bl < len(bls) and bl > -1:
            if bls[bl] != self._bond_lengths:
                self._bond_lengths = bls[bl]
                self._coot_client.load_refinement(self._bond_lengths.replace('.pdb', ''))
                new = True
            
        if std < len(stdevs) and std > -1:
            if stdevs[std] != self._std_devs:
                self._std_devs = stdevs[std]
                new = True
        
        if new:
            self.analyse()
            
            self._data_widgets[5].Clear()
            for t in sorted(self._residues.keys()):
                if t != 'avg':
                    if len(self._residues[t].keys()) > 0:
                        self._data_widgets[5].Append(self._rtypes[[x.lower() for x in self._rtypess].index(t)])
                
            self._data_widgets[5].SetSelection(0)
            self._set_residue_type('')
                
            self.draw()
    a=
    
    def _set_residue_type(self, event):
        self._residue_type = self._rtypes.index(self._data_widgets[5].GetValue())
        self._update_lists()
        self.draw()
        
        self.res_im = wx.Image('Resources/'+self._rtypess[self._residue_type].lower()+'.png', wx.BITMAP_TYPE_PNG).Scale(200,236).ConvertToBitmap()
        self.res.SetBitmap(self.res_im)
        
        if 'avg' in self._residues:
            sn = self._rtypess[self._residue_type].lower()
            if sn in self._residues['avg']:
                s = self._residues['avg'][sn]
                self._values[3].SetLabel(str(round(s, 2)))
            self._values[4].SetLabel(str(round(self._residues['avg']['b'], 2)))

    def _show_residue(self):
        if self._highlight == -1:
            return
    
        t  = self._rtypess[self._residue_type].lower()
        tu = self._rtypess[self._residue_type]    
    
        r = self._residues[t][self._residue_selection[self._highlight]]
        
        self.residue_info_title.SetLabel('Residue Info: ' + tu + '-' + str(self._residue_selection[self._highlight]))
        
        self.res_im = wx.Image('Resources/'+self._rtypess[self._residue_type].lower()+'.png', wx.BITMAP_TYPE_PNG).Scale(200,236).ConvertToBitmap()
        memDC = wx.MemoryDC()
        memDC.SetFont( wx.Font( 11, wx.DEFAULT, wx.NORMAL, wx.NORMAL) )
        memDC.SelectObject(self.res_im)
        
        labels = {0: [[1,85,10,20],[2,0,105,115]], 
                  1: [[1,85,10,20],[2,0,105,115]], 
                  2: [[1,85,10,20],[2,0,105,115]], 
                  3: [[1,95,105,115],[2,30,45,55],[2,95,20,30]]}
        for l in labels[self._residue_type]:
            
            if len(r[l[0]]) > 3:
                str1 = str(round(r[l[0]][0],2)) + '+' + str(r[l[0]][3])
            else:
                str1 = str(round(r[l[0]][0],2))
            memDC.DrawText(str1, l[1], l[2])
            memDC.DrawText('(' + str(round(r[l[0]][2],1)) + ')', l[1], l[3])
            
        memDC.SelectObject( wx.NullBitmap )
        self.res.SetBitmap(self.res_im)
        
        if 'r' in r.keys():
            self._values[0].SetLabel(str(round(r['r'][0],3)))
            self._values[1].SetLabel(str(round(r['r'][1],3)))
            self._values[2].SetLabel(str(round(r['r'][2],2)))
        else:
            self._values[0].SetLabel('')
            self._values[1].SetLabel('')
            self._values[2].SetLabel('')
            
        self._coot_client.centre_residue(self._residue_selection[self._highlight], 'CA')
    
    def _goto_omitted(self, event):
        selected = self._omitted[self.omitted_res.GetSelections()[0]]
        
        self._coot_client.centre_residue(selected, 'CA')
            
    
    def _on_click(self,event):
        if event.xdata:
            self._highlight = int(round(event.xdata, 0))
        else:
            self._highlight = -1
        self._show_residue()
        self.draw()
        

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
        self._omitted = {'asp': [], 'glu': [], 'his': [], 'arg': []}
        self._residues = {'asp': {}, 'glu': {}, 'his': {}, 'arg': {}}

        self._highlight = -1

        b_avg_array = []
        rlist = {'asp': {}, 'glu': {}, 'his': {}, 'arg': {}}
        t = {'ASP': [' CG ', ' OD1', ' OD2'], 'GLU': [' CD ', ' OE1', ' OE2']} 
        pdb = iotbx.pdb.input(file_name=self._bond_lengths)
        for a in pdb.atoms_with_labels():
            if a.resname in ['ASP', 'ALA', 'HIS', 'ARG', 'LYS', 'GLN', 'GLU', 
                            'TYR', 'PRO', 'LEU', 'ILE', 'MET', 'VAL', 'SER',
                            'ASN', 'CYS', 'GLY', 'TRP', 'PHE', 'THR', 'LYS']:
                b_avg_array.append(a.b)
        
            rid = int(a.resid())
            if a.resname in t.keys():
                n = t[a.resname]
                rn = a.resname.lower()
                
                if a.occ < 1:
                    if rid not in self._omitted[rn]:
                        self._omitted[rn].append(rid)
                    
                else:
                    if a.name in n:
                        id = n.index(a.name)
                        if rid in rlist[rn].keys():
                            rlist[rn][rid][id] = a
                        else:
                            rlist[rn][rid] = {id:a}
                             
            # his CG CD2 NE2, ND1 CE1 NE2
            elif a.resname == 'HIS':
                if a.occ < 1:
                    if rid not in self._omitted['his']:
                        self._omitted['his'].append(rid)
                    
                else:
                    atoms = [' CG ', ' CD2', ' NE2', ' ND1', ' CE1']
                    if a.name in atoms:
                        id = atoms.index(a.name)
                        if rid in rlist['his'].keys():
                            rlist['his'][rid][id] = a
                        else:
                            rlist['his'][rid] = {id:a}
            
            # arg CZ NH2, CZ NE, CZ NH1, CD NE?
            elif a.resname == 'ARG':
                if a.occ < 1:
                    if rid not in self._omitted['arg']:
                        self._omitted['arg'].append(rid)
                    
                else:
                    atoms = [' CZ ', ' NH2', ' NE ', ' NH1']
                    if a.name in atoms:           
                        id = atoms.index(a.name)
                        if rid in rlist['arg'].keys():
                            rlist['arg'][rid][id] = a
                        else:
                            rlist['arg'][rid] = {id:a}

        for t in rlist.keys():
            for rid,res in rlist[t].iteritems():
                if t == 'asp' or t == 'glu':
                    if len(res) == 3:
                        self._residues[t][rid] = {1: [res[0].distance(res[1]), res[1].occ, res[1].b], 2: [res[0].distance(res[2]), res[2].occ, res[2].b]}

                elif t == 'his':
                    if len(res) == 5:
                        self._residues[t][rid] = {1: [res[1].angle(res[0], res[2], True), res[0].occ, res[0].b], 2: [res[4].angle(res[3], res[2], True), res[3].occ, res[3].b]}

                elif t == 'arg':
                    if len(res) == 4:
                        self._residues[t][rid] = {1: [res[0].distance(res[1]), res[1].occ, res[1].b], 2: [res[0].distance(res[2]), res[2].occ, res[2].b], 3: [res[0].distance(res[3]), res[3].occ, res[3].b]}

        self._residues['avg'] = {'b': (sum(b_avg_array)/len(b_avg_array))}

        if os.path.exists(self._std_devs):
            devs = open(self._std_devs)
            asp_re = re.compile(r'CG_(\d+) OD(1|2)_\1 (\d+\.\d+)\((\d+)\)')
            glu_re = re.compile(r'CD_(\d+) OE(1|2)_\1 (\d+\.\d+)\((\d+)\)')
        
            his_re = [re.compile(r'CG_(\d+) CD2_\1 NE2_\1 (\d+)\((\d+)\)'),
                      re.compile(r'ND1_(\d+) CE1_\1 NE2_\1 (\d+)\((\d+)\)'),
                      re.compile(r'NE2_(\d+) CD2_\1 CG_\1 (\d+)\((\d+)\)'),
                      re.compile(r'NE2_(\d+) CE1_\1 ND1_\1 (\d+)\((\d+)\)'),
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
                            self._residues['his'][int(a.group(1))][(id%2)+1].append(float(a.group(3)))
                            
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
            self.residue_sel.Append(tu + ' - ' + str(i))
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
                self.ax1.errorbar(xa, l1, yerr=el1, fmt='ro', label='$C-O\gamma1')
                self.ax1.errorbar(xa, l2, yerr=el2, fmt='b^', label='$C-O\gamma2')
                self.ax2.plot(xa, b1, 'go', xa, b2, 'y^')
                self.ax1.axhline(y=1.21, color='0.7')
                self.ax1.axhline(y=1.31, color='0.7')
                self.ax1.axhspan(1.327, 1.293, alpha=0.6, color='0.9')
                self.ax1.axhspan(1.194, 1.226, alpha=0.6, color='0.9')
                self.ax1.set_ylim(min(l1+l2+[1.2])-0.2, max(l1+l2+[1.32])+0.05)
                self.ax1.set_ylabel('C-O (A)', fontsize=9)
                                      
            # his CG CD2 NE2, ND1 CE1 NE2
            elif self._residue_type == 2:
                self.ax1.errorbar(xa, l1, yerr=el1, fmt='ro', label='CG-CD2-NE2')
                self.ax1.errorbar(xa, l2, yerr=el2, fmt='b^', label='ND1-CE1-NE2')
                self.ax2.plot(xa, b1, 'go', xa, b2, 'y^')
                self.ax1.axhline(y=111.2, color='0.7')
                self.ax1.axhline(y=109.3, color='0.7')
                self.ax1.axhline(y=107.5, color='0.7')
                self.ax1.axhline(y=107.2, color='0.7')
                self.ax1.set_ylim(95, 115)
                self.ax1.set_ylabel('Angle', fontsize=9)
            
            # arg CZ NH2, CZ NE, CZ NH1, CD NE?        
            elif self._residue_type == 3:
                l3  = [self._residues[t][k][3][0] for k in x ]
                b3  = [self._residues[t][k][3][2] for k in x ]
                
                if len(self._residues[t][k][3]) == 4:
                    el3 = [self._residues[t][k][3][3] for k in x ]
                else:
                    el3 = [ 0 for k in x ]
                
                self.ax1.errorbar(xa, l1, yerr=el1, fmt='ro', label='CZ-NH2')
                self.ax1.errorbar(xa, l2, yerr=el2, fmt='b^', label='CZ-NE')
                self.ax1.errorbar(xa, l3, yerr=el3, fmt='b^', label='CZ-NH1')                
                self.ax2.plot(xa, b1, 'go', xa, b2, 'y^', xa, b3)
                self.ax1.set_ylim(min(l1+l2)-0.2, max(l1+l2)+0.05)
                self.ax1.set_ylabel('NZ-X (A)', fontsize=9)
                self.ax1.axhline(y=1.326, color='0.7')
                self.ax1.axhline(y=1.41, color='0.7')            
            
            self.ax2.axhline(y=self._residues['avg']['b'], color=(0.5,0.5,0), ls='--')
            self.ax2.set_ylim(min(b1+b2)-2, max(b1+b2)+20)
            
            self.ax2.set_xlim(-1, len(x))
            self.ax1.set_xticks(xa)
            self.ax1.set_xticklabels(xs, rotation='vertical', size=8)        

            self.ax1.tick_params(labelsize=8)
            self.ax2.tick_params(labelsize=8)

            if self._highlight > -1:
                self.ax1.axvspan(self._highlight-0.5, self._highlight+0.5, alpha=0.3, color='0.9')

            #handles, labels = self.ax1.get_legend_handles_labels()
            #handles2, labels2 = self.ax2.get_legend_handles_labels()
            #self.ax2.legend(handles+handles2, labels+labels2)

        self.canvas.draw()
        
    