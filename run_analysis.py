#!/usr/bin/env python3

# TODO:
#  1. Keep up with best moves in a hash so previous recommendations can be
#     accessed, such as when needing the suggested move instead of current one.
#  2. Perhaps keep up with more than just the recommended move so other
#     information can be accessed later.
#  3. Add option for which engine to use, though this will likely require a
#     config file so engines and paths can be provided on a per-system basis
#  4. Add another centipawn evaluation/analysis function. What I'm doing now is
#     comparing CP difference from one move to the next. What if I compared the
#     CP difference from the player's move to the engine's top chioce? I think
#     this is what the ChessBase Centipawn Analysis feature does. If not, it's
#     still interesting. I'm not sure how significant the different methods are,
#     but something to consider.
#  5. Fix the configuration abstraction. It's all wonky.
#  6. Implement status/progress bar of some sort
#  7. Try generating a fen for the current position and evaluating that, with
#     python-chess.
#  8. Or, what I really need to do is understand how python-chess works. There's
#     a weird one-off thing when iterating over the game and evaluating positions
#     and giving the move that triggered the eval. Either I'm confused or the
#     module is confused/ing. Guessing it's me.
#  9. Get stockfish to perform better; it takes much longer to evaluate
#     depth 20 in this script than it does in ChessBase. Maybe "permanent
#     brain" or something, but need to see if I can do that in
#     python-chess.
# 10. Improve evaluation of centipawn from move to move.
# 11. Add comparison of current move to best engine move, which is what the
#     Centipawn Analysis in ChessBase does.


#This could be useful:
#white_pieces = {'Pawn' : "♙", 'Rook' : "♖", 'Knight' : "♘", 'Bishop' : "♗", 'King' : "♔", 'Queen' : "♕" }

import sys
import os
import copy
import argparse

import logging
logging.basicConfig(level=logging.INFO)

from stockfish import Stockfish
import chess
import chess.pgn
import chess.engine

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
        self.parser.add_argument("-r", "--run-eval", action="store_true", help="Find evaluation swings")
        self.parser.add_argument("-l", "--list", action="store_true", help="Live moves")
        self.parser.add_argument("-e", "--elo", help="Set engine ELO")
        self.parser.add_argument("-n", "--print-fen", action="store_true", help="Print FEN")
        self.parser.add_argument("-d", "--depth", help="Depth from which to do analysis")
        self.parser.add_argument("-t", "--time", help="Set minimum move time for evaluation")
        self.parser.add_argument("-s", "--hash-size", help="Set engine hash size in MB")
        self.parser.add_argument("-b", "--show-best", action="store_true", help="Show best move at swing")
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

    def eval_move(self, m):
        return "Not implemented"

    def set_position(self, fen):
        return "Not implemented"

    def best_move(self):
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
        if self.args.args['elo']:
            self.set_elo(self.args.args['elo'])
        if self.args.args['hash_size']:
            self.set_hash(self.args.args['hash_size'])

        self.set_threads(6)

        self.game = chess.pgn.read_game(self.pgn)
        self.board = self.game.board()

        print("Config options:")
        print(self.args.args)
        print("Engine options:")
        print(self.engine.options)
#        print(f"chess.engine.Limit: {chess.engine.Limit}")

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

    @property
    def san(self):
        return self._san

    @san.setter
    def san(self, value):
        self._san = value

    @property
    def prev_board(self):
        return self._prev_board

    @prev_board.setter
    def prev_board(self, value):
        self._prev_board = value

    # color who made the move just pushed to board. Using prev_board because
    # we have pushed the move, so we're peeking at the previous move.
    @property
    def color_played(self):
        return self._color_played

    @color_played.setter
    def color_played(self, value):
        self._color_played = value

    def fullmove_number(self):
        return self.board.fullmove_number

    def fen(self):
        return self.board.fen()

    def ply(self):
        return self.board.ply()

    def san_and_push(self, move):
        # Copy the board prior to making the move so we can reference it later,
        # especially for calcluating what the best move was for the current
        # position (which means evaluating the previous position). A copy is
        # required here because it seems that Python (at least in this case) is
        # simply copying the reference, as without the copy changing `board`
        # also changes `prev_board`. Using deepcopy just to be safe.
        self.prev_board = copy.deepcopy(self.board)
        self.color_played = self.prev_board.turn
        self.san = self.board.san(move)

        return self.board.san_and_push(move)

    def moves(self):
        return self.game.mainline_moves()

    def run_centipawn(self):
        #print(f"run_centipawn(self) - {self.args.args['eval']}")
        return self.args.args['run_eval'] == True

    def run_list_moves(self):
        #print(f"run_list_moves(self) - {self.args.args['list']}")
        return self.args.args['list'] == True

    def set_depth(self, d):
        # This should work with python-chess
        chess.engine.Limit.depth = int(d)

    def set_move_time_min(self, t):
        chess.engine.Limit.time = float(t)

    def set_elo(self, elo):
        elo = int(elo)
        elo_min = self.engine.options['UCI_Elo'].min
        elo_max = self.engine.options['UCI_Elo'].max
        if elo < elo_min or elo > elo_max:
            print(f"Invalid value for ELO, {elo}: must be between {elo_min} and {elo_max}.")
            os._exit(1)

        # Set LimitStrength to ensure Elo is actually applied
        try:
            self.engine.configure({"UCI_LimitStrength": True})
        #    print(f"Limit strength: {self.engine.options['UCI_LimitStrength']}")
        except:
            print("Invalid option UCI_LimitStrength. Available options:")
            print(self.engine.options)
            os._exit(1)

        try:
            self.engine.configure({"UCI_Elo": elo})
        #    print(f"Engine elo: {self.engine.options['UCI_Elo']}")
        except:
            print("Invalid option, or value, UCI_Elo. Available options:")
            print(self.engine.options)
            os._exit(1)

    def set_hash(self, size):
        size = int(size)
        try:
            self.engine.configure({"Hash": size})
        #    print(f"Hash size: {self.engine.options['Hash']}")
        except:
            print("Invalid option Hash. Available options:")
            print(self.engine.options)
            os._exit(1)
        
    def set_threads(self, threads):
        threads = int(threads)
        try:
            self.engine.configure({"Threads": threads})
        except:
            print("Invalid option, or value, Threads. Available options:")
            print(self.engine.options)
            os._exit(1)

    def get_piece_at_square(self, square):
        return self.board.piece_at(square).symbol()

    def eval_move(self, move):
        # TODO: what is the right/best way to handle the `chess.engine.Limit`
        # thing? Is there no way to configure this per instance of engine?
        return self.engine.analyse(self.board, chess.engine.Limit)

    def best_move(self, b=None):
        # Typically we are going to analyze the previous position for the best
        # move because we want to know what move should have been played
        # instead of the one that was. But we allow a different board to be
        # passed in. (b=self.prev_board doesn't work as default value)
        if b == None:
            b = self.prev_board
        try:
            bm = str(b.san(self.engine.play(b, chess.engine.Limit).move))
            return bm
        except:
            return None

    def evaluate_centipawns(self, curr_score, prev_score):
        # TODO: does this need to be absolute value?
        #delta = abs(abs(curr_score) - abs(prev_score))
        delta = abs(curr_score - prev_score)
