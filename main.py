import os
import random
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")
print("\n>>> 正在執行【最新版本】的 Server (含任務一~四檢查) <<<\n")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
]

# 任務三：全域勝率統計
stats_db = {
    "total_games": 0,
    "wins": 0
}

# 記憶體儲存遊戲狀態
games_db: Dict[str, dict] = {}


class NewGameRequest(BaseModel):
    hard_mode: bool = False


class GuessRequest(BaseModel):
    game_id: str
    guess: str


def get_stats_data():
    total = stats_db["total_games"]
    wins = stats_db["wins"]
    win_rate = (wins / total * 100) if total > 0 else 0.0
    return {
        "total_games": total,
        "wins": wins,
        "win_rate": round(win_rate, 1)
    }


@app.get("/api/stats")
def get_stats():
    """ 任務三：回傳勝率數據 """
    return get_stats_data()


@app.post("/api/new-game")
def start_new_game(
    req: Optional[NewGameRequest] = None,
    hard_mode: Optional[bool] = Query(None)
):
    """ 
    任務四：建立新一局遊戲，接收可選參數 hard_mode (預設 False)，
    同時支援 Query Parameter 與 JSON Body。
    """
    is_hard = False
    if hard_mode is not None:
        is_hard = hard_mode
    elif req is not None:
        is_hard = req.hard_mode

    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "hard_mode": is_hard,
        "revealed_greens": {},  # 儲存 index -> char
        "finished": False
    }
    return {
        "game_id": game_id,
        "message": "New game started!",
        "hard_mode": is_hard,
        "stats": get_stats_data()
    }


@app.post("/api/guess")
def process_guess(req: GuessRequest):
    game_id = req.game_id
    guess = req.guess.upper()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")

    game = games_db[game_id]
    if game["finished"]:
        raise HTTPException(status_code=400, detail="Game already ended.")

    if len(guess) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    # 任務二：後端單字合法性檢查
    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in dictionary")

    # 任務四：Hard Mode 邏輯驗證（先前已確認為綠色的字母必須維持相同位置）
    if game["hard_mode"]:
        for idx, required_char in game["revealed_greens"].items():
            if guess[idx] != required_char:
                raise HTTPException(
                    status_code=400,
                    detail="Hard Mode: Must use revealed hint at green position"
                )

    # 驗證通過，消耗猜測次數
    game["attempts"] += 1
    target = game["target"]
    feedback = ["absent"] * 5
    target_letter_counts = {}

    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    # 1. 標記綠色 correct
    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1
            game["revealed_greens"][i] = guess[i]

    # 2. 標記黃色 present
    for i in range(5):
        if feedback[i] != "correct" and guess[i] in target:
            if target_letter_counts[guess[i]] > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    # 檢查是否過關或用盡 6 次機會
    is_correct = (guess == target)
    game_over = is_correct or (game["attempts"] >= 6)

    # 任務三：戰績累加
    if game_over and not game["finished"]:
        game["finished"] = True
        stats_db["total_games"] += 1
        if is_correct:
            game["status"] = "WON"
            stats_db["wins"] += 1
        else:
            game["status"] = "LOST"

    # 任務一：猜對或第 6 次猜錯時回傳答案；尚未結束則為 None
    revealed_target = target if game_over else None

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "target_word": revealed_target,
        "attempts": game["attempts"],
        "remaining_attempts": max(0, 6 - game["attempts"]),
        "stats": get_stats_data()
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
