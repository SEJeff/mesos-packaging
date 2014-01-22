%global commit     afe994774266154c544f5efc37f31a74cbf8a200 

%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global gentag      0.16.0-rc3

%global skiptests   1

Name:          mesos
Version:       0.16.0
Release:       3.%{shortcommit}%{?dist}
Summary:       Cluster manager for sharing distributed application frameworks
License:       ASL 2.0
URL:           http://mesos.apache.org/

Source0:       https://github.com/apache/mesos/archive/%{commit}/%{name}-%{version}-%{shortcommit}.tar.gz
Source1:       %{name}-tmpfiles.conf
Source2:       %{name}-master.service
Source3:       %{name}-slave.service

#####################################
# NOTE: This patch has been accepted upstream and can be removed next release
#####################################
Patch0:         https://issues.apache.org/jira/secure/attachment/12615152/MESOS-831.patch

#####################################
# NOTE: The modifications have been broken into three patches which are consistent 
# with *many* other projects, and are tracking @
#
# https://github.com/timothysc/mesos
# Full integration stream is: https://github.com/timothysc/mesos/tree/0.16.0-integ
#
# The shuffle patch is maintained because it is a
# patch that is trying to be pushed upstream, thus breaking it out as a series
# of steps doesn't make sense, but has been isolated into it's own patch per review.
####################################
#git diff --no-ext-diff 0.16.0  0.16.0-pre-shuffle > build_mods.patch
Patch1:          build_mods.patch
# git diff --no-ext-diff 0.16.0-pre-shuffle 0.16.0-post-shuffle > fileshuffle_mods.patch
# b/c order matters on a shuffle-patch. 
Patch2:          fileshuffle_mods.patch
# git diff --no-ext-diff 0.16.0 0.16.0-testing >testing_mods.patch
Patch3:          testing_mods.patch
Patch4:          libev_mod.patch

BuildRequires:  libtool
BuildRequires:  automake
BuildRequires:  autoconf
BuildRequires:  zlib-devel
BuildRequires:  libcurl-devel
BuildRequires:  http-parser-devel
BuildRequires:  boost-devel
BuildRequires:  glog-devel
BuildRequires:  gmock-devel
BuildRequires:  gtest-devel
BuildRequires:  gperftools-devel
BuildRequires:  libev-devel
BuildRequires:  leveldb-devel
BuildRequires:  protobuf-devel
BuildRequires:  python-boto
BuildRequires:  python-setuptools
BuildRequires:  protobuf-python
BuildRequires:  protobuf-java
BuildRequires:  python2-devel
BuildRequires:  zookeeper-lib-devel
BuildRequires:  openssl-devel
BuildRequires:  cyrus-sasl-devel
BuildRequires:  java-devel
BuildRequires:  systemd

Requires: protobuf-python

######################################
# NOTE: arm has no planned support upstream
# and fails to compile, thus disabled
######################################
ExcludeArch: %{arm}

%description
Apache Mesos is a cluster manager that provides efficient resource
isolation and sharing across distributed applications, or frameworks.
It can run Hadoop, MPI, Hypertable, Spark, and other applications on
a dynamically shared pool of nodes.

##############################################
%package devel
Summary:        Header files for Mesos development
Group:          Development/Libraries
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description devel
Provides header and development files for %{name}.
##############################################

%prep
%setup -q -n %{name}-%{commit}

%patch0 -p1
%patch1 -p1
%patch2 -p1
%patch3 -p1
%patch4 -p1

######################################
# NOTE: remove all bundled elements
# Still pushing upstream on removal
# but it may take some time.
######################################
rm -rf 3rdparty

%build
autoreconf -vfi
%configure --disable-static
make
######################################
# NOTE: %{?_smp_mflags}
# currently fails upstream
######################################

######################################
# NOTE: https://issues.apache.org/jira/browse/MESOS-899
# Python installation is still TBD:
#
# export PYTHONPATH=${PYTHONPATH}:{buildroot}{python_sitearch}
# mkdir -p {buildroot}{python_sitearch}
# python src/python/setup.py install --prefix={buildroot}{python_sitearch}
######################################

%check
######################################
# NOTE: as of 0.16.0 &> there has been a change in the startup routines which cause
# a substantial number of tests to fail/hang under mock.  However, they run fine under a local environment
# so they are disabled by default at this time.
######################################
%if %skiptests
  echo "Skipping tests, do to mock issues"
