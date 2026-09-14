"""strategy/portfolio.py — Allocator 70/30 + melon tilt"""
def target_coops(unlocked_cnt, day, money, plant_tiles):
    if day>10 and money>3000 and plant_tiles>5:
        return max(4, int(0.15 * (25*unlocked_cnt)))
    return 0

def should_plant_melon(melon_price, melon_tiles, unlocked_cnt, money, day, melon_seeds):
    return melon_price>200 and melon_tiles < max(2, (25*unlocked_cnt)//10) and money>1000 and day>5 and melon_seeds>0
