import sys; sys.path.insert(0,'/workspace')
import numpy as np
from world import World, ACTIVE, READY
from coordinators import DummyCoordinator
NO_CALVES=(1.0,0,0)
w = World(seed=0, n_cows=1, wolves_min=1, wolves_max=1, calf_count_probs=NO_CALVES)
c = DummyCoordinator(w.n_drones)
P = np.array([80.0, 150.0]); w.cows[0]=P.copy(); w.cow_vel[0]=0; w.cow_speeds[0]=0
w.phase="ESCOLTA"; w.pack_prey, w.pack_prey_kind = 0,"adult"
w.wolves[0]=np.array([150.0,150.0]); w.wolf_vel[0]=0
A,B=np.array([120.0,140.0]),np.array([120.0,160.0])
def set_line():
    w.drone_state[:]=READY; w.drones[:]=np.array([1e4,1e4]); w.drone_vel[:]=0
    w.drone_state[0]=ACTIVE; w.drones[0]=A.copy(); w.drone_state[1]=ACTIVE; w.drones[1]=B.copy(); w.drone_waypoint[:]=w.drones
def seg_cross(p1,p2,a,b):
    d1,d2=p2-p1,b-a; den=d1[0]*d2[1]-d1[1]*d2[0]
    if abs(den)<1e-12: return False
    t=((a[0]-p1[0])*d2[1]-(a[1]-p1[1])*d2[0])/den; u=((a[0]-p1[0])*d1[1]-(a[1]-p1[1])*d1[0])/den
    return 0<=t<=1 and 0<=u<=1
set_line()
for k in range(300):
    w.pack_prey, w.pack_prey_kind=0,"adult"; w.cows[0]=P.copy(); w.cow_vel[0]=0
    set_line(); prev=w.wolves[0].copy()
    w.step(c.act(None))
    dA=np.linalg.norm(w.wolves[0]-A); dB=np.linalg.norm(w.wolves[0]-B)
    cr = seg_cross(prev,w.wolves[0],A,B)
    if k<3 or 20<=k<=95 or cr:
        print(k, np.round(w.wolves[0],2), "v", np.round(w.wolf_vel[0],2), "dA %.1f dB %.1f"%(dA,dB), "scared", bool(w._wolf_scared[0]), "walled", bool(w._wolf_walled[0]), "CROSS" if cr else "", flush=True)
    if cr: break
