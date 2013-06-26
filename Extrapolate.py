import wx

import numpy as np

from iotbx.shelx import hklf, crystal_symmetry_from_ins
from iotbx import pdb

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas

from Tab import Tab
from PDBTools import PDBTools


# ----------------------------------------------------------------------------
# Cruickshank Extrapolations
class Extrapolate(Tab):

    def __init__(self, nb):
        Tab.__init__(self, nb)
        
        self.fig = Figure((5.0, 4.0), dpi=100)
        col = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND)
        self.fig.patch.set_facecolor((col[0]/255.0, col[1]/255.0, col[2]/255.0))
        self.canvas = FigCanvas(self, -1, self.fig)
        self.ax1 = self.fig.add_subplot(111)        
        self.ax1.set_position([0.1,0.1,0.85,0.86])
        self.ax1.set_ylabel('sig(x)', fontsize=9)
        self.ax1.set_xlabel('Resolution', fontsize=9)
        self.ax1.tick_params(labelsize=8)
        [i.set_linewidth(0.5) for i in self.ax1.spines.itervalues()]
        
        self.side_sizer = wx.FlexGridSizer(rows=0, cols=2, vgap=5, hgap=5)
        
        self.side_sizer.Add(wx.StaticText(self, -1, 'Vm'), 0, wx.EXPAND)
        self._mv = wx.StaticText(self, -1, '')
        self.side_sizer.Add(self._mv, 0, wx.EXPAND)

        self.side_sizer.Add(wx.StaticText(self, -1, 'Solvent'), 0, wx.EXPAND)
        self._s = wx.StaticText(self, -1, '')
        self.side_sizer.Add(self._s, 0, wx.EXPAND)
        
        self.side_sizer.Add(wx.StaticText(self, -1, 'Resolution'), 0, wx.EXPAND)
        self._dmin = wx.StaticText(self, -1, '')
        self.side_sizer.Add(self._dmin, 0, wx.EXPAND)

        self.side_sizer.Add(wx.StaticText(self, -1, 'Completeness'), 0, wx.EXPAND)
        self._c = wx.StaticText(self, -1, '')
        self.side_sizer.Add(self._c, 0, wx.EXPAND)

        self.side_sizer.Add(wx.StaticText(self, -1, 'R Factor'), 0, wx.EXPAND)
        self._r = wx.StaticText(self, -1, '')
        self.side_sizer.Add(self._r, 0, wx.EXPAND)

        self.side_sizer.Add(wx.StaticText(self, -1, 'R Free'), 0, wx.EXPAND)
        self._rfree = wx.StaticText(self, -1, '')
        self.side_sizer.Add(self._rfree, 0, wx.EXPAND)

        self.side_sizer.Add(wx.StaticText(self, -1, 'sig(x) R'), 0, wx.EXPAND)
        self._sigxr = wx.StaticText(self, -1, '')
        self.side_sizer.Add(self._sigxr, 0, wx.EXPAND)
        
        self.side_sizer.Add(wx.StaticText(self, -1, 'sig(x) Rfree'), 0, wx.EXPAND)
        self._sigxrf = wx.StaticText(self, -1, '')
        self.side_sizer.Add(self._sigxrf, 0, wx.EXPAND)
        
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.side_sizer, 0, wx.EXPAND|wx.ALL, 10)
        self.sizer.Add(self.canvas, 1, wx.EXPAND|wx.ALL, 5)
        
        
        self.SetSizer(self.sizer)





    def load_refinement(self, ref, stats):
        hkl = hklf.reader(open(ref.replace('.dat', '.hkl')))
        pdbf = pdb.input(file_name=ref.replace('.dat', '.pdb'))
        pdbt = PDBTools(file_name=ref.replace('.dat', '.pdb'))
        
        cs = crystal_symmetry_from_ins.extract_from(ref.replace('.dat', '.ins'))
        ma = hkl.as_miller_arrays(crystal_symmetry=cs)
        
        mp = pdbf.xray_structure_simple().scatterers()[0].multiplicity()
        s = pdbt.get_s()
        vm = cs.unit_cell().volume() / (pdbt.get_rmm() * mp)
        
        c = ma[0].completeness(d_max=stats['res'])
        dmin = stats['res']
        r = stats['r']
        rfree = stats['rfree']

        self._mv.SetLabel('%.2f' % vm)
        self._s.SetLabel('%.2f' % s)
        self._dmin.SetLabel('%.2f' % dmin)
        self._c.SetLabel('%.1f' % (c*100))
        self._r.SetLabel('%.3f' % r)
        self._rfree.SetLabel('%.3f' % rfree)
        
        sigxr = self._sigx_r(s, vm, c, r, dmin)
        self._sigxr.SetLabel('%.4f' % sigxr)
        sigxrf = self._sigx_rfree(s, vm, c, rfree, dmin)
        self._sigxrf.SetLabel('%.4f' % sigxrf)
        
        x = np.linspace(dmin+0.5,dmin-0.5, 20)
        ys = [[],[],[],[],[],[]]
        for i in x:
            sr = self._sigx_r(s, vm, c, r, i)
            ys[0].append(sr)
            ys[1].append(sr*1.15)
            ys[2].append(sr*0.85)
            
            sr = self._sigx_rfree(s, vm, c, rfree, i)
            ys[3].append(sr)
            ys[4].append(sr*1.15)
            ys[5].append(sr*0.85)
    
        self.ax1.plot(x, ys[0], 'b-', label='R')
        self.ax1.fill_between(x, ys[1], ys[2], alpha=0.15, facecolor='blue')

        self.ax1.plot(x, ys[3], 'g-', label='Rfree')
        self.ax1.fill_between(x, ys[4], ys[5], alpha=0.15, facecolor='green')
                
        al = self.ax1.axis()
        yam = al[3]-al[2]
        xam = al[1]-al[0]
                
        self.ax1.axvline(x=dmin, ymin=0, ymax=(sigxr-al[2])/yam, color='0.7')
        self.ax1.axhline(y=sigxr, xmin=0, xmax=(dmin-al[0])/xam, color='0.7')
        self.ax1.legend(prop={'size':8}, numpoints=1, loc='best', fancybox=True)

    def _sigx_r(self, s, vm, c, r, dmin):
        return 0.18*pow( (vm/(1+s)) - (0.135*pow(dmin,3)/c) , -0.5)*pow(c,-5/6)*r*pow(dmin, 5/2)


    def _sigx_rfree(self, s, vm, c, rfree, dmin):
        return 0.18*pow((1+s), 0.5)*pow(vm, -0.5)*pow(c, -5/6)*rfree*pow(dmin, 5/2)
