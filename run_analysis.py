#!/usr/bin/env python3

# TODO:
# 1. Keep up with best moves in a hash so previous recommendations can be
#    accessed, such as when needing the suggested move instead of current one.
# 2. Perhaps keep up with more than just the recommended move so other
#    information can be accessed later.
# 3. Add option for which engine to use, though this will likely require a
#    config file so engines and paths can be provided on a per-system basis

#This could be useful:
#white_pieces = {'Pawn' : "♙", 'Rook' : "♖", 'Knight' : "♘", 'Bishop' : "♗", 'King' : "♔", 'Queen' : "♕" }

import sys
import os
import argparse

from stockfish import Stockfish
import chess
import chess.pgn
import chess.engine

import logging
logging.basicConfig(level=logging.INFO)

STOCKFISH_BIN='/usr/bin/stockfish'

VALUATION_THRESHOLD_CP = 1.25*100

# Can set the strength of Stockfish to something more comparable to the ELO of
# the players in the game so stockfish evaluates based on that ELO. Could be
# useful. (actually not sure this affects position evaluation)
#stockfish = Stockfish(path=STOCKFISH_BIN, parameters={"Threads": 6, "UCI_LimitStrength": "true", "UCI_Elo": 1000})

# Default to max strength
stockfish = Stockfish(path=STOCKFISH_BIN, parameters={"Threads": 6, "UCI_LimitStrength": "false"})
engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_BIN)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Arg Parse Stuff")
    parser.add_argument("-f", "--file", help="PGN file to parse")
    parser.add_argument("-e", "--eval", action="store_true", help="Find evaluation swings")
    parser.add_argument("-l", "--list", action="store_true", help="Live moves")
    parser.add_argument("-d", "--depth", default=20, help="Depth from which to do analysis")
    parser.add_argument("-t", "--time", default=7.0, help="Set minimum move time for evaluation")
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

def set_depth(engine, d):
    #stockfish.set_depth(d)
    try:
        engine.configure({"depth": d})
    except:
        print("Invalid option. Available options:")
        print(engine.options["Hash"])
        os._exit(1)
    

def set_move_time_min(engine, t):
    #stockfish.update_engine_parameters({"Minimum Thinking Time": t})
    engine.configure({"Minimum Thinking Time": t})

#def set_pos(fen):
#    stockfish.set_fen_position(fen)

#def best_move(fen):
#    if stockfish.is_fen_valid(fen):
#        return stockfish.get_best_move()

def get_piece_at_square(board, square):
    return board.piece_at(square).symbol()

# Most of this probably needs to be moved to another function and have this
# function simply return the results of get_evaluation()
#def get_eval(engine, fen):
def get_eval(engine, board, limits):
    #e = stockfish.get_evaluation()
    return engine.analyse(board, limits)
    #v = e['value']
    #t = e['type']
    #v = info['score'].relative
    #print(f"get_eval returned {v} for info['score'].relative")

    #return str(v)
#    if t == 'cp':
#        # Leave as centipawns and allow caller to handle any desired
#        # conversions to pawn units.
#        # Also - leave it as a string so the return value type remains the same
#        # regardless of what is returned, so caller has to handle the difference.
#        return str(v)
#    elif t == 'mate':
#        color = "Black" if v < 0 else "White"
#        av = abs(int(v))
#        return f"M{av} for {color}"

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

#if config['depth']:
#    set_depth(engine, config['depth'])
#if config['time']:
#    set_move_time_min(engine, config['time'])
limits = chess.engine.Limit(time=config['time'], depth=config['depth'])

#print("Options available:")
#print(engine.options["Hash"])
print("Config options:")
print(f"{config}\n")

schach = chess.pgn.read_game(pgn)
board  = schach.board()
engine_valuations = {}

if config['eval']:
    previous_valuation = 0
    for move in schach.mainline_moves():
        # Make the move on the board and update to next ply
        san = board.san(move)
        turn = board.turn
        move_num = board.fullmove_number # i.e., not the ply
        ply = board.ply()

        board.push(move)
        if board.outcome():
            os._exit(1)

        #set_pos(fen)
        #valuation = get_eval(fen)
        #eval_info = get_eval(engine, board, float(config['time']), config['depth'])
        eval_info = get_eval(engine, board, limits)
        valuation = str(eval_info['score'].relative)
        engine_valuations[ply] = eval_info

#        print(f"Move = {board.san(move)}")
#        print(f"pv = {eval_info['pv']}")
        color = "White" if turn == chess.WHITE else "Black"
        if is_an_int(valuation):
            valuation = int(valuation)

            # Keep consistent with White eval: + good for White; - good for Black. The way
            # it currently works, + is good for the current color; - for the other. So a +
            # score for Black means Black is better. A - score for Black means that White
            # is better. But we generally use - for favoring Black and + favoring White.
            if turn == chess.BLACK:
                valuation = -valuation

            eval_diff = abs(valuation - previous_valuation)

#            if board.turn == chess.WHITE: print(f"{move_num}: ", end="")
#            print(f"{board.san(move)} ", end="")
#            if board.turn == chess.BLACK: print("")

            if turn == chess.WHITE:
                print(f"{move_num}:  {san} (fen: {board.fen()})")
            else:
                print(f"...: {san} (fen: {board.fen()})")

            if eval_diff > VALUATION_THRESHOLD_CP:
#                print(f"BestMove = {chess.engine.BestMove}")
                print(f"\nValuation swing at move {move_num}, {san} ({valuation})", end='')

                print(f"curr ply: {eval_info} --> (move {san})")
                if board.ply() > 1: print(f"prev ply: {engine_valuations[ply-1]}")
                print(f"curr valuation = {valuation}")
                print(f"prev valuation = {previous_valuation}")
                print("")

                if config['show_best']:
                    # This isn't right. This shows the next move in this
                    # position, not what should have been played instead of the
                    # move that caused this evaluation swing.
                    #print(f". Engine recommendation: {best_move(fen)}.")
                    print(f". Engine recommendation: {engine_valuations[ply-1]['pv'][1]}.")
                else:
                    print('')  # newline
            previous_valuation = valuation
        else:
            print(f"{valuation} at move {move_num}, {san}")

#        if move_num == 5:
#            print(f"Exiting on move {move_num}")
#            os._exit(1)
elif config['list']:
    for move in schach.mainline_moves():
        print(f"move = {move}; san = {board.san(move)}")
        board.push(move)
        if board.outcome():
            os._exit(1)
else:
# FEN for position in move 53:
# 6k1/R7/5p2/5P1P/3KP1P1/6b1/8/8 b - - 0 53
# SF in CB evaluates this to 0.00
#
# FEN for position in ...52:
# 6k1/R7/5p2/5P1P/3pP1P1/3K2b1/8/8 w - - 0 53
# 6k1/R7/5p2/5P1P/3pP1P1/3K2b1/8/8 w - - 0 53
# SF in CB evaluates this to +18 or so

    print("Evalation info for move 52, Bg3:")
    board = chess.Board("6k1/R7/5p2/5P1P/3pP1P1/3K2b1/8/8 w - - 0 53")
    info  = engine.analyse(board, chess.engine.Limit(depth=20))
    print(info)

    print("Evalation info for move 53, Kxd4:")
    # The position represented in FEN
    board = chess.Board("6k1/R7/5p2/5P1P/3KP1P1/6b1/8/8 b - - 0 53")
    info  = engine.analyse(board, chess.engine.Limit(depth=20))
    print(info)


    #print("Nothing to do. Did you provide an action?")
