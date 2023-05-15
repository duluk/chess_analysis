#!/usr/bin/env python3

# TODO:
# 1. Keep up with best moves in a hash so previous recommendations can be
#    accessed, such as when needing the suggested move instead of current one.
# 2. Perhaps keep up with more than just the recommended move so other
#    information can be accessed later.

import sys
import argparse

from stockfish import Stockfish
import chess
import chess.pgn

STOCKFISH_BIN='/usr/bin/stockfish'

VALUATION_THRESHOLD_CP = 1.25*100

# Can set the strength of Stockfish to something more comparable to the ELO of
# the players in the game so stockfish evaluates based on that ELO. Could be
# useful. (actually not sure this affects position evaluation)
#stockfish = Stockfish(path=STOCKFISH_BIN, parameters={"Threads": 6, "UCI_LimitStrength": "true", "UCI_Elo": 1000})

# Default to max strength
stockfish = Stockfish(path=STOCKFISH_BIN, parameters={"Threads": 6, "UCI_LimitStrength": "false"})

def parse_arguments():
    parser = argparse.ArgumentParser(description="Arg Parse Stuff")
    parser.add_argument("-f", "--file", help="PGN file to parse")
    parser.add_argument("-e", "--eval", action="store_true", help="Find evaluation swings")
    parser.add_argument("-d", "--depth", help="Depth from which to do analysis")
    parser.add_argument("-t", "--time", help="Set minimum move time for evaluation")
    parser.add_argument("-s", "--show-best", action="store_true", help="Show best move at swing")
    # Positional arguments if wanted:
    # parser.add_argument("src", help="source")
    # parser.add_argument("dst", help="dest")
    return vars(parser.parse_args())

def is_an_int(n):
    try:
        i = int(n)
        return True
    except ValueError:
        return False

def set_depth(d):
    stockfish.set_depth(d)

def set_move_time_min(t):
    stockfish.update_engine_parameters({"Minimum Thinking Time": t})

def set_pos(fen):
    stockfish.set_fen_position(fen)

def best_move(fen):
    if stockfish.is_fen_valid(fen):
        return stockfish.get_best_move()

def get_piece_at_square(board, square):
    return board.piece_at(square).symbol()

def get_eval(fen):
    e = stockfish.get_evaluation()
    v = e['value']
    t = e['type']

    if t == 'cp':
        # Leave as centipawns and allow caller to handle any desired
        # conversions to pawn units.
        # Also - leave it as a string so the return value type remains the same
        # regardless of what is returned, so caller has to handle the difference.
        return str(v)
    elif t == 'mate':
        color = "Black" if v < 0 else "White"
        av = abs(int(v))
        return f"M{av} for {color}"

def print_position_info(s, f, v):
    print(f"Evaluation: {v}")
    print(f"Move made: {s.move}\n")
    print(f"Next Best Move: {best_move(f)}")

config = parse_arguments()

pgn_file = config['file']
if pgn_file:
    pgn = open(pgn_file)
else:
    print("Using the test PGN file")
    pgn = open("test_game.pgn")

if config['depth']:
    set_depth(config['depth'])
if config['time']:
    set_move_time_min(config['time'])

schach = chess.pgn.read_game(pgn)
board  = schach.board()

if config['eval']:
    last_significant_valuation = 0
    for move in schach.mainline_moves():
        fen = board.fen()
        set_pos(fen)
        valuation = get_eval(fen)
        move_num = board.fullmove_number # i.e., not the ply

        if is_an_int(valuation):
            if abs(int(valuation) - last_significant_valuation) > VALUATION_THRESHOLD_CP:
                print(f"Valuation swing at move {move_num}, {board.san(move)} ({valuation})", end='')
                if config['show_best']:
                    # This isn't right. This shows the next move in this
                    # position, not what should have been played instead of the
                    # move that caused this evaluation swing.
                    #print(f". Engine recommendation: {best_move(fen)}.")
                    print(f". Engine recommendation: ???")
                else:
                    print('')  # newline
                last_significant_valuation = int(valuation)
        else:
            print(f"{valuation} at move {move_num}, {board.san(move)}")

        board.push(move)

        # TODO: I think this is out of date, mainly the schach variable
        #print_position_info(schach, fen, valuation)
else:
    print("Nothing to do. Did you provide an action?")
