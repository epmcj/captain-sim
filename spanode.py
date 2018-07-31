###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM)                        ##
##  Departamento de Ciencia da Computacao (DCC)                              ##
##  Universidade Federal de Minas Gerais (UFMG)                              ##
##                                                                           ##
##  Node that uses a shortest path algorithm (SPA) for data collection.      ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################

from spamessage import MessageGenerator as MG, BASIC_TTL, BROADCAST_ADDR, \
                        SPAFlags, SPATypes 
from basic_node import BasicNode
from sim_events import EventGenerator  as EG               
from modens     import AcousticModem   as AM, OpticalModem   as OM
from channels   import AcousticChannel as AC, OpticalChannel as OC
from clock      import Clock
import tools 

class SPAState:
    OUT_ROUTE = 0
    IN_ROUTE  = 1
    # DEAD      = 2

class SPANode(BasicNode):
    
    def __init__(self, addr, x, y, depth, energy, aTimeout, oTimeout,
                 clock=None, slotSize=1, numSlots=1, verbose=False):
        super(SPANode, self).__init__(addr, x, y, depth, energy, clock, 
                                      slotSize, numSlots, verbose)
        # for SP algorithm
        self.reqInt     = 10 # in rounds
        self.state      = SPAState.OUT_ROUTE 
        self.costToSink = tools.INFINITY
        if self.isSink is True:
            self.costToSink = 0
        self.nextHop     = None
        self.nextHopDist = tools.INFINITY
        self.useAcoustic = True
        # for retransmissions
        self.oTimeout = oTimeout
        self.aTimeout = aTimeout
        # self.verbose = verbose
        # self.inbox = []
        # self.outbox = [] # pair [msg, number of transmissions]
        # self.waitingACK = False
        # if (clock is None) or (clock.__class__.__name__ is not "Clock"):
        #     self.clock = Clock()
        # else:
        # self.addr      = addr
        # self.position  = [x, y, depth]
        #     self.clock = clock
        # self.energy    = energy
        # self.isSink = addr in self.sinkNodesAddr
        # for TDMA
        # self.round = 0         
        # Energy related
        # self.maxEnergy = energy
        # for recovery (next hop is dead)
        # self.msgsLostCount = 0
        # self.msgsLostLimit = 5
        # for statistics
        # self.recvdMsgsCounter = 0
        # self.sentMsgsCounter  = 0
        # self.avgNumHops = 0
        # self.maxNumHops = 0 
        # self.avgTimeSpent = 0
        # self.maxTimeSpent = 0
        # best for memory
        # self.acouticAck = MG.create_acoustic_ack(addr, 0)
        # time, _ = tools.estimate_transmission(self.acouticAck)
        # self.acousticAckTime = 2 * time # upper bound to ack time
        # self.opticalAck = MG.create_optical_ack(addr, 0)
        # time, _ = tools.estimate_transmission(self.opticalAck)
        # self.opticalAckTime = 2 * time # upper bound to ack time

    def move(self, newX, newY, newDepth):
        # Move node to new position.
        self.position[0] = newX
        self.position[1] = newY
        self.position[2] = newDepth

    def recharge(self):
        self.energy = self.maxEnergy

    def collect_data(self):
        # Generates an application message and puts it into the end of the 
        # outbox.
        # assert self.nextHop is not None, "No next hop found"
        # Simulating the application message as one optical data message.
        msg = MG.create_optical_datamsg(self.addr, 1, self.basicPayload,
                                        self.clock.read()) 
        if self.useAcoustic is True:
            end_msg = MG.create_acoustic_datamsg(self.addr, self.nextHop, msg,
                                                 self.clock.read())
        else:
            end_msg = MG.create_optical_datamsg(self.addr, self.nextHop, msg,
                                                self.clock.read()) 
        self.outbox.append([end_msg, 0])
        self.dataCollections += 1

    def execute(self):
        # This method is used to simulate the execution of the node. It will
        # return a message, and the required time to transmit it, when the node 
        # wants to communicate.
        currTime = self.clock.read()
        if self.energy <= 0:
            # self.state = SPAState.DEAD
            return []

        if currTime > self.endSlot and currTime < self.nextSlot:
            raise Exception("Node should not be called to execute")

        if self.verbose:
            print("Node " + str(self.addr) + " Curr Time: " + str(currTime) + \
                  " Nxt Slot: " + str(self.nextSlot))
        isNewSlot = False
        if currTime == self.nextSlot:
            isNewSlot = True
            self.update_tdma_info()
            if self.verbose:
                print("Round " + str(self.round))
        
        if self.msgsLostCount is self.msgsLostLimit:
            self.state         = SPAState.OUT_ROUTE
            self.costToSink    = tools.INFINITY
            self.nextHop       = None
            self.msgsLostCount = 0
            
        msg            = None
        execOnNextSlot = False 
        if self.state is SPAState.IN_ROUTE:
            # In this state the node is ready for routing data.
            msg = self.send_next_msg(self.endSlot - currTime)
            if msg is None and self.verbose:
                print("No message")

        elif self.state is SPAState.OUT_ROUTE:
            if self.isSink:
                self.state = SPAState.IN_ROUTE
                msg = MG.create_iamsg(self.addr, self.position, 0)
            else:
                if self.costToSink != tools.INFINITY:
                    self.state = SPAState.IN_ROUTE
                    msg = self.send_next_msg(self.endSlot - currTime)

                elif (self.round % self.reqInt) == 1:
                    msg = MG.create_req_joinmsg(self.addr)
                    execOnNextSlot = True
        else:
            raise Exception("Unknown state")
        
        events   = []
        callTime = self.nextSlot
        if msg is not None:
            txTime, energy, propTime = 0, 0, 0
            if  msg.flags & SPAFlags.ACOUSTIC:
                txTime, energy = tools.estimate_transmission(msg, AM.txRate, 
                                                        AM.txPowerConsumption)
                propTime = (self.nextHopDist / AC.soundSpeed) * 2.1
            else:
                txTime, energy = tools.estimate_transmission(msg, OM.txRate, 
                                                        OM.txPowerConsumption)
                propTime = (self.nextHopDist / OC.lightSpeed) * 2.1
            callTime = self.clock.read() + txTime + propTime
            # consumes node energy and generate event to send the message
            self.energy -= energy
            # always send a message and is called only on the next time slot
            events.append(EG.create_send_event(txTime, msg))

        if execOnNextSlot or (callTime >= self.endSlot):
            callTime = self.nextSlot
        events.append(EG.create_call_event(callTime, self.addr))
        
        return events

    def send_next_msg(self, remainingTime):
        # Sends the first message in the outbox if the time and energy are 
        # sufficient. Returns the sent message and the required time to 
        # transmit it (when the message requires an ack, the time is the sum
        # of both transmissions times - message and ack). 
        
        msg    = None
        if len(self.outbox) is not 0:
            while self.outbox[0][1] is self.MAX_TXS:
                # Reached the maximum number of transmissions allowed. 
                # Discard it and move on. Must check if the outbox got empty.
                if self.verbose:
                    print("(!) DROPPING MESSAGE")
                dmsg = (self.outbox.pop(0))[0]
                if (dmsg.flags & 0x0f) is SPATypes.COMMON_DATA:
                    self.msgsLostCount += 1
                self.dropdMsgsCounter += 1
                self.waitingACK        = False
                if self.msgsLostCount is self.msgsLostLimit or \
                   len(self.outbox) is 0:
                    return None # empty return
            # Will only sends a message if there is enough time and energy
            pair    = self.outbox[0]
            nextMsg = pair[0]
            if (nextMsg.flags & 0x0f) is SPATypes.COMMON_DATA:
                # Just the get the must updated next hop. (is useful when a 
                # next hop node dies)
                nextMsg.dst = self.nextHop
                if self.nextHop is None:
                    raise Exception("Node has no next hop.")
                if self.useAcoustic is True: 
                    # Must be update beacuse next hop may have changed and the
                    # node changed its state.
                    nextMsg.flags |= SPAFlags.ACOUSTIC 
                else:
                    nextMsg.flags &= ~SPAFlags.ACOUSTIC 
                if self.verbose:
                    print("{0:d} - {1:d}".format(nextMsg.src, nextMsg.dst))
                
            timeout, etime, eenergy = 0, 0, 0
            if (nextMsg.flags & SPAFlags.ACOUSTIC):
                etime, eenergy = tools.estimate_transmission(nextMsg, AM.txRate, 
                                                        AM.txPowerConsumption)
                acTimeout = (self.nextHopDist / AC.soundSpeed) * 2.1
                timeout = etime + acTimeout
            else:
                etime, eenergy = tools.estimate_transmission(nextMsg, OM.txRate, 
                                                        OM.txPowerConsumption)
                opTimeout = (self.nextHopDist / OC.lightSpeed) * 2.1
                timeout = etime + opTimeout
            
            if nextMsg.dst is BROADCAST_ADDR:
                if etime < remainingTime and eenergy < self.energy:
                    # Broadcasts do not need ACK so they only got send once.
                    msg = nextMsg
                    self.outbox.pop(0)
                else:
                    if self.verbose:
                        print("time is not enough")
            elif nextMsg.flags & SPAFlags.NEED_ACK:
                # Needs time to possibly receive the ACK.
                if timeout < remainingTime and eenergy < self.energy:
                    msg = nextMsg
                    self.outbox[0][1] += 1
                    self.waitingACK    = True
            else: 
                if self.verbose:
                    print("unknown message")
        else:
            if self.verbose:
                print("Empty outbox")
        # Just for statistics
        if msg is not None and (msg.flags & 0x0f) is SPATypes.COMMON_DATA:
            self.sentMsgsCounter += 1

        return msg

    def recv_msg(self, recvdMsg):
        # Function to be called when the node receives a message.
        if self.energy <= 0:
            # Node has no energy to receive the message
            return []

        events = []
        if recvdMsg.flags & SPAFlags.ACOUSTIC:
            recvTime     = (len(recvdMsg) * 8) / AM.txRate
            energyToRecv = recvTime * AM.rxPowerConsumption
        else:
            recvTime     = (len(recvdMsg) * 8) / OM.txRate
            energyToRecv = recvTime * OM.rxPowerConsumption
        if self.energy >= energyToRecv:
            self.energy -= energyToRecv
            self.handle_message(recvdMsg)
            if recvdMsg.flags & SPAFlags.NEED_ACK:
                # Generating ack to send
                if self.verbose:
                    print("Node " + str(self.addr) + " is sending ACK")
                acktime, energy = 0, 0
                if recvdMsg.flags & SPAFlags.ACOUSTIC:
                    ack = MG.create_acoustic_ack(self.addr, recvdMsg.src)
                    acktime, energy = tools.estimate_transmission(ack, 
                                            AM.txRate, AM.txPowerConsumption) 
                else:
                    ack = MG.create_optical_ack(self.addr, recvdMsg.src)
                    acktime, energy = tools.estimate_transmission(ack, 
                                            OM.txRate, OM.txPowerConsumption) 
                if self.energy > energy:
                    self.energy -= energy
                    time = self.clock.read() + acktime
                    events.append(EG.create_send_event(time, ack))
        else:
            if self.verbose:
                print("Missing energy (" + str(self.energy) + "|" +
                      str(energyToRecv) + ")")
        return events

    def handle_message(self, msg):
        # Handles the received messages acording to their types.
        msgType = msg.flags & 0x0f # first half is the type

        if msgType is SPATypes.COMMON_DATA:
            if self.verbose:
                print("Node " + str(self.addr) + \
                      ": handling data message from node " + str(msg.src))

            innerMsg      = msg.payload
            innerMsg.ttl -= 1
            if innerMsg.dst is not self.addr:
                if innerMsg.ttl is not 0:
                    if self.useAcoustic is True:
                        msg = MG.create_acoustic_datamsg(self.addr,
                                                         self.nextHop,
                                                         innerMsg,
                                                         self.clock.read())
                    else:
                        msg = MG.create_optical_datamsg(self.addr,
                                                        self.nextHop,
                                                        innerMsg,
                                                        self.clock.read())
                    self.outbox.append([msg, 0])
                else:
                    self.dropdMsgsCounter += 1
                    if self.verbose:
                        print("Message droped (TTL reached 0)")
            self.recvdMsgsCounter += 1
            if self.isSink is True:
                # Hops statistics
                corrCoeff = (self.recvdMsgsCounter - 1) / self.recvdMsgsCounter
                numHops = BASIC_TTL - innerMsg.ttl
                if numHops > self.maxNumHops:
                    self.maxNumHops = numHops
                self.avgNumHops *= corrCoeff
                self.avgNumHops += (numHops / self.recvdMsgsCounter) 
                # Time statistics
                time = self.clock.read() - innerMsg.ctime
                if self.verbose:
                    print("Received (time: " + str(time) + ")")
                if time > self.maxTimeSpent:
                    self.maxTimeSpent = time
                self.avgTimeSpent *= corrCoeff
                self.avgTimeSpent += (time / self.recvdMsgsCounter)

        elif (msgType is SPATypes.INFO_ANNOUN) or \
             (msgType is SPATypes.REP_JOIN):
            if self.verbose:
                print("Node " + str(self.addr) + \
                      ": handling info/rep_join message from node " + \
                      str(msg.src))
            nodePos   = msg.payload[0]
            nodeValue = msg.payload[1]
            dist      = tools.distance(self.position, nodePos)
            costToSink = nodeValue + dist
            if self.costToSink > costToSink:
                self.costToSink  = costToSink
                self.nextHop     = msg.src
                self.nextHopDist = dist
                self.useAcoustic = dist > OM.maxRange
                # To inform neighbors.
                msg = MG.create_iamsg(self.addr, self.position, self.costToSink)
                # Insert the message in que outbox or updates the next ot 
                # be sent. (control messages have high priority)
                if len(self.outbox) is not 0:
                    firstMsgType = self.outbox[0][0].flags & 0x0f
                    if firstMsgType is not SPATypes.INFO_ANNOUN:
                        self.outbox.insert(0, [msg, 0])
                    else:
                        self.outbox[0] = [msg, 0]
                else:
                    self.outbox.insert(0, [msg, 0])      

        elif msgType is SPATypes.REQ_JOIN:
            if self.verbose:
                print("Node " + str(self.addr) + \
                      ": handling req_join message from node " + str(msg.src))
            if self.state is SPAState.IN_ROUTE:
               # To inform neighbors.
                msg = MG.create_rep_joinmsg(self.addr, self.position, 
                                            self.costToSink)
                # Insert the message in que outbox or updates the next ot 
                # be sent. (control messages have high priority)
                if len(self.outbox) is not 0:
                    firstMsgType = self.outbox[0][0].flags & 0x0f
                    if firstMsgType is not SPATypes.REP_JOIN:
                        self.outbox.insert(0, [msg, 0])
                    else:
                        self.outbox[0] = [msg, 0]
                else:
                    self.outbox.insert(0, [msg, 0])  

        elif msgType is SPATypes.ACK:
            if self.verbose:
                print("Handling ACK from node " + str(msg.src))

            if self.waitingACK:
                self.outbox.pop(0)
                self.waitingACK = False
                if self.msgsLostCount is not 0:
                    self.msgsLostCount = 0
            else:
                if self.verbose:
                    raise Exception("error: unknown ack received")

        else:
            if self.verbose:
                raise Exception("unknown message type")
