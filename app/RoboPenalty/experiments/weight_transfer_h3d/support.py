"""Native contact forces and geometric support diagnostics; no control writes."""
import numpy as np
import mujoco

# Own measured material point from the passive H3B shin contact, not a new collider.
POINT_LOCAL=np.array([-.03184939016857404,-.024461886444184944,-.08459957767800226])

def hull(points):
    pts=sorted(set(map(tuple,np.asarray(points).reshape(-1,2))))
    if len(pts)<3:return np.asarray(pts)
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    a=[]
    for p in pts:
        while len(a)>=2 and cross(a[-2],a[-1],p)<=0:a.pop()
        a.append(p)
    b=[]
    for p in pts[::-1]:
        while len(b)>=2 and cross(b[-2],b[-1],p)<=0:b.pop()
        b.append(p)
    return np.array(a[:-1]+b[:-1])

def margin(p,poly):
    if len(poly)<3:return None
    values=[]
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        v=b-a;values.append((v[0]*(p[1]-a[1])-v[1]*(p[0]-a[0]))/np.linalg.norm(v))
    return float(min(values))

class Support:
    def __init__(self,m,k):
        self.m=m;self.k=k;self.floor=m.geom('floor').id;self.patch=m.geom('gk/geom_025').id
        self.feet=[{g for g in k.foot_geoms if m.body(int(m.geom_bodyid[g])).name.startswith('gk/'+side)} for side in ('left','right')]
        self.mass=float(sum(m.body_mass[b] for b in k.bodies));self.weight=self.mass*abs(float(m.opt.gravity[2]))

    def sample(self,d,t):
        m=self.m;forces=np.zeros((2,3));contacts=[];points=[];weighted=np.zeros(2);fzsum=0.;maxpen=0.;unexpected=[]
        for i,c in enumerate(d.contact):
            a,b=map(int,c.geom)
            if a not in self.k.geoms and b not in self.k.geoms:continue
            maxpen=max(maxpen,max(0.,-float(c.dist)));f=np.zeros(6);mujoco.mj_contactForce(m,d,i,f)
            if f[0]<=.001:continue
            kg=a if a in self.k.geoms else b;other=b if kg==a else a
            world=c.frame.reshape(3,3).T@f[:3]*(1 if kg==b else -1)
            side=next((s for s,geoms in enumerate(self.feet) if kg in geoms),None)
            if other==self.floor and side is not None:
                forces[side]+=world
                if world[2]>1.:
                    points.append(c.pos[:2].copy());weighted+=c.pos[:2]*world[2];fzsum+=world[2]
            else:unexpected.append(dict(t=t,geoms=[m.geom(a).name,m.geom(b).name],force_n=float(f[0])))
            contacts.append(dict(t=t,geoms=[m.geom(a).name,m.geom(b).name],side=side,position=c.pos.copy(),gap_m=float(c.dist),normal_n=float(f[0]),force_on_keeper_w=world))
        poly=hull(points) if points else np.empty((0,2));com=d.subtree_com[self.k.pelvis].copy()
        clearance=[]
        for side in self.feet:
            spheres=[g for g in side if m.geom_type[g]==mujoco.mjtGeom.mjGEOM_SPHERE and m.geom_contype[g]]
            clearance.append(min(float(d.geom_xpos[g,2]-m.geom_size[g,0]) for g in spheres))
        return dict(t=t,forces=forces,load=forces[:,2].copy(),right_share=float(forces[1,2]/forces[:,2].sum()) if forces[:,2].sum()>1 else None,
            com=com,cop=weighted/fzsum if fzsum>1 else np.array([np.nan,np.nan]),support_polygon=poly,com_margin_m=margin(com[:2],poly),
            point=d.geom_xpos[self.patch]+d.geom_xmat[self.patch].reshape(3,3)@POINT_LOCAL,
            knee=d.xpos[m.body('gk/right_knee_link').id].copy(),ankle=d.xpos[m.body('gk/right_ankle_roll_link').id].copy(),
            clearance=np.array(clearance),maxpen=maxpen,contacts=contacts,unexpected=unexpected)
