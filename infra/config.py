"""infra/config.py — MODE and constants (docs/README.md:12-21, docs/AGENTS.md:15)"""
CROPS = {
    "WHEAT": {"seed":10,"first":2,"max":4,"max_yield":6,"ongoing":False},
    "CARROT": {"seed":20,"first":2,"max":3,"max_yield":4,"ongoing":False},
    "TOMATO": {"seed":50,"first":8,"max":8,"max_yield":4,"ongoing":True},
    "STRAWBERRY": {"seed":100,"first":10,"max":10,"max_yield":4,"ongoing":True},
    "MELON": {"seed":80,"first":10,"max":12,"max_yield":6,"ongoing":False},
}
BASE = {"WHEAT":25,"CARROT":35,"TOMATO":60,"STRAWBERRY":120,"MELON":250,"EGG":50,"MILK":160,"WOOL":200,"FERTILIZER":100}
SELL_FLOOR = {"WHEAT":18,"CARROT":20,"TOMATO":35,"STRAWBERRY":80,"MELON":150,"EGG":38,"MILK":100,"WOOL":120,"FERTILIZER":55}
SHED_TILES = [(4,4),(5,4),(4,5),(5,5)]
MODE = "CONSERVATIVE"  # vs AGGRESSIVE
