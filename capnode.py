###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM)                        ##
##  Departamento de Ciencia da Computacao (DCC)                              ##
##  Universidade Federal de Minas Gerais (UFMG)                              ##
##                                                                           ##
##  Node that uses a CAPTAIN implementation for data collection.             ##
##                                                                           ##
##  TODO:                                                                    ##
##  * Improve node status verification                                       ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################
from capmessage import MessageGenerator as MG, BASIC_TTL, BROADCAST_ADDR, \
                       CAPTAINFlags, CAPTAINTypes
from basic_node import BasicNode
from sim_events import EventGenerator  as EG
from modens     import AcousticModem   as AM, OpticalModem   as OM
from channels   import AcousticChannel as AC, OpticalChannel as OC
from clock      import Clock
import random
import tools

class CAPTAINState:
    INITIAL        = 0
    CLUSTER_MEMBER = 1
    CLUSTER_HEAD   = 2
    DEAD           = 3 # just for debug

class CAPTAINStatus:
    IDLE        = 0
    DISCOVERING = 1
    ANNOUNCING  = 2
    ELECTING    = 3
    MEMBER_WAIT = 4
    HEAD_WAIT   = 5
    READY       = 6
    UPDATING    = 7
    RECOVERING  = 8
    EXCHANGE    = 9

