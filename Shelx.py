import os
import sys
import math
import wx
import re

from operator import itemgetter
from itertools import groupby

from iotbx import pdb, reflection_file_reader
from iotbx.shelx.write_ins import LATT_SYMM
from mmtbx.monomer_library import server

import ShelxData
from Constants import *

# ----------------------------------------------------------------------------
# Text manipulations for shelx ins files for refinement prep
class Shelx:

    def __init__(self, file):
        if os.path.exists(file):
            self._file = file
            
            ins = open(file)
            self._ins = ins.read().split('\n')
            ins.close()
        
    def set_type(self, type, cycles, options):
        if type == RESTRAINED:
            cmd = 'CGLS ' + str(cycles) + ' -1'
            self._restraints(1)
        
        elif type == PART_UNRESTRAINED:
            cmd = 'CGLS ' + str(cycles) + ' -1'
            self._restraints(0, residues=options['residues'])
            
        elif type == UNRESTRAINED:
            cmd = 'CGLS ' + str(cycles) + ' -1'
            self._restraints(0, all=True)
    
        elif type == FULL_MATRIX:
            cmd = 'L.S. 1' + ('' if options['rfree'] else ' -1')
            self._restraints(0, residues=options['residues'])
            
        print 'HYDROGENS ' + str(options['hydrogens'])
            
        rem = []
        for i,l in enumerate(self._ins):
            if 'L.S.' in l or 'CGLS' in l:
               self._ins[i] = cmd
               id = i
               
            if 'ACTA' in l or 'DAMP' in l or 'BLOC' in l:
                rem.append(i)
    
            if type == FULL_MATRIX:
                if 'MERG' in l:
                    self._ins[i] = 'MERG 2'
            
            if 'hydrogens' in options:            
                if 'HFIX' in l:
                    self._ins[i] = ('' if options['hydrogens'] else 'REM ') + self._ins[i].replace('REM ','')
    
    
        custom_damp = False
        cust_opts = []
        if 'custom' in options:            
            if options['custom']:
                if os.path.exists(options['custom']):
                    file = open(options['custom'])
                    cust_opts = file.read().split('\n')
                    file.close()

        if 'custom_text' in options:
            if options['custom_text']:
                cust_opts.extend(options['custom_text'].split('\n'))
                    
        for l in cust_opts:
            if 'DAMP' in l:
                custom_damp = True
                self._ins.insert(id+1, l.strip())
    
        
        if type == FULL_MATRIX:
            self._ins.insert(id+1, 'ACTA')
            
            if not custom_damp:
                self._ins.insert(id+1, 'DAMP 0 15')
            
            if options['bloc']:
                self._ins.insert(id+1, 'BLOC 1')
        else:
            rem.reverse()
            for r in rem:
                del self._ins[r]
                    
        if 'anis' in options:
            self._ins.insert(id+1, 'ANIS')


    def set_res(self, res, resl):
        for i,l in enumerate(self._ins):
            if l.find('SHEL') > -1:
               self._ins[i] = 'SHEL ' + str(resl) + ' ' + str(res)
        
    def _restraints(self, enable, **kwargs):
        all = ('all' in kwargs)
        
        residues = []
        if 'residues' in kwargs:
            residues = kwargs['residues']
                
        print enable
        rests = {'ASP': ['DFIX_ASP 1.249 CG OD1','DFIX_ASP 1.249 CG OD2'],
                 'GLU': ['DFIX_GLU 1.249 CD OE1','DFIX_GLU 1.249 CD OE2'],
                 
                 'HIS': ['DFIX_HIS 1.321 ND1 CE1','DFIX_HIS 1.321 ND1 NE2',
                         'DFIX_HIS 1.378 CG ND1','DFIX_HIS 1.354 CG CD2',
                         'DFIX_HIS 1.374 NE2 CD2',
                         'DANG_HIS 2.494 CG CE1','DANG_HIS 1.911 CG NE2',
                         'DANG_HIS 2.598 CE1 CD2','DANG_HIS 2.507 ND1 NE2',
                         'DANG_HIS 2.602 ND1 CD2'],
                 
                 'ARG': ['DFIX_ARG 1.326 CZ NH2','DFIX_ARG 1.326 CZ NH1',
                         'DFIX_ARG 1.326 CZ NE',
                         'DANG_ARG 2.297 NE NH1','DANG_ARG 2.297 NE NH2',
                         'DANG_ARG 2.304 NH1 NH2']}
    
        for i,l in enumerate(self._ins):
            r = l.replace('REM ', '')
            if all or enable:
                if self._find_rest(l):
                    self._ins[i] = r if enable else ('REM ' + r)
            
            else:
                for res in residues:
                    if res in rests:
                        for rest in rests[res]:
                            if l.find(rest) > -1:
                                self._ins[i] = 'REM ' + r
                    else:
                        if self._find_rest(l, res):
                            self._ins[i] = 'REM ' + r


    def _find_rest(self, l, r=''):
        return l.find('DFIX_'+r) > -1 or l.find('DANG_'+r) > -1 or l.find('RTAB_'+r) > -1 or l.find('FLAT_'+r) > -1 or l.find('CHIV_'+r) > -1


    def _hydrogens(self, enable):
        for i,l in enumerate(self._ins):
            if l.find('HFIX_'):
                self._ins[i] = ('' if enable else 'REM ') + self._ins[i].replace('REM ','')
               
    def set_hklf(self, f=1):
        if f == 1:
            t = 3
        else:
            t = 4
        
        for i,l in enumerate(self._ins):
            if l.find('HKLF') > -1:
               self._ins[i] = 'HKLF ' + str(t)

    def residue_list(self):
        list = {}
        for i,l in enumerate(self._ins):
            if l.find('RESI') > -1:
                a, b, resn = l.split()
                list[resn] = 1
                   
        return sorted(list.keys())

    def has_hydrogen(self):
        ret = False
        for i,l in enumerate(self._ins):
            if 'AFIX' in l:
                ret = True
                break
                
        return ret
        
    def write(self):
        f = open(self._file, 'w')
        f.write('\n'.join(self._ins))
        f.close()

