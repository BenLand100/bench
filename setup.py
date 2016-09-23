from setuptools import setup

setup(
    name = 'bench',
    version = '0.1',
    author = 'Matt Mottram',
    author_email = 'm.mottram@qmul.ac.uk',
    description = ('Benchmarking for SNO+'),
    url = 'http://github.com/mjmottram/bench',
    packages = ['bench', 'bench'],
    scripts = ['bin/bench_submit', 'bin/bench_check_jobs'],
    data_files = [('job', ['job/job.sh', 'job/benchmark.py'])],
    install_requires = ['argparse']
)
