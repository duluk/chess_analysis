from enum import Enum

VALUATION_THRESHOLD_CP = 1.25*100
CP_INACCURACY = 40
CP_MISTAKE    = 90
CP_BLUNDER    = 200

# Totally arbitrary
MATE_IN_ONE_CP = 250000
MATE_CP_SCALE  = 1000

# Centipawn Blunder Categories
class Category(Enum):
    INVALID    = 0x00
    OK         = 0x01
    INACCURATE = 0x02
    MISTAKE    = 0x04
    BLUNDER    = 0x08
