import wx
import wx.lib.scrolledpanel as scrolled

from iotbx import pdb

from mmtbx.rotamer import graphics
from mmtbx.validation import utils
from wxtbx import plots

from mmtbx.validation.ramalyze import ramalyze
from mmtbx.validation.rotalyze import rotalyze
from mmtbx.validation.cbetadev import cbetadev
from mmtbx.validation.clashscore import clashscore

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas

from Tab import Tab
from Shelx import Shelx, LSTParser
from PDBTools import PDBTools

class Validation(Tab, scrolled.ScrolledPanel):
    
    def __init__(self, nb):
        scrolled.ScrolledPanel.__init__(self, nb)
        
        self._rama_data = []
        self._rotamer_data = []
        self._cb_data = []
        self._clash_score = 99
        self._rmsds = [-1,-1]
        self._chain_lookup = {}
    
    def set_residues(self, residues):
        self._residues = residues
    
    def stats(self):
        return self._clash_score[''], self._rmsds
    
    def load_refinement(self, ref):
        self._pdb_file = ref.replace('.dat', '.pdb')
        self._ins_file = ref.replace('.dat', '.ins')
        self._lst_file = ref.replace('.dat', '.lst')
    
        lst = LSTParser(self._lst_file)
        pdb_io = pdb.input(file_name=self._pdb_file)
        
        self._chain_lookup = PDBTools().get_chains(self._pdb_file)
        
        r = clashscore()
        self._clash_score, self._clashes = clashscore.analyze_clashes(r,pdb_io)# verbose=True)
        self._clashes = self._clashes[''].split('\n')
        
        rama = ramalyze()
        output, self._rama_data = rama.analyze_pdb(pdb_io=pdb_io, outliers_only=False)
        
        rota = rotalyze()
        output, self._rotamer_data = rota.analyze_pdb(pdb_io, outliers_only=False)
        
        r = cbetadev()
        output, summary, self._cb_data = cbetadev.analyze_pdb(r,pdb_io=pdb_io,outliers_only=True)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        
        self._rmsds = lst.get_stats()
        
        # Summary
        self.stats_sizer = wx.FlexGridSizer(cols=3, rows=0, vgap=5, hgap=5)
        self.stats_sizer.Add(wx.StaticText(self, -1, 'RMSD Bonds'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '%.3f' % (self._rmsds[0])))
        self.stats_sizer.Add(wx.StaticText(self, -1, ''))
        self.stats_sizer.Add(wx.StaticText(self, -1, 'RMSD Angles'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '%.3f' % (self._rmsds[1])))
        self.stats_sizer.Add(wx.StaticText(self, -1, ''), 0, wx.EXPAND|wx.BOTTOM, 10)

        self.stats_sizer.Add(wx.StaticText(self, -1, 'B Factor (Protein)'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '%.2f' % (self._residues['avg']['pro'])))
        self.stats_sizer.Add(wx.StaticText(self, -1, ''), 0, wx.EXPAND|wx.BOTTOM)
        self.stats_sizer.Add(wx.StaticText(self, -1, 'B Factor (Solvent)'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '%.2f' % (self._residues['avg']['sol'])))
        self.stats_sizer.Add(wx.StaticText(self, -1, ''), 0, wx.EXPAND|wx.BOTTOM)
        self.stats_sizer.Add(wx.StaticText(self, -1, 'B Factor (All)'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '%.2f' % (self._residues['avg']['all'])))
        self.stats_sizer.Add(wx.StaticText(self, -1, ''), 0, wx.EXPAND|wx.BOTTOM, 10)
        
        
        self.stats_sizer.Add(wx.StaticText(self, -1, 'Ramachandran Outliers'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '%.1f' % (rama.get_outliers_count_and_fraction()[1]*100) + '%'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '(Goal ' + rama.get_outliers_goal()+')'))
        self.stats_sizer.Add(wx.StaticText(self, -1, 'Ramachandran Favoured'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '%.1f' % (rama.get_favored_count_and_fraction()[1]*100) + '%'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '(Goal ' + rama.get_favored_goal()+')'), 0, wx.EXPAND|wx.BOTTOM, 10)
        self.stats_sizer.Add(wx.StaticText(self, -1, 'Rotamer Outliers'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '%.1f' % (rota.get_outliers_count_and_fraction()[1]*100) + '%'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '(Goal ' + rota.get_outliers_goal()+')'))
        self.stats_sizer.Add(wx.StaticText(self, -1, 'C-beta Outliers'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '%d' % len(self._cb_data)))
        self.stats_sizer.Add(wx.StaticText(self, -1, '(Goal 0)'))
        self.stats_sizer.Add(wx.StaticText(self, -1, 'Clashscore'))
        self.stats_sizer.Add(wx.StaticText(self, -1, '%d' % self._clash_score['']))
        
        self.sizer.Add(self.stats_sizer, 0, wx.ALL, 10)
        
        # Ramachandran Outliers
        self.rama_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Ramachandran Outliers'),wx.VERTICAL)
        if rama.get_outliers_count_and_fraction()[1] > 0:
            rama_list = wx.ListCtrl(self, -1, style=wx.LC_REPORT)
            self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._show_rama, rama_list)
            sizes = [50, 50, 150, 80, 80, 80]
            for i, item in enumerate(['Chain', 'No', 'Residue', 'Score', 'Phi', 'Psi']):
                rama_list.InsertColumn(i, item, width = sizes[i])
            
            i = 0
            self._rama_outliers = []
            for r in self._rama_data:
                (chain_id,resseq,resname,quality,phi,psi,status,pos_name,xyz) = r
                if status == 'OUTLIER':
                    self._rama_outliers.append(r)
                    rama_list.InsertStringItem(i, str(chain_id))
                    rama_list.SetStringItem(i, 1, str(resseq))
                    rama_list.SetStringItem(i, 2, resname)
                    rama_list.SetStringItem(i, 3, '%.2f' % quality)
                    rama_list.SetStringItem(i, 4, '%.1f' % phi)
                    rama_list.SetStringItem(i, 5, '%.1f' % psi)
                    i += 1
            self.rama_sizer.Add(wx.StaticText(self, -1, '%d Ramachandran outliers found' % i), 0)
            self.rama_sizer.Add(rama_list, 0, wx.EXPAND|wx.ALL, 10)
            self.rama_list = rama_list
        
        else:
            self.rama_sizer.Add(wx.StaticText(self, -1, 'No Ramachandran Outliers'), 0)
        
        self.rama_sizer.Add(wx.Button(self, 0, 'Show Ramachandran Plot'), 0)
        self.Bind(wx.EVT_BUTTON, self.show_ramachandran, id=0)
        self.sizer.Add(self.rama_sizer, 0, wx.EXPAND|wx.ALL, 10)
    
    
        # Rotamer Outliers
        self.rota_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Rotamer Outliers'),wx.VERTICAL)
        if rota.get_outliers_count_and_fraction()[1] > 0:
            rota_list = wx.ListCtrl(self, -1, style=wx.LC_REPORT)
            self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._show_rota, rota_list)
            sizes = [50, 50, 150, 80, 80, 80, 80, 80]
            for i, item in enumerate(['Chain', 'No', 'Residue', 'Score', 'Chi1', 'Chi2', 'Chi3', 'Chi4']):
                rota_list.InsertColumn(i, item, width = sizes[i])
                    
            i = 0
            self._rota_outliers = []
            for r in self._rotamer_data:
                (chain_id,resseq,resname,quality,chi1,chi2,chi3,chi4,status,xyz) = r
                if status == 'OUTLIER':
                    self._rota_outliers.append(r)
                    rota_list.InsertStringItem(i, str(chain_id))
                    rota_list.SetStringItem(i, 1, str(resseq))
                    rota_list.SetStringItem(i, 2, resname)
                    rota_list.SetStringItem(i, 3, '%.2f' % quality)
                    rota_list.SetStringItem(i, 4, '%.1f' % chi1)
                    rota_list.SetStringItem(i, 5, '%.1f' % chi2 if chi2 is not None else 'None')
                    rota_list.SetStringItem(i, 6, '%.1f' % chi3 if chi3 is not None else 'None')
                    rota_list.SetStringItem(i, 7, '%.1f' % chi4 if chi4 is not None else 'None')
                    i += 1
            self.rota_sizer.Add(wx.StaticText(self, -1, '%d rotamer outliers found' % i), 0)
            self.rota_sizer.Add(rota_list, 1, wx.EXPAND|wx.ALL, 5)
            self.rota_list = rota_list
        else:
            self.rota_sizer.Add(wx.StaticText(self, -1, 'No Rotamer Outliers'))
    
        self.rota_sizer.Add(wx.Button(self, 1, 'Show Chi1-Chi2 Plots'))
        self.Bind(wx.EVT_BUTTON, self.show_rotamer, id=1)
        self.sizer.Add(self.rota_sizer, 0, wx.EXPAND|wx.ALL, 10)
    
    
        # C-beta Outliers
        self.cb_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'C-beta Outliers'),wx.VERTICAL)
        if len(self._cb_data) > 0:
            cb_list = wx.ListCtrl(self, -1, style=wx.LC_REPORT)
            self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._show_cb, cb_list)
            sizes = [50, 50, 150, 100, 100]
            for i, item in enumerate(['Chain', 'No', 'Residue', 'Deviation', 'Angle']):
                cb_list.InsertColumn(i, item, width = sizes[i])

            for i,r in enumerate(self._cb_data):
                (pdbf, alt, resname, chain_id, resseq, resseq2, dev, diheral, occ, altchar, xyz) = r
                cb_list.InsertStringItem(i, str(chain_id))
                cb_list.SetStringItem(i, 1, str(resseq+resseq2))
                cb_list.SetStringItem(i, 2, resname.upper())
                cb_list.SetStringItem(i, 3, '%.3f' % dev)
                cb_list.SetStringItem(i, 4, '%.2f' % diheral)

            self.cb_sizer.Add(wx.StaticText(self, -1, '%d C-beta outliers found' % len(self._cb_data)), 0)
            self.cb_sizer.Add(cb_list, 1, wx.EXPAND|wx.ALL, 5)
            self.cb_list = cb_list
        else:
            self.cb_sizer.Add(wx.StaticText(self, -1, 'No C-beta Outliers'))

        self.sizer.Add(self.cb_sizer, 0, wx.EXPAND|wx.ALL, 10)

        # Bad Clashes
        self.clash_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'All Atom Contacts'), wx.VERTICAL)
        if len(self._clashes) > 0:
            clash_list = wx.ListCtrl(self, -1, style=wx.LC_REPORT)
            self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._show_clash, clash_list)
            sizes = [50, 50, 80, 80, 50, 50, 80, 80, 100]
            for i, item in enumerate(['Chain', 'No', 'Residue', 'Atom', 'Chain', 'No', 'Residue', 'Atom', 'Overlap']):
                clash_list.InsertColumn(i, item, width = sizes[i])

            for i,r in enumerate(self._clashes):
                '    78 ILE  CD1     83 LEU HD21 :-0.402'
                clash_list.InsertStringItem(i, r[0:2].strip())
                clash_list.SetStringItem(i, 1, r[2:6].strip())
                clash_list.SetStringItem(i, 2, r[7:10].strip())
                clash_list.SetStringItem(i, 3, r[11:15].strip())
                clash_list.SetStringItem(i, 4, r[16:18].strip())
                clash_list.SetStringItem(i, 5, r[19:22].strip())
                clash_list.SetStringItem(i, 6, r[23:26].strip())
                clash_list.SetStringItem(i, 7, r[28:32].strip())
                clash_list.SetStringItem(i, 8, r[34:39].strip())

            self.clash_sizer.Add(wx.StaticText(self, -1, '%d bad clashes found' % i), 0)
            self.clash_sizer.Add(clash_list, 1, wx.EXPAND|wx.ALL, 5)
            self.clash_list = clash_list
                    
        else:
            self.clash_sizer.Add(wx.StaticText(self, -1, 'No Bad Clashes'))

        self.sizer.Add(self.clash_sizer, 0, wx.EXPAND|wx.ALL, 10)

    
        self._split_sites, self._npds = lst.get_site_info()
        # Split Sites
        self.split_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Split Sites'), wx.VERTICAL)
        if len(self._split_sites) > 0:
            split_list = wx.ListCtrl(self, -1, style=wx.LC_REPORT)
            self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._show_split, split_list)
            sizes = [100,100,100,50,80,100]
            for i, item in enumerate(['U1', 'U2', 'U3', 'No', 'Residue', 'Atom']):
                split_list.InsertColumn(i, item, width=sizes[i])
    
            i = 0
            for j,s in enumerate(self._split_sites):
                if '_' in s[3]:
                    split_list.InsertStringItem(i, str(s[0]))
                    split_list.SetStringItem(i, 1, str(s[1]))
                    split_list.SetStringItem(i, 2, str(s[2]))

                    atom,id = s[3].split('_')
                    
                    split_list.SetStringItem(i, 3, str(id))
                    split_list.SetStringItem(i, 4, str())
                    split_list.SetStringItem(i, 5, str(atom))
                    i += 1

            self.split_sizer.Add(wx.StaticText(self, -1, '%d possible split sites found' % len(self._split_sites)))
            self.split_sizer.Add(split_list, 0, wx.EXPAND|wx.ALL, 5)
            self.split_list = split_list
                
        else:
            self.split_sizer.Add(wx.StaticText(self, -1, 'No split sites found'))
        self.sizer.Add(self.split_sizer, 0, wx.EXPAND|wx.ALL, 10)
    
        # NPDs
        self.npd_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Non Positive Definites'), wx.VERTICAL)
        if len(self._npds) > 0:
            npd_list = wx.ListCtrl(self, -1, style=wx.LC_REPORT)
            self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._show_npd, npd_list)
            sizes = [100,100,100,50,80,100]
            for i, item in enumerate(['U1', 'U2', 'U3', 'No', 'Residue', 'Atom']):
                npd_list.InsertColumn(i, item, width=sizes[i])

            for i, s in enumerate(self._npds):
                npd_list.InsertStringItem(i, str(s[0]))
                npd_list.SetStringItem(i, 1, str(s[1]))
                npd_list.SetStringItem(i, 2, str(s[2]))
                
                atom, id = s[3].split('_')
                npd_list.SetStringItem(i, 3, str(id))
                npd_list.SetStringItem(i, 4, str())
                npd_list.SetStringItem(i, 5, str(atom))
                    
            self.npd_sizer.Add(wx.StaticText(self, -1, '%d non positive definite sites found' % len(self._npds)))
            self.npd_sizer.Add(npd_list, 0, wx.EXPAND|wx.ALL, 5)
            self.npd_list = npd_list

        else:
            self.npd_sizer.Add(wx.StaticText(self, -1, 'No non positive definite sites found'))
        self.sizer.Add(self.npd_sizer, 0, wx.EXPAND|wx.ALL, 10)

    
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)
        self.SetupScrolling()
    

    def show_rotamer(self, event):
        rota = RotamerFrame(self, 'Rotamer Plot', self._rotamer_data, self._ins_file)
        rota.Show()
        
    def show_ramachandran(self, event):
        rama = RamachandranFrame(self, 'Ramachandran Plot', self._rama_data, self._ins_file)
        rama.Show()

    
    def _show_residue(self, list, data, id):
        sel = list.GetFirstSelected()
    
        if sel > -1 and sel < len(data):
            rid = int(data[sel][id])
            self._coot_client.centre_residue(self._chain_lookup[rid], rid, 'CA')

    
    def _show_rama(self, e):
        self._show_residue(self.rama_list, self._rama_outliers, 1)

    def _show_rota(self, e):
        self._show_residue(self.rota_list, self._rota_outliers, 1)

    def _show_cb(self, e):
        self._show_residue(self.cb_list, self._cb_data, 4)

    def _show_clash(self, e):
        sel = self.clash_list.GetFirstSelected()
        
        if sel > -1 and sel < len(self._clashes):
            rid = int(self._clashes[sel][2:6].strip())
            self._coot_client.centre_residue(self._chain_lookup[rid], rid, 'CA')

    def _show_split(self, e):
        self._show_residue2(self.split_list, self._split_sites, 3)

    def _show_npd(self, e):
        self._show_residue2(self.npd_list, self._npds, 3)

    def _show_residue2(self, list, data, id):
        sel = list.GetFirstSelected()
        
        if sel > -1 and sel < len(data):
            lab = data[sel][id]
            atom, rid = lab.split('_')
            if not rid[-1].isdigit():
                rid = rid[0:-1]
            rid = int(rid)
            
            print sel, rid, id
            self._coot_client.centre_residue(self._chain_lookup[rid], rid, atom)

