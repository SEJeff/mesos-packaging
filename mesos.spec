%global commit      453b973bf93d55a3a8e5d7059e99c00ea460530e
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global tag         0.18.2-rc1
%global skiptests   1
%global libevver    4.15
%global py_version  2.7

Name:          mesos
Version:       0.18.2
Release:       1.%{shortcommit}%{?dist}
Summary:       Cluster manager for sharing distributed application frameworks
License:       ASL 2.0
URL:           http://mesos.apache.org/

Source0:       https://github.com/apache/mesos/archive/%{commit}/%{name}-%{version}-%{shortcommit}.tar.gz
Source1:       %{name}-tmpfiles.conf
Source2:       %{name}-master.service
Source3:       %{name}-slave.service
Source4:       %{name}-master-env.sh
Source5:       %{name}-slave-env.sh

#####################################
# NOTE: Tracking against:
# https://github.com/timothysc/mesos/tree/0.18-integ
####################################
Patch0:          mesos-0.18-integ.patch

BuildRequires: libtool
BuildRequires: automake
BuildRequires: autoconf
BuildRequires: java-devel
BuildRequires: zlib-devel
BuildRequires: libcurl-devel
BuildRequires: http-parser-devel
BuildRequires: boost-devel
BuildRequires: glog-devel
BuildRequires: gmock-devel
BuildRequires: gtest-devel
BuildRequires: gperftools-devel
BuildRequires: libev-source
BuildRequires: leveldb-devel
BuildRequires: protobuf-devel
BuildRequires: python-setuptools
BuildRequires: protobuf-python
BuildRequires: protobuf-java
BuildRequires: python2-devel
BuildRequires: zookeeper-lib-devel
BuildRequires: openssl-devel
BuildRequires: cyrus-sasl-devel
BuildRequires: systemd

BuildRequires: maven-local
BuildRequires: maven-plugin-bundle
BuildRequires: exec-maven-plugin
BuildRequires: maven-remote-resources-plugin
BuildRequires: maven-site-plugin
BuildRequires: protobuf-python
BuildRequires: python-boto

Requires: protobuf-python
Requires: python-boto

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
%package java
Summary:        Java interface for %{name}
Group:          Development/Libraries
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description java
The %{name}-java package contains Java bindings for %{name}.

##############################################
%package -n python-%{name}
Summary:        Python support for %{name}
BuildRequires:  python2-devel
Requires:       %{name}%{?_isa} = %{version}-%{release}
Requires:       python2

%description -n python-%{name}
The python-%{name} package contains Python bindings for %{name}.

##############################################

%prep
%setup -q -n %{name}-%{commit}
%patch0 -p1

######################################
# We need to rebuild libev and bind statically
# See https://bugzilla.redhat.com/show_bug.cgi?id=1049554 for details
######################################
cp -r %{_datadir}/libev-source libev-%{libevver}
cd libev-%{libevver}
autoreconf -i

######################################
# NOTE: remove all bundled elements
# Still pushing upstream on removal
# but it may take some time.
######################################
rm -rf 3rdparty

%build
######################################
# We need to rebuild libev and bind statically
# See https://bugzilla.redhat.com/show_bug.cgi?id=1049554 for details
cd libev-%{libevver}
export CFLAGS="$RPM_OPT_FLAGS -DEV_CHILD_ENABLE=0 -I$PWD"
export CXXFLAGS="$RPM_OPT_FLAGS -DEV_CHILD_ENABLE=0 -I$PWD"
%configure --enable-shared=no --with-pic
make libev.la
cd ../
######################################
export M2_HOME=/usr/share/xmvn
autoreconf -vfi
export LDFLAGS="$RPM_LD_FLAGS -L$PWD/libev-%{libevver}/.libs"
%configure --disable-static
make
######################################
# NOTE: %{?_smp_mflags}
# currently fails upstream
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

