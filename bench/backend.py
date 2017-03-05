import os
import glob
import stat
import shutil
import json
import string

import installer
import config
import database


def get_backend():
    '''Backend factory'''
    if config.submit_backend == 'qsub':
        return QSub(**config.qsub)
    elif config.submit_backend == 'dirac':
        return Dirac(**config.dirac)
    else:
        raise ValueError("Unknown backend: {0}".format(config.backend))


def get_rat_versions(directory, sw_install_type):
    '''Return a list of rat versions with a rat binary within a list of directories
    '''
    if sw_install_type == "CVMFS":
        rat_directories = sorted(glob.glob(os.path.join(directory, 'sw/*/rat-*')))
    elif sw_install_type == "Snoing":
        rat_directories = sorted(glob.glob(os.path.join(directory, 'rat-*')))
    else:
        raise ValueError("Unknown install type: {0}".format(sw_install_type))
    versions = []
    for rat_dir in rat_directories:
        rat_version = os.path.basename(rat_dir)[4:]
        try:
            mode = os.stat(os.path.join(rat_dir, 'bin/rat')).st_mode
            if (mode & stat.S_IXUSR):
                versions.append(rat_version)
        except OSError:
            # Binary doesn't exist
            pass
    return versions


def get_base_env_path(sw_install_type, sw_directory, rat_version):
    '''Get the path for a base install of RAT depending on the install type
    along with additional environment info to add
    '''
    env_additions = ''
    if sw_install_type == "Snoing":
        rat_env = os.path.join(sw_directory, 'env_rat-{0}.sh'.format(rat_version))
    elif sw_install_type == "CVMFS":
        rat_env = os.path.join(sw_directory, 'sw', rat_version, 'env_rat-{0}.sh'.format(rat_version))
        env_additions = 'source {0}\n'.format(os.path.join(sw_directory, 'env_cvmfs.sh'))
    else:
        raise ValueError("Unknown software install type: {0}".format(sw_install_type))
    return rat_env, env_additions


class QSub(object):
    '''Class for submitting to SGE and PBS systems via qsub.
    '''
    def __init__(self, extra_options, queue_name, job_base_directory, sw_install_type, sw_directory, install_directory):
        self.extra_options = extra_options
        self.queue_name = queue_name
        self.job_base_directory = job_base_directory
        self.sw_install_type = sw_install_type
        self.sw_directory = sw_directory
        self.install_directory = install_directory
        self.sw_versions = get_rat_versions(self.sw_directory, self.sw_install_type) 
    

    def get_job_directory(self, job_id):
        '''Return the directory for this job
        '''
        return os.path.join(self.job_base_directory, job_id)

        
    def check_job(self, rat_version, commit_hash, document_id):
        '''Run checks to ensure we can submit to this backend
        '''
        if not os.path.exists(self.job_base_directory):
            os.makedirs(self.job_base_directory)
        job_directory = self.get_job_directory(document_id)
        if not rat_version in self.sw_versions:
            raise ValueError("RAT version {0} not available".format(rat_version))
        if os.path.exists(job_directory):
            raise RuntimeError("Directory for this job already exists: {0}".format(job_directory))
        # Finally, check to ensure software is installed if using a commit hash
        if commit_hash: # Checks both '' and None
            env_path = os.path.join(self.install_directory, 'rat-{0}'.format(commit_hash))
            # Always try to install the software
            # Need to install the software
            base_environment, env_additions = get_base_env_path(self.sw_install_type, self.sw_directory, rat_version)
            installer.install_rat_snapshot(self.install_directory, commit_hash, base_environment, config.github_token, env_additions)


    def submit_job(self, document, macro_text):
        '''Submit a job to this backend
        '''
        job_directory = self.get_job_directory(document['_id'])
        os.makedirs(job_directory)
        with open(os.path.join(job_directory, 'macro.mac'), 'w') as macro_file:
            macro_file.write(macro_text)
        # Get the rat environment path
        if document.get('commitHash', ''):
            _, rat_environment = installer.get_sw_env_names(document['commitHash'])
            rat_environment = os.path.join(self.install_directory, rat_environment)
            env_additions = ''
        else:
            rat_environment, env_additions = get_base_env_path(self.sw_install_type, self.sw_directory, document['ratVersion'])
        # Write copies of each of the other input files to this directory
        # Potentially overkill, but means we don't have to worry about submitting jobs
        # and having the base repo edited!
        # The installed and distributed version have these files in the local bench
        # and job dirs - get's hacky:
        this_dir = os.path.dirname(__file__)
        db_file = os.path.join(this_dir, 'database.py')
        bench_file = os.path.join(this_dir, '../job/benchmark.py')
        job_file = os.path.join(this_dir, '../job/job.sh')
        for filename in db_file, bench_file:
            source = os.path.join(os.path.dirname(__file__), filename)
            destination = os.path.join(job_directory, os.path.basename(filename))
            shutil.copy(source, destination)
        # Copy the job script, but first add in the environment additions
        with open(job_file, 'r') as f_in:
            # Do this in case there are escaped strings (although the same could be said for password!)
            job_template = string.Template(f_in.read())
            job_script = job_template.substitute(EnvAdditions = env_additions, 
              jobdir = job_directory, ratenv = rat_environment,
              dbserver = config.db_server, dbname = config.db_name, 
              dbauth = config.db_auth, documentid = document['_id'], 
              ratversion = document['ratVersion'])
            destination = os.path.join(job_directory, 'job.sh')
            with open(destination, 'w') as f_out:
                f_out.write(job_script)
        # Submit the job, save the updated status submission metadata to the database
        job_script = os.path.join(job_directory, 'job.sh')
        command = 'qsub {0} -q {1} -e {2} -o {2} {2}/job.sh'.format(self.extra_options,
                                                                        self.queue_name,
                                                                        job_directory)
        os.system(command)
        document['job_directory'] = job_directory
        document['state'] = 'submitted' # Leave as waiting for now
        database.put(config.db_server, config.db_name, config.db_auth, document['_id'], json.dumps(document))