class CAPTAINNode(BasicNode):
    MAX_WAIT_ROUNDS = 3

    def __init__(self, addr, x, y, depth, energy, aTimeout, oTimeout,
                 clock=None, slotSize=1, numSlots=1, verbose=False):
        super(CAPTAINNode, self).__init__(addr, x, y, depth, energy, clock, 
                                          slotSize, numSlots, verbose)
        # for data aggregation
        self.dataStore        = []
        self.roundsToWait     = 2
        self.nextAgg          = tools.INFINITY
        self.lastAgg          = {}
        self.lastAgg["ctime"] = 0
        self.lastAgg["round"] = 0
        self.incWait          = 0
        self.waitingACK       = False
        # self.isSink = addr in self.sinkNodesAddr
        # for TDMA
        # self.round    = 0
        # self.slotSize = 0         
        # self.nextSlot = tools.INFINITY
        # Energy related
        # self.energy    = energy
        # self.maxEnergy = energy
        self.energyThresholds = [0.05, 0.2, 0.5]
        self.energyThreshold  = energy * self.energyThresholds.pop()
        self.criticalEnergy   = False
        # for retransmissions
        self.oTimeout = oTimeout
        self.aTimeout = aTimeout
        # for CAPTAIN
        self.state             = CAPTAINState.INITIAL
        self.status            = CAPTAINStatus.IDLE 
        self.highestScore      = [0, tools.INFINITY] # pair [score, addr]
        self.numReachableNodes = 0
        self.nextHop      = None
        self.nextHopDist  = tools.INFINITY
        self.hopsToSink   = tools.INFINITY
        self.stopWaiting  = False
        self.updateStatus = 0 # 0: not updating
                              # 1: update in progress
                              # 2: update done
        self.oneighbors  = {}
        self.cheadList   = {} # to route phase [addr, is in route]
        self.cmemberList = []
        # self.score  = 0
        self.greaterDistance = 0
        self.avgDistance = 0
        # for possible connection head-member
        self.minHopsToSink = tools.INFINITY
        self.memberAlternative = None
        # for possible leader exchange
        self.recvdRAfromMember = False
        self.roundsToRequest   = tools.INFINITY
        self.maybeNextHop      = None
        self.maybeHopsToSink   = tools.INFINITY
        # for recovery (next hop is dead)
        # self.msgsLostCount = 0
        # self.msgsLostLimit = 5
        self.deadNode      = None
        self.startRecovery = False
        # for statistics
        self.msgsCounter = 0
        self.numDataAggs = 0
        # self.recvdMsgsCounter = 0
        # self.sentMsgsCounter  = 0
        # self.avgNumHops = 0
        # self.maxNumHops = 0 
        # self.avgTimeSpent = 0
        # self.maxTimeSpent = 0
        # best for memory
        # self.acouticAck = MG.create_acoustic_ack(addr, 0)
        # time, energy = tools.estimate_transmission(self.acouticAck, AM.txRate,
        #                                       AM.txPowerConsumption)
        # self.acousticAckTime  = 2 * time # upper bound to ack time
        # self.acouticAckEnergy = 2 * energy
        # self.opticalAck = MG.create_optical_ack(addr, 0)
        # time, energy = tools.estimate_transmission(self.opticalAck, OM.txRate,
        #                                       OM.txPowerConsumption)
        # self.opticalAckTime   = 2 * time # upper bound to ack time
        # self.opticalAckEnergy = 2 * energy

    def collect_data(self):
        # Generates an application message and puts it into the end of the 
        # outbox.
        # assert self.nextHop is not None, "No next hop found"
        if self.verbose:
            print("Node " + str(self.addr) + " is collecting data")
        if self.incWait != 0:
            self.roundsToWait += self.incWait
            if self.verbose:
                self.report("New RtW: " + str(self.roundsToWait))
            self.incWait = 0

        # Simulating the application message as one optical data message.
        isHead = self.state is CAPTAINState.CLUSTER_HEAD
        sink_addr = 1
        num_srcs  = 1 # only this node                        
        msg = MG.create_acoustic_datamsg(src=self.addr, 
                                         dst=sink_addr, 
                                         payload=self.basicPayload, 
                                         ctime=self.clock.read(),
                                         srcs=num_srcs, 
                                         isHead=isHead) 

        if self.state is CAPTAINState.CLUSTER_HEAD:
            if (len(self.cmemberList) > 0) and (self.roundsToWait > 0):
                self.dataStore.append(msg)
                self.nextAgg = self.round + self.roundsToWait
            else:
                end_msg = MG.create_acoustic_datamsg(src=self.addr, 
                                                    dst=self.nextHop, 
                                                    payload=msg,
                                                    ctime=self.clock.read(),
                                                    srcs=num_srcs, 
                                                    isHead=isHead)
                self.outbox.append([end_msg, 0])
        else:
            end_msg = MG.create_optical_datamsg(src=self.addr, 
                                                dst=self.nextHop, 
                                                payload=msg,
                                                ctime=self.clock.read(), 
                                                srcs=num_srcs, 
                                                isHead=isHead) 
            self.outbox.append([end_msg, 0])
        self.dataCollections += 1

    def calculate_score(self):
        # Calculates node score based on amoung of neighbots and energy level.
        if self.isSink:
            score = tools.INFINITY
        elif self.numReachableNodes is len(self.oneighbors):
            # A node thar can"t reach other that is outside its neighbors can"t
            # be head.
            score = 0
        else:
            n = int(100 * len(self.oneighbors) / self.numReachableNodes)
            e = int(100 * (self.energy / self.maxEnergy))
            if self.verbose:
                print("E: " + str(e) + " N: " + str(n))
            score = e + n
        return score

    def aggregate_data(self):
        # Aggregates data by the time they were collected
        self.lastAgg["round"] = self.round
        self.numDataAggs += 1
        if len(self.dataStore) > 1:
            groups = []
            while len(self.dataStore) > 0:
                msgs = []
                ctime = self.dataStore[0].ctime
                if ctime > self.lastAgg["ctime"]:
                    self.lastAgg["ctime"] = ctime
                i = 0
                while i < len(self.dataStore):
                    msg = self.dataStore[i]
                    if msg.ctime == ctime:
                        msgs.append(self.dataStore.pop(i))
                    else:
                        i +=  1
                groups.append(msgs)

            for group in groups:
                # aggregating each group
                msg = group[0]
                msg.src  = self.addr
                if self.verbose:
                    print("Aggregated " + str(len(group)) + " messages")
                msg.srcs = len(group)
                end_msg  = MG.create_acoustic_datamsg(src=self.addr, 
                                                    dst=self.nextHop, 
                                                    payload=msg,
                                                    ctime=self.clock.read(), 
                                                    srcs=1, 
                                                    isHead=True) 
                self.outbox.append([end_msg, 0])

        elif len(self.dataStore) == 1:
            # if there is only its own message, then its optical neighbors are 
            # probably members of other clusters 
            msg = self.dataStore.pop()
            if msg.src == self.addr:
                self.roundsToWait = max(0, self.roundsToWait - 1)
            end_msg = MG.create_acoustic_datamsg(src=self.addr, 
                                                 dst=self.nextHop, 
                                                 payload=msg,
                                                 ctime=self.clock.read(), 
                                                 srcs=1, 
                                                 isHead=True) 
            self.outbox.append([end_msg, 0])

    def report(self, msg):
        print("Node " + str(self.addr) + ": " + msg)

    def execute(self):
        # This method is used to simulate the execution of the node. It will
        # return a message, and the required time to transmit it, when the node 
        # wants to communicate.
        currTime = self.clock.read()
        if self.energy <= 0:
            # if self.state is not CAPTAINState.DEAD:
            #     self.state = CAPTAINState.DEAD
            if self.verbose:
                print("Round " + str(self.round) + ": " + str(currTime))
                print("Node is dead")
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

        if self.isSink is False and self.energy <= self.energyThreshold and \
           (not self.criticalEnergy):
            self.energyThreshold = self.energyThresholds.pop()
            if len(self.energyThresholds) is 0:
                self.criticalEnergy = True
                
            if self.state is CAPTAINState.CLUSTER_HEAD and \
               len(self.cmemberList) is not 0:
                self.updateStatus = 1

        if isNewSlot: # new round
            if self.state is CAPTAINState.CLUSTER_HEAD:
                if self.round == self.nextAgg:
                    self.aggregate_data()    
                    self.nextAgg = tools.INFINITY       
                elif self.round > self.nextAgg:
                    raise Exception("Aggregation was not done in the right" + \
                        " time: " + str(self.nextAgg) + " x " + str(self.round))

            if self.verbose:
                print("Round " + str(self.round) + ": " + str(currTime))
            
            # Status machine
            if self.status is CAPTAINStatus.READY:
                if self.msgsLostCount >= self.msgsLostLimit:
                    self.status = CAPTAINStatus.RECOVERING
                    self.startRecovery = True
            
            elif self.status is CAPTAINStatus.IDLE:
                self.status = CAPTAINStatus.DISCOVERING

            elif self.status is CAPTAINStatus.DISCOVERING:
                self.status = CAPTAINStatus.ANNOUNCING

            elif self.status is CAPTAINStatus.ANNOUNCING:
                if self.state is CAPTAINState.INITIAL:
                    self.status = CAPTAINStatus.ELECTING
                else:
                    self.status = CAPTAINStatus.READY
                    
            elif self.status is CAPTAINStatus.ELECTING:
                if self.state is CAPTAINState.CLUSTER_MEMBER:
                    self.status = CAPTAINStatus.MEMBER_WAIT
                else:
                    self.status = CAPTAINStatus.HEAD_WAIT
                    
            elif self.status is CAPTAINStatus.MEMBER_WAIT: 
                if self.stopWaiting:
                    if self.isSink:
                        self.status = CAPTAINStatus.HEAD_WAIT
                    else:
                        self.status = CAPTAINStatus.READY
                else:
                    if self.roundsToRequest is 0:
                        self.status          = CAPTAINStatus.EXCHANGE
                        self.roundsToRequest = tools.INFINITY
            
            elif self.status is CAPTAINStatus.EXCHANGE and \
                self.hopsToSink is not tools.INFINITY:
                self.status = CAPTAINStatus.HEAD_WAIT
                
            elif self.status is CAPTAINStatus.HEAD_WAIT and self.stopWaiting:
                self.status = CAPTAINStatus.READY
 
            elif self.status is CAPTAINStatus.READY and self.updateStatus is 1:
                self.status = CAPTAINStatus.UPDATING
 
            elif self.status is CAPTAINStatus.UPDATING and \
                 self.updateStatus is 0:
                self.status = CAPTAINStatus.READY

            elif self.status is CAPTAINStatus.RECOVERING and \
                 self.nextHop is not None and self.msgsLostCount is 0:
                self.status = CAPTAINStatus.READY

        # Executing actions based on current state                
        msg            = None
        execOnNextSlot = False 
        if self.state is CAPTAINState.INITIAL:
            if self.status is CAPTAINStatus.DISCOVERING:
                # First stage: announces its own position to the other nodes
                # and then collects info the neighbors for a round.
                if self.isSink:
                    self.hopsToSink = 0
                    self.stopWaiting = False
                msg = MG.create_iamsg(self.addr, self.position, self.state,
                                      self.hopsToSink)
                if self.verbose:
                    print("Node " + str(self.addr) + " sending info msg")

            elif self.status is CAPTAINStatus.ANNOUNCING:
                # Second stage: now that the node know its neighbors it can 
                # calculate its score and, if necessary, announce it. If some 
                # of its neighbors is already part of a cluster, then it just
                # join it.
                
                if self.nextHop is not None:
                    if self.hopsToSink == tools.INFINITY:
                        self.state  = CAPTAINState.CLUSTER_MEMBER
                        print("Node " + str(self.addr) + " is member 1")
                    else:
                        self.state = CAPTAINState.CLUSTER_HEAD
                        print("Node " + str(self.addr) + " is head 1")
                    self.cbrBegin = self.round
                    msg = MG.create_camsg(self.addr, False, self.position)
                    if self.verbose:
                        print("Node " + str(self.addr) + " sending cluster msg")
                    self.stopWaiting = False
                    
                else:
                    score = self.calculate_score()
                    if self.highestScore[0] < score:
                        # Maybe received some score before its time to 
                        # calculate.
                        self.highestScore[0] = score
                        self.highestScore[1] = self.addr
                    msg = MG.create_samsg(self.addr, score)
                    if self.verbose:
                        print("Node " + str(self.addr) + " sending score msg")

            elif self.status is CAPTAINStatus.ELECTING:
                # Third stage: cluster head election. It will become one if its
                # score is the highest.
                if self.highestScore[1] is self.addr or self.isSink:
                    if self.isSink:
                        if self.verbose:
                            print("Node is sink: " + str(self.addr))
                    self.state = CAPTAINState.CLUSTER_HEAD
                    ishead = True
                else:
                    self.state = CAPTAINState.CLUSTER_MEMBER
                    self.nextHop = self.highestScore[1]
                    dist = tools.distance(self.position, 
                                          self.oneighbors[self.nextHop])
                    self.nextHopDist = dist
                    ishead = False
                self.stopWaiting = False
                msg = MG.create_camsg(self.addr, ishead, self.position)
                if self.verbose:
                    print("Node " + str(self.addr) + " sending cluster msg")
                
            else:
                raise Exception("Unknown initial status")
            
            execOnNextSlot = True
            
        else:
            if self.status is CAPTAINStatus.READY:
                # In this stage the node is ready for routing data.
                msg = self.send_next_msg(self.endSlot - currTime)
                if msg is None:
                    if self.verbose:
                        print("No message")
                    execOnNextSlot = True
            
            elif self.status is CAPTAINStatus.MEMBER_WAIT:
                # This stage is necessary for all nodes to walk together.
                self.roundsToRequest = self.roundsToRequest - 1
                if self.verbose:
                    print(str(self.roundsToRequest) + " rounds to request")
                if self.roundsToRequest < 0:
                    raise Exception("Error: negative rounds to request")
                if self.roundsToRequest == tools.INFINITY and \
                   self.maybeNextHop is not None:
                   # just became member (by exchanging)
                    msg = MG.create_camsg(self.addr, False, self.position)
                    if self.verbose:
                        print("Just became member")
                        print("Node " + str(self.addr) + " sending cluster msg")
                    execOnNextSlot = True
                    # clening info
                    self.maybeNextHop = None
                    
            elif self.status is CAPTAINStatus.EXCHANGE:
                # In this stage a member node may become a head to connect 
                # the network
                if self.nextHop in self.cheadList.keys():
                    msg = MG.create_optical_rqemsg(self.addr, self.nextHop)
                    if self.verbose:
                        print("Node " + str(self.addr) + 
                              " exchange request msg")
                    self.outbox.insert(0, [msg, 0])
                    self.waitingACK = True

                else:
                    if self.verbose:
                        print("Node " + str(self.addr) + " is a head now")
                    self.state       = CAPTAINState.CLUSTER_HEAD
                    self.nextHop     = self.maybeNextHop
                    self.nextHopDist = AM.maxRange # distance to next hop is
                                                   # not known
                    self.hopsToSink  = self.maybeHopsToSink
                    msg = MG.create_camsg(self.addr, True, self.position)
                    if self.verbose:
                        print("Node " + str(self.addr) + " sending cluster msg")
                    execOnNextSlot = True

            elif self.status is CAPTAINStatus.HEAD_WAIT:
                #
                self.stopWaiting = False
                if self.hopsToSink is not tools.INFINITY:
                    if self.maybeNextHop is not None:
                        # Just became head (by exchange)
                        msg = MG.create_camsg(self.addr, True, self.position)
                        if self.verbose:
                            print("Just became head")
                            print("Node " + str(self.addr) +
                                  " sending cluster msg")
                        # clening info
                        self.maybeNextHop = None
                        execOnNextSlot = True
                    else:
                        # All head neighbors have received the message of hops
                        if not False in self.cheadList.values():
                            self.stopWaiting = True
                        else:
                            for addr, got in self.cheadList.items():
                                if not got:
                                    if self.verbose:
                                        print("Missing node " + str(addr))
                        
                        msg = MG.create_ramsg(self.addr, True, self.nextHop,  
                                            self.hopsToSink, self.position)
                        if self.verbose:
                            print("Node " + str(self.addr) +
                                  " sending route msg")
                        execOnNextSlot = True
                else:
                    if self.memberAlternative is not None:
                        self.hopsToSink  = self.minHopsToSink
                        self.nextHop     = self.memberAlternative
                        self.nextHopDist = AM.maxRange # distance to next hop is
                                                       # not known
                        self.stopWaiting = True
                        msg = MG.create_ramsg(self.addr, True, self.nextHop,  
                                              self.hopsToSink, self.position)
                        if self.verbose:
                            print("Node " + str(self.addr) +
                                  "sending route msg")
                        execOnNextSlot = True

                    elif self.maybeNextHop is not None and \
                         self.hopsToSink == tools.INFINITY:
                        # allow another node to be head in its place 
                        msg = MG.create_optical_rpemsg(self.addr, 
                                                       self.maybeNextHop, 
                                                       True, 0)
                        if self.verbose:
                            print("Node " + str(self.addr) + \
                                  " positive exchange reply msg")
                        self.outbox.insert(0, [msg, 0])
                        self.waitingACK = True

            elif self.status is CAPTAINStatus.UPDATING:
                # This stage is used to potentially find another node, with 
                # better score, to be cluster head. 
                if self.updateStatus is 1:
                    # Requests the score of neighbors
                    self.highestScore[0] = self.calculate_score()
                    self.highestScore[1] = self.addr
                    msg = MG.create_rqsmsg(self.addr)
                    self.updateStatus = 2

                elif self.updateStatus is 2:
                    bestCandidate = self.highestScore[1]
                    if bestCandidate is not self.addr:
                        if self.verbose:
                            print("Node " + str(bestCandidate) + 
                                  " is the new cluster head")
                        msg = MG.create_uimsg(self.addr,
                                              bestCandidate,
                                              self.nextHop)
                        self.state = CAPTAINState.CLUSTER_MEMBER
                        self.nextHop = bestCandidate
                        dist = tools.distance(self.position, 
                                              self.oneighbors[bestCandidate])
                        self.nextHopDist = dist
                        # Updating lists
                        self.cheadList[bestCandidate] = True
                        self.cmemberList.remove(bestCandidate)
                    self.updateStatus = 0
                
                if msg is not None:
                    execOnNextSlot = True

            elif self.status is CAPTAINStatus.RECOVERING:
                # Recovering from a next hop lost
                if self.startRecovery:
                    self.startRecovery = False
                    # First round in recovering
                    self.deadNode    = self.nextHop
                    self.nextHop     = None
                    self.nextHopDist = tools.INFINITY
                    self.hopsToSink  = tools.INFINITY

                else:
                    if self.nextHop is None:
                        # Node didn"t receive any message from cluster
                        self.state = CAPTAINState.CLUSTER_HEAD
                    if self.deadNode is not None:
                        # Updating lists because node is really dead
                        if self.deadNode in self.cheadList:
                            del self.cheadList[self.deadNode]
                        if self.deadNode in self.cmemberList:
                            self.cmemberList.remove(self.deadNode)
                        if self.deadNode in self.oneighbors:
                            del self.oneighbors[self.deadNode]
                        self.numReachableNodes -= 1
                        self.deadNode = None

                if self.state is CAPTAINState.CLUSTER_MEMBER and \
                   len(self.oneighbors) is 0:
                    # if there are no more neighbors
                    self.state = CAPTAINState.CLUSTER_HEAD

                if self.nextHop is not None:
                    # Found some new next hop.
                    ishead = self.state is CAPTAINState.CLUSTER_HEAD
                    if ishead:
                        msg = MG.create_camsg(self.addr, ishead, self.position)
                    self.msgsLostCount = 0
                    self.deadNode = None
                else:              
                    msg = MG.create_rqrmsg(self.addr, self.deadNode)
                execOnNextSlot - True
                    
            else:
                raise Exception("Unknown cluster status")
        
        events   = []
        callTime = self.nextSlot
        if msg is not None:
            txTime, energy = 0, 0
            if  msg.flags & CAPTAINFlags.ACOUSTIC:
                txTime, energy = tools.estimate_transmission(msg, AM.txRate, 
                                                        AM.txPowerConsumption)
                acTimeout = self.aTimeout
                if (msg.flags & 0x0f) is CAPTAINTypes.COMMON_DATA:
                    acTimeout = (self.nextHopDist / AC.soundSpeed) * 2.1
                callTime = self.clock.read() + txTime + acTimeout
            else:
                txTime, energy = tools.estimate_transmission(msg, OM.txRate, 
                                                        OM.txPowerConsumption)
                opTimeout = self.oTimeout
                if (msg.flags & 0x0f) is CAPTAINTypes.COMMON_DATA:
                    ocTimeout = (self.nextHopDist / OC.lightSpeed) * 2.1
                callTime = self.clock.read() + txTime + opTimeout
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
        # of both transmissions times - message and ack.) 
        msg = None
        if len(self.outbox) is not 0:
            while self.outbox[0][1] is self.MAX_TXS:
                # Reached the maximum number of transmissions allowed. 
                # Discard it and move on. Must check if the outbox got empty.
                if self.verbose:
                    print("(!) DROPPING MESSAGE")
                dmsg = (self.outbox.pop(0))[0]
                if (dmsg.flags & 0x0f) is CAPTAINTypes.COMMON_DATA:
                    self.msgsLostCount += 1
                    self.dropdMsgsCounter += dmsg.payload.srcs
                else:
                    self.dropdMsgsCounter += 1
                self.waitingACK = False
                if self.msgsLostCount is self.msgsLostLimit or \
                   len(self.outbox) is 0:
                    return None # empty return
            # Will only sends a message if there is enough time and energy
            pair    = self.outbox[0]
            nextMsg = pair[0]
            if (nextMsg.flags & 0x0f) is CAPTAINTypes.COMMON_DATA:
                # Just the get the must updated next hop. (is useful when a 
                # next hop node dies)
                nextMsg.dst = self.nextHop
                if self.state is CAPTAINState.CLUSTER_HEAD: 
                    # Must be update beacuse next hop may have changed and the
                    # node changed its state.
                    nextMsg.flags |= CAPTAINFlags.ACOUSTIC
                    nextMsg.flags |= CAPTAINFlags.HEAD_SRC 
                else:
                    nextMsg.flags &= ~CAPTAINFlags.ACOUSTIC 
                    nextMsg.flags &= ~CAPTAINFlags.HEAD_SRC 
                
            timeout, etime, eenergy = 0, 0, 0
            if (nextMsg.flags & CAPTAINFlags.ACOUSTIC):
                etime, eenergy = tools.estimate_transmission(nextMsg, AM.txRate, 
                                                        AM.txPowerConsumption)
                acTimeout = self.aTimeout
                if (nextMsg.flags & 0x0f) is CAPTAINTypes.COMMON_DATA:
                    acTimeout = (self.nextHopDist / AC.soundSpeed) * 2.1
                timeout = etime + acTimeout
            else:
                etime, eenergy = tools.estimate_transmission(nextMsg, OM.txRate, 
                                                        OM.txPowerConsumption)
                opTimeout = self.oTimeout
                if (nextMsg.flags & 0x0f) is CAPTAINTypes.COMMON_DATA:
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
            elif nextMsg.flags & CAPTAINFlags.NEED_ACK:
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
        if msg is not None and (msg.flags & 0x0f) is CAPTAINTypes.COMMON_DATA:
            self.sentMsgsCounter += 1

        return msg

    def recv_msg(self, recvdMsg):
        # Function to be called when the node receives a message.
        if self.energy <= 0:
            # Node has no energy to receive the message
            return []

        events = []
        if recvdMsg.flags & CAPTAINFlags.ACOUSTIC:
            recvTime     = (len(recvdMsg) * 8) / AM.txRate
            energyToRecv = recvTime * AM.rxPowerConsumption
        else:
            recvTime     = (len(recvdMsg) * 8) / OM.txRate
            energyToRecv = recvTime * OM.rxPowerConsumption
        if self.energy >= energyToRecv:
            self.energy -= energyToRecv
            self.handle_message(recvdMsg)
            if recvdMsg.flags & CAPTAINFlags.NEED_ACK:
                # Generating ack to send
                if self.verbose:
                    print("Node " + str(self.addr) + " is sending ACK")
                ack, acktime, energy = None, 0, 0
                if recvdMsg.flags & CAPTAINFlags.ACOUSTIC:
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
        if self.verbose:
            print("Node " + str(self.addr), end=" ")
        if msgType is CAPTAINTypes.COMMON_DATA:
            if self.verbose:
                print("handling data message from node " + str(msg.src))

            innerMsg = msg.payload
            innerMsg.ttl -= 1
            if innerMsg.dst is not self.addr:
                if innerMsg.ttl is not 0:
                    if self.state is CAPTAINState.CLUSTER_MEMBER:
                        msg = MG.create_optical_datamsg(src=self.addr,
                                                        dst=self.nextHop,
                                                        payload=innerMsg,
                                                        ctime=self.clock.read(),
                                                        srcs=1, 
                                                        isHead=False)
                        self.outbox.append([msg, 0])
                    else:
                        fromHead = (innerMsg.flags >> 6) % 2
                        if fromHead == 1:
                            msg = MG.create_acoustic_datamsg(src=self.addr,
                                        dst=self.nextHop, payload=innerMsg,
                                        ctime=self.clock.read(), srcs=1, 
                                        isHead=True)
                            self.outbox.append([msg, 0])
                        else:
                            if innerMsg.src not in self.cmemberList:
                                # if it is next hop of an unknown node 
                                # (because of some previous error)
                                self.cmemberList.append(innerMsg.src)

                            if innerMsg.ctime <= self.lastAgg["ctime"]:
                                self.incWait = 1
                            self.dataStore.append(innerMsg)
                else:
                    self.dropdMsgsCounter += innerMsg.srcs
                    if self.verbose:
                        print("Message droped (TTL reached 0)")
            
            self.recvdMsgsCounter += 1
            if self.isSink is True:
                # Hops statistics
                self.msgsCounter += innerMsg.srcs
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

        elif msgType is CAPTAINTypes.INFO_ANNOUN:
            if self.verbose:
                print("handling info message from node " + str(msg.src))

            self.numReachableNodes += 1
            nodePosition = msg.payload[0]
            nodeState    = msg.payload[1]
            nodeHops     = msg.payload[2]
            distFromNode = tools.distance(self.position, nodePosition)
            # Adding in lists
            if nodeState is CAPTAINState.CLUSTER_HEAD:
                self.cheadList[msg.src] = nodeHops is not tools.INFINITY
            if distFromNode <= OM.maxRange:
                self.oneighbors[msg.src] = nodePosition
                if nodeState is CAPTAINState.CLUSTER_MEMBER and \
                   msg.src not in self.cmemberList:
                    self.cmemberList.append(msg.src)
            updtFactor = (self.numReachableNodes - 1) / self.numReachableNodes
            self.avgDistance = self.avgDistance * updtFactor
            self.avgDistance += (distFromNode / self.numReachableNodes)
            if distFromNode > self.greaterDistance:
                self.greaterDistance = distFromNode

            if self.state is CAPTAINState.INITIAL and not self.isSink:
                # If it is not in a cluster and some neighbor is already
                # member or a head, join it. It's preferable to join as
                # a member than as a head. 
                if distFromNode <= OM.maxRange:
                    if nodeState is not CAPTAINState.INITIAL:
                        currDist = tools.INFINITY
                        if self.nextHop in self.oneighbors:
                            nextPos  = self.oneighbors[self.nextHop]
                            currDist = tools.distance(self.position, nextPos)
                        if distFromNode < currDist:
                            self.nextHop     = msg.src
                            self.nextHopDist = distFromNode
                            self.hopsToSink  = tools.INFINITY

                else:
                    if nodeState is CAPTAINState.CLUSTER_HEAD:
                        if self.hopsToSink == tools.INFINITY:
                            if self.nextHop is None:
                                self.nextHop     = msg.src
                                self.nextHopDist = distFromNode
                                self.hopsToSink  = nodeHops + 1
                        else:
                            if (nodeHops + 1) < self.hopsToSink:
                                self.nextHop     = msg.src
                                self.nextHopDist = distFromNode
                                self.hopsToSink  = nodeHops + 1

                            elif (nodeHops + 1) == self.hopsToSink:
                                # probability to change the next hop (trying to 
                                # the overload in some nodes)
                                nhxprob = (AM.maxRange - distFromNode) / \
                                          AM.maxRange 
                                if random.random() < nhxprob:
                                    self.nextHop     = msg.src
                                    self.nextHopDist = distFromNode
                                    self.hopsToSink  = nodeHops + 1

            if (self.state is not CAPTAINState.INITIAL and \
               self.status is not CAPTAINStatus.DISCOVERING) and \
               nodeState is CAPTAINState.INITIAL:
                # When a node enters in the network and needs information.
                # Routing control messages have higher priority than data 
                # messages.
                msg = MG.create_iamsg(self.addr, self.position, self.state,
                                      self.hopsToSink)
                # Insert the message in que outbox or updates the next ot 
                # be sent. 
                if len(self.outbox) is not 0:
                    firstMsgType = self.outbox[0][0].flags & 0x0f
                    if firstMsgType is not CAPTAINTypes.INFO_ANNOUN:
                        self.outbox.insert(0, [msg, 0])
                    else:
                        self.outbox[0] = [msg, 0]
                else:
                    self.outbox.insert(0, [msg, 0])

        elif msgType is CAPTAINTypes.SCORE_ANNOUN or \
             msgType is CAPTAINTypes.REP_SCORE:
            if self.verbose:
                print("handling score message from node " + str(msg.src))
            
            nodeScore = msg.payload[0]
            if msg.src in self.oneighbors and \
               (self.status is CAPTAINStatus.ANNOUNCING or \
               self.status is CAPTAINStatus.DISCOVERING or \
               self.status is CAPTAINStatus.UPDATING):
                # Cluster heads are nodes with the highest score amoung its 
                # neighbors (in case of a tie, the node with lowest addr wins) 
                if (self.highestScore[0] < nodeScore) or \
                   (self.highestScore[0] == nodeScore and \
                    self.highestScore[1] > msg.src):
                    self.highestScore = [nodeScore, msg.src]

        elif msgType is CAPTAINTypes.CLUSTER_ANNOUN:
            if self.verbose:
                print("handling cluster message from node " + str(msg.src))
            nodeIsHead = msg.payload[0]
            if nodeIsHead:
                # A cluster head node will send its own address in the cluster
                # announcement payload
                if msg.src not in self.cheadList:
                    if self.status is CAPTAINStatus.ELECTING or \
                       self.status is CAPTAINStatus.ANNOUNCING: 
                        self.cheadList[msg.src] = False
                    else:
                        self.cheadList[msg.src] = True
                        
                if msg.src in self.cmemberList:
                    self.cmemberList.remove(msg.src)
            else:
                if msg.src in self.oneighbors and \
                   msg.src not in self.cmemberList:
                    self.cmemberList.append(msg.src)
                if msg.src in self.cheadList:
                    del self.cheadList[msg.src]

            if msg.src in self.oneighbors:
                if self.status is CAPTAINStatus.DISCOVERING:
                    self.nextHop = msg.src
                    dist = tools.distance(self.position, 
                                          self.oneighbors[self.nextHop])
                    self.nextHopDist = dist
                elif self.state is CAPTAINState.CLUSTER_MEMBER and \
                     nodeIsHead and msg.src is not self.nextHop:
                    self.nextHop = msg.src
                    dist = tools.distance(self.position, 
                                          self.oneighbors[self.nextHop])
                    self.nextHopDist = dist
                elif (self.status is CAPTAINStatus.HEAD_WAIT and \
                     self.maybeNextHop is msg.src):
                    # consequence of a head exchange process
                    self.state   = CAPTAINState.CLUSTER_MEMBER
                    self.status  = CAPTAINStatus.MEMBER_WAIT
                    self.nextHop = self.maybeNextHop
                    dist = tools.distance(self.position, 
                                          self.oneighbors[self.nextHop])
                    self.nextHopDist = dist
                    self.minHopsToSink = tools.INFINITY 
                elif self.status is CAPTAINStatus.EXCHANGE:
                    # another node became head
                    self.state   = CAPTAINState.CLUSTER_MEMBER
                    self.status  = CAPTAINStatus.MEMBER_WAIT
                    self.nextHop = msg.src 
                    dist = tools.distance(self.position, 
                                          self.oneighbors[self.nextHop])
                    self.nextHopDist = dist
                    self.minHopsToSink = tools.INFINITY 

        elif msgType is CAPTAINTypes.ROUTE_ANNOUN:
            if self.verbose:
                print("handling route message from node " + str(msg.src))
            nodeIsHead   = msg.payload[0]
            nodeNextHop  = msg.payload[1]
            nodeHops     = msg.payload[2] + 1
            nodePosition = msg.payload[3]
            if self.state is CAPTAINState.CLUSTER_HEAD:
                if nodeIsHead:
                    dist = tools.distance(self.position, nodePosition)
                    self.cheadList[msg.src] = True
                    if self.hopsToSink > nodeHops:
                        self.hopsToSink  = nodeHops
                        self.nextHop     = msg.src
                        self.nextHopDist = dist

                    elif self.hopsToSink == nodeHops:
                        # probability to change the next hop (trying to 
                        # the overload in some nodes)
                        nhxprob = (AM.maxRange - dist) / AM.maxRange 
                        if random.random() < nhxprob:
                            self.hopsToSink  = nodeHops
                            self.nextHop     = msg.src
                            self.nextHopDist = dist
                        
                elif self.isSink is False:
                    if nodeHops < self.minHopsToSink:
                        self.minHopsToSink = nodeHops
                        self.memberAlternative = msg.src

                    if self.nextHop is not None and \
                       nodeNextHop is not self.addr:
                        if msg.src in self.oneighbors and \
                           nodeHops <= (self.hopsToSink + 1):
                            # better be a member than a head 
                            self.state = CAPTAINState.CLUSTER_MEMBER
                            self.nextHop = msg.src
                            self.hopsToSink = nodeHops
                            dist = tools.distance(self.position, 
                                                  self.oneighbors[msg.src])
                            self.nextHopDist = dist
                            newMsg = MG.create_camsg(self.addr, False,
                                                     self.position)
                            self.outbox.insert(0, [newMsg, 0])

            if (self.status is CAPTAINStatus.MEMBER_WAIT or \
               self.status is CAPTAINStatus.ELECTING or \
               self.status is CAPTAINStatus.EXCHANGE):
                if self.nextHop is msg.src:
                    # For members
                    if nodeHops < self.minHopsToSink:
                        self.minHopsToSink = nodeHops
                        newMsg = MG.create_ramsg(self.addr, False, self.nextHop, 
                                                nodeHops, self.position)
                        self.outbox.insert(0, [newMsg, 0])
                    self.stopWaiting = True  
                    
                    if self.recvdRAfromMember:
                        # just clear things
                        self.recvdRAfromMember = False
                        self.roundsToRequest   = tools.INFINITY
                        self.maybeNextHop      = None
                else:
                    #
                    if not self.recvdRAfromMember:
                        self.recvdRAfromMember = True
                        self.roundsToRequest   = self.MAX_WAIT_ROUNDS
                        self.maybeNextHop      = msg.src
                        self.maybeHopsToSink   = nodeHops

                    elif self.recvdRAfromMember and nodeIsHead:
                        self.maybeNextHop    = msg.src      
                        self.maybeHopsToSink = nodeHops          

        elif msgType is CAPTAINTypes.REQ_SCORE:
            if self.verbose:
                print("handling req score msg from " + str(msg.src))

            if msg.src in self.oneighbors:
                score  = self.calculate_score()
                newMsg = MG.create_rpsmsg(self.addr, msg.src, score)
                if len(self.outbox) is not 0:
                    firstMsgType = self.outbox[0].flags & 0x0f
                    if firstMsgType is not CAPTAINTypes.REP_SCORE:
                        self.outbox.insert(0, [newMsg, 0])
                    else:
                        self.outbox[0] = [newMsg, 0]
                else:
                    self.outbox.append([newMsg, 0])

        elif msgType is CAPTAINTypes.UPDATE_INFO:
            if self.verbose:
                print("handling update info msg from " + str(msg.src))

            newHead    = msg.payload[0]
            newNextHop = msg.payload[1]
            if newHead is self.addr:
                # Must be a head now
                self.state   = CAPTAINState.CLUSTER_HEAD
                self.nextHop = newNextHop
                self.nextHopDist = AM.maxRange # distance to next hop is not 
                                               # known
            else:
                if self.nextHop is msg.src or newHead in self.oneighbors:
                    # Must update which node is the next hop
                    # ** Might be a problem if new head is out of range
                    self.nextHop = newHead
                    self.nextHopDist = AM.maxRange # distance to next hop is not 
                                                   # known
                self.cheadList[newHead] = True

            if newHead in self.oneighbors:
                self.cmemberList.remove(msg.payload[0])

            if msg.src in self.oneighbors:
                self.cmemberList.append(msg.src)

            del self.cheadList[msg.src]

            if self.verbose:
                print(self.cheadList)
                print(self.cmemberList)

        elif msgType is CAPTAINTypes.REQ_RINFO:
            if self.verbose:
                print("handling route info request msg from " + str(msg.src))

            if msg.src is not self.nextHop and \
               msg.payload[0] is not self.nextHop:
                # Only replies if the requester is not its own next hop and  
                # they don"t share the same next hop. (-_- can"t help)
                if self.state is CAPTAINState.CLUSTER_HEAD:
                    isHead     = True
                    hopsToSink = self.hopsToSink
                else:
                    isHead     = False
                    hopsToSink = self.minHopsToSink
                if msg.src in self.oneighbors:
                    newMsg = MG.create_optical_rprmsg(self.addr, msg.src,
                                                      isHead, self.nextHop,
                                                      hopsToSink)
                else:
                    newMsg = MG.create_acoustic_rprmsg(self.addr, msg.src,
                                                       isHead, self.nextHop,
                                                       hopsToSink)
                self.outbox.insert(0, [newMsg, 0])        

        elif msgType is CAPTAINTypes.REP_RINFO:
            if self.verbose:
                print("handling route info reply from " + str(msg.src))

            if self.status is CAPTAINStatus.RECOVERING:
                replier        = msg.src
                nodeIsHead     = msg.payload[0]
                nodeNextHop    = msg.payload[1]
                nodeHopsToSink = msg.payload[2]

                if replier is self.deadNode:
                    self.deadNode = None

                if replier in self.oneighbors:
                    if self.nextHop is None:
                        self.state         = CAPTAINState.CLUSTER_MEMBER
                        self.nextHop       = msg.src
                        dist = tools.distance(self.position, 
                                              self.oneighbors[self.nextHop])
                        self.nextHopDist = dist
                        self.hopsToSink    = tools.INFINITY
                        self.minHopsToSink = nodeHopsToSink

                if self.state is CAPTAINState.CLUSTER_HEAD:
                   if self.hopsToSink >= nodeHopsToSink and nodeIsHead:
                        self.nextHop    = msg.src
                        self.nextHopDist = AM.maxRange # distance to next hop is
                                                       # not known
                        self.hopsToSink = nodeHopsToSink + 1
        
        elif msgType is CAPTAINTypes.REQ_EXCHANGE:
            if self.verbose:
                print("handling exchange request from node " + str(msg.src))

            if self.state is CAPTAINState.CLUSTER_HEAD:
                if self.status is CAPTAINStatus.HEAD_WAIT and  \
                   self.hopsToSink == tools.INFINITY and self.maybeNextHop is None:
                    # Is not in route yet
                    self.maybeNextHop = msg.src
                else:
                    newMsg = MG.create_optical_rpemsg(self.addr, msg.src,  
                                                      False, self.hopsToSink)
                    self.outbox.insert(0, [newMsg, 0])        

        elif msgType is CAPTAINTypes.REP_EXCHANGE:
            if self.verbose:
                print("handling exchange reply from node " + str(msg.src))
                
            nodeCanChange = msg.payload[0]
            nodeHopsToSink = msg.payload[1] + 1    
            if self.status is CAPTAINStatus.EXCHANGE:
                if nodeCanChange:
                    # Become an cluster head and then send two messages: the
                    # first announces its new state (head) and the second
                    # continues the route formation process
                    self.state      = CAPTAINState.CLUSTER_HEAD
                    self.status     = CAPTAINStatus.HEAD_WAIT
                    self.hopsToSink = self.maybeHopsToSink
                    self.nextHop    = self.maybeNextHop
                    self.nextHopDist = AM.maxRange # distance to next hop is
                                                    # not known
                    if self.nextHop in self.cheadList:
                        self.cheadList[self.nextHop] = True
                else:
                    # Assume that next hop is part of the route
                    if self.verbose:
                        print("Can not be head")
                    if self.status is CAPTAINStatus.EXCHANGE and \
                       self.stopWaiting is False:
                        # is not part of the route yet (could have received a 
                        # route message)
                        self.minHopsToSink = nodeHopsToSink
                        self.stopWaiting   = True
                        self.status        = CAPTAINStatus.MEMBER_WAIT

                        newMsg = MG.create_ramsg(self.addr, False, self.nextHop, 
                                                nodeHopsToSink, self.position)
                        self.outbox.insert(0, [newMsg, 0])

        elif msgType is CAPTAINTypes.ACK:
            if self.verbose:
                print("handling ACK from node " + str(msg.src))

            if self.waitingACK:
                self.outbox.pop(0)
                self.waitingACK = False
                if self.msgsLostCount is not 0:
                    self.msgsLostCount = 0
            else:
                if self.verbose:
                    print("error: unknown ack received")

        else:
            if self.verbose:
                print("unknown message type")
