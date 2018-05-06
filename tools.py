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


def plotMultBarChart(data, errdata, datalabels, ticklabels, xlabel, ylabel, 
                     title, legendtitle = None, fileName=None):
    # NO VERIFICATIONS ARE DONE
    # create plot
    fig, axes = plt.subplots()
    index = np.arange(len(data[0]))
    barWidth = 0.4
    opacity = 0.8

    def autolabel(rects, val):
        """
        Attach a text label above each bar displaying its height
        """
        for rect in rects:
            height = rect.get_height()
            axes.text(rect.get_x() + rect.get_width()/2., height*1.02,
                      '%.2f' % float(height),
                    ha='center', va='bottom', fontsize=9)

    colors = ['#387ef5', '#ffc900', '#ef473a' , '#33cd5f']
    # colors = ['#b942f4', '#3ee8c6' , '#ffc900', '#33cd5f']
    for i in range(0, len(data)):
        index2 = index + (i+1) * barWidth
        rects = plt.bar(index2, data[i], barWidth,
                        alpha=opacity,
                        color=colors[i],
                        label=datalabels[i],
                        yerr = errdata[i],
                        ecolor = 'k')
        # autolabel(rects, data[i])
    # Set the tick labels font
    for label in (axes.get_xticklabels() + axes.get_yticklabels()):
        label.set_fontsize(24)
    plt.xlabel(xlabel, fontsize=24)
    plt.ylabel(ylabel, fontsize=24)
    plt.title(title)
    # axes = plt.gca()
    # maxy = 1.1 * max(max(data))
    # print(maxy)
    # axes.set_ylim([0, maxy])
    plt.gca().set_ylim(bottom=0)
    # axes.set_xlim([0, 5.5])
    pos = index + 2 * barWidth
    plt.xticks(pos, ticklabels)
    if legendtitle is not None:
        plt.legend(loc='best', title=legendtitle, fontsize=22, ncol=2)
    else:
        plt.legend(loc='best', fontsize=22, ncol=2)
        # plt.legend(loc='upper left')
    plt.tight_layout()
    if fileName is not None:
        plt.savefig(fileName, facecolor='w', transparent=True)
    else:
        plt.show()


def plotMultLineChart(xdata, ydata, errdata, datalabels, xlabel, ylabel, 
                      title, legendtitle=None, fileName=None):
    # NO VERIFICATIONS ARE DONE
    plt.figure()
    colors = ['#387ef5', '#ef473a' , '#ffc900', '#33cd5f']
    styles = ['-', '--', ':']
    for i in range(0, len(ydata)):
        plt.errorbar(xdata, ydata[i], yerr=errdata[i], linewidth=3,
                     linestyle=styles[i], label=datalabels[i], color=colors[i])

    axes = plt.gca()
    offset = (max(xdata) - min(xdata)) * 0.1
    axes.set_xlim([min(xdata) - offset, max(xdata) + offset])
    # axes.set_ylim([0, 1400])
    # Set the tick labels font
    for label in (axes.get_xticklabels() + axes.get_yticklabels()):
        label.set_fontsize(24)
    plt.xlabel(xlabel, fontsize=24)
    plt.ylabel(ylabel, fontsize=24)
    plt.title(title)
    if legendtitle is not None:
        plt.legend(loc='best', title=legendtitle, fontsize=22)
    else:
        plt.legend(loc='best', fontsize=22)
    plt.tight_layout()
    if fileName is not None:
        plt.savefig(fileName, facecolor='w', transparent=True)
    else:
        plt.show()