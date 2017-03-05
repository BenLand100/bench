import os
import re
import stat
import urllib2
import tarfile
import glob
import shutil
import time
from getpass import getpass
from base64 import b64encode

# Don't install any benchmarking specific info (e.g. config) here
# as this may run on a backend (e.g. Dirac) to download snapshots

def download_snapshot(fork, commit_hash, filename, token,
                      retries = 0, retry_limit = 10):
    '''Download RAT.
    '''
    url = "https://api.github.com/repos/{0}/rat/tarball/{1}".format(fork, commit_hash)
    url_request = urllib2.Request(url)
    url_request.add_header("Authorization", "token {0}".format(token))
    try:
        remote_file = urllib2.urlopen(url_request)
    except urllib2.URLError, e:
        print "Cannot connect to GitHub: ", e
        raise
    try:
        download_size = int(remote_file.info().getheaders("Content-Length")[0])
    except IndexError:
        if retries > retry_limit:
            raise RuntimeError('Could not download 
        else:
            time.sleep(5) #wait a bit before trying again.
            download_snapshot(fork, commit_hash, filename, token, retries+1, retry_limit)
    with open(filename, 'wb') as local_file:
        local_file.write(remote_file.read())
    remote_file.close()


def get_sw_env_names(commit_hash, fork = 'snoplus'):
    '''Return the expected environment and directory names
    for a template install
    '''
    sw_name = '{0}-rat-{1}'.format(fork, commit_hash)
    env_name = '{0}-env_rat-{1}.sh'.format(fork, commit_hash)
    return sw_name, env_name


def install_rat_snapshot(install_directory, commit_hash, base_environment, token, env_additions = '', fork = 'snoplus'):
    '''Install a rat snapshot'''
    sw_name, env_name = get_sw_env_names(commit_hash, fork)
    sw_path = os.path.join(install_directory, sw_name)
    env_path = os.path.join(install_directory, env_name)

    # Check if software already installed
    if os.path.exists(os.path.join(sw_path, 'bin/rat')) and os.path.exists(env_path):
        mode = os.stat(os.path.join(sw_path, 'bin/rat')).st_mode
        if (mode & stat.S_IXUSR):
            # already installed
            return env_path

    # First download the software if not already available
    download_directory = os.path.join(install_directory, 'cache')
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)
    zipname = os.path.join(download_directory, "rat.%s.%s.tar.gz" % (fork, commit_hash))
    if not os.path.exists(zipname):
        download_snapshot(fork, commit_hash, zipname, token)

    # Untar and ensure configure script is executable
    # Note, the created folder will [fork]-rat-[commit]
    # but the commit hash in the DB could be the short 8 char version.
    # Best to ensure we install to the same as the commit char...
    f = tarfile.open(zipname)
    temp_dir = os.path.join(install_directory, "_temp_")
    try:    
        f.extractall(temp_dir)
    except:
       raise Exception('Could not extract archive.')
    
    # Now just move the installed software across
    folders = glob.glob(os.path.join(temp_dir, '{0}-rat-*'.format(fork)))
    if len(folders) != 1:
        raise IndexError("Unexpected folder structure! {0}".format(folders))
    shutil.move(folders[0], sw_path)
    os.chmod(os.path.join(sw_path, 'configure'), stat.S_IRWXU)
    
    # Configure and install
    # First, copy the base environment text, removing the rat specific lines
    base_text = env_additions
    with open(base_environment, 'r') as env_file:
        pattern = r'\s*source\s*env_rat\w*\s*' # Match env_rat-xxx
        for line in env_file.readlines():
            if not re.match(pattern, line):
                base_text += '{0}\n'.format(line)
    
    # Write this text to file
    temp_env = os.path.join(install_directory, 'installerTemp.sh')
    temp_script = os.path.join(os.getcwd(), '_temp_.sh')
    with open(temp_env, 'w') as f:
        f.write(base_text)
    # FIXME: for some reason scons doesn't always work here
    with open(temp_script, 'w') as f:
        f.write('\
#!/bin/bash\n\
source {env}\n\
cd {dir}\n\
./configure\n\
source env.sh\n\
scons\n\
exit $?'.format(env = temp_env, dir = sw_path))
    rtc = os.system('/bin/bash {0}'.format(temp_script))
    if rtc != 0:
        raise RuntimeError("Unable to install RAT")

    # RAT script sometimes not created as exe
    os.chmod(os.path.join(sw_path, 'bin/rat'), stat.S_IRWXU)

    # Now generate the final env
    base_text += 'source {0}\n'.format(os.path.join(sw_path, 'env.sh'))
    with open(env_path, 'w') as f:
        f.write(base_text)

    return env_path