class SpaceGroup(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, 'Space Group', size=(300,100))
        self.Bind(wx.EVT_CLOSE, self._on_close)
        
        self.sg_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sg_sizer.Add(wx.StaticText(self, -1, 'Space Group'), 0, wx.EXPAND)
        self._sg = wx.TextCtrl(self, -1, '')
        self.sg_sizer.Add(self._sg, 0, wx.EXPAND)
    
        self._button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._startb = wx.Button(self, 0, 'Ok')
        self._startb.Bind(wx.EVT_BUTTON, self._ok)
        self._button_sizer.Add(self._startb, 1, wx.EXPAND|wx.ALL, 5)
        self._cancel = wx.Button(self, 1, 'Cancel')
        self._cancel.Bind(wx.EVT_BUTTON, self._on_close)
        self._button_sizer.Add(self._cancel, 1, wx.EXPAND|wx.ALL, 5)
    
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.sg_sizer)
        self.sizer.Add(self._button_sizer)
        
        self.SetSizer(self.sizer)
        self.Fit()
    
    def _ok(self, e):
        self.EndModal(1)
    
    def _on_close(self, event):
        self.EndModal(0)

    def sg(self):
        return str(self._sg.GetValue())

# ----------------------------------------------------------------------------
# PDB -> Shelx INS
class PDBImporter:

    def __init__(self, pdb_file, root, parent = None):
        self._complete = False
        self._parent = parent
        
        if os.path.exists(pdb_file):
            self._pdbf = pdb.input(file_name=pdb_file)
            atoms = self._pdbf.atoms_with_labels()
            symm = self._pdbf.crystal_symmetry()
            
            if symm.space_group() is None:
                wx.MessageBox('No spacegroup found in the selected PDB, please enter one', 'No Space Group Found', wx.OK | wx.ICON_INFORMATION)
                dlg = SpaceGroup(parent)
                dlg.CentreOnParent()
                val = dlg.ShowModal()
            
                if val:
                    from cctbx import crystal
                    new = crystal.symmetry(space_group=dlg.sg())
                    symm = symm.join_symmetry(new)
                else:
                    return
                            
            
            residues = []
            atc = {}
            s = {'ZSOLV':{}}
            for a in atoms:
                # phenix and shelx hydrogen naming conventions are not compatible
                if a.element_is_hydrogen():
                    continue
                    
                ch_id = a.chain_id
            
                # solvent to new chain
                if a.resname == 'HOH' or a.resname == 'DOD':
                    ch_id = 'ZZ' + a.chain_id
            
                if not a.resname in residues:
                    residues.append(a.resname)
                    
                if not ch_id in s:
                    s[ch_id] = {}
                    
                if not a.resseq_as_int() in s[ch_id]:
                    s[ch_id][a.resseq_as_int()] = {}
                
                if not a.altloc in s[ch_id][a.resseq_as_int()]:
                    s[ch_id][a.resseq_as_int()][a.altloc] = []
                    
                s[ch_id][a.resseq_as_int()][a.altloc].append(a)

            to_rem = []
            id = 1
            for c in s:
                if c.startswith('ZZ'):
                    to_rem.append(c)
                for r in s[c]:
                    confs = s[c][r].keys()
                    
                    for a in s[c][r][confs[0]]:
                        if not a.element in atc:
                            atc[a.element] = 0
                            
                        atc[a.element] += 1
                        
                    if c.startswith('ZZ'):
                        s['ZSOLV'][id] = s[c][r]
                        id += 1
            
            # work this out later...
            #atc[' H'] = atc[' C'] * 3
            
            for to_r in to_rem:
                del s[to_r]

            offsets = [0]
            for k in sorted(s.keys()):
                rmax = max(s[k].keys())
                offsets.append(int(1+rmax/100.0)*100+offsets[-1])

            last = offsets[-2] + 1
        
            cell = symm._unit_cell.parameters()
            mp = self._pdbf.xray_structure_simple().scatterers()[0].multiplicity()
            
            base = os.path.basename(pdb_file).replace('.pdb','')
            o = open(root + '/' + base + '_shelx.ins', 'w')
            
            print >> o, 'TITL Proton8 Input from ' + pdb_file 
            print >> o, 'CELL 1.0 %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f' % symm.unit_cell().parameters()
            print >> o, 'ZERR %d 0.01 0.01 0.01 0 0 0\n' % mp
            
            LATT_SYMM(o, symm.space_group())
            print >> o, 'SFAC ' + '  '.join(k.strip() for k in atc.keys())
            print >> o, 'UNIT ' + ' '.join(str(a*mp) for a in atc.values()) + '\n'
            
            print >> o, ShelxData._defs
            
            print >> o, 'DELU ' + ' '.join('$' + k.strip() + '_*' for k in atc.keys())
            print >> o, 'SIMU 0.1 ' + ' '.join('$' + k.strip() + '_*' for k in atc.keys())
            
            print >> o, 'ISOR 0.1 O_%d > LAST' % last
            print >> o, 'CONN 0 O_%d > LAST\n' % last
            
            print >> o, 'MERG 4\n'
            
            print >> o, ShelxData._rtab_defs
            print >> o, ShelxData._rest_defs

            
            for id,c in enumerate(sorted(s.keys())):
                if c is not 'ZSOLV':
                    cont = []
                    for k, g in groupby(enumerate(sorted(s[c].keys())), lambda (i,x):i-x):
                        l = map(itemgetter(1), g)
                        res = l[0]
                        nid = l[0] + offsets[id]
                        
                        a0  = sorted(s[c][res].keys())[0]
                        if s[c][res][a0][0].resname in ShelxData._r:
                            print >> o, 'REM HFIX 33 N_' + str(nid)
            
            print >> o, '\n'
            
                #res = sorted(s[c].keys())[0]
                #a0  = sorted(s[c][res].keys())[0]
                #if s[c][res][a0][0].resname in ShelxData._r:
                #    print >> o, 'REM HFIX 33 N_' + str(res) + '\n'

            print >> o, self._generate_restraints(sorted(residues))

            for r in sorted(residues):
            #    if r in ShelxData._rtab:
            #        print >> o, ShelxData._rtab[r]
                if r in ShelxData._r:
            #        print >> o, ShelxData._rest[ShelxData._r.index(r)]
                    print >> o, ShelxData._hfix[ShelxData._r.index(r)]

            print >> o, 'WGHT  0.1'
            #print >> o, 'FVAR  1.00000 ' + ' '.join([str(0.5) for i in range(mconf)])
        
            #print 'mconf total: ' + str(mconf)
        
            conf_id = 1
            for id,c in enumerate(sorted(s.keys())):
                for ri,r in enumerate(sorted(s[c].keys())):
                    alts = sorted(s[c][r].keys())
                    rn = s[c][r][alts[0]][0].resname
                    
                    # make all residues start with a letter
                    if rn[0].isdigit():
                        rn = 'A' + rn[0:2]                    
                        
                    print >> o, 'RESI %4d  %s' % (int(r)+offsets[id], rn)
                    
                    if ' ' in alts:
                        aof = 0
                    else:
                        aof = 1
                    
                    if len(alts) > 1:
                        conf_id += 1
                    #    op = 10*conf_id
                    #else:
                    op = 10
                    
                    for alt in sorted(s[c][r].keys()):
                        if len(alts) > 1 and not alt == ' ':
                            aid = alts.index(alt) + aof
                            print >> o, "PART   %d %d1" % (aid, conf_id * (-1 if aid == 2 else 1))
                            
                        for a in s[c][r][alt]:
                            #reset water occs
                            if a.resname == 'HOH':
                                a.occ = 1
                        
                            #if alts.index(alt) == 0:
                            a.occ += op
                            #else:
                            #    a.occ = (a.occ+op)*-1
                        
                            if a.uij_is_defined():
                                print >> o, "%-6s%3d % 8.6f % 8.6f % 8.6f % 8.5f  % 7.5f =" % (a.name.strip(), atc.keys().index(a.element)+1, a.xyz[0]/cell[0], a.xyz[1]/cell[1], a.xyz[2]/cell[2], a.occ, a.uij[0])
                                print >> o, "       % 7.5f  % 7.5f  % 7.5f  % 7.5f  % 7.5f" % (a.uij[1], a.uij[2], a.uij[5], a.uij[4], a.uij[3])
                            else:
                                print >> o, "%-6s%3d % 8.6f % 8.6f % 8.6f % 8.5f  %8.5f" % (a.name.strip(), 1, a.xyz[0]/cell[0], a.xyz[1]/cell[1], a.xyz[2]/cell[2], a.occ, a.b/(8*pow(math.pi,2)))

                    if len(alts) > 1:
                        print >> o, "PART   0"

            if conf_id - 1 > 11:
                print >> o, '\nFVAR  1.00000 %s   =' % (' '.join([str(0.5) for i in range(11)]))
                print >> o, '      %s' % (' '.join([str(0.5) for i in range(conf_id - 12)]))
            else:
                print >> o, '\nFVAR  1.00000 %s' % (' '.join([str(0.5) for i in range(conf_id - 1)]))

            print >> o, '\nHKLF 4'
            print >> o, 'END'
                
            print 'conf ids written: ' + str(conf_id)
            
            o.close()

            self._complete = True
    
    def finished(self):
        return self._complete
            
    # generate shelxl dfix, dang, rtab, chiv, flat for residues and ligands
    def _generate_restraints(self, res_ids):
        list = server.mon_lib_list_cif()
        self._residues = [ row["_chem_comp.id"] for row in list.cif["comp_list"]["_chem_comp"].iterrows() ]
        self._srv = server.server(list_cif=list)        

        bonds = {}
        output = []

        for r in res_ids:
            if not r in self._residues:
                self._generate_ligand_restraints()
                break
        
        for r in res_ids:
            res = self._srv.get_comp_comp_id_direct(r)
            
            if res is not None:
                for b in res.bond_list:
                    if not (b.atom_id_1.startswith('H') or b.atom_id_2.startswith('H')):
                        if not b.atom_id_1 in bonds:
                            bonds[b.atom_id_1] = {}
                            
                        bonds[b.atom_id_1][b.atom_id_2] = b.value_dist
                        output.append('DFIX_%s %.3f %s %s' % (r, b.value_dist, b.atom_id_1, b.atom_id_2))
            
                for a in res.angle_list:
                    if not (a.atom_id_1.startswith('H') or a.atom_id_2.startswith('H') or a.atom_id_3.startswith('H')):
                        ang = None
                        dist1 = None
                        dist2 = None
                        
                        if a.atom_id_1 in bonds:
                            if a.atom_id_2 in bonds[a.atom_id_1]:
                                dist1 = bonds[a.atom_id_1][a.atom_id_2]

                        if a.atom_id_2 in bonds:
                            if a.atom_id_1 in bonds[a.atom_id_2]:
                                dist1 = bonds[a.atom_id_2][a.atom_id_1]
                    
                        if a.atom_id_2 in bonds:
                            if a.atom_id_3 in bonds[a.atom_id_2]:
                                dist2 = bonds[a.atom_id_2][a.atom_id_3]

                        if a.atom_id_3 in bonds:
                            if a.atom_id_2 in bonds[a.atom_id_3]:
                                dist2 = bonds[a.atom_id_3][a.atom_id_2]
        
                        if a.value_angle is not None and dist1 is not None and dist2 is not None:
                            dang = math.sqrt(math.pow(dist1,2)+math.pow(dist2,2)-(2*dist1*dist2*math.cos((math.pi/180)*a.value_angle)))
                            output.append('DANG_%s %.3f %s %s' % (r, dang, a.atom_id_1, a.atom_id_3))
            
                for p in res.get_planes():
                    atoms = []
                    for a in p.plane_atoms:
                        if not a.atom_id.startswith('H'):
                            atoms.append(a.atom_id)
                    
                    if len(atoms) > 2:
                        output.append('FLAT_' + r + ' ' +  ' '.join(atoms))
                    

                output.append('CHIV_%s C' % r)
                for c in res.chir_list:
                    output.append('CHIV_%s %.3f %s' % (r, res.get_chir_volume_ideal(c) * (1 if c.volume_sign == 'positiv' else -1), c.atom_id_centre))
            
                for t in res.tor_list:
                    if t.id.startswith('chi'):
                        output.append('RTAB_%s %s %s %s %s %s' % (r, t.id.capitalize(), t.atom_id_1, t.atom_id_2, t.atom_id_3, t.atom_id_4))

                output.append('\n')
        
        
        return '\n'.join(output)

    # call elbow for ligands that dont have restraints and merge into monomer library
    def _generate_ligand_restraints(self):
        try:
            from elbow.scripts import elbow_on_pdb_file
        except ImportError:
            wx.MessageBox('Couldnt find phenix.elbow, you will need to manually generate ligand restraints', 'Couldnt find phenix.elbow', wx.OK | wx.ICON_INFORMATION)
            return
        
        wx.MessageBox('Generating restraints for ligands using elbow. This may take a few minutes.', 'Generating Restraints', wx.OK | wx.ICON_INFORMATION)
        rests = elbow_on_pdb_file.run(self._pdbf.as_pdb_string(), silent=True)
                                 
        if rests is not None:
            h, cifs, z = rests
            
            for ci in cifs:
                self._srv.process_cif_object(cif.reader(input_string=cifs[ci]).model())
                self._residues.append(ci)
            


