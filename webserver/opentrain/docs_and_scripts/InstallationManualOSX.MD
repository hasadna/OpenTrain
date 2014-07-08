Mac Installation (OSX Mavericks 10.9)
=====================

First make sure you have homebrew installed in your Mac - http://brew.sh. This package manager will be used for installing most of the packages needed. If you have brew already installed, make sure your brew is updated with the latest changes/formulas by running:

```
brew doctor 
brew update
```

Installing python and update pip and setuptools:

```
brew install python # run brew uninstall python or brew update python to make sure you have latest python 2.X installed
pip install --upgrade setuptools
pip install --upgrade pip
```

Install virtualenvwrapper and Django:

```
pip install virtualenvwrapper
pip install Django==1.6.5
```

Install scipy (numpy comes together as a dependency). That could take some time, make some cofee/tea !

```
brew install homebrew/python/scipy
```

Install other needed packages for Python:

```
pip install Fabric==1.8.1
pip install South==0.8.4
pip install django-bootstrap3-datetimepicker==2.1.0
pip install django-extensions==1.2.5
pip install django-statici18n==1.1
pip install python-dateutil==2.2
pip install pytz==2013.8
pip install redis==2.9.1
pip install requests==2.0.1
pip install django-tastypie
pip install psycopg2
```

Make sure you have postgres 9.3 installed. I really recommend using http://postgresapp.com. Make sure you can access postgres by running in the command line:

```
psql #(enter \q to quit the postgres client)
```

Clone the repository by issuing command "git clone https://github.com/hasadna/OpenTrain". Now we are going to create tables and populate the database with data. To create relevant tables in the database:

```
cd OpenTrain/webserver/opentrain
python manage.py sqlcreate --router=default | psql
python manage.py syncdb
python ./manage.py migrate
```

To generate the translation, install gettext

```
brew install gettext
brew link gettext --force
./end_trans.sh # Make sure you are inside OpenTrain/webserver/opentrain
```

Now populate the database with 2013 train data, run:

```
cd OpenTrain/webserver/opentrain
python manage.py downloadgtfs --from=0 --to=1
```

And finally populate the database with some device data:

```
cd OpenTrain/webserver/FAB
fab download_db:10 --password opentrain
```
Then run the server locally by running:

```
cd OpenTrain/webserver/opentrain
python manage.py runserver
```

And access the server at http://127.0.0.1:8000/. Congratulations !