%else
  export LD_LIBRARY_PATH=`pwd`/src/.libs
  make check 
%endif

%install
%make_install 

# fedora guidelines no .a|.la
rm -f %{buildroot}%{_libdir}/*.la

# system integration sysconfig setting
mv %{buildroot}%{_sysconfdir}/%{name}/deploy/* %{buildroot}%{_sysconfdir}/%{name}
rm -rf mv %{buildroot}%{_sysconfdir}/%{name}/deploy

mkdir -p %{buildroot}%{_sysconfdir}/tmpfiles.d
install -m 0644 %{SOURCE1} %{buildroot}%{_sysconfdir}/tmpfiles.d/%{name}.conf

mkdir -p -m0755 %{buildroot}/%{_var}/log/%{name}
mkdir -p %{buildroot}%{_unitdir}
install -m 0644 %{SOURCE2} %{SOURCE3} %{buildroot}%{_unitdir}/

mkdir -p %{buildroot}%{python_sitelib}
mv %{buildroot}%{_libexecdir}/%{name}/python/%{name} %{buildroot}%{python_sitelib}
rm -rf %{buildroot}%{_libexecdir}/%{name}/python

############################################
%files
%doc LICENSE README.md
%{_libdir}/libmesos-%{version}.so.*
%{_bindir}/mesos*
%{_sbindir}/mesos-*
%{_datadir}/%{name}/
%{_libexecdir}/%{name}/
#system integration aspects
%{_sysconfdir}/%{name}/
%{python_sitelib}/%{name}/
%{_var}/log/%{name}/
%config(noreplace) %_sysconfdir/tmpfiles.d/%{name}.conf
%{_unitdir}/%{name}*.service

%files devel
%doc LICENSE README.md
%{_includedir}/mesos/
%{_libdir}/libmesos.so
%{_libdir}/pkgconfig/%{name}.pc
############################################

%pre
getent group mesos >/dev/null || groupadd -f -r mesos
if ! getent passwd mesos >/dev/null ; then
      useradd -r -g mesos -d %{_sharedstatedir}/%{name} -s /sbin/nologin \
              -c "%{name} daemon account" mesos
fi
exit 0

%post
%systemd_post %{name}-slave.service %{name}-master.service
/sbin/ldconfig

%preun
%systemd_preun %{name}-slave.service %{name}-master.service

%postun
%systemd_postun_with_restart %{name}-slave.service %{name}-master.service
/sbin/ldconfig

%changelog
* Mon Jan 20 2014 Timothy St. Clair <tstclair@redhat.com> - 0.16.0-3.afe9947
- Updated to 0.16.0-rc3

* Mon Jan 13 2014 Timothy St. Clair <tstclair@redhat.com> - 0.16.0-2.d0cb03f
- Updating per review

* Tue Nov 19 2013 Timothy St. Clair <tstclair@redhat.com> - 0.16.0-1.d3557e8
- Update to latest upstream tip.

* Thu Oct 31 2013 Timothy St. Clair <tstclair@redhat.com> - 0.15.0-4.42f8640
- Merge in latest upstream developments 

* Fri Oct 18 2013 Timothy St. Clair <tstclair@redhat.com> - 0.15.0-4.464661f
- Package restructuring for subsuming library dependencies dependencies. 

* Thu Oct 3 2013 Timothy St. Clair <tstclair@redhat.com> - 0.15.0-3.8037f97
- Cleaning package for review

* Fri Sep 20 2013 Timothy St. Clair <tstclair@redhat.com> - 0.15.0-0.2.01ccdb
- Cleanup for system integration

* Tue Sep 17 2013 Timothy St. Clair <tstclair@redhat.com> - 0.15.0-0.1.1bc2941 
- Update to the latest mesos HEAD

* Wed Aug 14 2013 Igor Gnatenko <i.gnatenko.brain@gmail.com> - 0.12.1-0.4.dff92ff
- spec: cleanups and fixes
- spec: fix systemd daemon

* Mon Aug 12 2013 Timothy St. Clair <tstclair@redhat.com> - 0.12.1-0.3.dff92ff 
- Update and add install targets. 

* Fri Aug  9 2013 Igor Gnatenko <i.gnatenko.brain@gmail.com> - 0.12.1-0.2.cba04c1
- Update to latest
- Add python-boto as BR
- other fixes

* Thu Aug  1 2013 Igor Gnatenko <i.gnatenko.brain@gmail.com> - 0.12.1-0.1.eb17018
- Initial release