######################################
# NOTE: https://issues.apache.org/jira/browse/MESOS-899
export CFLAGS="$RPM_OPT_FLAGS -DEV_CHILD_ENABLE=0 -I$PWD"
export CXXFLAGS="$RPM_OPT_FLAGS -DEV_CHILD_ENABLE=0 -I$PWD"
export LDFLAGS="$RPM_LD_FLAGS -L$PWD/libev-%{libevver}/.libs"
export PYTHONPATH=%{buildroot}%{python_sitearch}
mkdir -p %{buildroot}%{python_sitearch}
python src/python/setup.py install --root=%{buildroot} --prefix=/usr
######################################

# fedora guidelines no .a|.la
rm -f %{buildroot}%{_libdir}/*.la

# system integration sysconfig setting
mv %{buildroot}%{_sysconfdir}/%{name}/deploy/* %{buildroot}%{_sysconfdir}/%{name}
rm -rf mv %{buildroot}%{_sysconfdir}/%{name}/deploy

mkdir -p %{buildroot}%{_sysconfdir}/tmpfiles.d
install -m 0644 %{SOURCE1} %{buildroot}%{_sysconfdir}/tmpfiles.d/%{name}.conf

install -m 0644 %{SOURCE4} %{buildroot}%{_sysconfdir}/%{name}
install -m 0644 %{SOURCE5} %{buildroot}%{_sysconfdir}/%{name}

mkdir -p -m0755 %{buildroot}/%{_var}/log/%{name}
mkdir -p -m0755 %{buildroot}/%{_var}/lib/%{name}
mkdir -p %{buildroot}%{_unitdir}
install -m 0644 %{SOURCE2} %{SOURCE3} %{buildroot}%{_unitdir}/

mkdir -p %{buildroot}%{python_sitelib}
mv %{buildroot}%{_libexecdir}/%{name}/python/%{name} %{buildroot}%{python_sitelib}
rm -rf %{buildroot}%{_libexecdir}/%{name}/python

######################
# install java bindings
######################
%mvn_artifact src/java/%{name}.pom src/java/target/%{name}-%{version}.jar
%mvn_install

############################################
%files
%doc LICENSE NOTICE
%{_libdir}/libmesos-%{version}.so.*
%{_bindir}/mesos*
%{_sbindir}/mesos-*
%{_datadir}/%{name}/
%{_libexecdir}/%{name}/
#system integration aspects
%{_sysconfdir}/%{name}/*.template
%{python_sitelib}/%{name}/
%attr(0755,mesos,mesos) %{_var}/log/%{name}/
%attr(0755,mesos,mesos) %{_var}/lib/%{name}/
%config(noreplace) %{_sysconfdir}/tmpfiles.d/%{name}.conf
%config(noreplace) %{_sysconfdir}/%{name}/*env.sh
%{_unitdir}/%{name}*.service

######################
%files devel
%doc LICENSE NOTICE
%{_includedir}/mesos/
%{_libdir}/libmesos.so
%{_libdir}/pkgconfig/%{name}.pc

######################
%files java
%doc LICENSE NOTICE
%{_jnidir}/%{name}/%{name}.jar
%{_mavenpomdir}/JPP.%{name}-%{name}.pom
%{_mavendepmapfragdir}/%{name}.xml
# we could include the java


######################
%files -n python-%{name}
%doc LICENSE NOTICE
%{python_sitearch}/mesos*.py*
%{python_sitearch}/_mesos.so
%{python_sitearch}/%{name}-%{version}-py%{py_version}.egg-info
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
* Wed May 14 2014 Timothy St. Clair <tstclair@redhat.com> - 0.18.2-1.453b973
- Rebase to latest 0.18.2-rc1

* Thu Apr 3 2014 Timothy St. Clair <tstclair@redhat.com> - 0.18.0-2.185dba5
- Updated to 0.18.0-rc6
- Fixed MESOS-1126 - dlopen libjvm.so

* Wed Mar 5 2014 Timothy St. Clair <tstclair@redhat.com> - 0.18.0-1.a411a4b
- Updated to 0.18.0-rc3
- Included sub-packaging around language bindings (Java & Python)
- Improved systemd integration
- Itegration to rebuild libev-source w/-DEV_CHILD_ENABLE=0

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
