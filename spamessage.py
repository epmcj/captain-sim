###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM)                        ##
##  Departamento de Ciencia da Computacao (DCC)                              ##
##  Universidade Federal de Minas Gerais (UFMG)                              ##
##                                                                           ##
##  Messages for the Shortest Path Algorithm (SPA).                          ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################
from message import *

# Fisrt half of byte
class SPATypes(MsgTypes): 
    # COMMON_DATA = 0x00
    # ACK         = 0x01
    # control messages
    INFO_ANNOUN = 0x02
    REQ_JOIN    = 0x03
    REP_JOIN    = 0x04

# Second half of byte
class SPAFlags(MsgFlags):
    # ACOUSTIC = 0x10
    # NEED_ACK = 0x20
    pass

class SPAMessage(Message):
    # Basic message
    headerSize = 10 # 4 bytes for each addr + 1 for type + payload length + 
                    # 1 for ttl (time is just for statistics)       
    def __init__(self, src, dst, flags, payload, ctime, ttl):
        super(SPAMessage, self).__init__(src, dst, flags, payload, ctime, 
                                         ttl)
    
class MessageGenerator:
    # Message that carries data
    def create_acoustic_datamsg(src, dst, payload, ctime, ttl = BASIC_TTL):
        opt = SPAFlags.ACOUSTIC + SPAFlags.NEED_ACK + SPATypes.COMMON_DATA
        return SPAMessage(src, dst, opt, payload, ctime, ttl)
    
    # Message that carries data
    def create_optical_datamsg(src, dst, payload, ctime, ttl = BASIC_TTL):
        opt = SPAFlags.NEED_ACK + SPATypes.COMMON_DATA
        return SPAMessage(src, dst, opt, payload, ctime, ttl)

    # Simple ACK
    def create_acoustic_ack(src, dst, ttl = BASIC_TTL):
        opt = SPAFlags.ACOUSTIC + SPATypes.ACK
        return SPAMessage(src, dst, opt, [], 0, ttl)

    # Simple ACK 
    def create_optical_ack(src, dst, ttl = BASIC_TTL):
        opt = SPATypes.ACK
        return SPAMessage(src, dst, opt, [], 0, ttl)

    # Message for information announcement
    def create_iamsg(src, position, value, ttl = BASIC_TTL):
        opt = SPAFlags.ACOUSTIC + SPATypes.INFO_ANNOUN
        return SPAMessage(src, BROADCAST_ADDR, opt, [position, value], 0, ttl)

    # Message for request
    def create_req_joinmsg(src, ttl = BASIC_TTL):
        opt = SPAFlags.ACOUSTIC + SPATypes.REQ_JOIN
        return SPAMessage(src, BROADCAST_ADDR, opt, [], 0, ttl)
    
    # Message for reply
    def create_rep_joinmsg(src, position, value, ttl = BASIC_TTL):
        opt = SPAFlags.ACOUSTIC + SPATypes.REP_JOIN
        return SPAMessage(src, BROADCAST_ADDR, opt, [position, value], 0, ttl)
