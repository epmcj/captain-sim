###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM)                        ##
##  Departamento de Ciencia da Computacao (DCC)                              ##
##  Universidade Federal de Minas Gerais (UFMG)                              ##
##                                                                           ##
##  Basic message to use with the simulator. Its structure must be           ##
##  respected.                                                               ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################
BROADCAST_ADDR = 0
BASIC_TTL      = 100

# Fisrt half of byte
class MsgTypes: 
    COMMON_DATA = 0x00
    ACK         = 0x01

# Second half of byte
class MsgFlags:
    ACOUSTIC = 0x10
    NEED_ACK = 0x20

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