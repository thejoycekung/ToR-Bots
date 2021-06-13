from typing import Optional, List

class FlairRank:
    def __init__(self, name: str, color: str, lower_bound: int, upper_bound: Optional[int] = None) -> None:
        self.name = name
        self.color = color
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound


    def has_rank(self, gamma: int) -> bool:
        """
        Determines if the given gamma count corresponds to this rank.
        """
        return self.lower_bound <= gamma and (self.upper_bound is None or self.upper_bound >= gamma)


    def passed_rank(self, gamma: int) -> bool:
        """
        Determines if the given gamma count had this rank already.
        """
        return self.lower_bound <= gamma
    

    def __str__(self) -> str:
        gamma_str = f"{self.lower_bound}+" if self.upper_bound is None else f"{self.lower_bound}-{self.upper_bound}"
        return f"{self.name} ({gamma_str})"

VISITOR = FlairRank("Visitor", "gray", 0, 0)
INITIATE = FlairRank("Initiate", "white", 1, 49)
GREEN = FlairRank("Green", "green", 50, 99)
TEAL = FlairRank("Teal", "teal", 100, 249)
PURPLE = FlairRank("Purple", "purple", 250, 499)
GOLD = FlairRank("Gold", "gold", 500, 999)
DIAMOND = FlairRank("Diamond", "diamond", 1000, 2499)
RUBY = FlairRank("Ruby", "ruby", 2500, 4999)
TOPAZ = FlairRank("Topaz", "topaz", 5000, 9999)
JADE = FlairRank("Jade", "jade", 10000, 24999)
SAPPHIRE = FlairRank("Sapphire", "sapphire", 25000)


RANK_LIST = [
    VISITOR,
    INITIATE,
    GREEN,
    TEAL,
    PURPLE,
    GOLD,
    DIAMOND,
    RUBY,
    TOPAZ,
    JADE,
    SAPPHIRE,
]


def get_cur_flair_rank(gamma: int) -> FlairRank:
    """
    Determines the current flair rank based on the current gamma score.
    """
    for rank in reversed(RANK_LIST):
        if rank.passed_rank(gamma):
            return rank

    return VISITOR


def get_valid_flair_ranks(gamma: int) -> List[FlairRank]:
    """
    Determines all valid flair ranks for the given gamma score.
    """
    return [rank for rank in RANK_LIST if rank.passed_rank(gamma)]
