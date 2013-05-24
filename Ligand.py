import os
import wx
import re

import matplotlib
matplotlib.use('WXAgg')
matplotlib.interactive(True)

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from mpl_toolkits.mplot3d import Axes3D, proj3d
import matplotlib.ticker as ticker

from iotbx import pdb
from wxtbx import bitmaps

import numpy as np

class Ligand(wx.Frame):

    def __init__(self, pdb_file='test/3HLX.pdb', name='', *args, **kwargs):
        wx.Frame.__init__(self,None,-1,'Ligand Explorer: ' + name, size=(500,300))
        
        self.fig = Figure((5.0, 5.0), dpi=100)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        
        if os.path.exists(pdb_file):
            p = pdb.input(pdb_file)
        else:
            self.Destroy()
            
        
        cols = {'C': 'black', 'O': 'red', 'N': 'blue', 'S': 'green', 'H': 'white'}

        self._refresh = False
        self._labs = []
        self._alabs = []

        self._ligands = {}
        for a in p.atoms_with_labels():
            if a.resname not in ['ARG', 'HIS', 'LYS', 'ASP', 'GLU', 'SER', 'THR',
                                 'ASN', 'GLN', 'CYS', 'GLY', 'PRO', 'ALA', 'ILE',
                                 'LEU', 'MET', 'PHE', 'TRP', 'TYR', 'VAL', 'HOH', 'DOD']:
                key = '%s %s-%s' % (a.chain_id, a.resname, a.resid().strip())
                if not key in self._ligands:
                    self._ligands[key] = {'at': [], 'id': a.resid().strip()}
            
                self._ligands[key]['at'].append(a)

        to_del = []
        for k,l in self._ligands.iteritems():
            l['c'] = np.array([ a.xyz for a in l['at']])
            l['col'] = np.array([ cols.get(a.element.strip() if a.element.strip() else a.name.strip()[0], 'black') for a in l['at']])
            if len(l['at']) < 3:
                to_del.append(k)

            l['rex'] = {}
            l['stdevs'] = {}
            for a in l['at']:
                an = a.name.strip()
                for b in l['at']:
                    bn = b.name.strip()
                    if a is not b:
                        if a.distance(b) < 1.8:
                            l['rex'][an+'-'+bn] = [re.compile(an+'_'+l['id']+' '+bn+'_'+l['id']+' (\d+\.?\d+)\((\d+)\)'),
                            re.compile(bn+'_'+l['id']+' '+an+'_'+l['id']+' (\d+\.?\d+)\((\d+)\)')]
    
    
        for d in to_del:
            del self._ligands[d]
        
        
        if 'stdevs' in kwargs:
            if os.path.exists(kwargs['stdevs']):
                stdevs = open(kwargs['stdevs'])
                start = False
                for l in stdevs:
                    if  '_geom_bond_atom_site_label_1' in l:
                        start = True
                    if '_geom_angle_atom_site_label_1' in l:
                        break
                
                    if start:
                        for k,lig in self._ligands.iteritems():
                            for id,rs in lig['rex'].iteritems():
                                for r in rs:
                                    m = r.match(l)
                                    if m:
                                        d = pow(10, len((m.group(1).split('.'))[1]))
                                        lig['stdevs'][id] = float(m.group(2))/d

                stdevs.close()
    
        
        self.ax1 = self.fig.add_subplot(111, projection='3d')
        self.ax1.set_position([-0.2, -0.2, 1.4, 1.4])

        self.toolbar = wx.ToolBar(self, style=wx.TB_3DBUTTONS|wx.TB_TEXT)                
                
        self.res_type = wx.ComboBox(self.toolbar, -1, choices=sorted(self._ligands.keys()), style=wx.CB_READONLY)
        self.res_type.Bind(wx.EVT_COMBOBOX, self._load_residue)

        close = self.toolbar.AddLabelTool(wx.ID_ANY, 'Close', bitmaps.fetch_icon_bitmap("actions", "no"))
        self.toolbar.AddSeparator()
        self.toolbar.AddControl(self.res_type)
        self.toolbar.AddSeparator()
        zi = self.toolbar.AddLabelTool(wx.ID_ANY, 'Zoom In', bitmaps.fetch_icon_bitmap("actions", "viewmag+"))
        zo = self.toolbar.AddLabelTool(wx.ID_ANY, 'Zoom Out', bitmaps.fetch_icon_bitmap("actions", "viewmag-"))
        self.toolbar.AddSeparator()
        save = self.toolbar.AddLabelTool(wx.ID_ANY, 'Save Figure', bitmaps.fetch_icon_bitmap("actions", "save_all"))
    
        self.Bind(wx.EVT_TOOL, self._close, close)
        self.Bind(wx.EVT_TOOL, self._save_figure, save)
        self.Bind(wx.EVT_TOOL, self._zoom_in, zi)
        self.Bind(wx.EVT_TOOL, self._zoom_out, zo)
                
        self.SetToolBar(self.toolbar)
        self.toolbar.Realize()
                
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        #self.sizer.Add(self.toolbar)
        self.sizer.Add(self.canvas, 1, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(self.sizer)
        self.Fit()

        self._load_residue('')
            
        self.canvas.mpl_connect('button_release_event', self.disable_refresh)
        self.canvas.mpl_connect('button_press_event', self.enable_refresh)
        self.canvas.mpl_connect('motion_notify_event', self.do_refresh)


    def _close(self, e):
        self.Destroy()
            
    def _zoom_in(self, e):
        self.ax1.dist -= 0.4
        self.refresh()
            
    def _zoom_out(self, e):
        self.ax1.dist += 0.4
        self.refresh()
            
    def _save_figure(self, e):
        dlg = wx.FileDialog(self, 'Save Image', os.getcwd(), '', '*.png', wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.fig.savefig(path, dpi=300, transparent=True)
        
        dlg.Destroy()
    
    def _load_residue(self, event):
        r = self._ligands[self.res_type.GetValue()]
        
        self.ax1.cla()
        self.ax1.mouse_init()
        self.ax1.w_xaxis.set_major_locator(ticker.NullLocator())
        self.ax1.w_yaxis.set_major_locator(ticker.NullLocator())
        self.ax1.w_zaxis.set_major_locator(ticker.NullLocator())
        self.ax1.set_frame_on(False)
        self.ax1.set_axis_off()
        
        self.ax1.scatter3D(r['c'][:,0], r['c'][:,1], r['c'][:,2], c=r['col'], s=400)
        
        m = max([max(r['c'][:,i])-min(r['c'][:,i]) for i in range(3)])

        for i,ax in enumerate(['set_xlim', 'set_ylim', 'set_zlim']):
            mn = min(r['c'][:,i])
            mx = max(r['c'][:,i])
            
            mid = mn+((mx - mn)/2)

            getattr(self.ax1, ax)(mid-(m/2), mid+(m/2))
                
        self._labs = []
        self._alabs = []
        for i,a in enumerate(r['at']):
            ac = r['c'][i]
            x2, y2, _ = proj3d.proj_transform(ac[0],ac[1],ac[2], self.ax1.get_proj())
            for j,b in enumerate(r['at']):
                if a is not b:
                    bc = r['c'][j]
                    if a.distance(b) < 1.8:
                        std = ''
                        
                        n = a.name.strip()+'-'+b.name.strip()
                        if n in r['stdevs']:
                            std = ' (' + str(r['stdevs'][n]) + ')'
                        
                        self.ax1.plot([ac[0], bc[0]], [ac[1], bc[1]], [ac[2], bc[2]], 'k-')
                        x3, y3, _ = proj3d.proj_transform(bc[0],bc[1],bc[2], self.ax1.get_proj())
                        self._labs.append([self.ax1.annotate('%.2f' % a.distance(b) + std, xy=self._midp(x2,y2,x3,y3), size=6), ac, bc])
            
            self._alabs.append([self.ax1.annotate(a.name.strip(), xy=(x2+0.002,y2+0.002), size=7), ac])

        self.canvas.draw()
            
    def _midp(self, x, y, x2, y2):
        return (((x2-x)/2) + x + 0.001, ((y2-y)/2) + y + 0.001)
            
    def enable_refresh(self, event):
        self._refresh = True
    
    def disable_refresh(self, event):
        self._refresh = False
    
    def do_refresh(self, event):
        if self._refresh:
            self.refresh()
    
    def refresh(self):
        for l in self._labs:
            x, y, _ = proj3d.proj_transform(l[1][0], l[1][1], l[1][2], self.ax1.get_proj())
            x2, y2, _ = proj3d.proj_transform(l[2][0], l[2][1], l[2][2], self.ax1.get_proj())
            l[0].xytext = self._midp(x, y, x2, y2)
        
        for l in self._alabs:
            x, y, _ = proj3d.proj_transform(l[1][0], l[1][1], l[1][2], self.ax1.get_proj())
            l[0].xytext = (x+0.002,y+0.002)
        
        self.canvas.draw()