class RamachandranFrame(plots.plot_frame):
    def __init__(self, parent, title, ramalyze_data, ins_file):
        self.canvas = None
        self.ramalyze_data = ramalyze_data
        
        self._ins = Shelx(ins_file)
        self._residue_list = ['*'] + self._ins.residue_list()
        
        self.pos_type = 'general'
        self.residue_name = '*'
        self.point_type = 'All'
        
        self.types = ["general", "glycine", "cis-proline", "trans-proline", "pre-proline", "isoleucine or valine"]
        self._data_types = ['All', 'Allowed/Outlier', 'Outlier']
        
        plots.plot_frame.__init__(self, parent=parent, title=title)
    
    
    def create_plot_panel(self):
        self.plot = graphics.ramachandran_plot()
        self.canvas = FigCanvas(self, -1, self.plot.figure)
        self.draw_plot()
        return self.canvas
    
    def draw_plot(self):
        stats = utils.get_rotarama_data(pos_type='general', convert_to_numpy_array=True)
        points, coords = graphics.get_residue_ramachandran_data(ramalyze_data=self.ramalyze_data,
                                                                position_type=self.pos_type,
                                                                residue_name=self.residue_name,
                                                                point_type=self.point_type)
        
        title = graphics.format_ramachandran_plot_title(self.pos_type, self.residue_name)
        self.plot.draw_plot(
                            stats=stats,
                            title=title,
                            points=points,
                            xyz=coords,
                            colormap="Blues",
                            contours=[0.1495, 0.376])
        
        if self.canvas is not None:
            self.canvas.draw()
    
    
    def draw_top_panel(self):
        self.top_panel = wx.Panel(parent=self, style=wx.SUNKEN_BORDER)
        self.top_sizer = wx.FlexGridSizer(rows=2, cols=4, vgap=5, hgap=5)
        
        self.top_sizer.Add(wx.StaticText(self, -1, 'Position Type'), 1, wx.EXPAND|wx.ALL, 5)
        self.pos_sel = wx.ComboBox(self, -1, choices=self.types, style=wx.CB_READONLY)
        self.pos_sel.Bind(wx.EVT_COMBOBOX, self._set_position_type)
        self.top_sizer.Add(self.pos_sel, 1, wx.EXPAND|wx.ALL, 5)
        
        self.top_sizer.Add(wx.StaticText(self, -1, 'Residue Name'), 1, wx.EXPAND|wx.ALL, 5)
        self.res_type = wx.ComboBox(self, -1, choices=self._residue_list, style=wx.CB_READONLY)
        self.res_type.Bind(wx.EVT_COMBOBOX, self._set_residue_name)
        self.top_sizer.Add(self.res_type, 1, wx.EXPAND|wx.ALL, 5)
        
        self.top_sizer.Add(wx.StaticText(self, -1, 'Show Data Points'), 1, wx.EXPAND|wx.ALL, 5)
        self.data_type = wx.ComboBox(self, -1, choices=self._data_types, style=wx.CB_READONLY)
        self.data_type.Bind(wx.EVT_COMBOBOX, self._set_data_type)
        self.top_sizer.Add(self.data_type, 1, wx.EXPAND|wx.ALL, 5)
        
        self.top_panel.SetSizer(self.top_sizer)
    
    
    def _set_position_type(self, event):
        self.pos_type = self.types[self.pos_sel.GetCurrentSelection()]
        self.draw_plot()
    
    def _set_data_type(self, event):
        self.point_type = self._data_types[self.data_type.GetCurrentSelection()]
        self.draw_plot()

    def _set_residue_name(self, event):
        self.residue_name = self._residue_list[self.res_type.GetCurrentSelection()]
        self.draw_plot()


    def OnSave(self, event):
        output_file = wx.FileSelector("Saved image name",
                                      default_path='',
                                      default_filename="plot.png",
                                      wildcard="Adobe PDF figure (*.pdf)|*.pdf|" + \
                                      "PNG image (*.png)|*.png|" + \
                                      "Postscript figure (*.ps)|*.ps", flags=wx.SAVE)
        if output_file != "" :
            self.plot.save_image(output_file)



