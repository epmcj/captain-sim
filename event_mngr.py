###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM)                        ##
##  Departamento de Ciencia da Computacao (DCC)                              ##
##  Universidade Federal de Minas Gerais (UFMG)                              ##
##                                                                           ##
##  An event manager that organizes events by their time.                    ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################
from heapq import heappop, heappush

class EventManager:
    def __init__(self):
        self.heap = []

    def insert(self, event):
        heappush(self.heap, event)

    def first(self):
        return self.heap[0]

    def get_next(self):
        return heappop(self.heap)
    
    def __len__(self):
        return len(self.heap)

