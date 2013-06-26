import iotbx.pdb

class PDBTools:

    _pdb_file = None
    _weights = { 'C': 12, 'O': 16, 'N': 14, 'S': 16, 'P': 15, 'H': 1 }
    
    def __init__(self, file_name=None):
        if file_name is not None:
            print file_name
            self._pdb_file = iotbx.pdb.input(file_name=file_name)

    def get_bond_lengths(self, pdb_file):
        self._omitted = {'asp': [], 'glu': [], 'his': [], 'arg': []}
        self._residues = {'asp': {}, 'glu': {}, 'his': {}, 'arg': {}}
        
        b_avg_array = [[],[],[]]
        rlist = {'asp': {}, 'glu': {}, 'his': {}, 'arg': {}}
        t = {'ASP': [' CG ', ' OD1', ' OD2'], 'GLU': [' CD ', ' OE1', ' OE2']} 
        pdb = iotbx.pdb.input(file_name=pdb_file)
        for a in pdb.atoms_with_labels():
            b_avg_array[2].append(a.b)
                    
            if a.resname in ['HOH', 'DOD']:
                b_avg_array[1].append(a.b)
            
            if a.resname in ['ASP', 'ALA', 'HIS', 'ARG', 'LYS', 'GLN', 'GLU', 
                             'TYR', 'PRO', 'LEU', 'ILE', 'MET', 'VAL', 'SER',
                             'ASN', 'CYS', 'GLY', 'TRP', 'PHE', 'THR', 'LYS']:
                b_avg_array[0].append(a.b)
        
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
                        #for i,a in res.iteritems():
                        #    print i,a.name

                        self._residues[t][rid] = {  1: [res[1].angle(res[0], res[2], True), res[1].occ, res[1].b], 
                                                    2: [res[4].angle(res[3], res[2], True), res[4].occ, res[4].b],
                                                    3: [res[2].angle(res[1], res[4], True), res[2].occ, res[2].b],
                                                    4: [res[3].angle(res[0], res[4], True), res[3].occ, res[3].b],
                                                    5: [res[0].angle(res[3], res[1], True), res[0].occ, res[0].b],
                                                    }

                elif t == 'arg':
                    if len(res) == 4:
                        self._residues[t][rid] = {1: [res[0].distance(res[1]), res[1].occ, res[1].b], 2: [res[0].distance(res[2]), res[2].occ, res[2].b], 3: [res[0].distance(res[3]), res[3].occ, res[3].b]}

        self._residues['avg'] = {}
        for i,k in enumerate(['pro', 'sol', 'all']):
            if len(b_avg_array[i]) > 0:
                val = sum(b_avg_array[i])/len(b_avg_array[i])
            else:
                val = 0;
            self._residues['avg'][k] = val

        #self._residues['avg'] = {'b': (sum(b_avg_array)/len(b_avg_array))}
        
        return self._omitted, self._residues


    # Get coot chain identifiers for a shelx ins file - splits on 21 residue difference apparantly??
    def get_chains(self, pdb_file):
        residues = []
        pdb = iotbx.pdb.input(file_name=pdb_file)
        for a in pdb.atoms_with_labels():
            rid = int(a.resid())
            if rid not in residues:
                residues.append(rid)

        cid = 'A'
        res_lookup = {}
        _last = 0
        for r in sorted(residues):
            if r - _last > 21:
                cid = chr(ord(cid)+1)
            
            res_lookup[r] = cid
            
            _last = r
        
        return res_lookup


    # Calculate rmm
    def get_rmm(self, pdb_file=None):
        if self._pdb_file is not None:
            pdb = self._pdb_file
        else:
            pdb = iotbx.pdb.input(file_name=file)
        
        rmm = 0

        for a in pdb.atoms_with_labels():
            if a.resname in ['ASP', 'ALA', 'HIS', 'ARG', 'LYS', 'GLN', 'GLU',
                             'TYR', 'PRO', 'LEU', 'ILE', 'MET', 'VAL', 'SER',
                             'ASN', 'CYS', 'GLY', 'TRP', 'PHE', 'THR', 'LYS']:
                
                rmm += self._weights[a.name.strip()[0]] * a.occ

        return rmm


    def get_s(self, pdb_file=None):
        if self._pdb_file is not None:
            pdb = self._pdb_file
        else:
            pdb = iotbx.pdb.input(file_name=pdb_file)
        
        s = 0
        tot = 0
    
        for a in pdb.atoms_with_labels():
            if a.resname in ['DOD', 'HOH']:
                if a.name.strip() == 'O':
                    s += a.occ
            else:
                tot += a.occ

        return s/tot
