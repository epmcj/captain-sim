###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM)                        ##
##  Departamento de Ciencia da Computacao (DCC)                              ##
##  Universidade Federal de Minas Gerais (UFMG)                              ##
##                                                                           ##
##  Events for the actions of the simulator. It defines codes for message    ##
##  receive, message send and node call (for execution) events. It also      ##
##  contains an Event Generator to create the events for the simulator.      ##
##  Events are represented by tuples for performance reasons.                ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################
class EventCode:
    MSG_RECV  = 0
    MSG_SEND  = 2
    NODE_CALL = 3

class EventGenerator:
    def create_call_event(time, addr):
        return (time, EventCode.NODE_CALL, addr)

    def create_send_event(time,  msg):
        return (time, EventCode.MSG_SEND, msg)

    def create_recv_event(time, addr, msg):
        return (time, EventCode.MSG_RECV, addr, msg)