import os

import xarray as xr
import click

_time_encoding = dict(units="seconds since 1970-01-01 00:00:00", calendar="standard")


def save_ds(ds, outfile):
    ds.attrs['Conventions'] = 'CF-1.6'
    click.echo('Saving to \'{}\''.format(outfile))
    ds.to_netcdf(outfile, encoding=dict(time=_time_encoding))


def convert(infile, outfile=None, variable=None, rename={},
        factor=None, newvarname=None, units=None, long_name=None,
        select={}, squeeze=False, split_by=None):
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

        if newvarname:
            da = da.rename(newvarname)

        if squeeze:
            da = da.squeeze(drop=True)

        if select:
            da = da.isel(**select)

        dsnew = da.to_dataset()

        if rename:
            dsnew = dsnew.rename(rename)

        if outfile is None:
            outfilebase = os.path.splitext(infile)[0]
            if split_by is None:
                outfilebase += '_cf1'
        else:
            outfilebase = os.path.splitext(outfile)[0]

        if split_by:
            for i in xrange(len(dsnew[split_by])):
                ext = '_{}{:04d}.nc'.format(split_by, i)
                dssub = dsnew.isel(**{split_by: i})
                save_ds(dssub, outfilebase + ext)
        else:
            ext = '.nc'
            save_ds(dsnew, outfilebase + ext)


@click.command()
@click.argument('infile', type=click.Path(file_okay=True))
@click.option('--outfile', help='Output file (default: infile + _cf1.nc)')
@click.option('--variable', help='Name of variable to extract (default: first data variable)')
@click.option('--rename', multiple=True, help='Rename variable or dimension (e.g. --rename time1=time)')
@click.option('--factor', type=float, help='Scale the variable by this factor (remember to update units)')
@click.option('--newvarname', help='Rename the variable to this name (see http://cfconventions.org/Data/cf-standard-names/36/build/cf-standard-name-table.html)')
@click.option('--units', help='Overwrite units attribute on data variable')
@click.option('--long_name', help='Overwrite long_name attribute on data variable')
@click.option('--select', multiple=True, help='Select an index along some dimension (e.g. --select height=0)')
@click.option('--squeeze / --no-squeeze', default=False, help='Drop length-1 dimensions (default: False)')
@click.option('--split-by', help='Split along this dimension')
def cli(rename, select, **kwargs):
    """Make netCDF file CF-1.6 compliant"""
    rename = dict([rn.split('=') for rn in rename])
    select = dict([sl.split('=') for sl in select])
    for k in select:
        select[k] = int(select[k])
    convert(rename=rename, select=select, **kwargs)


if __name__ == '__main__':
    cli()
