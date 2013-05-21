import subprocess
#import fcntl
import os
import re
import shutil
import pickle
import time
import wx
import inspect

from Queue import Queue
from threading import Thread

from Constants import *

DEBUG = 1

def debug_print(text):
    if DEBUG:
        print text

# ----------------------------------------------------------------------------
# Fork shelx and parse results
class Refinement:
    
    @staticmethod
    def set_proot(root):
        Refinement.proot = root
    
    _running_callback = None
    _start_callback = None
    _cycle_callback = None
    _finished_callback = None
    _error_callback = None

    def __init__(self, panel, type, input, title, res, resl, cycles, ins, hkl, id, options):
        self._parameters = {'status': 'Starting', 
                            'title': title,
                            'res': res, 'resl': resl,
                            'total_cycles': cycles,
                            'log':'', 
                            'input': input, 
                            'last_cycle': 0, 
                            'type': type, 
                            'rfree': -1, 'r': -1,
                            'cycles': {},
                            'time': time.time(),
                            'ins': ins,
                            'hkl': hkl,
                            'id': id,
                            'options': options
                            }
    
        self._first = 0
        self._type = type
        self._args = '-b20000' if options['target'] == LS else ''
        self._input = input
        self._panel = panel
        
        print str(options['target']) + ' ' + str(LS) + ' ' + str(options['target'] == LS)
        
        self._start_time = time.time()
        self.timer = wx.Timer(self._panel, 200)
        wx.EVT_TIMER(self._panel, 200, self.check_output)
        
        cmd =  self.proot + '/Resources/Programs/' + ('shelxl_mp.exe' if os.name =='nt' else 'shelxl_mp')
        print cmd
        if not os.path.exists(cmd):
            wx.MessageBox('Couldnt find shelx', 'Couldnt find shelx', style=wx.OK | wx.CENTRE)
            self.shelx = None
        else:
            self.timer.Start(100, False)
            self.shelx = subprocess.Popen([cmd, self._args, self._input], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.q = Queue()
            self.rt = Thread(target=self.queue_output, args=(self.shelx.stdout, self.shelx.stderr, self.q))
            self.rt.daemon = True
            self.rt.start()
        

    def queue_output(self, stdout, stderr, q):
        for line in iter(stdout.readline, b''):
            q.put(line)
        stdout.close()
        
        for line in iter(stderr.readline, b''):
            q.put(line)
        stderr.close()

    def set_callbacks(self, started, running, cycle, finished, error):
        self._running_callback = running
        self._start_callback = started
        self._cycle_callback = cycle
        self._finished_callback = finished
        self._error_callback = error
        
    def clear_callbacks(self):
        self._running_callback = None
        self._start_callback = None
        self._cycle_callback = None
        self._finished_callback = None
        self._error_callback = None

        
    def check_output(self, event):
        if not self._first:
            if self._start_callback:
                self._start_callback()            
            self._first = 1
    
        raw = ''
        for _ in range(self.q.qsize()):
            raw += self.q.get_nowait()
    
        if self.shelx.poll() is None:
            self._parameters['status'] = 'Running'
            if self._running_callback:
                self._running_callback('Refinement Running... (%ds)' % (time.time()-self._start_time))
        
            if raw:
                data = raw.split("\n")
                self._parameters['log'] += raw
                    
                # wR2 =  0.3067 before cycle   1 for  49239 data and 46380 / 46380 parameters
                wr_re  = re.compile(' wR2 =\s+(\d+.\d+)\s+before cycle\s+(\d+) for\s+(\d+) data and\s+\d+\s+/\s+(\d+)\s+parameters')
                # GooF = S =    11.478;     Restrained GooF =      3.826  for  60623 restraints
                wr_re2 = re.compile(' GooF = S =\s+(\d+.\d+);\s+Restrained GooF =\s+(\d+.\d+)')
                
                # R1(Free) =  0.1742 for  2507 Fo > 4sig(Fo)  and  0.1774 for all  2596 data
                rf_re = re.compile(' R1\(Free\) =\s+(\d+.\d+)\s+for\s+\d+\s+Fo > 4sig\(Fo\)\s+and\s+(\d+.\d+)')            
                # R1 =  0.1124 for  47524 Fo > 4sig(Fo)  and  0.1138 for all  49239 data
                r_re = re.compile(' R1 =\s+(\d+.\d+) for\s+\d+ Fo > 4sig\(Fo\)\s+and\s+(\d+.\d+)')            
                
                for line in data:
                    p = wr_re.match(line)
                    if p:
                        self._parameters['cycles'][int(p.group(2))] = [float(p.group(1)), 0, int(p.group(3)), int(p.group(4))]
                        self._parameters['r'] = str(round(float(p.group(1))/2,3)) + ' (est)'
                        self._parameters['last_cycle'] = int(p.group(2))
                    
                    p = wr_re2.match(line)
                    if p:
                        self._parameters['cycles'][self._parameters['last_cycle']][1] = float(p.group(1))
                        self._cycle_callback()
                
                    p = rf_re.match(line)
                    if p:
                        debug_print('got rfree')
                        self._parameters['rfree'] = float(p.group(2))

                    p = r_re.match(line)
                    if p:
                        debug_print('got r')
                        self._parameters['r'] = float(p.group(2))
                        
                        if self._cycle_callback:
                            self._cycle_callback()
            
        else:
            self._parameters['log'] += raw

            if (self._parameters['status'] != 'Aborted') and (self._parameters['r'] == -1 or type(self._parameters['r']) == type(str())):
                if self._error_callback:
                    self._error_callback(self._parameters['log'])
                self._parameters['status'] = 'Failed'
            
            if self._parameters['status'] == 'Running':
                self._parameters['status'] = 'Finished'
                
            if self.rt and self.rt.is_alive():
                self.rt.join()
            self.rt = None
            self.q = None
                
            self.timer.Stop()
            self.timer = None
            self.shelx = None
            self._panel = None
    
            self._parameters['timef'] = time.time()
    
            #if self._finished_callback:
            #    self._finished_callback()
            fin = self._finished_callback
            
            self.clear_callbacks()
            
            pickle.dump(self, open(self._parameters['input'] + '.dat', 'wb'))

            out = open(self._parameters['input'] + '.log', 'w')
            out.write(self._parameters['log'])
            out.close()

            if fin:
                fin()
            


    # nicked...
    def non_block_read(self, output):
        fd = output.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            return output.read()
        except:
            return ''
            
    def abort(self):
        if self.shelx:
            if self.shelx.poll() is None:
                self.shelx.terminate()
                self._parameters['status'] = 'Aborted'
            
            
    def parameters(self):
        return self._parameters

