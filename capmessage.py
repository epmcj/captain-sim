###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM),                       ##
##  Universidade Federal de Minas Gerais (UFMG).                             ##
##                                                                           ##
##  Messages for CAPTAIN.                                                    ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################
from message import *

# Fisrt half of byte
class CAPTAINTypes(MsgTypes): 
    # COMMON_DATA   = 0x00
    # ACK           = 0x01
    # control messages
    INFO_ANNOUN    = 0x02
    SCORE_ANNOUN   = 0x03
    CLUSTER_ANNOUN = 0x04
    ROUTE_ANNOUN   = 0x05
    REQ_SCORE      = 0x06
    REP_SCORE      = 0x07
    UPDATE_INFO    = 0x08
    REQ_RINFO      = 0x09
    REP_RINFO      = 0x0a
    REQ_EXCHANGE   = 0x0b
    REP_EXCHANGE   = 0x0c

# Second half of byte
class CAPTAINFlags(MsgFlags):
    # ACOUSTIC = 0x10
    # NEED_ACK = 0x20
    HEAD_SRC = 0x40

class CAPTAINMessage(Message):
    # Basic message
    headerSize = 10 # 4 bytes for each addr + 1 for type + payload length + 
                    # 1 for ttl (time is just for statistics)       
    def __init__(self, src, dst, flags, payload, ctime, srcs, ttl):
        super(CAPTAINMessage, self).__init__(src, dst, flags, payload, ctime, 
                                             ttl)
        self.srcs  = srcs  # just for statistics
    
class MessageGenerator:
    # Message that carries data
    def create_acoustic_datamsg(src, dst, payload, ctime, srcs, isHead, 
                                ttl = BASIC_TTL):
        opt = CAPTAINFlags.ACOUSTIC + CAPTAINFlags.NEED_ACK + \
              CAPTAINTypes.COMMON_DATA
        if isHead:
            opt = opt + CAPTAINFlags.HEAD_SRC
        return CAPTAINMessage(src, dst, opt, payload, ctime, srcs, ttl)
    
    # Message that carries data
    def create_optical_datamsg(src, dst, payload, ctime, srcs, isHead, 
                                ttl = BASIC_TTL):
        opt = CAPTAINFlags.NEED_ACK + CAPTAINTypes.COMMON_DATA
        return CAPTAINMessage(src, dst, opt, payload, ctime, srcs, ttl)

    # Simple ACK
    def create_acoustic_ack(src, dst, ttl = BASIC_TTL):
        opt = CAPTAINFlags.ACOUSTIC + CAPTAINTypes.ACK
        return CAPTAINMessage(src, dst, opt, [], 0, 1, ttl)

    # Simple ACK 
    def create_optical_ack(src, dst, ttl = BASIC_TTL):
        opt = CAPTAINTypes.ACK
        return CAPTAINMessage(src, dst, opt, [], 0, 1, ttl)

    # Message for information announcement
    def create_iamsg(src, position, state, hopsToSink, ttl = BASIC_TTL):
        opt = CAPTAINFlags.ACOUSTIC + CAPTAINTypes.INFO_ANNOUN
        return CAPTAINMessage(src, BROADCAST_ADDR, opt, \
                       [position, state, hopsToSink], 0, 1, ttl)

    # Message for score announcement
    def create_samsg(src, score, ttl = BASIC_TTL):
        opt = CAPTAINFlags.ACOUSTIC + CAPTAINTypes.SCORE_ANNOUN
        return CAPTAINMessage(src, BROADCAST_ADDR, opt, score, 0, 1, ttl)

    # Message for cluster announcement
    def create_camsg(src, ishead, position, ttl = BASIC_TTL):
        opt = CAPTAINFlags.ACOUSTIC + CAPTAINTypes.CLUSTER_ANNOUN
        return CAPTAINMessage(src, BROADCAST_ADDR, opt, [ishead, position], 0, 
                              1, ttl)

    # Message to create routes between cluster heads
    def create_ramsg(src, isHead, nextHop, hopsToSink, position, 
                     ttl = BASIC_TTL):
        opt = CAPTAINFlags.ACOUSTIC + CAPTAINTypes.ROUTE_ANNOUN
        return CAPTAINMessage(src, BROADCAST_ADDR, opt, [isHead, nextHop, \
                       hopsToSink, position], 0, 1, ttl)
    
    # Message to request neighbors score
    def create_rqsmsg(src, ttl = BASIC_TTL):
        opt = CAPTAINFlags.ACOUSTIC + CAPTAINTypes.REQ_SCORE
        return CAPTAINMessage(src, BROADCAST_ADDR, opt, [], 0, 1, ttl)
    
    # Message to reply a score request
    def create_rpsmsg(src, dst, score, ttl = BASIC_TTL):
        opt = CAPTAINFlags.NEED_ACK + CAPTAINTypes.REP_SCORE
        return CAPTAINMessage(src, dst, opt, score, 0, 1, ttl)
    
    # Message to inform new cluster head
    def create_uimsg(src, newHead, nextHop, ttl = BASIC_TTL):
        opt = CAPTAINFlags.ACOUSTIC + CAPTAINTypes.UPDATE_INFO
        return CAPTAINMessage(src, BROADCAST_ADDR, opt, [newHead, nextHop], 0, 
                              1, ttl)

    # Message to request info about routes that do not contain the dead node.
    def create_rqrmsg(src, deadNode, ttl = BASIC_TTL):
        opt = CAPTAINFlags.ACOUSTIC + CAPTAINTypes.REQ_RINFO
        return CAPTAINMessage(src, BROADCAST_ADDR, opt, deadNode, 0, 1, ttl)

    # Message to reply a route info request
    def create_acoustic_rprmsg(src, dst, isHead, nextHop, hopsToSink, 
                               ttl = BASIC_TTL):
        opt = CAPTAINFlags.ACOUSTIC + CAPTAINFlags.NEED_ACK + \
              CAPTAINTypes.REP_RINFO
        return CAPTAINMessage(src, dst, opt, [isHead, nextHop, hopsToSink], 0,
                              1, ttl)
    
    # Message to reply a route info request
    def create_optical_rprmsg(src, dst, isHead, nextHop, hopsToSink, 
                              ttl = BASIC_TTL):
        opt = CAPTAINFlags.NEED_ACK + CAPTAINTypes.REP_RINFO
        return CAPTAINMessage(src, dst, opt, [isHead, nextHop, hopsToSink], 0,
                              1, ttl)

    # Message to request a leader exchange
    def create_optical_rqemsg(src, dst, ttl = BASIC_TTL):
        opt = CAPTAINFlags.NEED_ACK + CAPTAINTypes.REQ_EXCHANGE
        return CAPTAINMessage(src, dst, opt, [], 0, 1, ttl)

    # Message to reply a leader exchange
    def create_optical_rpemsg(src, dst, canChange, hopsToSink, ttl = BASIC_TTL):
        opt = CAPTAINFlags.NEED_ACK + CAPTAINTypes.REP_EXCHANGE
        return CAPTAINMessage(src, dst, opt, [canChange, hopsToSink], 0, 1, ttl)