class RotamerFrame(plots.plot_frame):
    def __init__(self, parent, title, rotalyze_data, ins_file):
        self.rotalyze_data = rotalyze_data
        
        self._ins = Shelx(ins_file)
        self._residue_list = self._ins.residue_list()
        self._data_types = ['All', 'Allowed/Outlier', 'Outlier']
        
        self.residue_name = self._residue_list[0]
        self.point_type = 'All'
        
        self.plot = None

        plots.plot_frame.__init__(self, parent=parent, title=title)
    
    def create_plot_panel(self):
        self.plot = graphics.rotamer_plot()
        self.canvas = FigCanvas(self, -1, self.plot.figure)
        self.draw_plot()
        return self.canvas
  
    def draw_plot(self):
        stats = utils.get_rotarama_data(pos_type='general', convert_to_numpy_array=True)
        residue_name = 'GLN'
        points, coords = graphics.get_residue_rotamer_data(rotalyze_data=self.rotalyze_data,
                                                           residue_name=self.residue_name,
                                                           point_type=self.point_type)
        
        self.plot.draw_plot(
                     stats=stats,
                     title="Chi1-Chi2 plot for %s" % self.residue_name,
                     points=points,
                     xyz=coords,
                     colormap="Blues",
                     contours=None)
        
        if self.canvas is not None:
            self.canvas.draw()

    def draw_top_panel(self):
        self.top_panel = wx.Panel(parent=self, style=wx.SUNKEN_BORDER)
        self.top_sizer = wx.FlexGridSizer(rows=0, cols=4, vgap=5, hgap=5)
        
        self.top_sizer.Add(wx.StaticText(self, -1, 'Residue Name'), 1, wx.EXPAND|wx.ALL, 5)
        self.res_type = wx.ComboBox(self, -1, choices=self._residue_list, style=wx.CB_READONLY)
        self.res_type.Bind(wx.EVT_COMBOBOX, self._set_residue_name)
        self.top_sizer.Add(self.res_type, 1, wx.EXPAND|wx.ALL, 5)
        
        self.top_sizer.Add(wx.StaticText(self, -1, 'Show Data Points'), 1, wx.EXPAND|wx.ALL, 5)
        self.data_type = wx.ComboBox(self, -1, choices=self._data_types, style=wx.CB_READONLY)
        self.data_type.Bind(wx.EVT_COMBOBOX, self._set_data_type)
        self.top_sizer.Add(self.data_type, 1, wx.EXPAND|wx.ALL, 5)
        
        self.top_panel.SetSizer(self.top_sizer)

    
    def _set_data_type(self, event):
        self.point_type = self._data_types[self.data_type.GetCurrentSelection()]
        self.draw_plot()
    
    def _set_residue_name(self, event):
        self.residue_name = self._residue_list[self.res_type.GetCurrentSelection()]
        self.draw_plot()


    def OnSave(self, event):
        output_file = wx.FileSelector("Saved image name",
                                      default_path='',
                                      default_filename="plot.png",
                                      wildcard="Adobe PDF figure (*.pdf)|*.pdf|" + \
                                      "PNG image (*.png)|*.png|" + \
                                      "Postscript figure (*.ps)|*.ps", flags=wx.SAVE)
        if output_file != "" :
            self.plot.save_image(output_file)
