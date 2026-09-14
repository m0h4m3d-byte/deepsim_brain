"""core/state.py — StateParser (docs/AGENTS.md:35-38)"""
def parse_obs(obs):
    player = obs.get("player",0)
    day = obs.get("day", obs.get("step",0)//24)
    hour = obs.get("hour", obs.get("step",0)%24)
    farms = obs.get("farms",[])
    private = obs.get("private",{})
    market = obs.get("market",{})
    town = obs.get("town",{})
    return player, day, hour, farms, private, market, town
