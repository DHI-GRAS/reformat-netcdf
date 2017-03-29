import os

import xarray as xr
import click

_time_encoding = dict(units="seconds since 1970-01-01 00:00:00", calendar="standard")

@click.command()
@click.argument('infile')
@click.option('--varn', help='Name of variable to extract')
def convert(infile, varn='IRRATE_no_level'):
    """Convert wgrib2 netCDF to CF-1.6 format"""
    with xr.open_dataset(infile) as ds:
        # extract data array for variable
        rain_da = ds[varn]

        # convert to mm h-1
        factor = 3600.
        rain_da *= factor

        # rename to rainfall_flux
        # http://cfconventions.org/Data/cf-standard-names/36/build/cf-standard-name-table.html
        rain_ds = rain_da.to_dataset(name='rainfall_flux')

        # set conventions
        rain_ds.attrs['Conventions'] = 'CF-1.6'

        # write to output file
        outfile = os.path.splitext(infile)[0] + '_cf1.nc'
        rain_ds.to_netcdf(outfile, encoding=dict(time=_time_encoding))


if __name__ == '__main__':
    convert()
