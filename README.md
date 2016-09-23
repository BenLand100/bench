# Bench

Benchmarking for SNO+.

## Requirements

* Access to either a [snoing](http://github.com/snoplus/snoing) installation or CVMFS
* Batch system (SGE, PBS) running qsub

## Installation

Can be run without installation (assuming that the bench base directory is in your PYTHONPATH) or run: `python setup.py install`.

## Configuration & Usage

Ensure a config file (example in config/config.cfg) is available; all fields in [main] section must be completed.

To submit jobs:

```
bench_submit [path/to/config]
```

To reset job statuses (e.g. debugging):

```
bench_check_jobs [path/to/config]
```