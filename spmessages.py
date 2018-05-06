###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM),                       ##
##  Universidade Federal de Minas Gerais (UFMG).                             ##
##                                                                           ##
##  Messages for the Shortest Path Algorithm (SPA).                          ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################

BROADCAST_ADDR = 0
BASIC_TTL = 100

# Fisrt half of byte
class USPTypes: 
    COMMON_DATA = 0x00
    ACK         = 0x01
    # control messages
    INFO_ANNOUN = 0x02
    REQ_JOIN    = 0x03
    REP_JOIN    = 0x04

# Second half of byte
class USPFlags:
    ACOUSTIC = 0x10
    WITH_ACK = 0x20

class Message:
    # Basic message
    headerSize = 10 # 4 bytes for each addr + 1 for type + payload length + 
                    # 1 for ttl (time is just for statistics)       
    def __init__(self, src, dst, flags, payload, ctime, ttl):
        self.src   = src
        self.dst   = dst
        self.flags = flags
        self.ctime = ctime # just for statistics
        self.ttl   = ttl
        if hasattr(payload, '__len__'):
            self.payload = payload
        else:
            self.payload = [payload]

    def __len__(self):
        return (self.headerSize + len(self.payload))

    def __str__(self):
        return 'Message from: ' + str(self.src) \
                + ' to ' + str(self.dst) + '.' \
                + ' (len = ' + str(len(self)) + ')'
    
class MessageGenerator:
    # Message that carries data
    def create_acoustic_datamsg(src, dst, payload, ctime, ttl = BASIC_TTL):
        opt = USPFlags.ACOUSTIC + USPFlags.WITH_ACK + USPTypes.COMMON_DATA
        return Message(src, dst, opt, payload, ctime, ttl)
    
    # Message that carries data
    def create_optical_datamsg(src, dst, payload, ctime, ttl = BASIC_TTL):
        opt = USPFlags.WITH_ACK + USPTypes.COMMON_DATA
        return Message(src, dst, opt, payload, ctime, ttl)

    # Simple ACK
    def create_acoustic_ack(src, dst, ttl = BASIC_TTL):
        opt = USPFlags.ACOUSTIC + USPTypes.ACK
        return Message(src, dst, opt, [], 0, ttl)

    # Simple ACK 
    def create_optical_ack(src, dst, ttl = BASIC_TTL):
        opt = USPTypes.ACK
        return Message(src, dst, opt, [], 0, ttl)

    # Message for information announcement
    def create_iamsg(src, position, value, ttl = BASIC_TTL):
        opt = USPFlags.ACOUSTIC + USPTypes.INFO_ANNOUN
        return Message(src, BROADCAST_ADDR, opt, [position, value], 0, ttl)

    # Message for request
    def create_req_joinmsg(src, ttl = BASIC_TTL):
        opt = USPFlags.ACOUSTIC + USPTypes.REQ_JOIN
        return Message(src, BROADCAST_ADDR, opt, [], 0, ttl)
    
    # Message for reply
    def create_rep_joinmsg(src, position, value, ttl = BASIC_TTL):
        opt = USPFlags.ACOUSTIC + USPTypes.REP_JOIN
        return Message(src, BROADCAST_ADDR, opt, [position, value], 0, ttl)
