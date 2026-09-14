"""
Kaggriculture Low-Vol High-Mean Agent
Target mu >=120k : 70% WHEAT + 30% GOOSE/EGG, staggered planting, price-aware selling
Deterministic, no randomness outside board traversal tie-break NWSE
"""
import math
from infra.config import CROPS, BASE, SELL_FLOOR, SHED_TILES
from core.board import is_shed_adjacent, manhattan, next_step_toward

def get_board_size(farms):
    # try infer from tiles len
    try:
        return len(farms[0]["tiles"])
    except:
        return 10

# Global per-agent state (persists across turns within episode)
# Use function attribute
def agent(obs):
    # ---- parse obs ----
    player = obs.get("player",0)
    day = obs.get("day", obs.get("step",0)//24)
    hour = obs.get("hour", obs.get("step",0)%24)
    step = obs.get("step", day*24+hour)
    farms = obs.get("farms", [])
    private = obs.get("private", {})
    market = obs.get("market", {})
    town = obs.get("town", {})
    is_shop_open_day = (day % 3 == 0)

    if not farms or player >= len(farms):
        return {"farmer":["PASS"],"hands":[],"market":[]}
    me = farms[player]
    money = me.get("money",0)
    tiles = me.get("tiles",[])
    farmer_pos = me.get("farmer",[4,4])
    hands_pos = me.get("hands",[])
    unlocked = me.get("unlocked_quadrants", ["NW"])
    hires_today = me.get("hires_today",0)
    unlocked_set=set(unlocked)

    board_size = len(tiles) if tiles else 10
    half = board_size//2

    shed = private.get("shed",{})
    seeds = private.get("seeds",{})
    inventories = private.get("inventories",[{}])
    # inventories[0] is farmer
    farmer_inv = inventories[0] if len(inventories)>0 else {}
    total_shed_items = sum(shed.values()) if shed else 0
    shed_capacity = 100

    prices = market.get("prices",{})
    inventory_mkt = market.get("inventory",{})

    # ---- Market decisions ----
    market_ops = []

    wheat_seeds = seeds.get("WHEAT",0)
    if wheat_seeds < 20 and money > 35:
        need = 20 - wheat_seeds
        max_buy = min(need, int((money-35)//10) if money>35 else 0)
        if max_buy>0:
            market_ops.append(["BUY_SEED","WHEAT", max_buy])
            money -= max_buy*10
    # Strawberry for phase 2 (high value ongoing, 4 yields) - money>35 as replay 108777858 (spent to 60$)
    straw_seeds = seeds.get("STRAWBERRY",0)
    if day>=8 and straw_seeds < 10 and money > 35:
        need_s = 10 - straw_seeds
        max_buy_s = min(need_s, int((money-35)//100) if money>35 else 0)
        if max_buy_s>0:
            market_ops.append(["BUY_SEED","STRAWBERRY", max_buy_s])
            money -= max_buy_s*100
    melon_price = prices.get("MELON",250)
    melon_seeds = seeds.get("MELON",0)
    if melon_price>200 and melon_seeds < 5 and money > 35 and 2<=day<=8:
        need_m = 5 - melon_seeds
        max_buy_m = min(need_m, int((money-35)//80) if money>35 else 0)
        if max_buy_m>0:
            market_ops.append(["BUY_SEED","MELON", max_buy_m])
            money -= max_buy_m*80

    # Goose logic: after day 3, buy geese if we have coops capacity and money
    # Count coops and animals
    coops_empty=0
    coops_total=0
    animals_total=0
    empty_tiles=0
    plant_tiles=0
    weed_tiles=0
    for y in range(board_size):
        for x in range(board_size):
            t=None
            try:
                t=tiles[y][x]
            except: continue
            if t=="LOCKED": continue
            if t is None:
                empty_tiles+=1
            elif isinstance(t,dict):
                k=t.get("kind")
                if k=="WEED": weed_tiles+=1
                elif k=="PLANT": plant_tiles+=1
                elif k in ("COOP","PASTURE"):
                    coops_total+=1
                    if t.get("animal") is None:
                        coops_empty+=1
                    else:
                        animals_total+=1

    unlocked_tiles_count = 25*len(unlocked_set)
    is_shop_open_day = (day % 3 == 0)
    if day >= 27 or is_shop_open_day:
        target_hands = 11
    else:
        target_hands = max(2, unlocked_tiles_count//7)
        target_hands = min(11, target_hands)
    if day < 3 or is_shop_open_day or day>=27:
        desired_hands = target_hands
    else:
        if plant_tiles + weed_tiles > 10 or day>=27:
            desired_hands = target_hands
        elif plant_tiles + weed_tiles > 5:
            desired_hands = max(2, target_hands-2)
        else:
            desired_hands = max(1, target_hands-2) if day<20 else target_hands

    # Track hires needed
    # Only hire if hour < 12 (morning) to have time to work
    if hires_today < desired_hands:
        fib=[1,1,2,3,5,8,13,21]
        cost = fib[hires_today] if hires_today < len(fib) else 30
        if money > cost and money > 35:
            market_ops.append(["HIRE"])
            # don't also buy land same turn to respect maxMarketOrdersPerTurn
    # v2-75: only 75 tiles (NW+NE+SW), never buy SE in phase 1
    land_cost_map={"NE":1000,"SW":2000}
    land_order=["NE","SW"]
    remaining_land=[q for q in land_order if q not in unlocked_set]
    if remaining_land:
        next_land=remaining_land[0]
        cost_land=land_cost_map[next_land]
        used = plant_tiles+coops_total+weed_tiles
        utilization = used / unlocked_tiles_count if unlocked_tiles_count else 1
        # money>35: spend to 35$ to fill 60/75 as replay 108777858 (went to 60$)
        buffer = 35
        util_thresh = 0.30 if day<10 else 0.45
        if money > cost_land + buffer and utilization > util_thresh:
            # prioritize land over hiring
            # remove hire if we need land
            market_ops = [op for op in market_ops if op[0]!="HIRE"]
            market_ops.append(["BUY_LAND"])

    # v2-75: 14 coops/animals by day12 as in replay - money>35 aggressive
    if day>=4 and money>35 and unlocked_tiles_count>=25:
        if unlocked_tiles_count>=50:
            target_coops = 14 if day>=8 else 8
        else:
            target_coops = 5
    else:
        target_coops = 0
    # allow sheep/wool as in replay (they used sheep not goose)
    # we keep GOOSE but also allow SHEEP via same coop? Actually sheep needs pasture, goose needs coop
    # For now use GOOSE for coop, SHEEP for pasture - count pastures too

    # Build coops via farmer actions, buy animals via market
    goose_in_shed = shed.get("GOOSE",0)
    # inventory geese?
    goose_in_inv = sum(inv.get("GOOSE",0) for inv in inventories)
    total_goose_available = goose_in_shed + goose_in_inv
    # if we need more coops built, farmer will build; market buys geese
    # only buy geese if we have empty coops to place them
    if coops_empty>0 and animals_total < target_coops and money > 35:
        need_geese = coops_empty
        if need_geese>0:
            buy_n = min(2, need_geese, int((money-35)//300) if money>35 else 0)
            if buy_n>0 and not any(op[0]=="BUY_LAND" for op in market_ops):
                market_ops.append(["BUY_ANIMAL","GOOSE", buy_n])

    max_plants_allowed = max(12, unlocked_tiles_count - 3)
    # end-season filtering: clear board and sell all
    is_end_season = day >= 27
    force_sell = total_shed_items >= 85 or is_end_season
    for item in ["WHEAT","EGG","CARROT","TOMATO","FERTILIZER","MILK","WOOL","STRAWBERRY","MELON"]:
        cnt = shed.get(item,0)
        if cnt<=0: continue
        price = prices.get(item, BASE.get(item,10))
        floor = SELL_FLOOR.get(item, 10)
        # special: fertilizer we may keep some for fertilizing (keep 10)
        if item=="FERTILIZER" and cnt <=10 and not force_sell:
            continue
        # wheat we keep 15 for feed as buffer (15 wheat feeds 15 animals for 1 day)
        if item=="WHEAT" and cnt <= 15 and not force_sell and animals_total>0:
            # keep buffer but sell excess above 15
            cnt_to_sell = cnt - 15
            if cnt_to_sell<=0: continue
            # adjust cnt
            sell_cnt = cnt_to_sell
        else:
            sell_cnt = cnt

        # decide to sell
        should = False
        if force_sell:
            should=True
        elif price >= floor:
            if item in ("STRAWBERRY","MELON","MILK","WOOL"):
                # on shop open days, sell even at 0.5*base to capture demand spike
                thresh = 0.5 if is_shop_open_day else 0.7
                if price >= BASE[item]*thresh:
                    should=True
            else:
                should=True
        elif is_shop_open_day and item in ("MILK","WOOL","STRAWBERRY","TOMATO","EGG"):
            # shop opening day: sell at high price even if below floor, expect price rise
            if price >= BASE[item]*0.6:
                should=True
            else:
                should=False
        else:
            should=False

        if should:
            # sell in one order, cap quantity to not exceed maxMarketOrders but we have 10 slots
            # limit sell size to 20 to allow town to absorb? But to reduce ops, sell all
            # if we have many items, split? Not needed.
            # Ensure we don't exceed 10 market ops
            if len(market_ops) >= 9:
                break
            market_ops.append(["SELL", item, sell_cnt])

    # Cap at 10
    market_ops = market_ops[:10]

    # ---- Movement / field actions ----
    # Build task list
    tasks = []  # (priority, y,x, action, details)
    # Priority numbers lower = more urgent
    # 1 water/feed critical (consecutive 1)
    # 2 water/feed normal
    # 3 collect fertilizer
    # 4 care
    # 5 harvest ready
    # 6 dig weed
    # 7 fertilize
    # 8 plant/build
    # 9 move to shed to drop

    fertil_available = shed.get("FERTILIZER",0) + sum(inv.get("FERTILIZER",0) for inv in inventories)
    empty_positions=[]
    for y in range(board_size):
        for x in range(board_size):
            t=None
            try:
                t=tiles[y][x]
            except: continue
            if t=="LOCKED":
                continue
            if t is None:
                empty_positions.append((x,y))
                continue
            kind=t.get("kind")
            if kind=="WEED":
                tasks.append((1 if is_end_season else 6, y,x, "DIG", None))
            elif kind=="PLANT":
                crop=t.get("crop","WHEAT")
                info=CROPS.get(crop, CROPS["WHEAT"])
                watered=t.get("watered_today",False)
                consec=t.get("consecutive_unwatered",0)
                yield_units=t.get("yield_units",0)
                planted=t.get("planted_day",day)
                age = day - planted
                fertil_until=t.get("fertilized_until_day",-1)
                if not watered:
                    prio = 1 if consec>=1 else 2
                    tasks.append((prio, y,x, "WATER", None))
                # fertilize if in bonus window and have fertilizer
                if fertil_available>0:
                    bonus_start = (info["max"]+1)//2
                    if not info["ongoing"] and bonus_start <= age <= info["max"] and fertil_until < day:
                        tasks.append((3, y,x, "FERTILIZE", None))
                should_harvest=False
                harvest_prio=5
                if is_end_season and yield_units>0:
                    should_harvest=True
                    harvest_prio=1
                elif info["ongoing"]:
                    if yield_units>0:
                        should_harvest=True
                        harvest_prio=5
                else:
                    if age >= info["max"]:
                        if yield_units>0:
                            should_harvest=True
                            harvest_prio=1
                    elif age >= info["max"]-1 and yield_units>=3:
                        should_harvest=True
                        harvest_prio=2
                    elif age >= info["first"] and yield_units>=4:
                        should_harvest=True
                        harvest_prio=5
                    if age >= info["max"]+1 and yield_units>0:
                        should_harvest=True
                        harvest_prio=1
                if should_harvest:
                    tasks.append((harvest_prio, y,x, "HARVEST", None))
            elif kind in ("COOP","PASTURE"):
                animal=t.get("animal")
                if animal is None:
                    if total_goose_available>0 or goose_in_shed>0:
                        tasks.append((4, y,x, "PLACE_GOOSE", None))
                    else:
                        # keep empty, maybe dig to reuse for crops if excess coops?
                        pass
                else:
                    fed=t.get("fed_today",False)
                    consec_unfed=t.get("consecutive_unfed",0)
                    fertil_avail=t.get("fertilizer_available",False)
                    cared=t.get("cared_today",False)
                    y_units=t.get("yield_units",0)
                    if not fed:
                        prio=2 if consec_unfed>=1 else 4
                        tasks.append((prio, y,x, "FEED", None))
                    if fertil_avail:
                        tasks.append((5, y,x, "COLLECT_FERTILIZER", None))
                    if not cared and fed:
                        tasks.append((5, y,x, "CARE", None))
                    harvest_prio_a = 1 if is_end_season else 5
                    if y_units>0:
                        max_held=4 if animal=="GOOSE" else 6
                        if y_units>=1:
                            tasks.append((harvest_prio_a, y,x, "HARVEST", None))
            # else ignore
    # Staggered planting/building: limit to 3 per day, nearest to farmer
    # Prioritize filling board but evenly
    # stop planting crops that won't mature before season end (720 steps = day29)
    # wheat needs 4 days, melon 12, strawberry 10
    can_plant_wheat = day <= 26
    can_plant_melon = day <= 18
    can_plant_straw = day <= 20
    has_seeds = ( (seeds.get("WHEAT",0)>0 and can_plant_wheat) or (seeds.get("MELON",0)>0 and can_plant_melon) or (seeds.get("STRAWBERRY",0)>0 and can_plant_straw))
    if empty_positions and has_seeds and plant_tiles < max_plants_allowed and day < 27:
        empty_positions_sorted = sorted(empty_positions, key=lambda p: manhattan(farmer_pos, p))
        # 60/75 as in replay: 8/turn after day10 with 11 hands
        limit = 8 if day>=10 else 3
        remaining = max_plants_allowed - plant_tiles
        limit = min(limit, remaining, len(empty_positions_sorted))
        for (x,y) in empty_positions_sorted[:limit]:
            melon_price = prices.get("MELON",250)
            melon_tiles = sum(1 for row in tiles for t in row if isinstance(t,dict) and t.get("crop")=="MELON")
            straw_tiles = sum(1 for row in tiles for t in row if isinstance(t,dict) and t.get("crop")=="STRAWBERRY")
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
    # if need coops, add build tasks for empty tiles (money>35)
    if coops_total < target_coops and empty_positions and money>35:
        empty_sorted = sorted(empty_positions, key=lambda p: manhattan(farmer_pos, p))
        candidates = empty_sorted[3:] if len(empty_sorted)>3 else []
        if candidates:
            x,y = candidates[0]
            tasks.append((7, y,x, "BUILD_COOP", None))

    farmer_total = sum(farmer_inv.values()) if farmer_inv else 0
    shed_adj = SHED_TILES

    # Sort tasks by priority then by distance to farmer (deterministic)
    # For multi-unit, we will assign greedily
    # First, sort by priority
    tasks_sorted = sorted(tasks, key=lambda e: (e[0], e[1], e[2]))

    def choose_action(fx,fy, inv, is_farmer):
        inv_sum = sum(inv.values()) if inv else 0
        if is_farmer and coops_empty>0 and shed.get("GOOSE",0)>0 and inv.get("GOOSE",0)==0:
            if is_shed_adjacent(fx,fy, board_size):
                return ["PICKUP","GOOSE",1]
            else:
                best=None
                bestd=10**9
                for sx,sy in SHED_TILES:
                    d=manhattan((fx,fy),(sx,sy))
                    if d<bestd:
                        bestd=d
                        best=(sx,sy)
                if best:
                    return [next_step_toward(fx,fy,best[0],best[1],board_size)]
        if is_shed_adjacent(fx,fy, board_size) and inv_sum>0:
            if inv.get("GOOSE",0)>0 and coops_empty>0:
                pass
            else:
                return ["DROP"]
        # Global priority: find highest priority feasible task
        for prio_level in [1,2,3,4,5,6,7,8]:
            cands=[t for t in tasks_sorted if t[0]==prio_level]
            filt=[]
            for _,ty,tx,act,detail in cands:
                if act=="PLACE_GOOSE" and inv.get("GOOSE",0)==0:
                    continue
                if act=="PLANT":
                    if detail=="WHEAT" and seeds.get("WHEAT",0)==0:
                        continue
                    if detail=="MELON" and seeds.get("MELON",0)==0:
                        continue
                    if detail=="STRAWBERRY" and seeds.get("STRAWBERRY",0)==0:
                        continue
                if act=="FERTILIZE" and fertil_available==0:
                    continue
                filt.append((ty,tx,act,detail))
            if not filt:
                continue
            for ty,tx,act,detail in filt:
                if tx==fx and ty==fy:
                    if act=="WATER": return ["WATER"]
                    if act=="FEED": return ["FEED"]
                    if act=="COLLECT_FERTILIZER": return ["COLLECT_FERTILIZER"]
                    if act=="CARE": return ["CARE"]
                    if act=="HARVEST": return ["HARVEST"]
                    if act=="DIG": return ["DIG"]
                    if act=="FERTILIZE": return ["FERTILIZE"]
                    if act=="PLANT": return ["PLANT", detail]
                    if act=="BUILD_COOP": return ["BUILD_COOP"]
                    if act=="PLACE_GOOSE": return ["PLACE","GOOSE",1]
            best=None
            bestd=10**9
            for ty,tx,act,detail in filt:
                d=manhattan((fx,fy),(tx,ty))
                if d<bestd:
                    bestd=d
                    best=(tx,ty)
            if best:
                return [next_step_toward(fx,fy,best[0],best[1],board_size)]
            break
        # no feasible tasks
        if inv_sum>0:
            best=None
            bestd=10**9
            for sx,sy in SHED_TILES:
                d=manhattan((fx,fy),(sx,sy))
                if d<bestd:
                    bestd=d
                    best=(sx,sy)
            if best:
                return [next_step_toward(fx,fy,best[0],best[1],board_size)]
        return ["PASS"]

    # Farmer action
    farmer_inv_dict = farmer_inv if isinstance(farmer_inv,dict) else {}
    fx,fy = farmer_pos[0], farmer_pos[1]
    farmer_action = choose_action(fx,fy, farmer_inv_dict, True)

    # Hands actions
    hands_actions=[]
    for idx, pos in enumerate(hands_pos):
        hx,hy = pos[0], pos[1]
        inv = inventories[idx+1] if len(inventories)>idx+1 and isinstance(inventories[idx+1],dict) else {}
        # simple: hands don't pickup geese (farmer does), they focus on field work
        act=choose_action(hx,hy, inv, False)
        # hands at shed with inventory -> DROP
        if is_shed_adjacent(hx,hy, board_size) and sum(inv.values())>0 and act!=["DROP"]:
            act=["DROP"]
        hands_actions.append(act)

    # Special building: if no coops and we want to build one, handle BUILD_COOP
    # This is low priority; but if farmer is on empty tile and we target coops < target, build
    # Check if farmer_action is PLANT but we need coops -> override occasionally
    # Count if farmer on empty tile and coops_total < target_coops and money>100
    # Then BUILD_COOP instead of PLANT every 3rd empty task
    # building now handled via task priority 7

    return {"farmer": farmer_action, "hands": hands_actions, "market": market_ops}
