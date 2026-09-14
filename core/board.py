"""core/board.py — BoardModel (docs/README.md:149, docs/AGENTS.md:43)"""
def is_shed_adjacent(x,y, board_size=10):
    half=board_size//2
    return (x,y) in [(half-1,half-1),(half,half-1),(half-1,half),(half,half)]

def manhattan(a,b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])

def next_step_toward(fx,fy, tx,ty, board_size=10):
    best=None
    bestd=10**9
    for dx,dy,op in [(0,-1,"NORTH"),(0,1,"SOUTH"),(1,0,"EAST"),(-1,0,"WEST")]:
        nx,ny=fx+dx,fy+dy
        if 0 <= nx < board_size and 0 <= ny < board_size:
            d=abs(nx-tx)+abs(ny-ty)
            if d < bestd:
                bestd=d
                best=op
    if best and manhattan((fx,fy),(tx,ty))>0:
        return best
    return "PASS"
