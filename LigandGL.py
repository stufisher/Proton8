import os
import wx
import re
import math

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from mpl_toolkits.mplot3d import Axes3D, proj3d
import matplotlib.ticker as ticker

from iotbx import pdb
from wxtbx import bitmaps
from scitbx.math import minimum_covering_sphere
from scitbx.array_family import flex

from gltbx.wx_viewer import wxGLWindow, show_points_and_lines_mixin, animation_stepper
import gltbx.util
from gltbx import viewer_utils, quadrics
from gltbx.gl import *
from gltbx.glu import *
#import gltbx

import numpy as np

# ----------------------------------------------------------------------------
# LigandViewer Frame
class Ligand(wx.Frame):

    def __init__(self, pdb_file='/Users/vxn01537/Dropbox/Proton8/test/3HLX.pdb', name='', *args, **kwargs):
        wx.Frame.__init__(self,None,-1,'Ligand Explorer: ' + name, size=(800,700))
        
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
    
        

        self.toolbar = wx.ToolBar(self, style=wx.TB_3DBUTTONS|wx.TB_TEXT)                
                
        self.res_type = wx.ComboBox(self.toolbar, -1, choices=sorted(self._ligands.keys()), style=wx.CB_READONLY)
        self.res_type.Bind(wx.EVT_COMBOBOX, self._load_residue)

        close = self.toolbar.AddLabelTool(wx.ID_ANY, 'Close', bitmaps.fetch_icon_bitmap("actions", "no"))
        self.toolbar.AddSeparator()
        self.toolbar.AddControl(self.res_type)
        self.toolbar.AddSeparator()
        save = self.toolbar.AddLabelTool(wx.ID_ANY, 'Save Figure', bitmaps.fetch_icon_bitmap("actions", "save_all"))
    
        self.Bind(wx.EVT_TOOL, self._close, close)
        self.Bind(wx.EVT_TOOL, self._save_figure, save)
                
        self.SetToolBar(self.toolbar)
        self.toolbar.Realize()
                
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.viewer = LigandViewer(self)
        self.sizer.Add(self.viewer, 1, wx.EXPAND)

        self.SetSizer(self.sizer)
        #self.Fit()
    
        self._load_residue('')


    def _close(self, e):
        #self.viewer = None
        self.Destroy()
            
    def _save_figure(self, e):
        dlg = wx.FileDialog(self, 'Save Image', os.getcwd(), '', '*.png', wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            #self.fig.savefig(path, dpi=300, transparent=True)
            self.viewer.save_screen_shot(path, ['png'])
        
        dlg.Destroy()
    
    def _load_residue(self, event):
        r = self._ligands[self.res_type.GetValue()]
            
        uij = []
        bonds = []
        labels = []
        blabels = []
        for i,a in enumerate(r['at']):
            ac = r['c'][i]
            for j,b in enumerate(r['at']):
                if a is not b:
                    bc = r['c'][j]
                    if a.distance(b) < 1.8:
                        std = ''
                        
                        n = a.name.strip()+'-'+b.name.strip()
                        if n in r['stdevs']:
                            std = ' (' + str(r['stdevs'][n]) + ')'
                        bonds.append([i,j])
                        blabels.append('%.2f' % a.distance(b) + std)
    
            labels.append(a.name.strip())
            if a.uij[0] == -1:
                b = a.b/(8*pow(math.pi,2))
                uij.append((b,b,b,0,0,0))
            else:
                uij.append(a.uij)
    
        self.viewer.load_residue(atoms=r['c'], colours=r['col'], bonds=bonds, labels=labels, blabels=blabels, uij=uij)


# ----------------------------------------------------------------------------
# LigandViewer OpenGL Context
class LigandViewer(show_points_and_lines_mixin) :
    atom_colours = { 'black': (0.3,0.3,0.3),
                    'red': (1.0,0.0,0.0),
                    'green': (0.0,1.0,0.0),
                    'blue': (0.0,0.0,1.0),
                    'white': (1.0,1.0,1.0),
                    'grey': (0.5,0.5,0.5) }
    
    def __init__ (self, *args, **kwds) :
        self.first = True
        
        self.ellipsoid_display_list = None
        self.blabels_display_list = None
        self.minimum_covering_sphere = None
        
        kwds['attribList'] = [wx.glcanvas.WX_GL_DOUBLEBUFFER,
                              wx.glcanvas.WX_GL_SAMPLE_BUFFERS, GL_TRUE,
                              wx.glcanvas.WX_GL_DEPTH_SIZE, 16,
                              0, 0]
        
        
        show_points_and_lines_mixin.__init__(self, *args, **kwds)
        self.buffer_factor = 2
        self.min_slab = 4
        self.min_viewport_use_fraction = 0.1
        self.flag_show_fog = False
        self.flag_use_lights = True


    def load_residue(self, *args, **kwargs):
        self.points = flex.vec3_double(kwargs['atoms'])
        self.colours = kwargs['colours']
        self.line_i_seqs = kwargs['bonds']
        self.labels = kwargs['labels']
        self.blabels = kwargs['blabels']
        self.uij = kwargs['uij']

        self.minimum_covering_sphere = minimum_covering_sphere(points=self.points)
        self.spheres_display_list = None
        self.points_display_list = None
        self.lines_display_list = None
        self.labels_display_list = None
        self.ellipsoid_display_list = None
        self.blabels_display_list = None
    
        if not self.GL_uninitialised:
            self.move_rotation_center_to_mcs_center()
            self.fit_into_viewport()
    
    def InitGL(self):
        gltbx.util.handle_error()
        bgcolor = [1.0,1.0,1.0,0.0]
        #bgcolor = [0.0,0.0,0.0,0.0]
        glClearColor(*bgcolor)
        glEnable(GL_MULTISAMPLE)
        glDepthFunc(GL_LESS)
        glEnable(GL_ALPHA_TEST)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        self.setup_lighting()
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        self.ellipsoid = quadrics.proto_ellipsoid(slices=32, stacks=32)
        gltbx.util.handle_error()
    
    
    def DrawGL(self):
        if self.GL_uninitialised or len(self.points) == 0 :
            return
        
        self.SetCurrent(self.context)
        self.draw_lines()
        self.draw_labels()
        self.draw_blabels()
        self.draw_ellipsoids()
    

    
    def OnRedrawGL (self, event=None):
        if self.minimum_covering_sphere is None :
            gltbx.util.handle_error()
            glClear(GL_COLOR_BUFFER_BIT)
            glClear(GL_DEPTH_BUFFER_BIT)
            glFlush()
            self.SwapBuffers()
            gltbx.util.handle_error()
        else :
            if len(self.points) > 0 and self.first and not self.GL_uninitialised:
                self.move_rotation_center_to_mcs_center()
                self.fit_without_redraw()
                self.first = False
            
            wxGLWindow.OnRedrawGL(self, event)

    def process_pick_points(self):
        pass


    def fit_without_redraw(self):
        dx,dy,dz = self.compute_home_translation()
        move_factor=self.translation_move_factor((dx,dy,dz))
        mvm = gltbx.util.get_gl_modelview_matrix()
        for f in animation_stepper(time_move=self.animation_time, move_factor=move_factor):
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glTranslated(f*dx, f*dy, f*dz)
            glMultMatrixd(mvm)
                
    
    def _nudge(self, p):
        return (p[0]+0.002,p[1]+0.002,p[2]+0.002)

    def _midp(self, p, q):
        return ((q[0]-p[0])/2+p[0]+0.001, (q[1]-p[1])/2+p[1]+0.001, (q[2]-p[2])/2+p[2]+0.001)

    def _scale(self, u):
        for i in u:
            i = i*0.7
        return u

    def draw_spheres(self, scale_factor=1.0) :
        glMatrixMode(GL_MODELVIEW)
        if self.flag_use_lights:
            glEnable(GL_LIGHTING)
            glEnable(GL_LIGHT0)
            glEnable(GL_NORMALIZE)
        if self.spheres_display_list is None :
            self.spheres_display_list = gltbx.gl_managed.display_list()
            self.spheres_display_list.compile()
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            for i_seq, point in enumerate(self.points) :
                glColor3f(*self.atom_colours[self.colours[i_seq]])
                glPushMatrix()
                glTranslated(*point)
                glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, list(self.atom_colours[self.colours[i_seq]]) + [0.0])
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
                glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
                gltbx.util.SolidSphere(radius=0.2*scale_factor, slices=50, stacks=50)
                glPopMatrix()
            self.spheres_display_list.end()
        self.spheres_display_list.call()


    def draw_ellipsoids (self) :
        if self.ellipsoid_display_list is None :
            glMatrixMode(GL_MODELVIEW)
            if self.flag_use_lights :
                glShadeModel(GL_SMOOTH)
                glEnable(GL_DEPTH_TEST)
                glEnable(GL_LIGHTING)
                glEnable(GL_LIGHT0)
                glEnable(GL_NORMALIZE)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            self.ellipsoid_display_list = gltbx.gl_managed.display_list()
            self.ellipsoid_display_list.compile()

            for i_seq, uij in enumerate(self.uij) :
                if uij[0] != -1 :
                    col = list(self.atom_colours[self.colours[i_seq]]) + [1.0]
                    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, col)
                    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
                    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
                    self.ellipsoid.draw(self.points[i_seq], self._scale(uij))
            self.ellipsoid_display_list.end()
        self.ellipsoid_display_list.call()


    def draw_blabels(self):
        if self.blabels_display_list is None:
            font = gltbx.fonts.ucs_bitmap_8x13
            font.setup_call_lists()
            glDisable(GL_LIGHTING)
            glColor3f(1.0, 0.0, 0.0)
            self.blabels_display_list = gltbx.gl_managed.display_list()
            self.blabels_display_list.compile()
            for l_seq, lab in enumerate(self.blabels):
                glRasterPos3f(*self._midp(self.points[self.line_i_seqs[l_seq][0]], self.points[self.line_i_seqs[l_seq][1]]))
                font.render_string(lab)
            self.blabels_display_list.end()
            glEnable(GL_LIGHTING)
        self.blabels_display_list.call()


    def draw_labels(self, color=(1,1,1)):
        if (self.labels_display_list is None):
            font = gltbx.fonts.ucs_bitmap_8x13
            font.setup_call_lists()
            self.labels_display_list = gltbx.gl_managed.display_list()
            self.labels_display_list.compile()
            glColor3f(*color)
            for label,point in zip(self.labels, self.points):
                glRasterPos3f(*self._nudge(point))
                font.render_string(label)
            self.labels_display_list.end()
        self.labels_display_list.call()


    def draw_lines(self):
        if self.lines_display_list is None:
            glEnable(GL_LINE_SMOOTH)
            glEnable(GL_BLEND)
            glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
            glDisable(GL_LIGHTING)
    
            self.lines_display_list = gltbx.gl_managed.display_list()
            self.lines_display_list.compile()
            assert self.line_width > 0
            for i_seqs in self.line_i_seqs:
                color = self.line_colors.get(tuple(i_seqs))
                if (color is None):
                    color = self.line_colors.get(tuple(reversed(i_seqs)))
                    if (color is None):
                        color = (1,0,1)
                glColor3f(*color)
                glLineWidth(self.line_width)
                glBegin(GL_LINES)
                glVertex3f(*self.points[i_seqs[0]])
                glVertex3f(*self.points[i_seqs[1]])
                glEnd()
            self.lines_display_list.end()
        self.lines_display_list.call()