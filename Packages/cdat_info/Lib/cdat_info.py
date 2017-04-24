import subprocess

import version
Version = version.__describe__
ping_checked = False
check_in_progress = False


def version():
    sp = Version.split("-")
    vnm = "-".join(sp[:-2])
    vlist = vnm.split(".") + sp[-2:]
    return vlist


def get_drs_dirs():
    return [os.path.join(sys.prefix, "lib")]


def get_drs_libs():
    return ['drsfortran', 'gfortran']


sleep = 60  # minutes  (int required)

actions_sent = {}

SOURCE = 'CDAT'


def get_version():
    return Version


def get_prefix():
    import sys
    return sys.prefix


def get_sampledata_path():
    import os
    try:
        return os.path.join(os.environ["UVCDAT_SETUP_PATH"],
                            "share", "uvcdat", "sample_data")
    except KeyError:
        raise RuntimeError(
            "UVCDAT environment not configured. Please source the setup_runtime script.")


def runCheck():
    import cdat_info
    import os
    if cdat_info.ping_checked is False:
        check_in_progress = True
        val = None
        envanom = os.environ.get("UVCDAT_ANONYMOUS_LOG", None)
        if envanom is not None:
            if envanom.lower() in ['true', 'yes', 'y', 'ok']:
                val = True
            elif envanom.lower() in ['false', 'no', 'n', 'not']:
                val = False
            else:
                import warnings
                warnings.warn(
                    "UVCDAT logging environment variable UVCDAT_ANONYMOUS_LOG should be set to 'True' or 'False', you have it set to '%s', will be ignored" %
                    envanom)
        if val is None:  # No env variable looking in .uvcdat
            fanom = os.path.join(
                os.path.expanduser("~"),
                ".uvcdat",
                ".anonymouslog")
            if os.path.exists(fanom):
                f = open(fanom)
                for l in f.readlines():
                    sp = l.strip().split("UVCDAT_ANONYMOUS_LOG:")
                    if len(sp) > 1:
                        try:
                            val = eval(sp[1])
                        except:
                            pass
                f.close()

        reload(cdat_info)
        return val


def askAnonymous(val):
    import cdat_info
    import os
    while cdat_info.ping_checked is False and not val in [
            True, False]:  # couldn't get a valid value from env or file
        val2 = raw_input(
            "Allow anonymous logging usage to help improve UV-CDAT? (you can also set the environment variable UVCDAT_ANONYMOUS_LOG to yes or     no) [yes/no]")
        if val2.lower() in ['y', 'yes', 'ok']:
            val = True
        elif val2.lower() in ['n', 'no', 'not']:
            val = False
        if val in [True, False]:  # store result for next time
            try:
                fanom = os.path.join(
                    os.path.expanduser("~"), ".uvcdat", ".anonymouslog")
                if not os.path.exists(os.path.join(
                        os.path.expanduser("~"), ".uvcdat")):
                    os.makedirs(
                        os.path.join(
                            os.path.expanduser("~"),
                            ".uvcdat"))
                f = open(fanom, "w")
                print >>f, "#Store information about allowing UVCDAT anonymous logging"
                print >>f, "# Need sto be True or False"
                print >>f, "UVCDAT_ANONYMOUS_LOG: %s" % val
                f.close()
            except Exception as err:
                pass
    else:
        if cdat_info.ping_checked:
            val = cdat_info.ping
    cdat_info.ping = val
    cdat_info.ping_checked = True
    check_in_progress = False


def pingPCMDIdb(*args, **kargs):
    import cdat_info
    import os
    while cdat_info.check_in_progress:
        reload(cdat_info)
    val = cdat_info.runCheck()
    if val is False:
        cdat_info.ping_checked = True
        cdat_info.ping = False
        return
    try:
        if not cdat_info.ping:
            return
    except:
        pass
    cdat_info.askAnonymous(val)
    import threading
    kargs['target'] = pingPCMDIdbThread
    kargs['args'] = args
    try:
        t = threading.Thread(**kargs)
        t.start()
    except:
        pass


def pingPCMDIdbThread(*args, **kargs):
    import threading
    kargs['target'] = submitPing
    kargs['args'] = args
    t = threading.Thread(**kargs)
    try:
        t.start()
        import time
        time.sleep(5)  # Lets wait 5 seconds top for this ping to work
        if t.isAlive():
            try:
                t._Thread__stop()
            except:
                pass
    except:
        pass