# ----------------------------------------------------------------------------
# CIF -> Shelx HKL
class CIFImporter:

    def __init__(self, cif_file, f_label, r_label, root, new_rfree=False):
        self._complete = False
        
        if os.path.exists(cif_file):
            input = reflection_file_reader.any_reflection_file(cif_file)
            
            for ma in input.as_miller_arrays():
                if ma.info().label_string() == f_label:
                    fs = ma
                if not new_rfree:
                    if ma.info().label_string() == r_label:
                        rs = ma.data()

            if not new_rfree:
                any_flagged = False
                for r in rs:
                    if r == 'f':
                        any_flagged = True
                        break
                
                if not any_flagged:
                    new_rfree = True
                

            if new_rfree:
                rs = fs.generate_r_free_flags(0.05).data()
            
            t = fs.is_xray_intensity_array()
            h = fs.indices()
            sig = fs.sigmas()

            maxf = max(fs.data())
            
            sf = 1
            if maxf > 99999:
                sf = maxf/99999
            
            hkl = []
            for i, f in enumerate(fs.data()):
                if f is not None:
                    free = 1
                    if rs[i] == 'f' or (new_rfree and rs[i] != 0):
                        free = -1
                    
                    hkl.append("%4d%4d%4d%8.2f%8.2f%4d" % (h[i][0], h[i][1], h[i][2], f/sf, sig[i]/sf, free))
                
            hkl.append("   0   0   0    0.00    0.00")
        
            if t:
                t = 'I'
            else:
                t = 'F'        
        
            file = os.path.basename(cif_file).replace('.cif', '').replace('.mtz', '')
            file_name = root+'/'+file+'_'+t+'.hkl'
            
            output = open(file_name, 'w')
            output.write('\n'.join(hkl))
            output.close()
    
            self._complete = True

    def finished(self):
        return self._complete

