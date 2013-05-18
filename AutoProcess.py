from Constants import *

class AutoProcessManager:
    
    def __init__(self):
        self._processes = []

    def refinement_finished(self, id, status):
        for p in self._processes:
            p.refinement_finished(id, status)

    def new(self, title, refln, input, type, cycles, res, resl, options):
        params = {'title':title, 'refln':refln, 'input':input, 'cycles':cycles, 'res':res, 'resl':resl, 'options':options}
        self._processes.append(AutoProcess(options['ur_cycles'], options['total_cycles'], params))


class AutoProcess:
    
    @staticmethod
    def set_start_refinement(func):
        AutoProcess._start_refinement = func
    
    
    def __init__(self, ur_cycles, total_cycles, params):
        self._ur_cycles = ur_cycles
        self._total_cycles = total_cycles
        self._params = params
        
        self._ur_cycle = 0
        self._total_cycle = 0
        
        self._current_process = -1
        self._last_process = -1
        self._current_root = ''
        self._last_root = ''
        
        self._first = 1
    
        self.start_next_refinement()


    def refinement_finished(self, id, status):
        if id == self._current_process and status == 'Finished':
            self._last_process = self._current_process
            self._last_root = self._current_root
            self.start_next_refinement()


    def start_next_refinement(self):
        if self._ur_cycle <= self._ur_cycles * 2 and self._total_cycle < self._total_cycles:
            p = self._params
            
            if self._ur_cycle == (self._ur_cycles*2):
                self._total_cycle += 1
                self._ur_cycle = 0
                type = FULL_MATRIX
                cycles = 1
            
            else:
                type = RESTRAINED if self._ur_cycle % 2 == 0 else PART_UNRESTRAINED
                cycles = p['cycles']
        
            title = 'AUTO: %s [%d/%d %d/%d]' % (p['title'], self._ur_cycle/2, self._ur_cycles, self._total_cycle, self._total_cycles)
                
            if self._first:
                file = p['input']
                self._first = 0
            else:
                file = self._last_root + '.res'
                
            self._current_process, self._current_root = self._start_refinement(title, p['refln'], file, type, cycles, p['res'], p['resl'], p['options'])

            if not self._ur_cycle == (self._ur_cycles*2):
                self._ur_cycle += 1

