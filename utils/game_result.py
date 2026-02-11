"""Game result processing utilities."""
from typing import Optional, Tuple


def rework_game_result(result: str) -> Optional[str]:
    """
    Normalize game result strings to 'victory' or 'defeat'.

    Args:
        result: Raw result string from OCR

    Returns:
        'victory' if win, 'defeat' if loss, None otherwise
    """
    result_lower = result.lower().strip()
    win_keywords = [
        'victory', 'win', 'won', 'winner',
        'victoria', 'ganado', 'ganaste',
        'vitoire', 'gagne', 'gagné',
        'siegre', 'gewonnen', 'gewinn'
    ]

    for keyword in win_keywords:
        if keyword in result_lower:
            return 'victory'

    loss_keywords = [
        'defeat', 'loss', 'lose', 'lost',
        'derrota', 'perdido', 'perdiste',
        'defaite', 'perdu',
        'niederlage', 'verloren',
        'draw', 'tie', 'empate'
    ]

    for keyword in loss_keywords:
        if keyword in result_lower:
            return 'defeat'

    return None


def get_trophy_change(
    result: str,
    base_trophy_change: int = 24,
    win_streak_bonus: int = 0
) -> Optional[int]:
    """
    Calculate trophy change based on game result.

    Args:
        result: Game result string
        base_trophy_change: Base trophies gained/lost (default 24)
        win_streak_bonus: Bonus trophies for win streak

    Returns:
        Trophy change (positive for win, negative for loss), or None
    """
    normalized = rework_game_result(result)
    if normalized == 'victory':
        return base_trophy_change + win_streak_bonus
    elif normalized == 'defeat':
        return -base_trophy_change
    return None


TrophyRange = Tuple[int, int]


def get_trophy_range(trophies: int, win: bool) -> TrophyRange:
    """
    Predict the trophy range after a match.

    Args:
        trophies: Current trophy count
        win: Whether the match was won

    Returns:
        Tuple of (min, max) trophy range
    """
    if win:
        return (trophies + 24, trophies + 32)
    else:
        return (trophies - 24, trophies - 20)
