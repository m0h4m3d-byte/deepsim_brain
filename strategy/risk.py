"""strategy/risk.py — RiskManager (shed cap 100, cash buffer)"""
def can_buy_land(money, cost, utilization):
    return money > cost + 1500 and utilization > 0.5

def force_sell(total_shed):
    return total_shed >= 85
