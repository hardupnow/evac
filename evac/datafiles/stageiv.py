""" STAGE IV precip data.
"""


from .gribfile import GribFile

class StageIV(GribFile):
    def __init__(self,dir_or_file,load_1h=True,load_6h=False,load_24h=False,
                    loadobj=False):
        """"
        Args:
            dir_or_file         :   if directory, it scans for all files
                                        If file, it loads that one file.
        Todos:
            * Check for 9999s (missing) or negative. Other codes
            * Consistency: are we loading one or a group of files?

        """

        try:
            import pygrib
        except ImportError:
            print("You need to install pygrib for the StageIV class.")
            raise Exception
        else:
            self.pygrib = pygrib

        self.loadobj = loadobj

        # Determine whether to load one file or search in directory
        try:
            G = self.pygrib.open(dir_or_file)
        except OSError:
            ST4s = os.path.join(rootdir,'ST4*')
            print("Loading files in {0}".format(ST4s))
            fps = glob.glob(ST4s)
        else:
            fps = [dir_or_file,]

        self.DATA = {}
        if load_1h:
            self.DATA['01h'] = {}
        if load_6h:
            self.DATA['06h'] = {}
        if load_24h:
            self.DATA['24h'] = {}
        for fp in fps:
            # fp is the full path to the (grib?) file
            # f is the name of the file only
            f = os.path.basename(fp)
            t = self.date_from_fname(f)

            # if f.endswith('01h'):
                # d1h[t] = self.load_data(f)
            # elif f.endswith('06h'):
                # d6h[t] = self.load_data(f)
            # elif f.endswith('24h'):
                # d24h[t] = self.load_data(f)
            # else:
                # pass
            for accum_t in ('01h','06h','24h'):
                if f.endswith(accum_t) and (accum_t in self.DATA.keys()):
                    answer = self.load_data(fp,loadobj)
                    if answer is not False:
                        self.DATA[accum_t][t] = answer
                else:
                    pass

        # Assign all projection stats
        # pdb.set_trace()
        # print("All files in ",ST4s)
        # for fp in fps:
            # print(fp)
        # print("-"*10)

        self.projection()

    def get(self,utc,accum_hr='01h'):
        """
        Get a given time, in similar manner to WRFOut.

        Wrapper for return_array with reshape to 4D
        """
        data2D = self.return_array(utc,accum_hr=accum_hr)
        data4D = data2D[N.newaxis,N.newaxis,:,:]
        return data4D

    def date_from_fname(self,f):
        _1, d, _2 = f.split('.')
        fmt = '%Y%m%d%H'
        utc = datetime.datetime.strptime(d,fmt)
        return utc

    def load_data(self,f,loadobj=False):
        if loadobj:
            # Return Pygrib object if valid grib file
            try:
                G = self.pygrib.open(f)
            except OSError:
                return False
            else:
                return G
        else:
            # Return file path if valid grib file
            try:
                G_test = self.pygrib.open(f)
            except OSError:
                return False
            else:
                return f

    def load_gribpart(self,G):
        if G is None:
            G = self.arbitrary_pick()
        if isinstance(G,str):
            G = self.load_data(G,loadobj=True)
        G.seek(0)
        gg = G.select(name='Total Precipitation')[0]
        return gg

    def load_accum(self,G):
        gg = self.load_gribpart(G)
        arr = gg.values
        return arr

    def return_latlon(self,G):
        if G is None:
            G = self.arbitrary_pick()
        gg = self.load_gribpart(G)
        latlon = gg.latlons()
        lats, lons = latlon
        return lats,lons

    def return_array(self,utc,accum_hr='01h'):
        G = self.DATA[accum_hr][utc]
        return self.load_accum(G)

    def return_point(self,utc,lat,lon,accum_hr='01h'):
        lats, lons = self.return_latlon(None)
        latidx,lonidx = utils.get_latlon_idx(lats,lons,lat,lon)
        arr = self.return_array(utc,accum_hr=accum_hr)
        # pdb.set_trace()
        return arr[latidx,lonidx]


    def projection(self):
        self.m = Basemap(projection='npstere',lon_0=-105.0,#lat_1=60.0,
                # llcrnrlon=lllon,llcrnrlat=lllat,urcrnrlon=urlon,urcrnrlat=urlat,
                            boundinglat=24.701632)
        G = self.arbitrary_pick()
        self.lats, self.lons = self.return_latlon(G)
        self.xx, self.yy = self.m(self.lons,self.lats)
        # pdb.set_trace()
        # self.mx, self.my = N.meshgrid(self.xx,self.yy)

        # lllon = -119.023
        self.lllon = self.lons[0,0]
        # lllat = 23.117
        self.lllat = self.lats[0,0]
        # urlon = -59.9044
        self.urlon = self.lons[-1,-1]
        # urlat = 45.6147234
        self.urlat = self.lats[-1,-1]

        self.shape = self.lats.shape
        assert self.lats.shape == self.lons.shape

    def arbitrary_pick(self):
        # pdb.set_trace()
        accum = list(self.DATA.keys())[0]
        utc = list(self.DATA[accum].keys())[0]
        return self.DATA[accum][utc]