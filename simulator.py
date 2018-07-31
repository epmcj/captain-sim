###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM)                        ##
##  Departamento de Ciencia da Computacao (DCC)                              ##
##  Universidade Federal de Minas Gerais (UFMG)                              ##
##                                                                           ##
##  Simulator for underwater optical-acoustic networks.                      ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################
from basic_node import BasicNode
from event_mngr import EventManager
from sim_events import EventGenerator as EG, EventCode
from channels   import AcousticChannel, OpticalChannel
from message    import *
from modens     import AcousticModem as AM, OpticalModem as OM
from clock      import Clock
import tools

class Simulator:
    beta = 0
    def __init__(self, verbose=False):
        self.packetSize   = 0
        self.tdmaSlotSize = 0
        # channels
        self.achannel = AcousticChannel(k = 2.0, s = 0.0, w = 0.0)
        self.ochannel = OpticalChannel(c  = 4.3e-2, T = 298.15, \
                                       S = OM.sensitivity, \
                                       R = OM.shuntResistance, \
                                       Id = OM.maxDarkCurrent, \
                                       Il = OM.incidentCurrent, \
                                       Ar = OM.Ar, At = OM.At, \
                                       bw = OM.bandWidth, \
                                       theta = OM.beamDivergence)
        # application parameters
        self.appStart    = tools.INFINITY
        self.appInterval = tools.INFINITY
        self.appStop     = tools.INFINITY 
        # control
        self.clock     = Clock()
        self.evMngr    = EventManager()
        self.verbose   = verbose
        self.firstNode = 0
        # node control
        self.nodesUpdated = True
        self.numNodes   = 0
        self.nodesRef   = {} # __
        self.aneighbors = {} # __
        self.oneighbors = {} # __
        # statistics
        self.atxs        = 0
        self.afailedRxs  = 0
        self.asucceedRxs = 0
        self.otxs        = 0
        self.ofailedRxs  = 0
        self.osucceedRxs = 0

    def add_node(self, node):
        #
        assert issubclass(type(node), BasicNode)
        assert node.addr is not BROADCAST_ADDR, "Node addr is invalid (addr=0)"
        node.set_clock_src(self.clock)
        node.set_verbose(self.verbose)
        self.nodesRef[node.addr] = node
        self.nodesUpdated = False

    def set_tdma_slot(self, tdmaSlotSize):
        self.tdmaSlotSize = tdmaSlotSize

    def set_packet_size(self, packetSize):
        self.packetSize = packetSize

    def set_data_collection(self, appStart, appInterval, appStop=tools.INFINITY):
        self.appStart    = appStart
        self.appInterval = appInterval
        self.appStop     = appStop

    def get_num_nodes(self):
        return len(self.nodesRef.values())

    def get_num_acoustic_txs(self):
        return self.atxs

    def get_num_acoustic_successes(self):
        return self.asucceedRxs

    def get_num_acoustic_failures(self):
        return self.afailedRxs

    def get_num_optical_txs(self):
        return self.otxs

    def get_num_optical_successes(self):
        return self.osucceedRxs

    def get_num_optical_failures(self):
        return self.ofailedRxs

    # necessary for broadcast
    def __update_nodes_info(self):
        if self.verbose: 
            print("Updating nodes information")
        self.numNodes = len(self.nodesRef)
        for addr1 in self.nodesRef.keys():
            # updating tdma info
            self.nodesRef[addr1].update_time_slot_size(self.tdmaSlotSize)
            self.nodesRef[addr1].update_num_time_slots(self.numNodes)
            # updating neighborhood references
            aneighbors = []
            oneighbors = []
            for addr2 in self.nodesRef.keys():
                if addr1 is not addr2:
                    node1 = self.nodesRef[addr1]
                    node2 = self.nodesRef[addr2]
                    distance = tools.distance(node1.position, node2.position)
                    if distance <= AM.maxRange:
                        aneighbors.append(addr2)
                    if distance <= OM.maxRange:
                        oneighbors.append(addr2)
            self.aneighbors[addr1] = aneighbors
            self.oneighbors[addr1] = oneighbors

    def create_app_msgs(self):
        # Method to feed the routing algorithm with application messages.
        for node in self.nodesRef.values():
            if node.energy > 0 and node.isSink is False:
                node.collect_data()

    def print_data(self):
        print("Time: {0:.5f}".format(self.clock.read()))
        print("Number of acoustic transmissions: " + str(self.atxs))
        print("Number of optical transmissions: "  + str(self.otxs))

    def __handle_send_event(self, event):
        # Check if some transmission is successful. In case of success, events
        # for message receptions are created.
        msg          = event[2]
        isAcoustic   = msg.flags & MsgFlags.ACOUSTIC
        destinations = []
        if msg.dst == BROADCAST_ADDR:
            assert isAcoustic, "Optical broadcasts are not allowed"
            destinations = self.aneighbors[msg.src]
        else:
            destinations = [msg.dst]

        if isAcoustic:
            self.atxs += 1
        else:
            self.otxs += 1

        for dst in destinations:
            srcPos = self.nodesRef[msg.src].position
            dstPos = self.nodesRef[dst].position
            dist   = tools.distance(srcPos, dstPos)
            if self.verbose:
                print("Message " + str(msg.src) + "->" + str(dst), end=" ")
            if isAcoustic:
                success = self.achannel.use(AM.frequency, AM.txPower, dist, \
                                            len(msg))
                if success:
                    self.asucceedRxs += 1
                    propTime = self.achannel.get_propagation_time(dist)
                    recvTime = self.clock.read() + propTime
                    self.evMngr.insert(EG.create_recv_event(recvTime, dst, msg))
                    if self.verbose:
                        print("was successfull: will arrive " + str(recvTime))
                else:
                    if self.verbose:
                        print("failed")
                    self.afailedRxs  += 1
            else:
                success = self.ochannel.use(OM.txPower, dist, dist, self.beta, \
                                            len(msg))
                if success:
                    self.osucceedRxs += 1
                    propTime = self.ochannel.get_propagation_time(dist)
                    recvTime = self.clock.read() + propTime
                    self.evMngr.insert(EG.create_recv_event(recvTime, dst, msg))
                    if self.verbose:
                        print("was successfull: will arrive " + str(recvTime))
                else:
                    if self.verbose:
                        print("failed")
                    self.ofailedRxs  += 1

    def start(self, stopExec):
        assert (stopExec > 0), "Execution time must be > 0" 
        assert (self.tdmaSlotSize > 0), "TDMA time slots must be > 0" 
        assert (self.packetSize > 0), "Packet size can not be <= 0"
        assert (len(self.nodesRef) is not 0), "Missing nodes" 
        assert (self.appStart is not tools.INFINITY), "Missing app start time"
        assert (self.appInterval is not tools.INFINITY), "Missing app "+ \
                                                         "interval time"
        assert (self.appStop > self.appStart), "Stop time must be > start time"

        # if it is the first simulation start call
        if not self.clock.alarm_is_on():
            # set alarm to start the data collection process
            self.clock.set_alarm(self.create_app_msgs, self.appStart, \
                                 self.appInterval, self.appStop)
            # Creating a basic payload to avoid large memory usage
            # Removes two header size because of Packet inside Packet 
            # (used for statistics)
            payloadSize = self.packetSize - (2 * Message.headerSize)
            basicPayload = list(0 for x in range(0, payloadSize))
            for node in self.nodesRef.values():
                node.basicPayload = basicPayload
                node1stSlot       = self.clock.read() + (self.tdmaSlotSize * \
                                    (node.addr - 1))
                self.evMngr.insert(EG.create_call_event(node1stSlot, node.addr))
        
        # Updating node information because some node was recently added
        if not self.nodesUpdated:
            self.__update_nodes_info()

        nodesList = [0] + list(self.nodesRef.values()) # to align with addresses
        numSlots  = int(stopExec/self.tdmaSlotSize)
        print("Simulation started")
        while len(self.evMngr) != 0:
            event = self.evMngr.get_next()
            eTime = event[0]
            if eTime >= stopExec:
                break
            self.clock.force_time(eTime) # adjusting time for event
            ecode = event[1]
            naddr = event[2]
            if ecode is EventCode.NODE_CALL:
                if self.verbose:
                    print("Node " + str(naddr) + " is executing")
                newEvents = nodesList[naddr].execute()
                for newEvent in newEvents:
                    # msg send events are handled
                    if newEvent[1] is EventCode.MSG_SEND:
                       self.__handle_send_event(newEvent)
                    else:
                        self.evMngr.insert(newEvent)
            elif ecode is EventCode.MSG_RECV:
                msg = event[3]
                if self.verbose:
                    print("Node " + str(naddr) + " is receiving a message")
                newEvents = nodesList[naddr].recv_msg(msg)
                for newEvent in newEvents:
                    # msg send events are handled
                    if newEvent[1] is EventCode.MSG_SEND:
                       self.__handle_send_event(newEvent)
                    else:
                        self.evMngr.insert(newEvent)
            else:
                raise Exception("Unknown event code " + str(ecode))
        print("Simulation finished")