def submitPing(source, action, source_version=None):
    try:
        import urllib2
        import sys
        import os
        import cdat_info
        import hashlib
        import urllib
        if source in ['cdat', 'auto', None]:
            source = cdat_info.SOURCE
        if cdat_info.ping:
            if not source in actions_sent.keys():
                actions_sent[source] = []
            elif action in actions_sent[source]:
                return
            else:
                actions_sent[source].append(action)
            data = {}
            uname = os.uname()
            data['platform'] = uname[0]
            data['platform_version'] = uname[2]
            data['hashed_hostname'] = hashlib.sha1(uname[1]).hexdigest()
            data['source'] = source
            if source_version is None:
                data['source_version'] = cdat_info.get_version()
            else:
                data['source_version'] = source_version
            data['action'] = action
            data['sleep'] = cdat_info.sleep
            data['hashed_username'] = hashlib.sha1(os.getlogin()).hexdigest()
            urllib2.urlopen(
                'http://uv-cdat.llnl.gov/UVCDATUsage/log/add/',
                urllib.urlencode(data))
    except Exception as err:
        pass

def download_sample_data_files(files_md5,path=None):
    """Downloads sample data from a list of files
    Default download directory is os.environ["UVCDAT_SETUP_PATH"]
    then data will be downloaded to that path.

    :Example:

        .. doctest:: download_sample_data

            >>> import os # use this to check if sample data already exists
            >>> if not os.path.isdir(os.environ['UVCDAT_SETUP_PATH']):
            ...     cdat_info.download_sample_data_files()

    :param path: String of a valid filepath.
        If None, sample data will be downloaded into the
        vcs.sample_data directory.
    :type path: `str`_ or `None`_
    """
    import requests
    import hashlib
    if not os.path.exists(files_md5) or os.path.isdir(files_md5):
        raise RuntimeError("Invalid file type for list of files: %s" % files_md5)
    if path is None:
        path = get_sampledata_path()
    samples = open(files_md5).readlines()
    download_url_root = samples[0].strip()
    if len(download_url_root.split())>1:
        # Old style
        download_url_root = "http://uvcdat.llnl.gov/cdat/sample_data/"
        n0 = 0
    else:
        n0=1
    for sample in samples[n0:]:
        good_md5, name = sample.split()
        local_filename = os.path.join(path, name)
        try:
            os.makedirs(os.path.dirname(local_filename))
        except:
            pass
        attempts = 0
        while attempts < 3:
            md5 = hashlib.md5()
            if os.path.exists(local_filename):
                f = open(local_filename)
                md5.update(f.read())
                if md5.hexdigest() == good_md5:
                    attempts = 5
                    continue
            print "Downloading: '%s' from '%s' in: %s" % (name, download_url_root, local_filename)
            r = requests.get(
                "%s/%s" % (download_url_root, name),
                stream=True)
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:  # filter local_filename keep-alive new chunks
                        f.write(chunk)
                        md5.update(chunk)
            f.close()
            if md5.hexdigest() == good_md5:
                attempts = 5
            else:
                attempts += 1

import os
import sys
os.environ["UVCDAT_SETUP_PATH"] = sys.prefix
CDMS_INCLUDE_DAP = 'yes'
CDMS_DAP_DIR = '.'
CDMS_HDF_DIR = '.'
CDMS_GRIB2LIB_DIR = sys.prefix
CDMS_INCLUDE_GRIB2LIB = 'yes'
CDMS_INCLUDE_DRS = 'no'
CDMS_INCLUDE_HDF = 'no'
CDMS_INCLUDE_PP = 'yes'
CDMS_INCLUDE_QL = 'no'
drs_file = os.path.join(sys.prefix, 'lib', 'libdrs.a')
netcdf_directory = sys.prefix
netcdf_include_directory = sys.prefix + '/include'
cdunif_include_directories = [
    sys.prefix + '/include/cdms'] + [
        sys.prefix + '/include',
        sys.prefix + '/lib/libffi-3.1/include',
        '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.11.sdk/usr/include',
    '/usr/X11R6/include'] + []
cdunif_library_directories = [sys.prefix + '/lib'] + get_drs_dirs(
) + [sys.prefix + '/lib'] + ["/usr/X11/lib", "/usr/X11R6/lib"]
cdunif_libraries = ['cdms', 'netcdf'] + ['netcdf'] + \
    get_drs_libs() + [] + ['grib2c', 'png', 'jasper']
x11include = ['/usr/X11R6/include', '/usr/include', '/opt/include']
x11libdir = ['/usr/X11R6/lib', '/usr/lib', '/opt/lib']
mathlibs = ['m']
externals = sys.prefix