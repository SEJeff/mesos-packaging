%global commit     c51312665029554b49b7401f511a24ddd63bcd41 
%global shortcommit %(c=%{commit}; echo ${c:0:7})
%global tag         0.22.0
%global skiptests   1
%global libevver    4.15
%global py_version  2.7

# build unbundled for fedora but enable
# bundled builds for others.
%if 0%{?fedora} >= 20
%global unbundled   1
%else
%global unbundled   0
%endif

%global systemmvn   1

Name:          mesos
Version:       0.22.0
Release:       SNAPSHOT.1.%{shortcommit}%{?dist}
Summary:       Cluster manager for sharing distributed application frameworks
License:       ASL 2.0
URL:           http://mesos.apache.org/

Source0:       https://github.com/apache/mesos/archive/%{commit}/%{name}-%{version}-%{shortcommit}.tar.gz
Source1:       %{name}-tmpfiles.conf
Source2:       %{name}-master.service
Source3:       %{name}-slave.service
Source4:       %{name}-master
Source5:       %{name}-slave

####################################
Patch0:        mesos-0.21-integ.patch
Patch1:        mesos-0.21.0-http-parser.patch

BuildRequires: libtool
BuildRequires: automake
BuildRequires: autoconf
BuildRequires: java-devel
BuildRequires: zlib-devel
BuildRequires: libcurl-devel
BuildRequires: python-setuptools
BuildRequires: python2-devel
BuildRequires: openssl-devel
BuildRequires: cyrus-sasl-devel
BuildRequires: systemd

%if %systemmvn
BuildRequires: maven-local
BuildRequires: maven-plugin-bundle
BuildRequires: maven-gpg-plugin
BuildRequires: maven-clean-plugin
BuildRequires: maven-shade-plugin
BuildRequires: maven-dependency-plugin
BuildRequires: exec-maven-plugin
BuildRequires: maven-remote-resources-plugin
BuildRequires: maven-site-plugin
%endif

%if %unbundled
BuildRequires: http-parser-devel
BuildRequires: boost-devel
BuildRequires: glog-devel
BuildRequires: gmock-devel
BuildRequires: gflags-devel
BuildRequires: gtest-devel
%ifnarch s390 s390x
BuildRequires: gperftools-devel
%endif
BuildRequires: libev-source
BuildRequires: leveldb-devel
BuildRequires: protobuf-python
BuildRequires: protobuf-java
BuildRequires: zookeeper-devel
#BuildRequires: zookeeper-lib-devel
BuildRequires: protobuf-devel
BuildRequires: picojson-devel
BuildRequires: python-pip
BuildRequires: python-wheel
BuildRequires: subversion-devel

Requires: protobuf-python
Requires: python-boto
Requires: python-pip
Requires: python-wheel
%endif

%ifarch x86_64
%if 0%{?fedora} >= 20
Requires: docker-io
%else
Requires: docker
%endif
%endif

# The slaves will indirectly require time syncing with the master
# nodes so just call out the dependency.
Requires: ntpdate

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
%patch0 -p1 -F2
%patch1 -p1

%if %unbundled
# remove all bundled elements prior to build
rm -f `find . | grep [.]tar`

######################################
# We need to rebuild libev and bind statically
# See https://bugzilla.redhat.com/show_bug.cgi?id=1049554 for details
######################################
cp -r %{_datadir}/libev-source libev-%{libevver}
cd libev-%{libevver}
autoreconf -i
%endif

%build

echo "CXXFLAGS=$CXXFLAGS"
######################################
# We need to rebuild libev and bind statically
# See https://bugzilla.redhat.com/show_bug.cgi?id=1049554 for details
%if %unbundled
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
ZOOKEEPER_JAR="/usr/share/java/zookeeper/zookeeper.jar:/usr/share/java/slf4j/api.jar:/usr/share/java/slf4j/log4j12.jar:/usr/share/java/log4j.jar" %configure --disable-bundled --disable-static
%else
autoreconf -vfi
%configure --disable-static
%endif

make
#%{?_smp_mflags}

%check
######################################
# NOTE: as of 0.16.0 &> there has been a change in the startup routines which
# cause a substantial number of tests to fail/hang under mock.  However, they
# run fine under a local environment so they are disabled by default at this
# time.
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
%if %unbundled
export CFLAGS="$RPM_OPT_FLAGS -DEV_CHILD_ENABLE=0 -I$PWD"
export CXXFLAGS="$RPM_OPT_FLAGS -DEV_CHILD_ENABLE=0 -I$PWD"
export LDFLAGS="$RPM_LD_FLAGS -L$PWD/libev-%{libevver}/.libs"
%endif

export PYTHONPATH=%{buildroot}%{python_sitearch}
mkdir -p %{buildroot}%{python_sitearch}
pushd src/python
python setup.py install --root=%{buildroot} --prefix=/usr
popd