#        print(f"curr_score = {curr_score}; prev_score = {prev_score}; delta = {delta}")

        # If White or Black are improving, it's probably not a blunder.
        if self.color_played == chess.WHITE and curr_score > prev_score:
            return Category.OK
        if self.color_played == chess.BLACK and curr_score < prev_score:
            return Category.OK

        if delta > const.CP_BLUNDER:
            return Category.BLUNDER
        elif delta > const.CP_MISTAKE:
            return Category.MISTAKE
        elif delta > const.CP_INACCURACY:
            return Category.INACCURATE
        else:
            return Category.OK

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

    def set_position(self, fen):
        engine.set_fen_position(fen)

    def best_move_fen(fen):
        if engine.is_fen_valid(fen):
            return engine.get_best_move()

def is_an_int(n):
    try:
        i = int(n)
        return True
    except ValueError:
        return False

args = Arguments()
schach = Stockfish_PythonChess(args)

#print(f"config: {schach.args.args}")

if schach.run_centipawn():
    previous_valuation = 0
    for move in schach.moves():
        # At this point we are at the previous move, or before the move stored in
        # `move` has actually been made (pushed) on the board, so anything about
        # the board is for the previous move (or starting position on the first
        # time)

        # Get the move number (as opposed to ply) before making the move (push)
        # on the board, as otherwise the number will be off.
        move_num = schach.fullmove_number()

        # Put the move on the board so that board represents the move just made
        # (the move we're "on"). This makes it the next player's turn, so
        # everything is from the perspective of the opposite color from who
        # just made this move. So we call san_and_push to retrieve the san of
        # the move just made while playing the move on the board.
        san = schach.san_and_push(move)
        ply = schach.ply()

        # Get the evaluation of the position of the move just played
        eval_info = schach.eval_move(move)

        # Normalize on white's perspective so a positive number means White's
        # advantage and a negative number means Black's advanatage - makes
        # things much easier and took me a while to realize this was possible
        # and easier to do.
        valuation = str(eval_info['score'].white().score())

        if is_an_int(valuation):
            valuation = int(valuation)

            # This may go bye bye, but for now I wanted to be able to list the
            # moves along with the evaluation.
            if schach.args.args['list']:
                if schach.color_played == chess.WHITE: print(f"{move_num}: ", end="")
                print(f"{san} ", end="")
                if schach.color_played == chess.BLACK: print("")

            # For printing the FEN, each move on separate line
            if schach.args.args['print_fen']:
                if schach.color_played == chess.WHITE:
                    print(f"{move_num}:  {san} (fen: {schach.fen()})")
                else:
                    print(f"...: {san} (fen: {schach.fen()})")

            cp_category = schach.evaluate_centipawns(valuation, previous_valuation)
            if cp_category == Category.INACCURATE:
                print("Inaccuracy ", end='')
            elif cp_category == Category.MISTAKE:
                print("Mistake ", end='')
            elif cp_category == Category.BLUNDER:
                print("Blunder ", end='')

            if cp_category != Category.OK:
                san = f"...{san}" if schach.color_played == chess.BLACK else san
                print(f"at move {move_num}, {san} ({valuation})", end='')
        
                if schach.args.args['show_best']:
                    print(f". Engine suggests {schach.best_move()}.")
                else:
                    print('')  # newline

            previous_valuation = valuation
        else:
            valuation = str(eval_info['score'].white().mate())
            print(f"#{valuation} at move {move_num}, {san}")

            # Make up something totally arbitrary but showing the significance
            # of mate possibility, giving higher value to lower numbers (mate
            # in 1 is almost infinitely better than mate in 3). Of course just
            # subtracting valuation from MATE_IN_ONE_CP works also, but not
            # quite as different from mate in 1 to mate in 2.
            # e.g., eval['score'].white().score(mate_score=const.MATE_IN_ONE_CP)
            previous_valuation = const.MATE_IN_ONE_CP-(int(valuation)*const.MATE_CP_SCALE)
    schach.engine.close()
elif schach.run_list_moves():
    for move in schach.moves():
        print(f"move = {move}; san = {schach.board.san(move)}")
        schach.board.push(move)
    schach.engine.close()
else:
    print("Nothing to do. Did you provide an action?")
