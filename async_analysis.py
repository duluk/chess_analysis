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
args = vars(parser.parse_args())

date_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
logging.basicConfig(filename=f"{const.LOG_DIR}/analysis.debug.{date_str}.log", level=logging.DEBUG)

def get_game(pgn):
    return chess.pgn.read_game(open(pgn))

def evaluate_centipawns(turn_played, pov_curr_score, pov_prev_score):
    if pov_curr_score.is_mate():
        # This doesn't seem like the right way to do this
        #curr_score = chess.engine.Cp(pov_curr_score.score(mate_score=const.MATE_IN_ONE_CP)).score()
        curr_score = pov_curr_score.score(mate_score=const.MATE_IN_ONE_CP)
#        return Category.MATE
    else:
        curr_score = pov_curr_score.score()

    if pov_prev_score.is_mate():
        # This doesn't seem like the right way to do this
        prev_score = pov_prev_score.score(mate_score=const.MATE_IN_ONE_CP)
#        return Category.MATE
    else:
        prev_score = pov_prev_score.score()

    delta = curr_score - prev_score
#        print(f"curr_score = {curr_score}; prev_score = {prev_score}; delta = {delta}")

    # If White or Black are improving, it's probably not a blunder. This is
    # an attempt at addressing the documentation's warning above about
    # comparing scores.
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
    board = game.board()

    prev_score = chess.engine.Cp(0)
    for move in game.mainline_moves():
        played = board.turn
        move_num = board.fullmove_number
        san = board.san_and_push(move)

        #info = await engine.analyse(board, chess.engine.Limit(depth=25))
        #info = await engine.analyse(board, chess.engine.Limit(time=0.5))
        info = await engine.analyse(board, chess.engine.Limit)
        score = info['score'].white()
        depth = info['depth']
        #print(f"Score after {san}: {score}")

        cp_category = evaluate_centipawns(played, score, prev_score)

        # If want "Mate in ..." listed, uncomment this
#        if score.is_mate():
#            cp_category = Category.MATE

        if cp_category == Category.INACCURATE:
            print("Inaccuracy ", end='')
        elif cp_category == Category.MISTAKE:
            print("Mistake ", end='')
        elif cp_category == Category.BLUNDER:
            print("Blunder ", end='')
        elif cp_category == Category.MATE:
            print(f"Mate in {score.mate()} ", end='')

        if cp_category != Category.OK:
            san = f"...{san}" if played == chess.BLACK else san
            print(f"at move {move_num}, {san} (p:{prev_score},c:{score}; depth={depth})")
        
        if score.is_mate():
            # Again, need to figure out the right way to do this
            prev_score = chess.engine.Cp(score.score(mate_score=const.MATE_IN_ONE_CP))
        else:
            prev_score = score

    await engine.quit()

asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
asyncio.run(main())
