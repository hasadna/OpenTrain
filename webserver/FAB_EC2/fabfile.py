from fabric.api import * #@UnusedWildImport
import fabric.contrib.files
import os

# Configuration for DigitalOcean
# You need to create the user manually
env.hosts = ['ec2-54-220-55-95.eu-west-1.compute.amazonaws.com']
env.user = 'ubuntu'
env.key_filename = os.path.expanduser('~/hasadna_opentrain_1.pem')

# Ec2 configuration

env.django_base_dir = os.path.join('/home/%s/' % (env.user),'opentrain/OpenTrain/webserver/opentrain')
env.repo = 'https://github.com/hasadna/OpenTrain.git'
env.repo_dir = 'opentrain/OpenTrain'  #dir after clone
env.dns = 'ec2-54-220-55-95.eu-west-1.compute.amazonaws.com'

def get_ctx():
    ctx = {
           'HOME' : '/home/' + env.user,
            'IP' : env.host,
            'USER' : env.user,
            'DJANGO_BASE_DIR' : env.django_base_dir,
            'DNS' : env.dns
            }
    return ctx

@task
@hosts('localhost')
def localhost():
    env.hosts = ['localhost']
    env.user = os.environ['USER']
    env.django_base_dir = os.path.join(os.path.dirname(os.getcwd()),'opentrain')


@task
def create_new():
    """ run all tasks to after new instance is created """
    update_host()
    update_apt()
    update_pip()
    update_git()
    update_conf()
    db_first_time()
    
@task
def update_host():
    """ general host update """
    sudo('apt-get update')
    sudo('apt-get --yes -q upgrade')

@task
def update_apt(package=None):
    """ updates/install all apt packages """
    packages = ('git',
    			'nginx',
    			'postgresql-client',
    			'postgresql',
    			'supervisor',
                'python-pip',
		        'gfortran',
                'libpq-dev',
                'python-dev',
                'redis-server',
                'libfreetype6-dev',
                'python-scipy',
                'python-numpy',
                'python'
    	)

    for p in packages:
        if not package or p == package:
            if p == 'nginx':
                sudo('apt-get install -q --yes --upgrade python-software-properties')
                sudo('add-apt-repository --yes ppa:nginx/stable')
                sudo('apt-get -q update')
            if p == 'redis-server':
                sudo('add-apt-repository --yes ppa:rwky/redis')
                sudo('apt-get -q update')
            print 'Installing package ' + p
            sudo('apt-get install -q --yes --upgrade %s' % (p))

def get_basedir(dir):
    dir = dir.rstrip('/')
    return dir.rpartition('/')[0]

@task
def update_git():
    """ pull git repo """
    with cd(env.repo_dir):
        run('git pull')

    # collect static / compile translations
    with cd(env.django_base_dir):
        with prefix('source /home/ubuntu/opentrain/bin/activate'):
            run('python manage.py migrate')
            run('mkdir -p tmp-trans') # fake folder for debug
            run('python manage.py collectstatic --noinput')
            run('python manage.py compilemessages')
            run('python manage.py compilejsi18n -l he -d django')
    
           
@task
def update_pip():
    """ updates/install all pip packages """
    sudo('pip install --upgrade pip')
    sudo('pip install setuptools --no-use-wheel --upgrade')
    put('files/requirements.txt','/tmp/requirements.txt')
    sudo('pip install -r /tmp/requirements.txt')
    
@task
def update_conf():
    """ update conf file for supervisor/nginx """
    ctx = get_ctx()
    
    run('mkdir -p log')
    run('mkdir -p bin')
    
    # copy gunicorn script
    fabric.contrib.files.upload_template('files/run_gunicorn.sh',
                                         'bin',
                                         context=ctx
                                         )
    with cd('bin'):
        run('chmod +x run_gunicorn.sh')
        
    # NGINX
    fabric.contrib.files.upload_template('files/nginx/opentrain.conf',
                                         '/etc/nginx/sites-available/',
                                         context=ctx,
                                         use_sudo=True)
    sudo('rm -f /etc/nginx/sites-enabled/opentrain.conf')
    sudo('rm -f /etc/nginx/sites-enabled/default')
    sudo('ln -s /etc/nginx/sites-available/opentrain.conf /etc/nginx/sites-enabled/opentrain.conf')
    # This is an issue in DigitalOcean
    fabric.contrib.files.uncomment('/etc/nginx/nginx.conf','server_names_hash_bucket_size',use_sudo=True)
    sudo('service nginx reload')
    sudo('service nginx restart')

    # restart conf
    fabric.contrib.files.upload_template('files/supervisor/opentrain.conf',
                                         '/etc/supervisor/conf.d/',
                                         context=ctx,
                                         use_sudo=True)
    sudo('sudo supervisorctl reread')
    sudo('supervisorctl update')
    sudo('supervisorctl restart opentrain')


@task
def reload_all():
    sudo('sudo supervisorctl reread')
    sudo('supervisorctl update')
    sudo('supervisorctl restart opentrain')
    sudo('service nginx restart')
    reload_gunicorn()

@task
def db_first_time():
    """ initialize Postgres DB """
    with cd(env.django_base_dir):
        run('python manage.py sqlcreate --router=default| sudo -u postgres psql')
        run('python manage.py syncdb --noinput')
        
@task
def db_reset():
    """ Reset (deletes and recreate) Postgres DB """
    with cd(env.django_base_dir):
        run('python manage.py sqlcreate -D --router=default | sudo -u postgres psql')
        run('python manage.py syncdb --noinput')
        
@task
def reload_gunicorn():
    """ reload the gunicorn process """
    run('kill -HUP `cat %(HOME)s/opentrain.id`' % get_ctx())


@task
def download_db(days=-1,no_restore=False):
    """ Opentrain only. backup db on remote server and donwload it locally """
    import os
    with cd(env.django_base_dir):
        if days > 0:
            run('python manage.py backupreports --days %s' % (days))
        else:
            run('python manage.py backupreports')
        localfile = '/tmp/backup.gz'
        remotefile = '/tmp/backup.gz'
        if os.path.exists(localfile):
            os.remove(localfile)    
        get(remotefile,localfile)
        if not no_restore:
            os.system('cd ../opentrain ; python manage.py restorereports')
    
@task
def analyze_reports():
    with cd(env.django_base_dir):
        run('./reanalyze.py')
        
        
@task
def copy_dir(remote,dest_dir):
    fabric.operations.get(remote, dest_dir)
    
@task
def manage(command):
    with cd(env.django_base_dir):
        run('python manage.py %s' % (command))


    
    


