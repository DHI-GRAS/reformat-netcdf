import logging
import datetime
from scipy.io import netcdf as nc
import numpy as np

logging.captureWarnings(True)

_time_encoding = dict(units="seconds since 1970-01-01 00:00:00", calendar="standard")

def create_grid_dimensions(ds, londata, latdata):
    """Create grid dimensions and variables on open netcdf file

    Parameters
    ----------
    ds : netCDF4.Dataset or scipy.io.netcdf.netcdf_file
        open netCDF file in 'w' mode
    londata : 1D or 2D(lat,lon) array
        longitude data
    latdata : 1D or 2D(lat,lon) array
        latitude data
    """
    # get shapes and dimensions
    nndim = np.ndim(londata) * np.ndim(latdata)
    if nndim == 4:
        latdim = ('lat', 'lon')
        londim = ('lat', 'lon')
        latshape = tuple([int(d) for d in np.shape(latdata)])
        lonshape = tuple([int(d) for d in np.shape(londata)])
    elif nndim == 1:
        latdim = ('lat', )
        londim = ('lon', )
        latshape = len(latdata)
        lonshape = len(londata)
    else:
        raise ValueError("londata and latdata must have the same shape (1D or 2D).")
    # create dimensions
    ds.createDimension('lat', latshape)
    ds.createDimension('lon', lonshape)
    # create coord variables
    latvar = ds.createVariable('lat', 'd', latdim)
    lonvar = ds.createVariable('lon', 'd', londim)
    # store data
    latvar[:] = latdata
    lonvar[:] = londata
    # add meta
    latvar.long_name = latvar.standard_name = 'latitude'
    lonvar.long_name = lonvar.standard_name = 'longitude'
    # add units
    latvar.units = 'degrees_north'
    lonvar.units = 'degrees_east'


def create_time_dimension(ds, ntime=None, timedata=None,
        units=_time_encoding['units'], calendar=_time_encoding['calendar']):
    """Create time dimension and variable on open netcdf file

    Parameters
    ----------
    ds : netCDF4.Dataset or scipy.io.netcdf.netcdf_file
        open netCDF file in 'w' mode
    ntime : int
        length of time dimension
        None for unlimited
    units, calendar : str
        target units and calendar
        default: fd defaults

    Returns
    -------
    timevar : time variable object
    """
    ds.createDimension('time', ntime)
    timevar = ds.createVariable('time', 'i4', ('time',))
    timevar.units = units
    timevar.calendar = calendar
    timevar.standard_name = 'time'
    if timedata is not None:
        timevar[:] = timedata
    return timevar


def create_data_variable(ds, name, dtype, dims=None, _FillValue=None, **attrs):
    """Create data variable on netCDF dataset

    Parameters
    ----------
    ds : open netCDF4.Dataset
        input dataset
    name : str
        variable name
    dtype : str or np.dtype
        data type
    dims : tuple
        dimensions (e.g. ('lat', 'lon'))
        guessed if not provided
    _FillValue : int or float
        target _FillValue
    attrs : dict
        attributes to add to data variable
        e.g. encoding

    Note
    ----
    For data with time dimension, the time dimension must already exists
    when calling this function.
    """
    if dims is None:
        if 'time' in ds.dimensions:
            dims = ('time', 'lat', 'lon')
        else:
            dims = ('lat', 'lon')
    try:
        datavar = ds.createVariable(name, dtype, dims, fill_value=_FillValue)
    except TypeError:
        # ds is scipy.io.netcdf.netcdf_file
        datavar = ds.createVariable(name, dtype, dims)
        if _FillValue is not None:
            datavar._FillValue = _FillValue
    for k,v in attrs.items():
        setattr(datavar, k, v)

    return datavar


def date2num(dates):
    """Converts datetime `dates` to numbers to be stored in the variable `timevar`

    Parameters
    ----------
    dates : datetime.datetime or sequence of such
        dates to convert to time stamps to feed to netCDF time variable
    """
    # Convert the timestamp from seconds since 1970 to year-DOY
    dates = np.atleast_1d(dates)
    refdate = datetime.datetime(1970,1,1)
    nums = np.asarray(
            [(d-refdate).total_seconds() for d in dates],
            dtype=int)
    return np.squeeze(nums)[()]


def convert(infile, outfile, variable,
        units=None, long_name=None,
        factor=None, fill_missing=None):
    """Convert a netCDF file to CF-1.6 with some reformatting

    Parameters
    ----------
    infile, outfile : str, str
        paths to input/output files
    variable : str
        data variable to extract
    units : str
        overwrite units attribute on variable
    long_name : str
        overwrite long_name attribute on variable
    factor : float
        multiply the data by this factor
        set to None or 0 to disable
    fill_missing : float
        replace missing data with this value
    """
    with nc.netcdf_file(infile) as dsin, \
            nc.netcdf_file(outfile, 'w') as dsout:

        invar = dsin.variables
        try:
            indatavar = invar[variable]
        except KeyError:
            raise KeyError('Variable \'{}\' not found in dataset.'.format(variable))

        # grid
        try:
            londata = invar['longitude'][:]
            latdata = invar['latitude'][:]
        except KeyError:
            londata = invar['lon'][:]
            latdata = invar['lat'][:]
        create_grid_dimensions(dsout, londata, latdata)

        # time
        intime = invar['time']
        outunits = _time_encoding['units']
        if intime.units[:len(outunits)].lower() != outunits.lower():
            raise ValueError('Input time data has incompatible units: \'{}\'.'.format(intime.units))
        timedata = intime[:]
        create_time_dimension(dsout, ntime=len(timedata), timedata=timedata)

        # data variable
        if units is None:
            units = getattr(indatavar, 'units', '')
        if long_name is None:
            long_name = getattr(indatavar, 'long_name', '')
        attrs = dict(units=units, long_name=long_name)
        src_fill_value = getattr(indatavar, '_FillValue', np.nan)
        if fill_missing is None:
            tgt_fill_value = np.nan
            attrs.update(_FillValue=tgt_fill_value)
        else:
            tgt_fill_value = np.float(fill_missing)

        indata = indatavar[:]
        indata = np.ma.masked_values(indata, src_fill_value, copy=False)
        if factor:
            indata = indata * factor
        outdatavar = create_data_variable(dsout, name='rainfall_rate',
                dtype='f4', dims=('time', 'lat', 'lon'), **attrs)
        outdatavar[:] = indata.filled(tgt_fill_value)

        dsout.Conventions = 'CF-1.6'


if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser(description='Convert output from wgrib2 to CF-1.6')
    parser.add_argument('infile', help='Input netCDF file')
    parser.add_argument('outfile', help='Output netCDF file')
    parser.add_argument('--variable', help='Variable name in input file')
    parser.add_argument('--units', help='Overwrite units attribute on variable')
    parser.add_argument('--long_name', help='Overwrite long_name attribute on variable')
    parser.add_argument('--factor', type=float, help='Factor to multiply the data with (default: 1)')
    parser.add_argument('--fill_missing', type=float, help='Fill missing data with this value')
    args = parser.parse_args()

    convert(**vars(args))
