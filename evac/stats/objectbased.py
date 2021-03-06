""" Identify objects in an array.
"""
import pdb
import os

import numpy as N
import scipy.ndimage as ndimage
import scipy.ndimage.filters as filters
import matplotlib.pyplot as plt

from evac.datafiles.wrfout import WRFOut
from evac.plot.scales import Scales
from evac.datafiles.radar import Radar
from evac.plot.figure import Figure
from evac.plot.birdseye import BirdsEye

class ObjectBased:
    """ Object-based verification superclass.

    Todo:
        * Incorporate SAL logic
        * Be able to look up properties of objects
        * Link with other scores, e.g. CRPS
        * Link with other ObjectBased() instances (e.g. for SAL)

    Args:
        arr: 2D numpy array to identify objects in
        helpful_dbz: display helpful prompt if raw_data min is -32,
            as some radar data are bounded by 0 dBZ, rathern than -32
    """
    def __init__(self,arr,thresh='auto',footprint=500,f=1/15,
                    helpful_dbz=True,datamin=None):
        assert arr.ndim == 2

        self.raw_data = arr

        if datamin is not None:
            self.raw_data[self.raw_data < datamin] = datamin

        if (-32.1 < arr.min() < -31.9) and helpful_dbz:
            print("This looks like radar data. Please check other instances"
                "of this data is not capped at 0 dBZ, otherwise this raw"
                "data also needs capping at 0.")

        # self.metadata = {}
        self.thresh = thresh
        self.footprint = int(footprint)
        self.f = f
        self.identify_objects()
        self.nobjects = len(self.objects)
        self.maxobjn = self.find_max_objidx()

    def find_max_objidx(self):
        """ Get the largest object number.
        """
        maxidx = 0
        for k,v in self.objects.items():
            if int(k) > maxidx:
                maxidx = int(k)
        return maxidx


    def identify_objects(self,):
        # self.metadata['Rmax'] = N.max(self.raw_data)
        self.Rmax = N.max(self.raw_data)

        if self.thresh == 'auto':
            self.Rstar = self.f * self.Rmax
            # self.metadata['Rstar'] = self.f * self.metadata['Rmax']
        else:
            self.Rstar = float(self.thresh)

        # if self.use_scikit:
            # self.hessian_operators()
        # else:
        self.object_operators()

    def hessian_operators(self):
        from skimage.feature import blob_doh
        blob_doh(image=self.raw_data)

    def object_operators(self):
        """ This needs some explaining.
        """
        mask = N.copy(self.raw_data)
        mask[self.raw_data < self.Rstar] = False
        mask[self.raw_data >= self.Rstar] = True
        self.masked_data = mask
        labeled, num_objects = ndimage.label(mask)

        sizes = ndimage.sum(mask, labeled, list(range(num_objects+1)))

        masksize = sizes < self.footprint
        remove_pixel = masksize[labeled]
        labeled[remove_pixel] = 0

        labels = N.unique(labeled)
        label_im = N.searchsorted(labels, labeled)

        # dic['objects'] = {}
        self.objects = {}

        # Total R for objects
        R_objs_count = 0

        for ln,l in enumerate(labels):
            cy, cx = ndimage.measurements.center_of_mass(self.raw_data,labeled,l)
            if ln == 0:
                # This is the centre of mass for the entire domain.
                self.x_CoM = (cx,cy)
            else:
                self.objects[l] = {}
                self.objects[l]['CoM'] = (cy,cx)
                self.objects[l]['Rn'] = ndimage.sum(self.raw_data,labeled,l)
                self.objects[l]['RnMax'] = ndimage.maximum(self.raw_data,labeled,l)
                self.objects[l]['Vn'] = self.objects[l]['Rn']/self.objects[l]['RnMax']
                if not N.isnan(self.objects[l]['Rn']):
                    R_objs_count += self.objects[l]['Rn']

        self.R_tot = R_objs_count
        self.obj_array = labeled
        return

    def active_px(self,fmt='pc'):
        """ Return number of pixels included in objects.
        Args:
            fmt (bool): if True, returns the active pixel count
                expressed as percentage.
        """
        active_px = N.count_nonzero(self.obj_array)
        tot_px = self.obj_array.size

        if fmt == 'pc':
            return (active_px/(tot_px*1.0))*100.0
        else:
            return active_px, tot_px

    def get_cell_attributes(self,cell_data,):
        """ Returns stats on object/cell attributes.
        
        This could be things like max updraught or helicity.

        Max updraught is computed at all levels at all grid points
        in the object.

        Args:
            cell_data: 2D or 3D array of a field the same size as the
                object-based field. The lats/lons correspond directly
                to the raw_data passed into self originally.
        """
        if cell_data.ndim == 3:
            cell_data = N.max(cell_data,axis=0)
        assert cell_data.ndim == 2
        nobjs = len(self.objects)
        cellattr_dict = dict()
        cellattr_arr = N.zeros([nobjs])

        for nidx,(n,o) in enumerate(self.objects.items()):
            # The grid points of each object is labelled
            # in self.obj_array.
            grid_2d_idx = N.where(self.obj_array == n)
            arr_obj = cell_data[grid_2d_idx[0],grid_2d_idx[1]]
            max_w = N.max(arr_obj)

            # Data in a dictionary and array
            cellattr_dict[n] = max_w
            cellattr_arr[nidx] = max_w
        
        return cellattr_arr, cellattr_dict

    def plot(self,fpath,fmt='default',W=None,vrbl='REFL_comp',
                # Nlim=None,Elim=None,Slim=None,Wlim=None):
                ld=None,lats=None,lons=None,fig=None,ax=None):
        """ Plot basic quicklook images.

        Setting fmt to 'default' will plot raw data,
        plus objects identified.
        """
        if ld is None:
            ld = dict()
        nobjs = len(self.objects)

        if fmt == 'default':
            # if fig is None:
            F = Figure(ncols=2,nrows=1,figsize=(8,4),
                        fpath=fpath)
            # F.W = W
            with F:
                ax = F.ax[0]
                # Plot raw array
                BE = BirdsEye(ax=ax,fig=F.fig)

                # Discrete colormap
                import matplotlib as M
                cmap_og = M.cm.get_cmap('tab20')
                # cmap_colors = [cmap_og(i) for i in range(cmap_og.N)]
                color_list = cmap_og(N.linspace(0,1,nobjs))
                # cmap = M.colors.ListedColormap(M.cm.tab20,N=len(self.objects))
                cmap = M.colors.LinearSegmentedColormap.from_list('discrete_objects',color_list,nobjs)
                # bounds = N.linspace(0,nobjs,nobjs+1)
                # norm = M.colors.BoundaryNorm(bounds,cmap_og.N)
                masked_objs = N.ma.masked_less(self.obj_array,1)
                
                BE.plot2D(plottype='pcolormesh',data=masked_objs,save=False,
                            cb='horizontal',
                            #clvs=N.arange(1,nobjs),
                            W=W,
                            cmap=cmap,mplkwargs={'vmin':1},**ld,lats=lats,lons=lons)

                ax = F.ax[1]
                S = Scales(vrbl)
                BE = BirdsEye(ax=ax,fig=F.fig)
                BE.plot2D(data=self.raw_data,save=False,
                            W=W,
                            cb='horizontal',lats=lats,lons=lons,
                            cmap=S.cm,clvs=S.clvs,**ld)
        return

    def __iter__(self):
        self.object_idx = -1
        self.object_list = list(self.objects.keys())
        return self

    def __next__(self):
        self.object_idx += 1
        if self.object_idx > self.nobjects-1:
            raise StopIteration
        key = self.object_list[self.object_idx]
        obj = self.objects[key]
        return key,obj
