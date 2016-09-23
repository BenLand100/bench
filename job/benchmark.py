from argparse import ArgumentParser
from distutils.version import LooseVersion
import os
import glob
from subprocess import Popen
import json
import httplib
import database
import time
import re

# Globals
_scale = {'kB': 1024.0, 'mB': 1024.0*1024.0, 'gB': 1024.0*1024.0*1024.0,
          'KB': 1024.0, 'MB': 1024.0*1024.0, 'GB': 1024.0*1024.0*1024.0}
_n_events = 20
_log_name = 'bench.log'
_root_name = 'bench'
_macro_name = 'macro.mac'
_memory_limit = 3 * _scale["GB"]


class BenchmarkError(Exception):
    '''Custom error class to catch when running benchmarking.
    '''
    def __init__(self, message):
        super(BenchmarkError, self).__init__(message)


def log_reader_post_450(log_file):
    '''Read log files for RAT 4.6.0 onwards
    '''
    time_info = {}
    name_counter = {}
    # Some awkward regexing!
    proc_block_pattern = r'\s*(?P<name>.*?):\s*DSEvent:\s*(?P<calls>\d*)\s*call\w*,\s*\<?\s*(?P<time>.*?)\s*s/call,\s*<?(?P<total>.*?)s total[.]\W?'
    gsim_block_pattern = r'\s*Gsim:\s*(?P<name>.\w*):\s*(?P<calls>\d*)\s*call\w*,\s*<?\s*(?P<time>.*?)\s*s/call,\s*<?(?P<total>.*?)s total[.]\W?'

    with open(log_file, 'r') as log:
        # Add a bool to switch and exclude conditional processor lines
        proc_blocks = False
        gsim_blocks = False

        for line in log.readlines():
            if "ProcBlock::~ProcBlock" in line:
                proc_blocks = True
                gsim_blocks = False
            elif "ConditionalProcBlock::~ConditionalProcBlock" in line:
                proc_blocks = False
                gsim_blocks = False
            elif "Gsim::~Gsim" in line:
                proc_blocks = False
                gsim_blocks = True

            # Prock blocks always before gsim blocks
            if proc_blocks:
                match = re.match(proc_block_pattern, line)
            elif gsim_blocks:
                match = re.match(gsim_block_pattern, line)
            else:
                match = None

            if match:
                name = match.group('name')
                time_per_event = match.group('time')
                calls = int(match.group('calls'))
                if calls != 1:
                    # 1 call is indicative of a run call (e.g. GSim Run call)
                    if name in name_counter:
                        # e.g. multiple calls to the same processor
                        temp_name = '{0}_{0:02d}'.format(name, name_counter[name])
                        name_counter[name] += 1
                    else:
                        temp_name = name
                        name_counter[name] = 1
                    time_info[temp_name] = float(time_per_event)

        # Now find the total time per event (sum of all components)
        total_time = 0.0
        for k, v in time_info.iteritems():
            total_time += v
        time_info["Total"] = total_time
        return time_info


def get_log_reader(rat_version):
    '''LogReader factor based on rat version
    '''
    version = LooseVersion(rat_version)    
    if version > LooseVersion('4.5.0'):
        return log_reader_post_450
    else:
        raise BenchmarkError("get_log_reader: unhandled RAT version {0}".format(rat_version))


def check_memory(pid_file):
    '''Returns virtual memory of a process defined in a PID file
    '''
    # Format: "VmSize:  257852 kB"
    pattern = r'VmSize:\s*(?P<size>\d*)\s*(?P<format>\D*)\W'
    lines = ''
    with open(pid_file, 'r') as f:
        for line in f.readlines():
            lines += line
            match = re.match(pattern, line)
            if match:
                virtual_mem = float(match.group('size'))
                mem_format = match.group('format')
                return virtual_mem * _scale[mem_format]
    # The file does contain memory lines when the job is finished
    return -1



def start_rat():
    '''Start RAT running a macro to get per event statistics and memory usage
    '''
    try:
        ratdir = os.environ['RATROOT']
        ratsys = os.environ['RATSYSTEM']
    except KeyError:
        raise BenchmarkError("Missing RATROOT/RATSYSTEM in environment")
    ratexe = '{0}/bin/rat_{1}'.format(ratdir, ratsys)
    ratargs = [ratexe, '-l', _log_name, '-N', _n_events, '-o', _root_name, _macro_name]
    # Ensure all are strings
    ratargs = [str(a) for a in ratargs]
    try:
        p = Popen(args = ratargs, shell = False)
    except Exception, e:
        # Catch anything here!
        raise BenchmarkError("Unable to run rat: {0}".format(e))
    return p


def monitor_memory(process):
    '''Montor memory usage while a process is running
    '''
    # Extract the process ID (NOTE: only works on linux)
    pid_file = '/proc/{0}/status'.format(process.pid)
    # Sample memory for max of 10 mins, return max:
    max_memory = None
    while True:
        try:
            time.sleep(1)
            memory = check_memory(pid_file)
            if memory > _memory_limit:
                raise BenchmarkError("Memory usage of {1} exceeds {0} limit".format(\
                        memory, memory_limit))
            if memory > max_memory:
                max_memory = memory
            if memory < 0:
                # Assume process is done
                break
        except IOError, e:
            # Assume process is done
            break
    if not max_memory: # Also checks 0
        raise BenchmarkError("No apparent memory usage!")
    return max_memory


def get_file_sizes():
    '''Stat the output size of all ROOT files
    '''
    root_files = glob.glob("*.root")
    total_storage = 0
    for f in root_files:
        total_storage += os.path.getsize(f)
    if total_storage == 0:
        raise BenchmarkError("No output ROOT files found")
    return total_storage


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('db_server')
    parser.add_argument('db_name')
    parser.add_argument('db_auth')
    parser.add_argument('document_id')
    parser.add_argument('rat_version')
    args = parser.parse_args()

    # Put the whole of the benchmarking within a try / except
    # to catch any BenchmarkError in order to save a failed
    # state with status to the database (NB could do the post from the exception)
    try:
        process = start_rat()
        max_memory = monitor_memory(process)
        # Ensure RAT has completed
        process.communicate()
        # Get file sizes and processing times
        total_storage = get_file_sizes()
        log_reader = get_log_reader(args.rat_version)
        processor_times = log_reader(_log_name)
        # Finally, save the outputs to the database
        document = json.loads(database.get(args.db_server, args.db_name, args.db_auth, args.document_id))
        document['state'] = 'completed'
        document['eventTime'] = processor_times
        document['eventSize'] = total_storage / _n_events
        document['memoryMax'] = max_memory
        database.put(args.db_server, args.db_name, args.db_auth, args.document_id, json.dumps(document))
        print "Benchmarking complete, document {0} updated".format(args.document_id)
    except BenchmarkError, e: 
        document = json.loads(database.get(args.db_server, args.db_name, args.db_auth, args.document_id))
        document['state'] = 'failed'
        document['error'] = str(e)
        database.put(args.db_server, args.db_name, args.db_auth, args.document_id, json.dumps(document))
        raise
