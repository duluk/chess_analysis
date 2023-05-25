#!/usr/bin/env python3

import sys
import os
import argparse
import datetime
import logging

import asyncio

import chess
import chess.pgn
import chess.engine

import constants as const
from constants import Category

class Complete_Board:
    def __init__(self, game):
        self.game = game
        self.board = game.board()
        self.san = []
        self.push_all_moves

    def push_all_moves(self):
        for move in self.game.mainline_moves():
            # This will be zero-based of course, but that's consistent with how
            # the move_stack works anyway, so a given ply is still accessible
            # with board.ply()-1
            self.san.append(self.board.san_and_push(move))

        return board

    def ply(self, n, san_or_uci=True):
        # san_or_uci = True for san; False for uci
        if san_or_uci:
            return self.san[n-1]
        else:
            return self.board.move_stack[n-1].uci()

    # This may not be used. Depends on how this class ends up being used.
    # Probably more about random access (the ply method) than keeping this
    # object in sync with some other board that is being pushed to as each move
    # is analyzed...but that may not be how I end up doing things.
    def next_ply(self, san_or_uci=True):
        # san_or_uci = True for san; False for uci
        curr_ply = self.board.ply()
        if san_or_uci:
            return self.san[curr_ply-1]
        else:
            return self.board.move_stack[curr_ply-1].uci()

if not const.LOG_DIR:
    const.LOG_DIR = '.'
elif not os.path.exists(const.LOG_DIR):
    try:
        os.mkdir(const.LOG_DIR)
    except OSError as error:
        print(error)
        os._exit(1)

parser = argparse.ArgumentParser(description="Arg Parse Stuff")
parser.add_argument("-f", "--file", help="PGN file to parse")
parser.add_argument("-e", "--elo", type=int, help="Set engine ELO")
parser.add_argument("-d", "--depth", type=int, help="Depth from which to do analysis")
parser.add_argument("-t", "--time", type=float, help="Set minimum move time for evaluation")
parser.add_argument("-s", "--hash-size", default=1024, type=int, help="Set engine hash size in MB")
parser.add_argument("-p", "--player-moves", action="store_true", help="Compare each player move to previous player move")
parser.add_argument("-c", "--computer-moves", action="store_false", help="Compare each player move to best computer move")
args = vars(parser.parse_args())

date_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
logging.basicConfig(filename=f"{const.LOG_DIR}/analysis.debug.{date_str}.log", level=logging.DEBUG)

def get_game(pgn):
    return chess.pgn.read_game(open(pgn))

def evaluate_player_cp(ply_analysis, prev_ply_analysis, turn_played):
    pov_curr_score = ply_analysis['player_eval']
    if pov_curr_score.is_mate():
        curr_score = pov_curr_score.score(mate_score=const.MATE_IN_ONE_CP)
#        return Category.MATE
    else:
        curr_score = pov_curr_score.score()

    # If None then this is the first move, for which there is no previous move.
    # The general evaluation prior to making the first move is usually around
    # 30 centipawns; setting it to 15 as a hedge of sorts.
    pov_prev_score = prev_ply_analysis['player_eval'] if prev_ply_analysis else chess.engine.Cp(15)
    if pov_prev_score.is_mate():
        prev_score = pov_prev_score.score(mate_score=const.MATE_IN_ONE_CP)
#        return Category.MATE
    else:
        prev_score = pov_prev_score.score()

    delta = curr_score - prev_score
#        print(f"curr_score = {curr_score}; prev_score = {prev_score}; delta = {delta}")

    # If White or Black are improving, it's probably not a blunder. This is
    # an attempt at addressing the documentation's warning about
    # comparing player scores from move to move.
    if turn_played == chess.WHITE and curr_score > prev_score:
        return Category.OK
    if turn_played == chess.BLACK and curr_score < prev_score:
        return Category.OK

#    if delta > 20000:
#        return Category.MATE
    if delta > const.CP_BLUNDER:
        return Category.BLUNDER
    elif delta > const.CP_MISTAKE:
        return Category.MISTAKE
    elif delta > const.CP_INACCURACY:
        return Category.INACCURATE
    else:
        return Category.OK

def evaluate_engine_cp(engine_score, player_score, turn_played):
    engine_score = engine_score.score(mate_score=25000)
    player_score = player_score.score(mate_score=25000)

    delta = engine_score - player_score
    # Scores are normalized on White, so when evaluating from Black's
    # perspective we need to invert the result so that a postivie score is good
    # for Black.
    delta = -delta if turn_played == chess.BLACK else delta

#    if delta > 20000:
#        return Category.MATE
    if delta > const.CP_BLUNDER:
        return Category.BLUNDER
    elif delta > const.CP_MISTAKE:
        return Category.MISTAKE
    elif delta > const.CP_INACCURACY:
        return Category.INACCURATE
    else:
        return Category.OK

