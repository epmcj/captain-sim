###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM)                        ##
##  Departamento de Ciencia da Computacao (DCC)                              ##
##  Universidade Federal de Minas Gerais (UFMG)                              ##
##                                                                           ##
##  Implementation of both acoustic and optical modems used in the simulator ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################

class Modem:
    def __init__(self, txPower, mrange):
        self.txPower = txPower
        self.range   = mrange


class AcousticModem:
    # Evologics S2CR 18/34 acoustic modem
    # www.evologics.de/files/DataSheets/EvoLogics_S2CR_1834_Product_Information.pdf
    minFrequency         = 18     # kHz
    maxFrequency         = 34     # kHz
    frequency            = 26     # kHz
    idlePowerConsumption = 2.5e-3 # W
    rxPowerConsumption   = 1.3    # W
    txPowerConsumption   = 2.8    # W
    # txPower              = 158    # dB re uPa**2
    txPower              = 171.47 # (4.47 + 167) dB re 1 uPa; 2.8 W ==> 4.47 dBW
    maxRange             = 1.0e3  # m
    txRate               = 1.0e4  # 10 kbps 

class OpticalModem:
    # BlueComm 200 optical modem
    # www.sonardyne.com/app/uploads/2016/06/Sonardyne_8361_BlueComm_200.pdf
    # Si PIN Hamamatsu S5971 high-speed photodiode
    waveLength         = 514    # nm
    beamDivergence     = 0.5    # rad
    bandWidth          = 1.0e5  # Hz
    shuntResistance    = 1.43e9 # ohm
    maxDarkCurrent     = 1.0e-9 # A
    incidentCurrent    = 1.0e-6 # A
    Ar                 = 1.1e-6 # m**2
    At                 = 1.0e-5 # m**2
    sensitivity        = 0.26   # A/W
    txPower            = 37.78  # dBm (6 W)
    rxPowerConsumption = 10     # W
    txPowerConsumption = 15     # W
    maxRange           = 50     # m
    txRate             = 1.0e6  # 1 Mbps
        
        