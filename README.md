MapIt International
===================

This repository houses a Django project which runs
http://international.mapit.mysociety.org, mySociety's administrative boundary tool
based on heterogenous sources of boundary data for particular
countries. (This is distinct from
http://global.mapit.mysociety.org which is based on
OpenStreetMap boundary data with a single license.)

If you're looking to create a MapIt in your country, work on any of the
underlying code, or re-use it as an app in another Django project, you
probably want https://github.com/mysociety/mapit.

This repository is only for the Django project that uses and deploys MapIt in a
specific way for international.mapit.mysociety.org, so that we can include some
specific additions that other re-users of MapIt may not want.

Local Development
-----------------
There's a Vagrantfile which will install a fully working dev environment for
you.
