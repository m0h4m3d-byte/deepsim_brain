"""core/economy.py — TownDemandForecast (docs/README.md:171, docs/AGENTS.md:22)"""
def expected_daily_demand(unlocked_shops):
    # 6 ticks/day per shop + 1 town center
    # Returns dict product->demand per day (approx)
    base = {"WHEAT":1,"CARROT":1,"TOMATO":1,"STRAWBERRY":1,"MELON":1,"EGG":1,"MILK":1,"WOOL":1}
    # count shops
    from collections import Counter
    cnt=Counter(unlocked_shops)
    # mapping shop->products
    shop_map={
        "BAKERY":["EGG","WHEAT"],
        "PIZZA_SHOP":["MILK","TOMATO","WHEAT"],
        "BRUNCH_SPOT":["EGG","WHEAT","STRAWBERRY"],
        "YARN_STORE":["WOOL"],
        "ICE_CREAM_SHOP":["STRAWBERRY","MILK","WHEAT"],
        "PET_CAFE":["CARROT"],
        "SMOOTHIE_SHOP":["STRAWBERRY","MILK"],
        "FARMERS_MARKET":["WHEAT","CARROT","TOMATO","STRAWBERRY"],
        "BAKERY":["EGG","WHEAT"],
    }
    demand=dict(base)
    for shop, n in cnt.items():
        key=shop.upper()
        prods=shop_map.get(key, [])
        mult=2 if key in ("YARN_STORE","PET_CAFE") else 1
        for p in prods:
            demand[p]=demand.get(p,0)+ n*6*mult
    return demand
