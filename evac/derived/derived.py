""" For computing derived variables from existing fields.

TODO: steal a lot of these from WRFOut.
TODO: there might be some overlap from stats.
"""

def cold_pool_strength(self,X,time,swath_width=100,env=0,dz=0):
    """
    Returns array the same shape as WRF domain.

    Args:
        X   :   cross-section object with given path
                    This path goes front-to-back through a bow
        km  :   width in the line-normal direction
        env :   (x,y) for location to sample environmental dpt
    """

    # Set up slices
    tidx = self.get_time_idx(time)
    lvidx = False
    lonidx = False
    latidx = False

    # Get wind data
    wind10 = self.get('wind10',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    T2 = self.get('T2',tidx,lvidx,lonidx,latidx)[0,0,:,:]

    # This is the 2D plane for calculation data
    coldpooldata = N.zeros(wind10.shape)

    # Compute required C2 fields to save time
    dpt = self.get('dpt',tidx,lvidx,lonidx,latidx)[0,:,:,:]
    Z = self.get('Z',tidx,lvidx,lonidx,latidx)[0,:,:,:]
    HGT = self.get('HGT',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    heights = Z-HGT
    # pdb.set_trace()

    if isinstance(env,collections.Sequence):
        xx_env = N.arange(env[0]-2,env[0]+3)
        yy_env = N.arange(env[1]-2,env[1]+3)
        dpt_env = N.mean(dpt[:,yy_env,xx_env],axis=1)

    # All cross-sections (parallel)

    # xxx = [X.xx,]
    # yyy = [X.yy,]
    X.translate_xs(-swath_width/2)
    for n in range(swath_width):
        print(("Cross section #{0}".format(n)))
    # for xx, yy in zip(xxx, yyy):
        X.translate_xs(1)
        xx = X.xx
        yy = X.yy
        xx = xx.astype(int)
        yy = yy.astype(int)
        wind_slice = wind10[yy,xx]
        T2_slice = T2[yy,xx]
        slice_loc = self.find_gust_front(wind_slice,T2_slice,X.angle)

        gfx = xx[slice_loc]
        gfy = yy[slice_loc]
        gf_pts = N.intersect1d(N.where(xx==gfx)[0],N.where(yy==gfy)[0])
        gf_pt = gf_pts[int(len(gf_pts)/2.0)]
        xx_cp = xx[:gf_pt]
        yy_cp = yy[:gf_pt]
        # pdb.set_trace()

        # Compute enviromental dpt at each height
        # Average all levels from the location of gust front
        # forwards to the end of the cross-section.
        if not env:
            xx_env = xx[gf_pt+1:]
            yy_env = yy[gf_pt+1:]
            dpt_env = N.mean(dpt[:,yy_env,xx_env],axis=1)
        # pdb.set_trace()

        for x,y in zip(xx_cp,yy_cp):
        #for x,y in zip(xx,yy):
            if dz:
                coldpooldata[y,x] = self.compute_cpdz(x,y,dpt[:,y,x],heights[:,y,x],dpt_env)
                # pdb.set_trace()
            else:
                coldpooldata[y,x] = N.sqrt(self.compute_C2(x,y,dpt[:,y,x],heights[:,y,x],dpt_env))

    return coldpooldata

def compute_cpdz(self,x,y,dpt,heights,dpt_env):
    """
    Cold pool depth

    Args:
        x       :   x location in domain
        y       :   y location in domain
        dpt     :   density potential temperature slice
        heights :   height AGL slice
        dpt_env :   environmental dpt, column
    """

    dz, zidx = self.cold_pool_depth(dpt,heights,dpt_env)
    # import pdb; pdb.set_trace()
    return dz

def compute_C2(self,x,y,dpt,heights,dpt_env):
    """
    C^2 as found in James et al. 2006 MWR

    Args:
        x       :   x location in domain
        y       :   y location in domain
        dpt     :   density potential temperature slice
        heights :   height AGL slice
        dpt_env :   environmental dpt, column
    """

    dz, zidx = self.cold_pool_depth(dpt,heights,dpt_env)
    C2 = -2*mc.g*((dpt[zidx]-dpt_env[zidx])/dpt_env[zidx])*dz
    # print("dpt = {0} ... dpt_env = {1} ... C2 = {2}".format(dpt[0],dpt_env[0],C2))
    return C2

def cold_pool_depth(self,dpt,heights,dpt_env):
    dz = 0
    # thresh = -2.0
    thresh = -1.0
    for d,z, de in zip(dpt[1:],heights[1:],dpt_env[1:]):
        dptp = d - de
        if dptp > thresh:
            break
        dz = z

    if isinstance(dz,float):
        zidx = N.where(heights==dz)[0]
    else:
        zidx = 0
    # import pdb; pdb.set_trace()
    return dz, zidx

def find_gust_front(self,wind_slice,T2_slice,angle,method=3):
    """
    Find location of maximum shear in the horizontal wind along a
    1D slice.

    Args:
        wind_slice      :   1D numpy array
        T2_slice        :   temp 2m slice
        angle           :   angle of slice cross-section
        method          :   way to locate gust front
    """

    shp = wind_slice.shape

    # Compute gradient quantities
    shear = N.zeros(shp)
    T2grad = N.zeros(shp)

    for n in range(shp[0]):
        if n == 0 or n == shp[0]-1:
            shear[n] = 0
        else:
            len1 = abs(self.dx / N.sin(angle))
            len2 = abs(self.dx / N.cos(angle))
            hyp = min((len1,len2))
            # In kilometres:
            shear[n] = ((wind_slice[n+1]-wind_slice[n-1])/(2*hyp))*1000.0
            T2grad[n] = ((T2_slice[n+1]-T2_slice[n-1])/(2*hyp))*1000.0
            # N.W.DX

    # pdb.set_trace()

    # Go from B to A
    # Find first location where T2 drops and shear is ?

    if method==1:
        ### METHOD 1: USING THRESHOLDS
        # By default
        gfidx = shp/2
        for n, s, t in zip(list(range(shp))[::-1],shear[::-1],T2grad[::-1]):
            if (abs(s)>2.0) and (t<2.0):
                gfidx = n
                break

    elif method==2 or method==3:

        ### METHOD 2: FINDING MAX GRADIENTS AND AVERAGING
        shear = abs(shear)
        T2grad = abs(T2grad)

        xsh_idx = N.where(shear == shear.max())[0][0]
        xtg_idx = N.where(T2grad == T2grad.max())[0][0]
        print(("Max shear loc: {0} ... max tempgrad loc: {1}".format(xsh_idx,xtg_idx)))

        if method==2:
            gfidx = int((xsh_idx + xtg_idx)/2.0)
        else:
            gfidx = max([xsh_idx,xtg_idx])

    return gfidx
    # maxshearloc[0][0] returns the integer

def compute_frontogenesis(self,time,level):
    """
    Note that all variables fetched with self.get have been
    destaggered and are at the same location.

    Returns:
        Front       :   Frontgenesis in Kelvin per second.
    """
    # import pdb; pdb.set_trace()
    #ds = 1 # Number of grid point to compute horizontal gradient over
    #dx = ds
    #dy = ds
    #dz = 1 # Normal for vertical
    tidx = self.get_time_idx(time)
    tidxs = (tidx-1,tidx,tidx+1)

    if (tidx == 0) or (tidx == self.wrf_times.shape[0]-1):
        Front = None
    else:
        nt,nl,ny,nx = self.get('U',utc=tidx,level=1).shape
        U = N.zeros([3,3,ny,nx])
        V = N.zeros_like(U)
        W = N.zeros_like(U)
        T = N.zeros_like(U)
        if level == 2000:
            # Use the bottom three model levels
            P = N.zeros_like(U)
            for n, t in enumerate(tidxs):
                U[n,...] = self.get('U',utc=t,level=1)
                V[n,...] = self.get('V',utc=t,level=1)
                W[n,...] = self.get('W',utc=t,level=1)
                T[n,...] = self.get('T',utc=t,level=N.arange(3))
                P[n,...] = self.get('pressure',utc=t,level=N.arange(3))
                # Average different in pressure between model levels
                # This field is passed into the gradient
                # THIS IS NOT USED RIGHT NOW
                dp = N.average(abs(0.5*(0.5*(P[2,2,:,:]-P[2,0,:,:]) +
                            0.5*(P[0,2,:,:]-P[0,0,:,:]))))

        elif isinstance(level,int):
            dp = 15 # hPa to compute vertical gradients

            for n, t in enumerate(tidxs):
                U[n,...] = self.get_p('U',t,level)
                V[n,...] = self.get_p('V',t,level)
                W[n,...] = self.get_p('W',t,level)

                # 3D array has dimensions (vertical, horz, horz)
                T[n,...] = self.get_p('T',t,(level-dp,level,level+dp))

                # Compute omega
                # P = rho* R* drybulb
                # drybulb = T/((P0/P)^(R/cp)

        drybulb = 273.15 + (T/((100000.0/(level*100.0))**(mc.R/mc.cp)))
        rho = (level*100.0)/(mc.R*drybulb)
        omega = -rho * mc.g * W

        # Time difference in sec
        dt = self.utc[tidx+1]-self.utc[tidx]
        dTdt, dTdz, dTdy, dTdx = N.gradient(T,dt,dp*100.0,self.dy, self.dx)
        # Gradient part
        grad = (dTdx**2 + dTdy**2)**0.5
        # Full derivative - value wrong for dgraddz here
        dgraddt, dgraddz, dgraddy, dgraddx = N.gradient(grad,dt,dp*100.0,self.dy, self.dx)
        # Full equation
        Front = dgraddt[1,1,:,:] + U[1,1,:,:]*dgraddx[1,1,:,:] + V[1,1,:,:]*dgraddy[1,1,:,:] # + omega[1,1,:,:]*dgraddz[1,1,:,:]
    return Front

def compute_accum_rain(self,utc,accum_hr):
    """
    Needs to be expanded to include other precip
    """
    dn = utils.ensure_datenum(utc)
    idx0 = self.get_time_idx(dn-(3600*accum_hr))
    idx1 = self.get_time_idx(dn)
    # range_idx = range(start_idx,end_idx+1)
    total0 = (self.get('RAINNC',utc=idx0) +
                self.get('RAINC',utc=idx0))
    total1 = (self.get('RAINNC',utc=idx1) +
                self.get('RAINC',utc=idx1))
    accum = total1 - total0
    return accum

def compute_satvappres(self,tidx,lvidx,lonidx,latidx,other):
    t = self.get('drybulb',utc=tidx,level=lvidx,lons=lonidx,lats=latidx,other='C')
    es = 6.1*N.exp(0.073*t)
    return es

def compute_vappres(self,tidx,lvidx,lonidx,latidx,other):
    RH = self.get('RH',utc=tidx,level=lvidx,lons=lonidx,lats=latidx)
    es = self.get('es',utc=tidx,level=lvidx,lons=lonidx,lats=latidx)
    e = RH*es
    return e

def compute_spechum(self,tidx,lvidx,lonidx,latidx,other):
    es = self.get('es',utc=tidx,level=lvidx,lons=lonidx,lats=latidx)
    p = self.get('pressure',utc=tidx,level=lvidx,lons=lonidx,lats=latidx)
    q = 0.622*(es/p)
    return q

def compute_Td_2(self,tidx,lvidx,lonidx,latidx,other='C'):
    """
    Another version of Td
    From p70 Djuric Weather Analysis
    """
    e = self.get('e',utc=tidx,level=lvidx,lons=lonidx,lats=latidx)
    Td = 273*((N.log(e) - N.log(6.1))/(19.8 - (N.log(e) - N.log(6.1))))
    if other == 'K':
        Td =+ 273.15
    return Td

def compute_derivatives(self,U,V,axis=None):
    dargs = (self.dx,self.dx)
    dkwargs = {'axis':None}
    if len(U.shape) == 2:
        dudx, dudy = N.gradient(U,self.dx,self.dx)
        dvdx, dvdy = N.gradient(V,self.dx,self.dx)
    elif len(U.shape) == 3:
        nt = U.shape[0]
        dudx = N.zeros_like(U)
        dvdx = N.zeros_like(U)
        dudy = N.zeros_like(U)
        dvdy = N.zeros_like(U)
        for t in range(nt):
            dudx[t,...], dudy[t,...] = N.gradient(U[t,...],self.dx,self.dx)
            dvdx[t,...], dvdy[t,...] = N.gradient(V[t,...],self.dx,self.dx)
    return dudx, dudy, dvdx, dvdy

def compute_stretch_deformation(self,U,V):
    dudx, dudy, dvdx, dvdy = self.compute_derivatives(U,V)
    Est = dudx - dvdy
    return Est

def compute_shear_deformation(self,U,V):
    dudx, dudy, dvdx, dvdy = self.compute_derivatives(U,V)
    Esh = dudy + dvdx
    return Esh

def compute_total_deformation(self,U,V):
    Esh = self.compute_shear_deformation(U,V)
    Est = self.compute_stretch_deformation(U,V)
    E = (Est**2 + Esh**2)**0.5
    return E

def compute_vorticity(self,U,V):
    # Axis = 1 for vertical vorticity, if there's no time selected?
    dudx, dudy, dvdx, dvdy = self.compute_derivatives(U,V,)#axis=1)
    zeta = dvdx - dudy
    return zeta

def return_vorticity(self,tidx,lvidx,lonidx,latidx,other):
    # pdb.set_trace()
    U = self.get('U',tidx,lvidx,lonidx,latidx)[:,0,:,:]
    V = self.get('V',tidx,lvidx,lonidx,latidx)[:,0,:,:]
    zeta = self.compute_vorticity(U,V)
    return zeta

def compute_fluid_trapping_diagnostic(self,tidx,lvidx,lonidx,latidx,other):
    U = self.get('U10',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    V = self.get('V10',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    E = self.compute_total_deformation(U,V)
    zeta = self.compute_vorticity(U,V)
    omega2 = 0.25*(E**2 - zeta**2)
    return omega2

def compute_divergence(self,U,V):
    dudx, dudy, dvdx, dvdy = self.compute_derivatives(U,V)
    div = dudx + dvdy
    return div

def compute_instantaneous_local_Lyapunov(self,tidx,lvidx,lonidx,latidx,other):
    # import pdb; pdb.set_trace()
    U = self.get('U',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    V = self.get('V',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    E = self.compute_total_deformation(U,V)
    zeta = self.compute_vorticity(U,V)
    div = self.compute_divergence(U,V)
    EzArr = (E**2  - zeta**2)**0.5
    Ez_nonan = N.nan_to_num(EzArr)
    # D =  0.5*(div + (E**2  - zeta**2)**0.5)
    D =  0.5*(div + Ez_nonan)
    # import pdb; pdb.set_trace()
    return D

def return_axis_of_dilatation_components(self,tidx,lvidx=False,lonidx=False,
                                            latidx=False,other=False):
    U = self.get('U10',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    V = self.get('V10',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    Esh = self.compute_shear_deformation(U,V)
    Est = self.compute_stretch_deformation(U,V)
    E = self.compute_total_deformation(U,V)
    zeta = self.compute_vorticity(U,V)

    psi1 = 0.5 * N.arctan2(Esh,Est)
    # chi1 = psi1 + 0.5*N.nan_to_num(N.arcsin(zeta/E))
    chi1 = psi1 + 0.5*(N.arcsin(zeta/E))

    return N.cos(chi1), N.sin(chi1)

def compute_omega(self,tidx,lvidx,lonidx,latidx,other):
    # Rising motion in Pa/s
    # dp/dt of air parcel
    W = self.get('W',tidx,lvidx,lonidx,latidx)[0,:,:,:]
    rho = self.get('density',tidx,lvidx,lonidx,latidx)[0,:,:,:]
    omega = -rho * -mc.g * W # I think it's meant to be minus g?
    # import pdb; pdb.set_trace()
    return omega

def compute_density(self,tidx,lvidx,lonidx,latidx,other):
    drybulb = self.get('drybulb',tidx,lvidx,lonidx,latidx,other='K')
    P = self.get('pressure',tidx,lvidx,lonidx,latidx)
    rho = P/(mc.R*drybulb)
    # drybulb = 273.15 + (T/((100000.0/(level*100.0))**(mc.R/mc.cp)))
    return rho

def compute_CAPE(self,tidx,lvidx,lonidx,latidx,other):
    """
    INCOMPLETE!

    CAPE method based on GEMPAK's pdsuml.f function

    Inputs:

    tidx,lvidx,lonidx,latidx  :   dictionary of level/time/lat/lon



    Outputs:
    CAPE    :   convective available potential energy
    CIN     :   convective inhibition
    """
    # Make sure all levels are obtained
    #tidx,lvidx,lonidx,latidx['lv'] = slice(None,None)

    totalCAPE = 0
    totalCIN = 0

    theta = self.get('theta',tidx,lvidx,lonidx,latidx)
    Z = self.get('Z',tidx,lvidx,lonidx,latidx)

    for lvidx in range(theta.shape[1]-1):
        if lvidx < 20:
            continue
        # This should loop over the levels?
        """
        z1      :   bottom of layer (index)
        z2      :   top of layer (index)
        th1     :   theta (environ) at z1
        th2     :   theta (environ) at z2
        thp1    :   theta (parcel) at z1
        thp2    :   theta (parcel) at z2
        """

        z1 = Z[0,lvidx,...]
        z2 = Z[0,lvidx+1,...]

        th1 = theta[0,lvidx,...]
        th2 = theta[0,lvidx+1,...]

        thp1 = 0
        thp2 = 0

        capeT = 0.0
        cinT = 0.0

        dt2 = thp2 - th2
        dt1 = thp1 - th1

        dz = z2 - z1

        dt1_pos_ma = N.ma.masked_greater(dt1,0)
        dt1_neg_ma = N.ma.masked_less(dt1,0)

        dt2_pos_ma = N.ma.masked_greater(dt2,0)
        dt2_neg_ma = N.ma.masked_less(dt2,0)

        dt1_pos = N.select([dt1>0],[dt1])
        dt1_neg = N.select([dt1<0],[dt1])
        dt2_pos = N.select([dt2>0],[dt1])
        dt2_neg = N.select([dt2<0],[dt1])

        pdb.set_trace()

        if (dt1 > 0) and (dt2 > 0):
            capeT = ((dt2 + dt1)*dz)/(th2+th1)
        elif dt1 > 0:
            ratio = dt1/(dt1-dt2)
            zeq = z1 + (dz*ratio)
            teq = th1 + ((th2-th1)*ratio)
            capeT = (dt1*(zeq-z1))/(th1+teq)
            cinT = (dt2*(z2-zeq))/(th2+teq)
        elif dt2 > 0:
            ratio = dt2/(dt2-dt1)
            zfc = z2-(dz*ratio)
            tfc = th2-((th2-th1)*ratio)
            capeT = (dt2*(z2-zfc)/(tfc+th2))
            cinT = (dt1*(zfc-z1)/(tfc+th1))
        else:
            cinT = ((dt2+dt1)*dz)/(th2+th1)

        if capeT > 0:
            CAPE = capeT * cc.g
        else:
            CAPE = 0

        if cinT < 0:
            CIN = cinT * cc.g
        else:
            CIN = 0

            totalCAPE += CAPE
            totalCIN += CIN

    return totalCAPE,totalCIN

def compute_RH(self,tidx,lvidx,lonidx,latidx,other):

    T = self.get('drybulb',tidx,lvidx,lonidx,latidx,other='C')
    Td = self.get('Td',tidx,lvidx,lonidx,latidx)
    RH = N.exp(0.073*(Td-T))
    # pdb.set_trace()
    return RH*100.0

def compute_temp_advection(self,tidx,lvidx,lonidx,latidx,other):
    U = self.get('U',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    V = self.get('V',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    T = self.get('drybulb',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    dTdx, dTdy = N.gradient(T,self.DX,self.DY)
    field = -U*dTdx - V*dTdy
    # pdb.set_trace()
    return field

def compute_PMSL_gradient(self,tidx,lvidx,lonidx,latidx,other):
    P = self.get('PMSL',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    dPdx, dPdy = N.gradient(P,self.dx,self.dy)
    field = N.sqrt(dPdx**2 + dPdy**2)
    # import pdb; pdb.set_trace()
    return field

def compute_T2_gradient(self,tidx,lvidx,lonidx,latidx,other):
    T2 = self.get('T2',tidx,lvidx,lonidx,latidx)[0,0,:,:]
    dTdx, dTdy = N.gradient(T2,self.dx,self.dy)
    field = N.sqrt(dTdx**2 + dTdy**2)
    # import pdb; pdb.set_trace()
    return field

def compute_dryairmass(self,tidx,lvidx,lonidx,latidx,other):
    MU = self.get('MU',tidx,lvidx,lonidx,latidx)
    MUB = self.get('MUB',tidx,lvidx,lonidx,latidx)
    return MU + MUB

def compute_pmsl(self,tidx,lvidx,lonidx,latidx,other):
    P = self.get('PSFC',tidx,lvidx,lonidx,latidx)
    T2 = self.get('T2',tidx,lvidx,lonidx,latidx)
    HGT = self.get('HGT',tidx,lvidx,lonidx,latidx)

    temp = T2 + (6.5*HGT)/1000.0
    pmsl = P*N.exp(9.81/(287.0*temp)*HGT)

    #sm = kwargs.get('smooth',1)
    #data = pmsl[0,::sm,::sm]
    #return data
    return pmsl

def compute_buoyancy(self,tidx,lvidx,lonidx,latidx,other=False):
    """
    Method from Adams-Selin et al., 2013, WAF
    """
    theta = self.get('theta',tidx,lvidx,lonidx,latidx)
    thetabar = N.mean(theta)
    qv = self.get('QVAPOR',tidx,lvidx,lonidx,latidx)
    qvbar = N.mean(qv)

    B = cc.g * ((theta-thetabar)/thetabar + 0.61*(qv - qvbar))
    return B

def compute_mixing_ratios(self,tidx,lvidx,lonidx,latidx,other=False):
    qv = self.get('QVAPOR',tidx,lvidx,lonidx,latidx)
    qc = self.get('QCLOUD',tidx,lvidx,lonidx,latidx)
    qr = self.get('QRAIN',tidx,lvidx,lonidx,latidx)

    try:
        qi = self.get('QICE',tidx,lvidx,lonidx,latidx)
    except KeyError:
        print("MP scheme has no ice data.")
        qi = 0

    try:
        qs = self.get('QSNOW',tidx,lvidx,lonidx,latidx)
    except KeyError:
        print("MP scheme has no snow data.")
        qs = 0

    try:
        qg = self.get('QGRAUP',tidx,lvidx,lonidx,latidx)
    except KeyError:
        print("MP scheme has no graupel data.")
        qg = 0

    rh = qc + qr + qi + qs + qg
    rv = qv

    return rh, rv

def compute_qtotal(self,tidx,lvidx,lonidx,latidx,other):
    qtotal, _ = self.compute_mixing_ratios(tidx,lvidx,lonidx,latidx)
    return qtotal

def compute_dptp(self,tidx,lvidx,lonidx,latidx,other):
    dpt = self.get('dpt',tidx,lvidx,lonidx,latidx)
    dpt_mean = N.mean(dpt)
    dptp = dpt - dpt_mean
    return dptp

def compute_T2_pertub(self,tidx,lvidx,lonidx,latidx,other):
    T2 = self.get('T2',tidx,lvidx,lonidx,latidx)
    T2_mean = N.mean(T2)
    T2p = T2-T2_mean
    return T2p

def compute_Q_pert(self,tidx,lvidx,lonidx,latidx,other):
    Q = self.get('QVAPOR',tidx,lvidx,lonidx,latidx)
    Q_mean = N.mean(Q)
    Qp = Q-Q_mean
    return Qp

def compute_dpt(self,tidx,lvidx,lonidx,latidx,other):
    """
    Potential: if surface level is requested, choose sigma level just
    about the surface. I don't think this affects any
    other dictionaries around...
    """
    # if tidx,lvidx,lonidx,latidx['lv'] == 0:
        # tidx,lvidx,lonidx,latidx['lv'] = 0
    theta = self.get('theta',tidx,lvidx,lonidx,latidx)
    rh, rv = self.compute_mixing_ratios(tidx,lvidx,lonidx,latidx)

    dpt = theta * (1 + 0.61*rv - rh)
    return dpt

def compute_geopotential_height(self,tidx,lvidx,lonidx,latidx,other):
    geopotential = self.get('PH',tidx,lvidx,lonidx,latidx) + self.get('PHB',tidx,lvidx,lonidx,latidx)
    Z = geopotential/9.81
    return Z

def compute_geopotential(self,tidx,lvidx,lonidx,latidx,other):
    geopotential = self.get('PH',tidx,lvidx,lonidx,latidx) + self.get('PHB',tidx,lvidx,lonidx,latidx)
    return geopotential

def compute_wind10(self,tidx,lvidx,lonidx,latidx,other):
    u = self.get('U10',tidx,lvidx,lonidx,latidx)
    v = self.get('V10',tidx,lvidx,lonidx,latidx)
    data = N.sqrt(u**2 + v**2)
    return data

def compute_pressure(self,tidx,lvidx,lonidx,latidx,other):
    PP = self.get('P',tidx,lvidx,lonidx,latidx)
    PB = self.get('PB',tidx,lvidx,lonidx,latidx)
    pressure = PP + PB
    return pressure

def compute_drybulb(self,tidx,lvidx,lonidx,latidx,other='K'):
    theta = self.get('theta',tidx,lvidx,lonidx,latidx)
    P = self.get('pressure',tidx,lvidx,lonidx,latidx)

    # Theta-e at level 2
    drybulb = theta*((P/100000.0)**(287.04/1004.0))
    if other=='K':
        return drybulb
    elif other=='C':
        return drybulb-273.15

def compute_theta(self,tidx,lvidx,lonidx,latidx,other):
    theta = self.get('T',tidx,lvidx,lonidx,latidx)
    Tbase = 300.0
    theta = Tbase + theta
    return theta

def compute_wind(self,tidx,lvidx,lonidx,latidx,other):
    # pdb.set_trace()
    u = self.get('U',tidx,lvidx,lonidx,latidx)
    v = self.get('V',tidx,lvidx,lonidx,latidx)
    data = N.sqrt(u**2 + v**2)
    return data

def compute_shear(self,tidx,lvidx,lonidx,latidx,other=False):
    """
    Args:
        other   :      dictionary of 'top' and 'bottom' levels, km

    Todos:
        * Could make this faster with numpy.digitize()?
    """
    if not other:
        print("No shear heights specified. Using 0-6 km by default.")
        topm = 6000.0
        botm = 0.0
        # print("Choose top and bottom for shear calc.")
        # raise Exception
    else:
        topm = other['top']*1000
        botm = other['bottom']*1000

    u = self.get('U',tidx,lvidx,lonidx,latidx)
    v = self.get('V',tidx,lvidx,lonidx,latidx)
    Z = self.get('Z',tidx,lvidx,lonidx,latidx)

    topidx = N.zeros((self.y_dim,self.x_dim))
    botidx = N.zeros((self.y_dim,self.x_dim))
    ushear = N.zeros((self.y_dim,self.x_dim))
    vshear = N.zeros((self.y_dim,self.x_dim))

    for j in range(self.x_dim):
        for i in range(self.y_dim):
            # import pdb; pdb.set_trace()
            topidx[i,j] = round(N.interp(
                            topm,Z[0,:,i,j],list(range(self.z_dim))))
            botidx[i,j] = round(N.interp(
                            botm,Z[0,:,i,j],list(range(self.z_dim))))
            ushear[i,j] = u[0,topidx[i,j],i,j] - u[0,botidx[i,j],i,j]
            vshear[i,j] = v[0,topidx[i,j],i,j] - v[0,botidx[i,j],i,j]

    # Find indices of bottom and top levels
    # topidx = N.where(abs(Z-topm) == abs(Z-topm).min(axis=1))
    # botidx = N.where(abs(Z-botm) == abs(Z-botm).min(axis=1))

    # ushear = u[0,:,topidx] - u[0,:,botidx]
    # vshear = v[0,topidx,:,:] - v[0,botidx,:,:]

    shear = N.sqrt(ushear**2 + vshear**2)
    # pdb.set_trace()
    return shear

def compute_thetae(self,tidx,lvidx,lonidx,latidx,other):
    P = self.get('pressure',tidx,lvidx,lonidx,latidx) # Computed
    Drybulb = self.get('temp',tidx,lvidx,lonidx,latidx)
    Q = self.get('Q',tidx,lvidx,lonidx,latidx)

    thetae = (Drybulb + (Q * cc.Lv/cc.cp)) * (cc.P0/P) ** cc.kappa
    return thetae

def compute_olr(self,tidx,lvidx,lonidx,latidx,other):
    OLR = self.get('OLR',tidx,lvidx,lonidx,latidx)
    sbc = 0.000000056704
    ir = ((OLR/sbc)**0.25) - 273.15
    return ir

def compute_REFL_comp(self,tidx,lvidx,lonidx,latidx,other):
    # lvidx = None
    # pdb.set_trace()
    refl = self.get('REFL_10CM',tidx,lvidx,lonidx,latidx,other)[0,:,:,:]
    refl_comp = N.max(refl,axis=0)
    return refl_comp

def compute_comp_ref(self,tidx,lvidx,lonidx,latidx,other):
    """Amend this so variables obtain at start fetch only correct date, lats, lons
    All levels need to be fetched as this is composite reflectivity
    """
    T2 = self.get('T2',tidx,False,lonidx,latidx)
    # QR = self.nc.variables['QRAIN'][PS['t'],:,PS['la'],PS['lo']]
    QR = self.get('QRAIN',tidx,False,lonidx,latidx) # This should get all levels
    PSFC = self.get('PSFC',tidx,False,lonidx,latidx)

    try:
        QS = self.get('QSNOW',tidx,False,lonidx,latidx)
    except:
        QS = N.zeros(N.shape(QR))
    rhor = 1000.0
    rhos = 100.0
    rhog = 400.0
    rhoi = 917.0

    no_rain = 8.0E6
    # How do I access this time?
    no_snow = 2.0E6 * N.exp(-0.12*(T2-273.15))
    no_grau = 4.0E6

    density = N.divide(PSFC,(287.0 * T2))
    Qra_all = QR[0,...]
    Qsn_all = QS[0,...]

    for j in range(len(Qra_all[1,:,1])):
        curcol_r = []
        curcol_s = []
        for i in range(len(Qra_all[1,1,:])):
                maxrval = N.max(Qra_all[:,j,i])
                maxsval = N.max(Qsn_all[:,j,i])
                curcol_r.append(maxrval)
                curcol_s.append(maxsval)
        N_curcol_r = N.array(curcol_r)
        N_curcol_s = N.array(curcol_s)
        if j == 0:
            Qra = N_curcol_r
            Qsn = N_curcol_s
        else:
            Qra = N.row_stack((Qra, N_curcol_r))
            Qsn = N.row_stack((Qsn, N_curcol_s))

    # Calculate slope factor lambda
    lambr = (N.divide((3.14159 * no_rain * rhor), N.multiply(density, Qra)+N.nextafter(0,1))) ** 0.25
    lambs = N.exp(-0.0536 * (T2 - 273.15))

    # Calculate equivalent reflectivity factor
    Zer = (720.0 * no_rain * (lambr ** -7.0)) * 1E18
    Zes = (0.224 * 720.0 * no_snow * (lambr ** -7.0) * (rhos/rhoi) ** 2) * 1E18
    Zes_int = N.divide((lambs * Qsn * density), no_snow)
    Zes = ((0.224 * 720 * 1E18) / (3.14159 * rhor) ** 2) * Zes_int ** 2

    Ze = N.add(Zer, Zes)
    dBZ = N.nan_to_num(10*N.log10(Ze))
    return dBZ

def compute_simref_atlevel(self,level=1):
    pass
    return data

def compute_DCP(self):
    """
    Derecho Composite Parameter (Evans and Doswell, 2001, WAF)
    And info from SPC Mesoanalyses
    """
    DCAPE = self.get('DCAPE')
    MUCAPE = self.get('MUCAPE')
    shear_0_6 = self.get('shear',0,6)
    meanwind_0_6 = self.get('meanwind',0,6)
    DCP = (DCAPE/980.0)*(MUCAPE/2000.0)*(shear_0_6/20.0)*(meanwind_0_6/16.0)
    return DCP

def compute_DCAPE(self):

    pass

def compute_thetae(self,tidx,lvidx,lonidx,latidx,other):
    P = self.get('pressure',tidx,lvidx,lonidx,latidx)
    T = self.get('drybulb',tidx,lvidx,lonidx,latidx,units='K')
    Td = self.get('Td',tidx,lvidx,lonidx,latidx)
    p2, t2 = thermo.drylift(P,T,Td)
    x = thermo.wetlift(p2,t2,100.0)
    thetae = thermo.theta(100.0, x, 1000.0)
    return thetae


def compute_Td(self,tidx,lvidx,lonidx,latidx,other):
    """
    Using HootPy equation
    """
    Q = self.get('QVAPOR',tidx,lvidx,lonidx,latidx)
    P = self.get('pressure',tidx,lvidx,lonidx,latidx)
    w = N.divide(Q, N.subtract(1,Q))
    e = N.divide(N.multiply(w,P), N.add(0.622,w))/100.0
    a = N.multiply(243.5,N.log(N.divide(e,6.112)))
    b = N.subtract(17.67,N.log(N.divide(e,6.112)))
    Td = N.divide(a,b)
    # pdb.set_trace()
    return Td
