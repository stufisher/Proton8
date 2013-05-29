import coot
import coot_python
import gtk
import gobject
import inspect

from SimpleXMLRPCServer import SimpleXMLRPCServer

class CootInterface:
    def __init__(self):
        self.xmlrpc_server = SimpleXMLRPCServer(("localhost", 41734))
        self.xmlrpc_server.socket.settimeout(0.01)
        self.xmlrpc_server.register_instance(CootFunctions(), True)  
        gobject.timeout_add(250, self.timeout_func)
    
        loc = inspect.getfile(inspect.currentframe()).replace('Coot.py', '')
        read_cif_dictionary(loc + 'Resources/sh_monomer.cif')
    
    def timeout_func (self, *args) :
        if self.xmlrpc_server is not None :
            self.xmlrpc_server.handle_request()
        return True    

class CootFunctions:
    def __init__(self):
        self.coot = coot
        
        self._loaded_pbds = []
        self._loaded_maps = []
    
    def load_refinement(self, base, lst=False):
        self.close_maps()
        self.close_models()
    
        read_shelx_ins_file(base + '.res', 0)
        handle_shelx_fcf_file(base + '.fcf')
        if lst:
            read_shelx_lst_file(base + '.lst', 0)
        
        return True
        
    def centre_residue(self, chain, id, atom):
        #set_zoom_factor(21)
        set_go_to_atom_chain_residue_atom_name(chain, id, atom)
        
        return True
        
    def close_maps(self) :
        old_maps = map_molecule_list()
        for imol in old_maps :
            close_molecule(imol)
        return True

    def close_models(self) :
        old_mols = molecule_number_list()
        for imol in old_mols :
            if (not have_unsaved_changes_p(imol)) :
                close_molecule(imol)
        return True        


def startup():
    gui = CootInterface()
    
    
startup()