async def main() -> None:
    _, engine = await chess.engine.popen_uci('/usr/bin/stockfish')
    
    pgn_file = args['file']
    if not pgn_file:
        print("Using the test PGN file")
        pgn_file = "test_game.pgn"
    
    if args['depth']:
        chess.engine.Limit.depth = args['depth']
    if args['time']:
        chess.engine.Limit.time = args['time']
    if args['elo']:
        elo = args['elo']
        elo_min = engine.options['UCI_Elo'].min
        elo_max = engine.options['UCI_Elo'].max
        if elo < elo_min or elo > elo_max:
            print(f"Invalid value for ELO, {elo}: must be between {elo_min} and {elo_max}.")
            os._exit(1)
        # Set LimitStrength to ensure Elo is actually applied
        try:
            await engine.configure({"UCI_LimitStrength": True})
        except:
            print("Invalid option UCI_LimitStrength. Available options:")
            print(engine.options)
            os._exit(1)
    
        try:
            await engine.configure({"UCI_Elo": elo})
        except:
            print("Invalid option, or value, UCI_Elo. Available options:")
            print(engine.options)
            os._exit(1)
    if args['hash_size']:
        size = args['hash_size']
        try:
            await engine.configure({"Hash": size})
        #    print(f"Hash size: {engine.options['Hash']}")
        except:
            print("Invalid option Hash. Available options:")
            print(engine.options)
            os._exit(1)
    
    # Setting this to greater than 1 seems to affect depth and performance; I
    # don't know - maybe a VM thing. Leaving it alone seems to work best.
#    threads = 1
#    try:
#        await engine.configure({"Threads": threads})
#    except:
#        print("Invalid option, or value, Threads. Available options:")
#        print(engine.options)
#        os._exit(1)

    game = get_game(pgn_file)
    #board_complete = Complete_Board(game)

    game_white = game.headers['White']
    game_black = game.headers['Black']
    game_date = game.headers['Date']

    print(f"Analyzing game between {game_white} and {game_black} on {game_date}")

    game_analysis = []
    node = game.end()
    while not node == game.root():
        prev_node = node.parent
        board = prev_node.board()
        move = node.move
        analysis = await engine.analyse(board, chess.engine.Limit)

        info = {
                'analysis': analysis,
                'player_move': move,
                'player_san': board.san(move),
                'best_move': board.san(analysis['pv'][0]),
                'best_eval': analysis['score'].white(),
                'player_color': board.turn,
                'move_num':  board.fullmove_number,
               }

        # It's unfortuate to need to run analysis again. There has to be a way
        # to avoid this.
        if move == analysis['pv'][0]:
            # Player made best move; no need to eval again
            #info['player_eval'] = analysis['score'].white().score(mate_score=25000)
            info['player_eval'] = analysis['score'].white()
        else:
            board.push(move)
            analysis = await engine.analyse(board, chess.engine.Limit)

            #info['player_eval'] = analysis['score'].white().score(mate_score=25000)
            info['player_eval'] = analysis['score'].white()

            board.pop()

        # May need to format this later (cf. eval_human in annotator)
        info['player_comment'] = info['player_eval']
        node.comment = str(info['player_eval'])

        game_analysis.append(info)
        node = prev_node

#    for ply in reversed(game_analysis):
#        print(f"{ply['player_san']}:")
#        print(f"\tPlayer eval: {ply['player_eval']}")
#        print(f"\tBest move: {ply['best_move']}")
#        print(f"\tBest move score: {ply['best_eval']}")

    prev_ply = None
    for ply in reversed(game_analysis):
        san = ply['player_san']
        best_san = ply['best_move']
        move_num = ply['move_num']
        played = ply['player_color']
        player_score = ply['player_eval']
        engine_score = ply['best_eval']
        depth = ply['analysis']['depth']
        prev_score = prev_ply['player_eval'] if prev_ply else chess.engine.Cp(0)

        if args['player_moves']:
            player_cp_category = evaluate_player_cp(ply, prev_ply, played)
            if player_cp_category != Category.OK:
                print("PvP ", end='')
                if player_cp_category == Category.INACCURATE:
                    print("Inaccuracy ", end='')
                elif player_cp_category == Category.MISTAKE:
                    print("Mistake ", end='')
                elif player_cp_category == Category.BLUNDER:
                    print("Blunder ", end='')
                elif player_cp_category == Category.MATE:
                    print(f"Mate in {player_score.mate()} ", end='')

                san = f"...{san}" if played == chess.BLACK else san
                print(f"at move {move_num}, {san} (p:{prev_score},c:{player_score}; depth={depth})")

        if args['computer_moves']:
            engine_cp_category = evaluate_engine_cp(engine_score, player_score, played)
            if engine_cp_category != Category.OK:
                print("PvE ", end='')
                if engine_cp_category == Category.INACCURATE:
                    print("Inaccuracy ", end='')
                elif engine_cp_category == Category.MISTAKE:
                    print("Mistake ", end='')
                elif engine_cp_category == Category.BLUNDER:
                    print("Blunder ", end='')
                elif engine_cp_category == Category.MATE:
                    print(f"Mate in {engine_score.mate()} ", end='')

                san = f"...{san}" if played == chess.BLACK else san
                print(f"at move {move_num}, {san}. Best move: {best_san} (p:{player_score},b:{engine_score},d:{depth})")

        prev_ply = ply

    await engine.quit()

asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
asyncio.run(main())
