#!/usr/bin/env python3

# TODO:
# 1. Keep up with best moves in a hash so previous recommendations can be
#    accessed, such as when needing the suggested move instead of current one.
# 2. Perhaps keep up with more than just the recommended move so other
#    information can be accessed later.
# 3. Add option for which engine to use, though this will likely require a
#    config file so engines and paths can be provided on a per-system basis
# 4. Add another centipawn evaluation/analysis function. What I'm doing now is
#    comparing CP difference from one move to the next. What if I compared the
#    CP difference from the player's move to the engine's top chioce? I think
#    this is what the ChessBase Centipawn Analysis feature does. If not, it's
#    still interesting. I'm not sure how significant the different methods are,
#    but something to consider.
# 5. Fix the configuration abstraction. It's all wonky.

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

import constants as const
from   constants import Category
import config    as conf

class Arguments:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Arg Parse Stuff")
        self.arguments = self.parse_arguments()
        self.args = vars(self.arguments)

    def parse_arguments(self):
        self.parser.add_argument("-f", "--file", help="PGN file to parse")
        self.parser.add_argument("-e", "--eval", action="store_true", help="Find evaluation swings")
        self.parser.add_argument("-l", "--list", action="store_true", help="Live moves")
        self.parser.add_argument("-n", "--print-fen", action="store_true", help="Print FEN")
        self.parser.add_argument("-d", "--depth", help="Depth from which to do analysis")
        self.parser.add_argument("-t", "--time", help="Set minimum move time for evaluation")
        self.parser.add_argument("-s", "--show-best", action="store_true", help="Show best move at swing")
        # Positional arguments if wanted:
        # self.parser.add_argument("src", help="source")
        # self.parser.add_argument("dst", help="dest")
        return self.parser.parse_args()

    @property
    def args(self):
        return self._args

    @args.setter
    def args(self, value):
        self._args = value

class Engine_Analysis:
    def __init__(self, binary = None):
        self.binary = binary

    def set_depth(self, d):
        return "Not implemented"

    def set_move_time_min(self, t):
        return "Not implemented"

    def moves(self):
        return "Not implemented"

    def get_eval(self, e, b, l):
        return "Not implemented"

    def set_position(self, fen):
        return "Not implemented"

    def best_move_fen(self, fen):
        return "Not implemented"

    def print_position_info(self, s, f, v):
        return "Not implemented"

class Stockfish_PythonChess(Engine_Analysis):
    def __init__(self, args, binary=conf.DEFAULT_STOCKFISH_BIN):
        Engine_Analysis.__init__(self, binary)
        self.args = args
        self.engine = chess.engine.SimpleEngine.popen_uci(self.binary)

        # TODO: args.args is ridiculous; fix this
        self.pgn_file = self.args.args['file']
        if self.pgn_file:
            self.pgn = open(self.pgn_file)
        else:
            print("Using the test PGN file")
            self.pgn = open("test_game.pgn")

        if self.args.args['depth']:
            self.set_depth(self.args.args['depth'])
        if self.args.args['time']:
            self.set_move_time_min(self.args.args['time'])

        self.game = chess.pgn.read_game(self.pgn)
        self.board = self.game.board()

        #print("Config options:")
        #print(config.args)

    @property
    def game(self):
        return self._game

    @game.setter
    def game(self, value):
        self._game = value

    @property
    def board(self):
        return self._board

    @board.setter
    def board(self, value):
        self._board = value

    @property
    def engine(self):
        return self._engine

    @engine.setter
    def engine(self, value):
        self._engine = value

    def moves(self):
        return self.game.mainline_moves()

    def run_centipawn(self):
        #print(f"run_centipawn(self) - {self.args.args['eval']}")
        return self.args.args['eval'] == True

    def run_list_moves(self):
        #print(f"run_list_moves(self) - {self.args.args['list']}")
        return self.args.args['list'] == True

    def set_depth(self, d):
        # I don't know if this is python-chess or Stockfish
        #try:
        #    self.engine.configure({"depth": d})
        #except:
        #    print("Invalid option. Available options:")
        #    print(self.engine.options["Hash"])
        #    os._exit(1)

        # But this should work with python-chess
        chess.engine.Limit.depth = int(d)

    def set_move_time_min(self, t):
        chess.engine.Limit.time = float(config['time'])

    def get_piece_at_square(self, square):
        return self.board.piece_at(square).symbol()

    # Most of this probably needs to be moved to another function and have this
    # function simply return the results of get_evaluation()
    def get_eval(self):
        # TODO: what is the right/best way to handle the `chess.engine.Limit`
        # thing? Is there no way to configure this per instance of engine?
        return self.engine.analyse(self.board, chess.engine.Limit)

    def print_position_info(self, s, f, v):
        return "Not implemented"
        #print(f"Evaluation: {v}")
        #print(f"Move made: {s.move}\n")
        #print(f"Next Best Move: {best_move(f)}")

class Stockfish_Stockfish(Engine_Analysis):
    def __init__(self, binary=conf.DEFAULT_STOCKFISH_BIN):
        Engine_Analysis.__init__(self, binary)

        # Can set the strength of Stockfish to something more comparable to the ELO of
        # the players in the game so stockfish evaluates based on that ELO. Could be
        # useful. (actually not sure this affects position evaluation)
        engine_weak = Stockfish(path=STOCKFISH_BIN, parameters={"Threads": 6, "UCI_LimitStrength": "true", "UCI_Elo": 1000})

        # Default to max strength
        engine_strong = Stockfish(path=STOCKFISH_BIN, parameters={"Threads": 6, "UCI_LimitStrength": "false"})

        self.set_engine('Strong')

    @property
    def engine(self):
        return self._engine

    @engine.setter
    def engine(self, value):
        self._engine = value

    # TODO: should this be an enum or constant?
    def set_engine(self, strong_weak = "Strong"):
        if strong_weak == 'Strong':
            self.engine = engine_strong
        elif strong_weak == 'Weak':
            self.engine = engine_weak
        else:
            raise f"Invalid option given for set_engine: {strong_weak}"

    def set_depth(self, d):
        engine.set_depth(d)

    def set_move_time_min(self, t):
        engine.update_engine_parameters({"Minimum Thinking Time": t})
        # I don't know which class this is supposed to be for:
        #engine.configure({"Minimum Thinking Time": t})

    def set_position(self, fen):
        engine.set_fen_position(fen)

    def best_move_fen(fen):
        if stockfish.is_fen_valid(fen):
            return stockfish.get_best_move()

