###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM),                       ##
##  Universidade Federal de Minas Gerais (UFMG).                             ##
##                                                                           ##
##  Auxiliary Tools. Contains:                                               ##
##  - function to calculate distance between two points                      ##
##  - function to distribute nodes (generate their 3d positions)             ##
##  - Clock class for time tracking                                          ##
##  - functions to estimate transmission                                     ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################

import operator
import random
from math import floor, sqrt, pi, sin, cos

import matplotlib.pyplot as plt
import matplotlib
import numpy as np

from ucmessages import UOARFlags
from modens import AcousticModem as AM
from modens import OpticalModem as OM

INFINITY = float('inf')

class Tools:
    def distance(a, b):
        c = list(map(operator.sub, a, b))
        c = map(lambda x: x ** 2, c)
        return sqrt(sum(c))

    def distribute_nodes(xmax, ymax, depthmax, numClusters, numNodes, numSinks):
        if numClusters <= 0:
            numc = 1
        else:
            numc = numClusters
        xsize = xmax / numc
        ysize = ymax / numc
        dsize = depthmax / numc
        allSectors = list(range(0, numc ** 3))
        
        nodes = []
        for i in range(0, numSinks):
            nx = random.random() * xsize
            ny = random.random() * ysize
            nodes.append([nx, ny, 0])

        for i in range(0, numc):
            index = random.randint(0, len(allSectors)-1)
            currSector = allSectors.pop(index)
            d = floor(currSector / (numc**2))
            yx = currSector % (numc**2)
            y = floor(yx / numc)
            x = yx % numc
            
            x *= xsize
            y *= ysize
            d *= dsize

            for j in range(0, numNodes):
                nx = x + random.random() * xsize
                ny = y + random.random() * ysize
                nd = d + random.random() * dsize
                nodes.append([nx, ny, nd])

        return nodes

    def distribute_nodes_in_cluster(xmax, ymax, depthmax, numClusters, 
                                    numNodesPerCluster, clusterDiam, numSinks):
        #   z 
        #   | B /
        #   |../
        #   | /
        #   |/      
        #   + ------ x
        #
        #   y
        #   |    /
        #   | A /
        #   |../
        #   | /
        #   + --------- x
        #
        # A = 0..2pi
        # B = 0..pi
        nodesPerCluster = int(numNodesPerCluster)
        numClusters = int(numClusters)

        nodes = []
        cRadius = clusterDiam / 2
        # Generating sink nodes
        for i in range(0, numSinks):
            nx = random.random() * xmax
            ny = random.random() * ymax
            nodes.append([nx, ny, 0])
        
        for i in range(0, numClusters):
            # cluster center
            ccx = random.random() * xmax
            ccy = random.random() * ymax
            ccz = random.random() * depthmax
            for j in range(0, nodesPerCluster):
                a = random.random() * 2 * pi
                b = random.random() * pi
                dist = random.random() * cRadius
                px = ccx + sin(a) * dist
                py = ccy + cos(a) * dist
                pz = ccz + cos(b) * dist
                nodes.append([px, py, pz])
        
        return nodes

    def estimate_transmission(msg):
        if (msg.flags & UOARFlags.ACOUSTIC):
            time = (len(msg) * 8) / AM.transmssionRate
            energy = time * AM.txPowerConsumption
        else:
            time = (len(msg) * 8) / OM.transmssionRate
            energy = time * OM.txPowerConsumption
        return time, energy

class Clock:
    def __init__(self):
        self.__currTime = 0
        self.nextCall = INFINITY
        self.lastCall = INFINITY
        self.interval = 0
        self.routine = None

    def run(self, time):
        self.__currTime = self.__currTime + time
        if self.__currTime >= self.nextCall:
            self.routine()
            if self.nextCall >= self.lastCall:
                self.nextCall = INFINITY
            else:
                self.nextCall = self.nextCall + self.interval
    
    def read(self):
        return self.__currTime

    def set_alarm(self, call, start, interval, stop = INFINITY):
        self.nextCall = start
        while self.nextCall <= self.__currTime:
            self.nextCall = self.nextCall + self.interval

        self.interval = interval
        self.lastCall = stop
        self.routine = call

    def alarm_is_on(self):
        return self.nextCall is not INFINITY
