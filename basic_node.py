###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM)                        ##
##  Departamento de Ciencia da Computacao (DCC)                              ##
##  Universidade Federal de Minas Gerais (UFMG)                              ##
##                                                                           ##
##  Node base implementation.                                                ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################

from clock import Clock

class BasicNode:
    # basic
    MAX_TXS       = 3
    sinkNodesAddr = [1]
    basicPayload  = []

    def __init__(self, addr, x, y, depth, energy, clock, slotSize, numSlots, 
                 verbose):
        assert type(clock) is Clock or clock is None, "Need a clock object"
        self.addr     = addr
        self.isSink   = addr in self.sinkNodesAddr
        self.position = [x, y, depth] 
        self.clock    = clock
        # for TDMA
        self.round    = 0
        self.slotSize = slotSize
        self.numSlots = numSlots
        self.endSlot  = 0
        self.nextSlot = slotSize * (addr - 1)
        self.verbose  = verbose
        # energy related
        self.maxEnergy = energy
        self.energy    = energy
        # for messages
        self.inbox         = []
        self.outbox        = [] # pair [msg, number of transmissions]
        self.msgsLostCount = 0
        self.msgsLostLimit = 5
        # for statistics
        self.recvdMsgsCounter = 0
        self.dropdMsgsCounter = 0
        self.dataCollections  = 0
        self.sentMsgsCounter  = 0
        self.avgNumHops       = 0
        self.maxNumHops       = 0 
        self.avgTimeSpent     = 0
        self.maxTimeSpent     = 0

    def move(self, newX, newY, newDepth):
        # Move node to new position.
        self.position[0] = newX
        self.position[1] = newY
        self.position[2] = newDepth

    def set_clock_src(self, clock):
        self.clock = clock

    def set_verbose(self, verbose):
        self.verbose = verbose

    def recharge(self, energy):
        self.energy += energy
        self.energy = min(self.energy, self.maxEnergy)

    def update_time_slot_size(self, newSize):
        assert newSize > 0, "Time slot can not be <= 0"
        if self.verbose:
            print("Updating node " + str(self.addr) + " time slot size from " +\
                  str(self.slotSize) + " to " + str(newSize))
        self.slotSize = newSize
        self.nextSlot = self.round * newSize * self.numSlots + \
                        newSize * (self.addr - 1)

    def update_num_time_slots(self, numSlots):
        assert numSlots > 0, "The number of slots can not be <= 0"
        self.numSlots = numSlots

    def update_tdma_info(self):
        self.round    += 1
        self.currSlot  = self.nextSlot
        self.endSlot   = self.currSlot + self.slotSize
        self.nextSlot += self.slotSize * self.numSlots

    def get_outbox_len(self):
        return len(self.outbox)

    def execute(self):
        raise NotImplementedError

    def collect_data(self):
        raise NotImplementedError
    
    def recv_msg(self, recvMsg):
        raise NotImplementedError