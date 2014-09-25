# This file contains environment variables that are passed to mesos-master.
# To get a description of all options run mesos-master --help; any option
# supported as a command-line option is also supported as an environment
# variable.

# Some options you're likely to want to set:
export MESOS_log_dir=/var/log/mesos
export MESOS_work_dir=/var/run/mesos
export MESOS_port=5050

# For isolated sandbox testing
#export MESOS_ip=127.0.0.1