def is_an_int(n):
    try:
        i = int(n)
        return True
    except ValueError:
        return False

def evaluate_centipawns(cp_diff):
    if cp_diff > const.CP_BLUNDER:
        return Category.BLUNDER
    elif cp_diff > const.CP_MISTAKE:
        return Category.MISTAKE
    elif cp_diff > const.CP_INACCURACY:
        return Category.INACCURATE
    else:
        return Category.OK

args = Arguments()

schach = Stockfish_PythonChess(args)
engine_valuations = {}

#print(f"config: {schach.args.args}")

if schach.run_centipawn():
    previous_valuation = 0
    for move in schach.moves():
        # Make each of these a getter that uses board; so schach.san(move) would be
        # implemented as "return self.board.san(move)"
        san = schach.board.san(move)
        turn = schach.board.turn
        move_num = schach.board.fullmove_number # i.e., not the ply
        ply = schach.board.ply()

        # This has to be a hack and wrong. I save the information for the current
        # move, like SAN and turn and whatnot, but if I don't put this call here
        # the evaluated position is somehow off by one based on what I see in 
        # ChessBase.
        schach.board.push(move)

        #eval_info = get_eval(engine, board, chess.engine.Limit)
        eval_info = schach.get_eval()
        valuation = str(eval_info['score'].relative)
        engine_valuations[ply] = eval_info

        if is_an_int(valuation):
            valuation = int(valuation)

            # TODO: pretty sure this is wrong. Relative score is relative to each player,
            # so a positive score is good for that player, and negative is bad. It applies
            # to both white and black.
            # Keep consistent with White eval: + good for White; - good for Black. The way
            # it currently works, + is good for the current color; - for the other. So a +
            # score for Black means Black is better. A - score for Black means that White
            # is better. But we generally use - for favoring Black and + favoring White.
            if schach.board.turn == chess.BLACK:
                valuation = -valuation

            eval_diff = abs(valuation - previous_valuation)

            if schach.args.args['list']:
                if turn == chess.WHITE: print(f"{move_num}: ", end="")
                print(f"{san} ", end="")
                if turn == chess.BLACK: print("")

            # For printing the FEN, each move on separate line
            if schach.args.args['print_fen']:
                if turn == chess.WHITE:
                    print(f"{move_num}:  {san} (fen: {board.fen()})")
                else:
                    print(f"...: {san} (fen: {board.fen()})")

            cp_category = evaluate_centipawns(eval_diff)
            if cp_category == Category.INACCURATE:
                print("Inaccuracy ", end='')
            elif cp_category == Category.MISTAKE:
                print("Mistake ", end='')
            elif cp_category == Category.BLUNDER:
                print("Blunder ", end='')

            if cp_category != Category.OK:
                #    print(f"cp_category = {cp_category}")
                san = f"...{san}" if turn == chess.BLACK else san
                print(f"at move {move_num}, {san} ({valuation})", end='')
        
                # print(f"curr ply: {eval_info} --> (move {san})")
                # if board.ply() > 1: print(f"prev ply: {engine_valuations[ply-1]}")
                # print(f"curr valuation = {valuation}")
                # print(f"prev valuation = {previous_valuation}")
                # print("")
        
                if schach.args.args['show_best']:
                    # This isn't right. This shows the next move in this
                    # position, not what should have been played instead of the
                    # move that caused this evaluation swing.
                    #print(f". Engine recommendation: {best_move(fen)}.")
                    print(f". Engine recommendation: {engine_valuations[ply-2]['pv'][1]}.")
                else:
                    print('')  # newline

            previous_valuation = valuation
        else:
            print(f"{valuation} at move {move_num}, {san}")
    schach.engine.close()
elif schach.run_list_moves():
    for move in schach.moves():
        print(f"move = {move}; san = {schach.board.san(move)}")
        schach.board.push(move)
    schach.engine.close()
else:
    print("Nothing to do. Did you provide an action?")

# # Some debugging stuff I want to leave
# # FEN for position in move 53:
# # 6k1/R7/5p2/5P1P/3KP1P1/6b1/8/8 b - - 0 53
# # SF in CB evaluates this to 0.00
# #
# # FEN for position in ...52:
# # 6k1/R7/5p2/5P1P/3pP1P1/3K2b1/8/8 w - - 0 53
# # 6k1/R7/5p2/5P1P/3pP1P1/3K2b1/8/8 w - - 0 53
# # SF in CB evaluates this to +18 or so
# 
# print("Evalation info for move 52, Bg3:")
# board = chess.Board("6k1/R7/5p2/5P1P/3pP1P1/3K2b1/8/8 w - - 0 53")
# info  = engine.analyse(board, chess.engine.Limit(depth=20))
# print(info)
# 
# print("Evalation info for move 53, Kxd4:")
# # The position represented in FEN
# board = chess.Board("6k1/R7/5p2/5P1P/3KP1P1/6b1/8/8 b - - 0 53")
# info  = engine.analyse(board, chess.engine.Limit(depth=20))
# print(info)
