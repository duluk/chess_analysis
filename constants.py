from enum import Enum

#VALUATION_THRESHOLD_CP = 1.25*100

class Moves(Enum):
    INVALID    = 0x00
    OK         = 0x01
    INACCURATE = 0x02
    MISTAKE    = 0x04
    BLUNDER    = 0x08

# Centipawn Blunder Categories
class Category(Enum):
    THRESHOLD  = 1.25*100
    INACCURACY = 40
    MISTAKE    = 90
    BLUNDER    = 200
