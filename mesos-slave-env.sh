# This file contains environment variables that are passed to mesos-slave.
# To get a description of all options run mesos-slave --help; any option
# supported as a command-line option is also supported as an environment
# variable.

# You must at least set MESOS_master.

# The mesos master URL to contact. Should be host:port for
# non-ZooKeeper based masters, otherwise a zk:// or file:// URL.
export MESOS_master=$HOSTNAME:5050

# For isolated sandbox testing
#export MESOS_master=127.0.0.1:5050

# For a complete listing of options execute 'mesos-slave --help'
export MESOS_log_dir=/var/log/mesos
export MESOS_work_dir=/var/run/mesos
export MESOS_containerizers=docker,mesos

# systemd cgroup integration
export MESOS_isolation='cgroups/cpu,cgroups/mem'
export MESOS_cgroups_root='system.slice/mesos-slave.service'
export MESOS_cgroups_hierarchy=/sys/fs/cgroup

