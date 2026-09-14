"""strategy/scheduler.py — Improved TaskScheduler for 60/75 fill (money>35)
Priorities: 1=critical water/feed+end-season harvest, 2=normal water/feed, 3=fertilize+straw/melon plant, 4=care/collect, 5=harvest, 6=weed, 7=build
Deterministic NWSE tie-break, distance-aware.
"""
from infra.config import CROPS

def build_tasks(tiles, board_size, day, is_end_season, fertil_available, seeds, money, prices, unlocked_tiles_count, plant_tiles, empty_positions, coops_total, target_coops):
    tasks=[]
    for y in range(board_size):
        for x in range(board_size):
            t=None
            try: t=tiles[y][x]
            except: continue
            if t=="LOCKED": continue
            if t is None: continue
            kind=t.get("kind")
            if kind=="WEED":
                tasks.append((1 if is_end_season else 6, y,x, "DIG", None))
            elif kind=="PLANT":
                crop=t.get("crop","WHEAT"); info=CROPS.get(crop, CROPS["WHEAT"])
                watered=t.get("watered_today",False); consec=t.get("consecutive_unwatered",0)
                yield_units=t.get("yield_units",0); planted=t.get("planted_day",day); age=day-planted
                fertil_until=t.get("fertilized_until_day",-1)
                if not watered:
                    prio=1 if consec>=1 else 2
                    tasks.append((prio, y,x, "WATER", None))
                if fertil_available>0:
                    bonus_start=(info["max"]+1)//2
                    if not info["ongoing"] and bonus_start <= age <= info["max"] and fertil_until < day:
                        tasks.append((3, y,x, "FERTILIZE", None))
                should=False; hp=5
                if is_end_season and yield_units>0: should=True; hp=1
                elif info["ongoing"]:
                    if yield_units>0: should=True; hp=5
                else:
                    if age>=info["max"] and yield_units>0: should=True; hp=1
                    elif age>=info["max"]-1 and yield_units>=3: should=True; hp=2
                    elif age>=info["first"] and yield_units>=4: should=True; hp=5
                    if age>=info["max"]+1 and yield_units>0: should=True; hp=1
                if should: tasks.append((hp, y,x, "HARVEST", None))
            elif kind in ("COOP","PASTURE"):
                animal=t.get("animal")
                if animal is None: pass
                else:
                    fed=t.get("fed_today",False); consec_unfed=t.get("consecutive_unfed",0)
                    if not fed:
                        prio=2 if consec_unfed>=1 else 4
                        tasks.append((prio, y,x, "FEED", None))
                    if t.get("fertilizer_available",False):
                        tasks.append((5, y,x, "COLLECT_FERTILIZER", None))
                    if not t.get("cared_today",False) and fed:
                        tasks.append((5, y,x, "CARE", None))
                    hp_a=1 if is_end_season else 5
                    if t.get("yield_units",0)>0:
                        tasks.append((hp_a, y,x, "HARVEST", None))
    # planting — staggered 60/75: 8/turn after day10 with 11 hands (money>35 allows filling even at 35$)
    can_plant_wheat = day <= 26
    can_plant_melon = day <= 18
    can_plant_straw = day <= 20
    has_seeds = ((seeds.get("WHEAT",0)>0 and can_plant_wheat) or (seeds.get("MELON",0)>0 and can_plant_melon) or (seeds.get("STRAWBERRY",0)>0 and can_plant_straw))
    if empty_positions and has_seeds and plant_tiles < max(12, unlocked_tiles_count-3) and day < 27:
        limit = 8 if day>=10 else 3
        remaining = max(12, unlocked_tiles_count-3) - plant_tiles
        limit = min(limit, remaining, len(empty_positions))
        for y,x in empty_positions[:limit]:
            melon_price=prices.get("MELON",250)
            melon_tiles=sum(1 for row in tiles for t in row if isinstance(t,dict) and t.get("crop")=="MELON")
            straw_tiles=sum(1 for row in tiles for t in row if isinstance(t,dict) and t.get("crop")=="STRAWBERRY")
            if can_plant_melon and melon_price>200 and melon_tiles < max(4, unlocked_tiles_count//12) and money>35 and 2<=day<=8 and seeds.get("MELON",0)>0:
                tasks.append((3, y,x, "PLANT", "MELON"))
            elif can_plant_straw and day>=8 and straw_tiles < max(8, unlocked_tiles_count//5) and seeds.get("STRAWBERRY",0)>0:
                tasks.append((3, y,x, "PLANT", "STRAWBERRY"))
            elif seeds.get("WHEAT",0)>0 and can_plant_wheat:
                tasks.append((3, y,x, "PLANT", "WHEAT"))
            elif seeds.get("MELON",0)>0 and can_plant_melon:
                tasks.append((3, y,x, "PLANT", "MELON"))
            elif seeds.get("STRAWBERRY",0)>0 and can_plant_straw:
                tasks.append((3, y,x, "PLANT", "STRAWBERRY"))
    if coops_total < target_coops and empty_positions and money>35:
        cands = empty_positions[3:] if len(empty_positions)>3 else []
        if cands:
            y,x = cands[0]
            tasks.append((7, y,x, "BUILD_COOP", None))
    # deterministic sort by priority then y,x
    return sorted(tasks, key=lambda e: (e[0], e[1], e[2]))

