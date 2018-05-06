###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM),                       ##
##  Universidade Federal de Minas Gerais (UFMG).                             ##
##                                                                           ##
##  Node with shortest path algorithm (SPA).                                 ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################

from spmessages import MessageGenerator as MG, BASIC_TTL
from spmessages import BROADCAST_ADDR, Message, USPFlags, USPTypes 
from modens import AcousticModem as AM
from modens import OpticalModem as OM
from tools import Tools, INFINITY

class USPState:
    OUT_ROUTE = 0
    IN_ROUTE  = 1
    # DEAD      = 2 # just for debug

class USPNode:
    maxTransmissions = 3
    sinkNodesAddr = [1]
    basicPayload = []
    def __init__(self, addr, x, y, depth, energy, clock, verbose = False):
        assert clock.__class__.__name__ is 'Clock', 'Need a clock object'
        self.verbose = verbose
        self.inbox = []
        self.outbox = [] # pair [msg, number of transmissions]
        self.waitingACK = False
        self.isSink = addr in self.sinkNodesAddr
        self.clock = clock
        # for TDMA
        self.round = 0         
        #
        self.addr      = addr
        self.position  = [x, y, depth]
        # Energy related
        self.energy    = energy
        self.maxEnergy = energy
        self.criticalEnergy = False
        # for SP algorithm
        self.reqInt = 10 # in rounds
        self.state = USPState.OUT_ROUTE 
        if self.isSink is True:
            self.value = 0
        else:
            self.value = INFINITY
        self.nextHop = None
        self.useAcoustic = True
        # for retransmissions
        self.numRetries = 0
        # for recovery (next hop is dead)
        self.msgsLostCount = 0
        self.msgsLostLimit = 2
        self.deadNode      = None
        # for statistics
        self.recvdMsgsCounter = 0
        self.sentMsgsCounter  = 0
        self.avgNumHops = 0
        self.maxNumHops = 0 
        self.avgTimeSpent = 0
        self.maxTimeSpent = 0
        # best for memory
        self.acouticAck = MG.create_acoustic_ack(addr, 0)
        time, _ = Tools.estimate_transmission(self.acouticAck)
        self.acousticAckTime = 2 * time
        self.opticalAck = MG.create_optical_ack(addr, 0)
        time, _ = Tools.estimate_transmission(self.opticalAck)
        self.opticalAckTime = 2 * time

    def move(self, newX, newY, newDepth):
        # Move node to new position.
        self.position[0] = newX
        self.position[1] = newY
        self.position[2] = newDepth

    def recharge(self):
        self.energy = self.maxEnergy

    def application_generate_msg(self):
        # Generates an application message and puts it into the end of the 
        # outbox.
        # assert self.nextHop is not None, 'No next hop found'
        # Simulating the application message as one optical data message.
        msg = MG.create_optical_datamsg(self.addr, 1, self.basicPayload,
                                        self.clock.read()) 
        if self.useAcoustic is True:
            end_msg = MG.create_acoustic_datamsg(self.addr, self.nextHop,
                                                 msg, self.clock.read())
        else:
            end_msg = MG.create_optical_datamsg(self.addr, self.nextHop, msg,
                                                self.clock.read()) 
        self.outbox.append([end_msg, 0])

    def execute(self, maxTime, isNewSlot):
        # This method is used to simulate the execution of the node. It will
        # return a message, and the required time to transmit it, when the node 
        # wants to communicate.
        msg    = None
        time   = maxTime
        energy = 0

        if self.energy <= 0:
            # if self.state is not USPState.DEAD:
            #     self.state = USPState.DEAD
            return time, msg

        if isNewSlot: # new round
            self.round += 1
            if self.verbose:
                print('Round ' + str(self.round) + ': ' + str(self.clock.read()))

        if self.msgsLostCount is self.msgsLostLimit:
            self.state = USPState.OUT_ROUTE
            self.value = INFINITY
            self.nextHop = None
            self.msgsLostCount = 0
            
        if self.state is USPState.IN_ROUTE:
            # In this state the node is ready for routing data.
            time, msg = self.send_next_msg(maxTime)
            if msg is None and self.verbose:
                print('No message')

        elif self.state is USPState.OUT_ROUTE:
            if self.isSink:
                msg = MG.create_iamsg(self.addr, self.position, 0)
                self.state = USPState.IN_ROUTE
            else:
                if self.value != INFINITY:
                    time, msg = self.send_next_msg(maxTime)
                    self.state = USPState.IN_ROUTE

                elif (self.round % self.reqInt) == 1:
                    msg = MG.create_req_joinmsg(self.addr)

            if msg is not None:
                _, energy = Tools.estimate_transmission(msg)
                self.energy -= energy
            
        else:
            raise Exception('Unknown state')
        
        return time, msg

    def send_next_msg(self, remainingTime):
        # Sends the first message in the outbox if the time and energy are 
        # sufficient. Returns the sent message and the required time to 
        # transmit it (when the message requires an ack, the time is the sum
        # of both transmissions times - message and ack). 
        energy = 0
        time = 0
        msg = None
        if len(self.outbox) is not 0:
            while self.outbox[0][1] is self.maxTransmissions:
                # Reached the maximum number of transmissions allowed. 
                # Discard it and move on. Must check if the outbox got empty.
                if self.verbose:
                    print('(!) DROPPING MESSAGE')
                dmsg = (self.outbox.pop(0))[0]
                if (dmsg.flags & 0x0f) is USPTypes.COMMON_DATA:
                    self.msgsLostCount += 1
                self.waitingACK = False
                if self.msgsLostCount is self.msgsLostLimit or \
                   len(self.outbox) is 0:
                    return time, msg
            # Will only sends a message if there is enough time and energy
            pair = self.outbox[0]
            nextMsg = pair[0]
            if (nextMsg.flags & 0x0f) is USPTypes.COMMON_DATA:
                # Just the get the must updated next hop. (is useful when a 
                # next hop node dies)
                nextMsg.dst = self.nextHop
                if self.nextHop is None:
                    print('ERROR !!!')
                if self.useAcoustic is True: 
                    # Must be update beacuse next hop may have changed and the
                    # node changed its state.
                    nextMsg.flags |= USPFlags.ACOUSTIC 
                else:
                    nextMsg.flags &= ~USPFlags.ACOUSTIC 
                if self.verbose:
                    print('{0:d} - {1:d}'.format(nextMsg.src, nextMsg.dst))
                
            etime, eenergy = Tools.estimate_transmission(nextMsg)
            if nextMsg.dst is BROADCAST_ADDR:
                if etime < remainingTime and eenergy < self.energy:
                    # Broadcasts do not need ACK so they only got send once.
                    msg = nextMsg
                    self.outbox.pop(0)
                    self.energy -= eenergy
                    time = etime
                else:
                    if self.verbose:
                        print('time is not enough')
            elif  nextMsg.flags & USPFlags.WITH_ACK:
                # Needs time to possibly receive the ACK.
                # Supposing that ack size is at maximum 2 * header size.
                if (nextMsg.flags & USPFlags.ACOUSTIC):
                    etimeAck = etime + self.acousticAckTime
                else:
                    etimeAck = etime + self.opticalAckTime
                if etimeAck < remainingTime and energy < self.energy:
                    msg = nextMsg
                    self.outbox[0][1] += 1
                    self.waitingACK = True
                    self.energy -= eenergy
                    time = etime
                else:
                    if self.verbose:
                        print('time is not enough (' + str(remainingTime) + ')')
            else: 
                if self.verbose:
                    print('unknown message')
        else:
            if self.verbose:
                print('Empty outbox')
        # Just for statistics
        if msg is not None and (msg.flags & 0x0f) is USPTypes.COMMON_DATA:
            self.sentMsgsCounter += 1

        return time, msg

    def recv_msg(self, recvMsg):
        #
        msg  = None
        time = 0
        if recvMsg.flags & USPFlags.ACOUSTIC:
            recvTime = (len(recvMsg) * 8) / AM.transmssionRate
            energyToRecv = recvTime * AM.rxPowerConsumption
        else:
            recvTime = (len(recvMsg) * 8) / OM.transmssionRate
            energyToRecv = recvTime * OM.rxPowerConsumption
        if self.energy >= energyToRecv:
            self.energy -= energyToRecv
            self.handle_message(recvMsg)
            if recvMsg.flags & USPFlags.WITH_ACK:
                # Generating ack to send
                if self.verbose:
                    print('Sending ACK')
                if recvMsg.flags & USPFlags.ACOUSTIC:
                    #ack = MG.create_acoustic_ack(self.addr, recvMsg.src)
                    ack = self.acouticAck
                    ack.dst = recvMsg.src
                else:
                    #ack = MG.create_optical_ack(self.addr, recvMsg.src)
                    ack = self.opticalAck
                    ack.dst = recvMsg.src
                etime, energy = Tools.estimate_transmission(ack)
                if self.energy > energy:
                    msg  = ack
                    time = etime
                    self.energy -= energy
        else:
            if self.verbose:
                print('Missing energy (' + str(self.energy) + '|' +
                      str(energyToRecv) + ')')
        return time, msg

    def handle_message(self, msg):
        # Handles the received messages acording to their types.
        msgType = msg.flags & 0x0f # first half is the type

        if msgType is USPTypes.COMMON_DATA:
            if self.verbose:
                print('Handling data message from node ' + str(msg.src))

            innerMsg = msg.payload
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
                    if self.verbose:
                        print('Message droped (TTL reached 0)')
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
                    print('Received (time: ' + str(time) + ')')
                if time > self.maxTimeSpent:
                    self.maxTimeSpent = time
                self.avgTimeSpent *= corrCoeff
                self.avgTimeSpent += (time / self.recvdMsgsCounter)

        elif (msgType is USPTypes.INFO_ANNOUN) or (msgType is USPTypes.REP_JOIN):
            if self.verbose:
                print('Handling info message from node ' + str(msg.src))
            nodePos   = msg.payload[0]
            nodeValue = msg.payload[1]
            dist  = Tools.distance(self.position, nodePos)
            value = nodeValue + dist
            if self.value > value:
                self.value       = value
                self.nextHop     = msg.src
                self.useAcoustic = dist > OM.maxrange
                # To inform neighbors.
                msg = MG.create_iamsg(self.addr, self.position, self.value)
                # Insert the message in que outbox or updates the next ot 
                # be sent. (control messages have high priority)
                if len(self.outbox) is not 0:
                    firstMsgType = self.outbox[0][0].flags & 0x0f
                    if firstMsgType is not USPTypes.INFO_ANNOUN:
                        self.outbox.insert(0, [msg, 0])
                    else:
                        self.outbox[0] = [msg, 0]
                else:
                    self.outbox.insert(0, [msg, 0])      

        elif msgType is USPTypes.REQ_JOIN:
            if self.verbose:
                print('Handling request message from node ' + str(msg.src))
            if self.state is USPState.IN_ROUTE:
               # To inform neighbors.
                msg = MG.create_rep_joinmsg(self.addr, self.position, self.value)
                # Insert the message in que outbox or updates the next ot 
                # be sent. (control messages have high priority)
                if len(self.outbox) is not 0:
                    firstMsgType = self.outbox[0][0].flags & 0x0f
                    if firstMsgType is not USPTypes.REP_JOIN:
                        self.outbox.insert(0, [msg, 0])
                    else:
                        self.outbox[0] = [msg, 0]
                else:
                    self.outbox.insert(0, [msg, 0])  

        elif msgType is USPTypes.ACK:
            if self.verbose:
                print('Handling ACK from node ' + str(msg.src))

            if self.waitingACK:
                self.outbox.pop(0)
                self.waitingACK = False
                if self.msgsLostCount is not 0:
                    self.msgsLostCount = 0
            else:
                if self.verbose:
                    print('error: unknown ack received')

        else:
            if self.verbose:
                print('unknown message type')
