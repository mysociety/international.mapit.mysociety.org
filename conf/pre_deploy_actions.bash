#!/bin/bash

# abort on any errors
set -e

# check that we are in the expected directory
cd "$(dirname $BASH_SOURCE)"/..

# Some env variables used during development seem to make things break - set
# them back to the defaults which is what they would have on the servers.
PYTHONDONTWRITEBYTECODE=""

# create the virtual environment
virtualenv_dir='.venv'
virtualenv_activate="$virtualenv_dir/bin/activate"

if [ ! -f "$virtualenv_activate" ]
then
    python3 -m venv $virtualenv_dir
fi

source $virtualenv_activate

# Install wheel
pip install wheel

# Install the correct version of GDAL
pip install gdal==$(gdal-config --version)

# Improve SSL behaviour
pip install pyOpenSSL ndg-httpsclient pyasn1

# Install all the packages
pip install -r requirements.txt

# make sure that there is no old code (the .py files may have been git deleted)
find . -name '*.pyc' -delete

# Compile CSS
mapit_make_css

# gather all the static files in one place
python manage.py collectstatic --noinput --link
