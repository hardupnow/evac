import pdb
import multiprocessing
from multiprocessing import Queue, Process, Pool

import numpy as N
import matplotlib as M
import matplotlib.pyplot as plt
import scipy.stats as SS

### 1D PLOT ###

"""
### VARIABLES ###
R = 0 # Function, varying with scale t
dR = 0 # height of pulse - rainfatll intensity increment
rho = 3 # width of pulse - rainfall duration
ppcen = 0 # centre of pulse according to Poisson process
mu = 0.025 # constant rate for Poisson process
rhotick = 0 # random duration
alpha = 5/3 # ?>>
H = 1/alpha # scaling exponent
lamb = 0 # ???
L0 = 0 # Interval min
L = 400 # Interval max
l = L/6 # Inner interval length
s = 8 # smoothing factor. S -> inf makes rectangular
u = 0 # distance from centre of echo
rho_i = 1 # minimum resolution or inner scale - in pixels
# rho_0 = mu*L # outer scale
rho_0 = 1200 # outer scale
n = 1.6e5 # number of pulses
# Enforce L/l between 3 and 6
"""
### TEST DISTRUBTION ###
# fig,ax = plt.subplots(1)
# a_ = rho_i + 1
# b_ = rho_0
# xx = N.linspace(SS.reciprocal.ppf(0.01, a_, b_),
                # SS.reciprocal.ppf(0.99, a_, b_), 100)
# ax.plot(xx,SS.reciprocal.pdf(xx,a_,b_))
# fig.show()


def get_poisson(L,mu,size):
    # poisson = []
    # for nd in ndim:
    # poisson.append(N.random.poisson(lam=mu,size=n))
    return N.random.poisson(lam=L/mu,size=size)
        # yield poisson

###### Fig 7 ########
fig7 = 0
if fig7:
    n = 50000
    rho_0 = 50000
    l = 10000
    L = 20000
    mu = 2.5
    alpha = 5/3
    H = 1/alpha
    rho_i = 1

    R = N.zeros(l,dtype=N.float64)
    centres = N.random.random_integers(low=0,high=L,size=n)
    # centreP = get_poisson(centreU,mu,n)[0]
    rholist = N.arange(rho_i,rho_0+1)
    cdf = 1/rholist
    pdf = N.diff(cdf)*-1
    pdf_full = N.append(pdf,1-pdf.sum())

    for centreU in centres:
        centreP = get_poisson(centreU,mu,n)[0]
        rhotick = N.random.choice(rholist,p=pdf_full)
        dR = N.random.choice((-1,1)) * rhotick**H
        hw = rhotick/2
        R[int(centreP-hw):int(centreP+hw)] += dR

    fig,ax = plt.subplots(1)
    ax.plot(R)
    fig.show()
    assert True==False

####### Fig. 8 ########
def get_donut(xx,yy,cenx,ceny,rad,wid):
    circle = (xx - int(cenx)) ** 2 + (yy - int(ceny)) ** 2
    donut = N.logical_and(circle < (rad + wid/2), circle > (rad - wid/2))
    pdb.set_trace()
    return donut


def fractal_worker(size=False,high=False,rholist=False,xx=False,
                yy=False,delta=False,sigma=False,s=False,
                mu=False,pdf_full=False,R=False,q=False):
    centrex = N.random.random_integers(low=0,high=high,size=size)
    centrey = N.random.random_integers(low=0,high=high,size=size)
    count = 0
    # checkstart = time.time()
    for cenx, ceny in zip(centrex,centrey):
        rhotick = 0
        count += 1
        if not count%200:
            print('Doing plot #',count,"of",size)
            # checkpoint = time.time()
            # elapsed = "{0:.1f}".format(checkpoint-checkstart)
            # print("200 took ",elapsed,"sec")
            # checkstart = checkpoint
            # del checkpoint
        cenxP = get_poisson(cenx,mu,1)[0]
        cenyP = get_poisson(ceny,mu,1)[0]

        while rhotick < rho_i:
            rhotick = N.random.choice(rholist,p=pdf_full)

        dR = N.random.choice((-1,1)) * rhotick**H
        # Rc = N.zeros_like(R)
        u = N.sqrt(((xx-cenx)**2)+((yy-ceny)**2))
        R += dR * N.exp(-1*((u**2/rhotick**2)-delta**2)/sigma**2)**(2*s)
        # Rc = dR * N.exp(-1*((u**2/rhotick**2)-delta**2)/sigma**2)**(2*s)
        # donut = get_donut(xx,yy,cenxP,cenyP,delta,sigma)
        # donut = get_donut(xx,yy,cenxP,cenyP,640,60)
        # R += Rc
        # centreP = get_poisson(centreU,mu,n)[0]
        # rhotick = N.random.choice(rholist,p=pdf_full)
        # hw = rhotick/2
        # R[int(centreP-hw):int(centreP+hw)] += dR
    # return R
    q.put(R)


if __name__ == '__main__':
    CPUs = multiprocessing.cpu_count()-1
    rho_i = 6
    rho_0 = 900
    l = 300
    L = 300
    # n = 160000
    # n = CPUs*9000
    n = CPUs*6000
    s = 2
    mu = 2.5
    # LAMB = 1.2 * N.pi
    LAMB = 1.2
    LAMBstar = N.sqrt(LAMB**2 - 1)
    delta = 0.5*(LAMBstar + LAMB)
    sigma = 0.5*(LAMB-LAMBstar)
    alpha = 5 # ?>>
    H = 1/alpha # scaling exponent


    rholist = N.arange(1,rho_0+1)
    cdf = 1/rholist
    pdf = N.diff(cdf)*-1
    pdf_full = N.append(pdf,1-pdf.sum())

    R = N.zeros([L,L],dtype=N.float64)
    xx, yy = N.mgrid[:L, :L]

    print("Starting computation now")
    # paralellise the processing
    npart = int(n/CPUs)
    Rs = []
    Rsum = N.zeros_like(R)


    # Pool = multiprocessing.Pool(CPUs)
    queues = [Queue() for c in range(CPUs)]
    kw = {}
    kw['size'] = npart
    kw['high'] = L
    kw['rholist'] = rholist
    kw['xx'] = xx
    kw['yy'] = yy
    kw['delta'] = delta
    kw['sigma'] = sigma
    kw['s'] = s
    kw['mu'] = mu
    kw['pdf_full'] = pdf_full
    kw['R'] = R
    jobs = []
    for q in queues:
        KW = kw.copy()
        KW['q'] = q
        jobs.append(Process(target=fractal_worker,kwargs=KW))

    for job in jobs:
        job.start()
    for qn,q in enumerate(queues):
        print("Getting Queue #",qn)
        Rq = q.get()
        Rsum += Rq
    for job in jobs:
        job.join()
    return Rsum
