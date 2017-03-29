# reformat netCDF

Make netCDF files CF-1.6 compliant

NB: This is actually mostly about adding the "Conventions" attribute.

## Two versions

`using_xarray` is the preferred method if you can install `xarray`, `netCDF4` etc., e.g. via Anaconda.

`using_scipy` is lighter on the requirements and can be more easily compiled into an executable.
