"""
save_data.py
============

Persistência do high score em disco (save.json).

São só duas funções simples — sem classes — porque essa é toda
a "lógica" necessária. Os try/except garantem que o jogo nunca
trava por causa de um arquivo ausente ou corrompido; nesses
casos, simplesmente assume high score = 0.
"""
import json
import os
from config import SAVE_FILE


def load_high_score():
    """Lê o high score salvo. Retorna 0 se não existir ou der erro."""
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE) as f:
                return json.load(f).get('high_score', 0)
        except Exception:
            pass
    return 0


def save_high_score(score, current_high):
    """
    Compara `score` (pontuação da partida que acabou) com
    `current_high` (melhor pontuação salva até agora).

    Salva o maior valor em disco e retorna esse valor — é esse
    retorno que o main.py guarda em self.high_score.
    """
    new_high = max(score, current_high)
    try:
        with open(SAVE_FILE, 'w') as f:
            json.dump({'high_score': new_high}, f)
    except Exception:
        pass
    return new_high
