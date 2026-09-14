"""core/market_model.py — PriceEngine (docs/README.md:208-214)"""
import math
# f functions as per docs/README.md:213
def _f(name, x, T):
    if name=="linear":
        return x/T if T else 0
    if name=="sq":
        return (x/T)**2 if T else 0
    if name=="sqrt":
        return math.sqrt(x/T) if T and x>=0 else 0
    if name=="log":
        return math.log(1+x)/math.log(1+T) if T else 0
    if name=="hinge":
        u=x/T if T else 0
        return u + 8*max(0, u-1)**2
    return 0

def price_for(inv, params):
    base=params["base"]; I0=params["I0"]; T=params["T"]
    if inv < I0:
        f=_f(params["below_func"], I0-inv, T)
        amp=params["below_target"]*base / max(1e-9, _f(params["below_func"], T, T))
        return max(1, round(base + amp*f))
    elif inv > I0:
        f=_f(params["above_func"], inv-I0, T)
        amp=params["above_target"]*base / max(1e-9, _f(params["above_func"], T, T))
        return max(1, round(base - amp*f))
    return base