# ----------------------------------------------------------------------------
# LST -> Arrays/Data
class LSTParser:

    def __init__(self, lst_file):
        if os.path.exists(lst_file):
            self._file = lst_file
            
            lst = open(lst_file)
            self._lst = lst.read().split('\n')
            lst.close()

    def get_site_info(self):
        split = re.compile(r'\s+(\d+.\d+)\s+(\d+.\d+)\s+(\d+.\d+)\s+(\w+)\s+may be split into')
        npd = re.compile(r'\s+(\-?\d+.\d+)\s+(\-?\d+.\d+)\s+(\-?\d+.\d+)\s+(\w+)\s+\*\* NON POSITIVE DEFINITE')
        
        self._sites = []
        self._npds = []
        
        for l in self._lst:
            m = split.match(l)
            if m:
                self._sites.append([m.group(1), m.group(2), m.group(3), m.group(4)])
                
            m = npd.match(l)
            if m:
                self._npds.append([m.group(1), m.group(2), m.group(3), m.group(4)])
                        
        return self._sites, self._npds


    def get_stats(self):
        bonds = -1
        angles = -1
        rms = re.compile('\s+rms deviation\s+(\d+.\d+)\s+(\d+.\d+)\s+(\d+.\d+)')
        
        for l in self._lst:
            m = rms.match(l)
            if m:
                bonds = float(m.group(2))
                angles = math.acos(float(m.group(3)))

        return bonds, angles




