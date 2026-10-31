"""Read-only geometry and post-step motor observations. No actuator ownership."""
import numpy as np
import mujoco


def arm_geoms(model,keeper):
    return [g for g in sorted(keeper.geoms)
            if any(s in model.body(int(model.geom_bodyid[g])).name for s in ('elbow','wrist'))
            and (model.geom_contype[g] or model.geom_conaffinity[g])]


def envelope(model,data,geoms):
    lows=[];highs=[]
    for g in geoms:
        rotation=data.geom_xmat[g].reshape(3,3)
        center=data.geom_xpos[g]+rotation@model.geom_aabb[g,:3]
        extent=abs(rotation)@model.geom_aabb[g,3:]
        lows.append(center-extent);highs.append(center+extent)
    return dict(lower=np.min(lows,axis=0).tolist(),upper=np.max(highs,axis=0).tolist(),
                meaning='Conservative collision AABB envelope, not proof of reachable contact')


class MotorMonitor:
    def __init__(self,m,keeper,rail,caps):
        self.m,self.k,self.rail,self.caps=m,keeper,rail,np.asarray(caps)
        self.rows=[];self.streak=np.zeros(29);self.longest=np.zeros(29);self.peak=np.zeros(29)
        self.contacts=[];self.counter=0;self.peak_speed=0.;self.range_error=0.;self.pelvis_error=0.
        self.ball_contacts=[];self.ball_geom=m.geom('ball_geom').id

    def sample(self,d,reference,reference_velocity,torque):
        m,k=self.m,self.k;q=d.qpos[k.qpos];v=d.qvel[k.dofs];actual=d.qfrc_actuator[k.dofs]
        self.peak=np.maximum(self.peak,abs(actual))
        self.streak=np.where(abs(actual)>=.98*self.caps,self.streak+m.opt.timestep,0)
        self.longest=np.maximum(self.longest,self.streak)
        self.peak_speed=max(self.peak_speed,float(abs(v).max()))
        ranges=m.jnt_range[k.joints]
        self.range_error=max(self.range_error,float(np.maximum(ranges[:,0]-q,q-ranges[:,1]).max()))
        self.pelvis_error=max(self.pelvis_error,float(abs(d.xpos[k.pelvis]-(d.xpos[self.rail.carriage]+[0,0,.793])).max()))
        selfpairs=[]
        for contact_index,c in enumerate(d.contact[:d.ncon]):
            a,b=int(c.geom1),int(c.geom2)
            if a in k.geoms and b in k.geoms:
                selfpairs.append(dict(geoms=[m.geom(a).name,m.geom(b).name],distance_m=float(c.dist)))
            if (a==self.ball_geom and b in k.geoms) or (b==self.ball_geom and a in k.geoms):
                force=np.zeros(6);mujoco.mj_contactForce(m,d,contact_index,force)
                self.ball_contacts.append(dict(time_s=float(d.time),geom=m.geom(b if a==self.ball_geom else a).name,
                    distance_m=float(c.dist),normal_force_n=float(force[0])))
        if selfpairs:self.contacts.append(dict(time_s=float(d.time),pairs=selfpairs))
        if self.counter%10==0:
            self.rows.append(dict(time_s=float(d.time),q_rad=q.tolist(),v_rad_s=v.tolist(),
                reference_rad=reference.tolist(),reference_velocity_rad_s=reference_velocity.tolist(),
                commanded_torque_nm=np.asarray(torque).tolist(),actual_torque_nm=actual.tolist(),
                rail_q_m=float(d.qpos[self.rail.qpos]),rail_v_mps=float(d.qvel[self.rail.dof]),
                arms_envelope=envelope(m,d,arm_geoms(m,k)),
                min_ball_arm_surface_distance_m=min(float(mujoco.mj_geomDistance(m,d,self.ball_geom,int(g),100.,None)) for g in arm_geoms(m,k)),
                wrists={side:d.xpos[m.body('gk/'+side+'_wrist_yaw_link').id].tolist() for side in ('left','right')}))
        self.counter+=1

    def summary(self):
        return dict(rows=self.rows,effective_caps_nm=self.caps.tolist(),peak_actual_nm=self.peak.tolist(),
            saturation_longest_s=self.longest.tolist(),persistent_saturation=bool((self.longest>=.1).any()),
            saturation_definition='>=98% effective torque cap for at least 0.1 continuous simulated seconds',
            self_contacts=self.contacts,peak_speed_rad_s=self.peak_speed,joint_range_violation_rad=self.range_error,
            ball_contacts=self.ball_contacts,
            pelvis_error_m=self.pelvis_error,torques_within_caps=bool((self.peak<=self.caps+1e-6).all()))
