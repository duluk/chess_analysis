#!/usr/bin/env python3

from stockfish import Stockfish
import chess.pgn

STOCKFISH_BIN='/usr/bin/stockfish'

VALUATION_THRESHOLD_CP = 1.25*100

stockfish = Stockfish(path=STOCKFISH_BIN, parameters={"Threads": 4, "UCI_LimitStrength": "true", "UCI_Elo": 1000})

def set_pos(fen):
    stockfish.set_fen_position(fen)

def best_move(fen):
    if stockfish.is_fen_valid(fen):
        return stockfish.get_best_move()

def get_eval(fen):
    e = stockfish.get_evaluation()
    v = e['value']
    t = e['type']

    # TODO: the return type should be the same and the calling code deal with how
    # to handle the values differently
    if t == 'cp':
        # TODO: should this be converted to pawn units (v/100)
        return v
    elif t == 'mate':
        color = "Black" if v < 0 else "White"
        av = abs(int(v))
        return f"M{av} for {color}"


pgn = open("test_game.pgn")
schach = chess.pgn.read_game(pgn)

last_significant_valuation = 0
while schach.next():
    schach = schach.next()
    fen = schach.board().fen()
    set_pos(fen)
    valuation = get_eval(fen)
    move_num = round(int(schach.ply())/2)

    if isinstance(valuation, int):
        if abs(valuation - last_significant_valuation) > VALUATION_THRESHOLD_CP:
            print(f"Valuation swing at move {move_num}, {schach.move} ({valuation})")
            last_significant_valuation = valuation
    elif isinstance(valuation, str):
        print(f"{valuation} at move {move_num}, {schach.move}")

    #print(f"Evaluation: {valuation}")
    #print(f"Move made: {schach.move}\n")
    #print(f"Next Best Move: {best_move(fen)}")
