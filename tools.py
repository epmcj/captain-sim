###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM)                        ##
##  Departamento de Ciencia da Computacao (DCC)                              ##
##  Universidade Federal de Minas Gerais (UFMG)                              ##
##                                                                           ##
##  Auxiliary Tools. Contains:                                               ##
##  - function to calculate distance between two points                      ##
##  - functions to distribute nodes (generate their 3d positions)            ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################

import operator
import random
from math   import floor, sqrt, pi, sin, cos
from modens import AcousticModem as AM, OpticalModem as OM

INFINITY = float("inf")

def distance(a, b):
    c = list(map(operator.sub, a, b))
    c = map(lambda x: x ** 2, c)
    return sqrt(sum(c))

def distribute_nodes(xmax, ymax, depthmax, txDist, numNodes, numSinks):
    # Simple random distribution.
    assert xmax      > 0
    assert ymax      > 0
    assert depthmax  > 0
    assert txDist    > 0
    assert numNodes  > 0
    assert numSinks >= 0

    nodes = []
    for i in range(0, numSinks):
        nx = random.random() * xmax
        ny = random.random() * ymax
        nodes.append([nx, ny, 0])

    # creating the (nnodes - 1) remaining nodes
    while len(nodes) < (numNodes + numSinks):
        nx = random.random() * xmax
        ny = random.random() * ymax
        nz = random.random() * depthmax
        # checking if the node is isolated from the others
        isolated = True
        for i in range(len(nodes)):
            if distance([nx, ny, nz], nodes[i]) <= txDist:
                isolated = False
                break
        if not isolated:
            nodes.append([nx, ny, nz])

    return nodes


def distribute_nodes_in_clusters(xmax, ymax, depthmax, txDist, numClusters, 
                                 numNodesPerCluster, clusterDiam, numSinks):
    #  Random distribution with garanteed clusters.
    #   z                   y
    #   | B /               |    / 
    #   |../                | A /
    #   | /                 |../
    #   |/                  | /
    #   + ------ x          + --------- x
    #
    #   B = 0..pi           A = 0..2pi
    #
    assert xmax                > 0
    assert ymax                > 0
    assert depthmax            > 0
    assert txDist              > 0
    assert numNodesPerCluster  > 0
    assert clusterDiam         > 0
    assert numSinks           >= 0

    nodesPerCluster = int(numNodesPerCluster)
    numClusters     = int(numClusters)
    cRadius         = clusterDiam / 2

    # Generating sink nodes
    sinks = []
    for i in range(0, numSinks):
        nx = random.random() * xmax
        ny = random.random() * ymax
        sinks.append([nx, ny, 0])

    clusters = []
    for sink in sinks:
        sinkc           = {}
        sinkc["center"] = sink
        sinkc["nodes"]  = sink
        clusters.append(sinkc)
    # generating cluster centers to assure connectivity
    for cid in range(0, numClusters):
        cluster = {}
        isBad = True
        while isBad:
            ccx = random.random() * xmax
            ccy = random.random() * ymax
            ccz = random.random() * depthmax
            cluster["center"] = [ccx, ccy, ccz]

            for c in clusters:
                dist = distance(c["center"], cluster["center"])
                # clusters are too close
                if dist <= clusterDiam:
                    isBad = True
                    break
                elif dist <= txDist:
                    isBad = False
    
        cluster["nodes"]  = []
        for j in range(0, nodesPerCluster):
            a = random.random() * 2 * pi
            b = random.random() * pi
            dist = random.random() * cRadius
            px = ccx + sin(a) * dist
            py = ccy + cos(a) * dist
            pz = ccz + cos(b) * dist
            cluster["nodes"].append([px, py, pz])
        clusters.append(cluster)

    # joining clusters nodes (but not the sinks, yet)
    nodes = []
    for i in range(numSinks, len(clusters)):
        nodes += clusters[i]["nodes"]
    random.shuffle(nodes)
    nodes = sinks + nodes
    return nodes

def estimate_transmission(msg, txRate, txPowerConsumption):
    # Estimate the energy and the time required for a transmission to happen.
    time   = (len(msg) * 8) / txRate
    energy = time * txPowerConsumption
    return time, energy