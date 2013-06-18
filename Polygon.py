import wx
import math

from cctbx.array_family import flex
from wxtbx import polygon as pgn, polygon_db_viewer
from iotbx import pdb
from mmtbx import polygon

from Tab import Tab


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
    #@staticmethod
    #def set_stats(func):
    #    Compare._stats = func
    
    def __init__(self, nb):
        Tab.__init__(self, nb)
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
    
    def set_stats(self, func):
        self._stats = func
    
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
        
        self.sizer.Add(self.pg_sizer, 1, wx.EXPAND)
        self.sizer.Add(self.polygon_panel, 2, wx.EXPAND, wx.ALL, 10)
        
        self.sizer.Layout()
    
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