mkdir -p  %{buildroot}%{python_sitelib}
cp -rf %{buildroot}%{_libexecdir}/%{name}/python/%{name}/* %{buildroot}%{python_sitelib}
rm -rf %{buildroot}%{_libexecdir}/%{name}/python

pushd src/python/native
python setup.py install --root=%{buildroot} --prefix=/usr --install-lib=%{python_sitearch}
popd

rm -rf %{buildroot}%{python_sitearch}/*.pth

pushd src/python/interface
python setup.py install --root=%{buildroot} --prefix=/usr
popd
######################################

# fedora guidelines no .a|.la
rm -f %{buildroot}%{_libdir}/*.la
rm -f %{buildroot}%{_libdir}/libexamplemodule*
rm -f %{buildroot}%{_libdir}/libtest*

# Move the inclusions under mesos folder for developers
mv -f %{buildroot}%{_includedir}/stout %{buildroot}%{_includedir}/%{name}
mv -f %{buildroot}%{_includedir}/process %{buildroot}%{_includedir}/%{name}

# system integration sysconfig setting
mkdir -p %{buildroot}%{_sysconfdir}/%{name}

mkdir -p %{buildroot}%{_sysconfdir}/tmpfiles.d
install -m 0644 %{SOURCE1} %{buildroot}%{_sysconfdir}/tmpfiles.d/%{name}.conf

mkdir -p %{buildroot}%{_sysconfdir}/sysconfig
install -m 0644 %{SOURCE4} %{buildroot}%{_sysconfdir}/sysconfig
install -m 0644 %{SOURCE5} %{buildroot}%{_sysconfdir}/sysconfig

# NOTE: The following removes the deployment scripts and tooling.
# It's still debatable if we should use it.
rm -rf %{buildroot}%{_sysconfdir}/%{name}
rm -f  %{buildroot}%{_sbindir}/mesos-*.sh

mkdir -p -m0755 %{buildroot}/%{_var}/log/%{name}
mkdir -p -m0755 %{buildroot}/%{_var}/lib/%{name}
mkdir -p %{buildroot}%{_unitdir}
install -m 0644 %{SOURCE2} %{SOURCE3} %{buildroot}%{_unitdir}/

######################
# install java bindings
######################
%mvn_artifact src/java/%{name}.pom src/java/target/%{name}-%{version}.jar
%mvn_install

######################
# install the examples
######################
make clean
mkdir -p %{buildroot}%{_datadir}/%{name}
cp -rf src/examples %{buildroot}%{_datadir}/%{name}

############################################
%files
%doc LICENSE NOTICE
%{_libdir}/libmesos.so.*
%{_bindir}/mesos*
%{_sbindir}/mesos-*
%{_datadir}/%{name}/
%{_libexecdir}/%{name}/
#system integration files
%{python_sitelib}/%{name}/
%attr(0755,mesos,mesos) %{_var}/log/%{name}/
%attr(0755,mesos,mesos) %{_var}/lib/%{name}/
%config(noreplace) %{_sysconfdir}/tmpfiles.d/%{name}.conf
%config(noreplace) %{_sysconfdir}/sysconfig/%{name}*
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
%if 0%{?fedora} >= 21
%{_datadir}/maven-metadata/%{name}.xml
%{_datadir}/maven-poms/%{name}/%{name}.pom
%else
%{_mavenpomdir}/JPP.%{name}-%{name}.pom
%{_mavendepmapfragdir}/%{name}.xml
%endif

######################
%files -n python-%{name}
%doc LICENSE NOTICE
%{python_sitelib}/*
%{python_sitearch}/*
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
* Tue Dec 9 2014 Timothy St. Clair <tstclair@redhat.com> - 0.22.0-1.SNAPSHOT.ab8fa65
- Update to track next release

* Tue Dec 9 2014 Timothy St. Clair <tstclair@redhat.com> - 0.21.0-6.ab8fa65
- Fix for python bindings

* Fri Nov 21 2014 Timothy St. Clair <tstclair@redhat.com> - 0.21.0-5.ab8fa65
- Update to latest build

* Thu Oct 23 2014 Timothy St. Clair <tstclair@redhat.com> - 0.21.0-4.SNAPSHOT.e960cdf
- Update to include examples

* Thu Oct 9 2014 Timothy St. Clair <tstclair@redhat.com> - 0.21.0-3.SNAPSHOT.c96ba8f6
- Update and shifting configs to latest.

* Tue Sep 30 2014 Timothy St. Clair <tstclair@redhat.com> - 0.21.0-2.SNAPSHOT.3133734
- Removing scripts and updating systemd settings.

* Tue Sep 23 2014 Timothy St. Clair <tstclair@redhat.com> - 0.21.0-1.SNAPSHOT.3133734
- Initial prototyping

* Wed Aug 27 2014 Timothy St. Clair <tstclair@redhat.com> - 0.20.0-2.f421ffd
- Fixes for system integration

* Wed Aug 20 2014 Timothy St. Clair <tstclair@redhat.com> - 0.20.0-1.f421ffd
- Rebase to new release 0.20

* Sun Aug 17 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.18.2-6.453b973
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.18.2-5.453b973
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Tue May 27 2014 Dennis Gilmore <dennis@ausil.us> - 0.18.2-4.453b973
- add patch to enable building on all primary and secondary arches
- remove ExcludeArch %%{arm}

* Tue May 27 2014 Timothy St. Clair <tstclair@redhat.com> - 0.18.2-3.453b973
- Fixes for systemd

* Fri May 23 2014 Petr Machata <pmachata@redhat.com> - 0.18.2-2.453b973
- Rebuild for boost 1.55.0

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
