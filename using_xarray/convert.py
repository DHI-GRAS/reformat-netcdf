import os

import xarray as xr
import click

_time_encoding = dict(units="seconds since 1970-01-01 00:00:00", calendar="standard")


def convert(infile, outfile=None, variable=None,
        factor=None, name=None, units=None, long_name=None):
    """Convert wgrib2 netCDF to CF-1.6 format"""
    with xr.open_dataset(infile) as ds:
        # extract data array for variable
        if variable is None:
            da = ds.data_vars.values()[0]
        else:
            da = ds[variable]

        if factor:
            da *= factor

        if units is not None:
            da.attrs['units'] = units
        if long_name is not None:
            da.attrs['long_name'] = long_name

        if name is not None:
            namekw = dict(name=name)
        else:
            namekw = {}
        dsnew = da.to_dataset(**namekw)

        dsnew.attrs['Conventions'] = 'CF-1.6'

        if outfile is None:
            outfile = os.path.splitext(infile)[0] + '_cf1.nc'
        dsnew.to_netcdf(outfile, encoding=dict(time=_time_encoding))


@click.command()
@click.argument('infile', type=click.Path(file_okay=True))
@click.option('--outfile', help='Output file (default: infile + _cf1.nc)')
@click.option('--variable', help='Name of variable to extract (default: first data variable)')
@click.option('--factor', type=float, help='Scale the variable by this factor (remember to update units)')
@click.option('--name', help='Rename the variable to this name (see http://cfconventions.org/Data/cf-standard-names/36/build/cf-standard-name-table.html)')
@click.option('--units', help='Overwrite units attribute on data variable')
@click.option('--long_name', help='Overwrite long_name attribute on data variable')
def cli(**kwargs):
    """Make netCDF file CF-1.6 compliant"""
    convert(**kwargs)


if __name__ == '__main__':
    cli()
