import pdb
import collections
import os

from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib as M
M.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as N

from evac.datafiles.wrfout import WRFOut
from evac.utils.defaults import Defaults
from evac.plot.figure import Figure
from evac.plot.scales import Scales
import evac.stats as stats

class BirdsEye(Figure):
    """ Top-down 2D plots.

    Todo:
        * multiple plots on same figure - like a 'hold' - maybe by
            using set and get decorators. Or stopping save/close.
        * Massive rewrite with cartopy, now basemap is depreciated.
        * Move most options to mplkwargs (e.g. cmap, levels).

    Args:
        ax,fig (optional): If None (default), then a new figure/axis object
            will be created in the instance (via parent class 
            :class:`~evac.plot.figure.Figure`.
        ideal (bool): If True, options for an idealised plot will be used.
            For example, no lat/lon.
        proj (str,bool): If `str`, such as `'merc'`, this will set the 
            instance's plotting projection.
        mplargs, mplkwargs: Arguments to pass to matplotlib.

    Returns:
        A figure is generated (if no fig/ax is specified), or plotting (onto an
            existing figure).
    """

    def __init__(self,ax=None,fig=None,ideal=False,proj='merc',
                 mplargs=[],mplkwargs={},):#W=None):
        """ Setting ideal to True removes the geography (e.g. for idealised
        plots)
        """
        self.proj = proj
        self.ideal = ideal

        super(BirdsEye,self).__init__(ax=ax,fig=fig,mplargs=mplargs,
                                      mplkwargs=mplkwargs)

    def plot2D(self,data,fname=False,outdir=False,plottype='contourf',
                    save=True,smooth=1,lats=False,lons=False,
                    clvs=None,cmap=None,title=False,cb=True,
                    locations=False,m=False,x=None,y=None,
                    Nlim=False,Elim=False,Slim=False,Wlim=False,
                    color='k',inline=False,cblabel=False,ideal=False,
                    drawcounties=False,mplargs=[],mplkwargs={},
                    extend=False,nx=None,ny=None,cen_lat=None,cen_lon=None,
                    lat_ts=None,W=None,hold=False):

        """
        Generic method that plots any matrix of data on a map

        Inputs:
        data        :   2D matrix of data
        outdir      :   path to plots
        outf        :   filename for output (with or without .png)

        Optional:
        plottype    :   matplotlib function for plotting
        smooth      :   Gaussian smooth by this many grid spaces
        clvs        :   scale for contours
        title       :   title on plot
        save        :   whether to save to file

        :param locations:       Locations to plot on the basemap.
                                Format: locations = {'label':(lat,lon),etc}
        :type locations:        dict
        """
        if isinstance(cmap,str):
            cmap = M.cm.get_cmap(cmap)
        save = getattr(self,'save_opt',save)
        hold = getattr(self,'hold_opt',hold)
        if plottype not in ("pcolor","pcolormesh"):
            mplkwargs['levels'] = clvs
        mplkwargs['cmap'] = cmap
        # WRFOut instance for help plotting.
        self.W = W
        if save:
            assert (fname is not False) and (outdir is not False)
        # INITIALISE
        self.data = data
        if self.ideal:
            ideal = True
        if ideal:
            self.bmap = self.ax
            # pdb.set_trace()
            self.y = N.arange(len(data[:,0]))
            self.x = N.arange(len(data[0,:]))

        # Can all this be moved into Figure() or whatever?
    # def basemap_from_newgrid(self,Nlim=None,Elim=None,Slim=None,Wlim=None,proj='merc',
                    # lat_ts=None,resolution='i',nx=None,ny=None,
                    # tlat1=30.0,tlat2=60.0,cen_lat=None,cen_lon=None,
                    # lllon=None,lllat=None,urlat=None,urlon=None,
                    # drawcounties=False):
        # self.basemap_from_newgrid(Nlim=Nlim,Elim=Elim,Slim=Slim,Wlim=Wlim,xx=x,yy=y,
                                # drawcounties=drawcounties,nx=nx,ny=ny,lons=lons,lats=lats,
                                # lat_ts=lat_ts)

        elif (not x) and (not y):
            if (not m):
                if not Nlim:
                    self.bmap,self.x,self.y = self.basemap_setup(smooth=smooth,lats=lats,
                                                        lons=lons,drawcounties=drawcounties)#ax=self.ax)
                else:
                    self.bmap,self.x,self.y = self.basemap_setup(smooth=smooth,lats=lats,
                                                        lons=lons,Nlim=Nlim,Elim=Elim,
                                                        Slim=Slim,Wlim=Wlim,drawcounties=drawcounties)

            else:
                self.bmap = m
                self.x, self.y = self.bmap(lons,lats)

        else:
            self.bmap = m
            self.x = x
            self.y = y

        mplargs = [self.x,self.y,self.data,] + mplargs

        # TODO: move this logic to other methods
        if plottype == 'contour':
            mplkwargs['colors'] = color
            mplkwargs['inline'] = inline
            # This won't work in Python 3
            # f1 = self.bmap.contour(*mplargs,**mplkwargs)
            # Fixed:
            f1 = self.bmap.contour(*mplargs,**mplkwargs)
            # This is repeated below
            
            if inline:
                plt.clabel(f1,inline=True,fmt='%d',color='black',fontsize=9)
        elif plottype == 'contourf':
            if isinstance(extend,str):
                mplkwargs['extend'] = extend
            # f1 = self.bmap.contourf(*mplargs,**mplkwargs)
            f1 = self.ax.contourf(*mplargs,**mplkwargs)
        elif plottype == 'pcolor':
            # f1 = self.bmap.pcolor(*mplargs,**mplkwargs)
            f1 = self.ax.pcolor(*mplargs,**mplkwargs)
        elif plottype == 'pcolormesh':
            # f1 = self.bmap.pcolormesh(*mplargs,**mplkwargs)
            f1 = self.ax.pcolormesh(*mplargs,**mplkwargs)
        elif plottype == 'scatter':
            # f1 = self.bmap.scatter(*mplargs,**mplkwargs)
            f1 = self.ax.scatter(*mplargs,**mplkwargs)
        # elif plottype == 'quiver':
            # f1 = self.bmap.quiver(*mplargs,**mplkwargs)
        else:
            print("Specify correct plot type.")
            raise Exception

        if ideal:
            self.ax.set_aspect('equal')
        if isinstance(locations,dict):
            self.plot_locations(locations)
        if isinstance(title,str):
            self.ax.set_title(title)
        if cb != False:
            if cb==True:
                cb1 = plt.colorbar(f1,orientation='vertical',ax=self.ax)
            elif cb=='horizontal':
                cb1 = plt.colorbar(f1,orientation='horizontal',ax=self.ax)
            elif cb == 'only':
                save = False
                self.fig,self.ax = plt.subplots(figsize=(4,0.8))
                cb1 = plt.colorbar(f1,cax=self.ax,orientation='horizontal')
                if isinstance(cblabel,str):
                    cb1.set_label(cblabel)
                self.save(outdir,fname+'_cb')
            else:
                cb1 = plt.colorbar(f1,orientation='vertical',cax=cb)
        if cb and isinstance(cblabel,str):
            cb1.set_label(cblabel)
        if save:
            self.save(outdir,fname)
            plt.close(self.fig)

    def plot_locations(self,locations):
        for k,v in locations.items():
            if isinstance(v,tuple) and len(v) == 2:
                xpt, ypt = self.bmap(v[1],v[0])
                # bbox_style = {'boxstyle':'square','fc':'white','alpha':0.5}
                self.bmap.plot(xpt,ypt,'ko',markersize=3,zorder=100)
                self.ax.text(xpt,ypt,k,ha='left',fontsize=7)
                # self.ax.text(xpt-15000,ypt,k,bbox=bbox_style,ha='left',fontsize=7)
            else:
                print("Not a valid location argument.")
                raise Exception
        return

    def do_contour_plot(self):
        pass

    def do_contourf_plot(self):
        pass

    def do_pcolormesh_plot(self):
        pass

    def plot_streamlines(self,U,V,outdir,fname,lats=False,lons=False,smooth=1,
                            title=False,lw_speed=False,density=1.8,ideal=False):
        """
        Plot streamlines.

        U       :   U-component of wind (nx x ny)
        V       :   V-component of wind (same dimensions)

        lw_speed    :   linewidth is proportional to wind speed
        """
        if ideal:
            m = plt
            x = N.arange(len(U[:,0]))
            y = N.arange(len(U[0,:]))
        else:
            m,x,y = self.basemap_setup(lats=lats,lons=lons)

        if lw_speed:
            wind = N.sqrt(U**2 + V**2)
            lw = 5*wind/wind.max()
        else:
            lw = 1

        if smooth>1:
            U = stats.gauss_smooth(U,smooth)
            V = stats.gauss_smooth(V,smooth)

        # m.streamplot(x[self.W.x_dim/2,:],y[:,self.W.y_dim/2],U,V,
                        # density=density,linewidth=lw,color='k',arrowsize=3)
        m.streamplot(x,y,U,V,
                        density=density,linewidth=lw,color='k',arrowsize=3)

        if isinstance(title,str):
            self.ax.set_title(title)

        self.save(outdir,fname)

    def spaghetti(self,t,lv,va,contour,wrfouts,outpath,da=0,dom=0):
        """
        wrfouts     :   list of wrfout files

        Only change dom if there are multiple domains.
        """
        m,x,y = self.basemap_setup()

        time_idx = self.W.get_time_idx(t)

        colours = utils.generate_colours(M,len(wrfouts))

        # import pdb; pdb.set_trace()
        if lv==2000:
            lv_idx = None
        else:
            print("Only support surface right now")
            raise Exception

        lat_sl, lon_sl = self.get_limited_domain(da)

        slices = {'t': time_idx, 'lv': lv_idx, 'la': lat_sl, 'lo': lon_sl}

        # self.ax.set_color_cycle(colours)
        ctlist = []
        for n,wrfout in enumerate(wrfouts):
            self.W = WRFOut(wrfout)
            data = self.W.get(va,slices)[0,...]
            # m.contour(x,y,data,levels=[contour,])
            ct = m.contour(x,y,data,colors=[colours[n],],levels=[contour,],label=wrfout.split('/')[-2])
            print(("Plotting contour level {0} for {1} from file \n {2}".format(
                            contour,va,wrfout)))
            # ctlist.append(ct)
            # self.ax.legend()

        # labels = [w.split('/')[-2] for w in wrfouts]
        # print labels
        # self.fig.legend(handles=ctlist)
        # plt.legend(handles=ctlist,labels=labels)
        #labels,ncol=3, loc=3,
        #                bbox_to_anchor=[0.5,1.5])

        datestr = utils.string_from_time('output',t,tupleformat=0)
        lv_na = utils.get_level_naming(va,lv)
        naming = ['spaghetti',va,lv_na,datestr]
        if dom:
            naming.append(dom)
        fname = self.create_fname(*naming)
        self.save(outpath,fname)

    def make_subplot_label(ax,label):
        ax.text(0.05,0.85,label,transform=ax.transAxes,
            bbox={'facecolor':'white'},fontsize=15,zorder=1000)
        return
