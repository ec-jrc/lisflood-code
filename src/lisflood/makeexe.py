from distutils.core import setup
import py2exe
import numpy
import numpy.ma
import pcraster
import pcraster.framework

#import sys,os

#sys.argv.append('py2exe')

#from glob import glob

#data_files = [("Microsoft.VC90.CRT", glob(r'C:\Windows\winsxs\x86_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.21022.8_none_bcb86ed6ac711f91\*.*'))]
#setup(data_files=data_files, console=['lisf1.py'])
#setup(console=['lisf1.py'])
opts = {'py2exe': {'optimize': 0, "includes" : [ "netCDF4_utils","netcdftime","numpy","numpy.ma","pcraster"], 'dll_excludes': ["MSVCP90.dll","libzmq.pyd","geos_c.dll","api-ms-win-core-string-l1-1-0.dll","api-ms-win-core-registry-l1-1-0.dll","api-ms-win-core-errorhandling-l1-1-1.dll","api-ms-win-core-string-l2-1-0.dll","api-ms-win-core-profile-l1-1-0.dll","api-ms-win*.dll","api-ms-win-core-processthreads-l1-1-2.dll","api-ms-win-core-libraryloader-l1-2-1.dll","api-ms-win-core-file-l1-2-1.dll","api-ms-win-security-base-l1-2-0.dll","api-ms-win-eventing-provider-l1-1-0.dll","api-ms-win-core-heap-l2-1-0.dll","api-ms-win-core-libraryloader-l1-2-0.dll","api-ms-win-core-localization-l1-2-1.dll","api-ms-win-core-sysinfo-l1-2-1.dll","api-ms-win-core-synch-l1-2-0.dll","api-ms-win-core-heap-l1-2-0.dll","api-ms-win-core-handle-l1-1-0.dll","api-ms-win-core-io-l1-1-1.dll","api-ms-win-core-com-l1-1-1.dll","api-ms-win-core-memory-l1-1-2.dll","api-ms-win-core-version-l1-1-1.dll","api-ms-win-core-version-l1-1-0.dll",'api-ms-win-core-localization-obsolete-l1-3-0.dll','api-ms-win-core-delayload-l1-1-1.dll','api-ms-win-core-rtlsupport-l1-2-0.dll','api-ms-win-core-string-obsolete-l1-1-0.dll']}}
setup(console=['lisf1.py'],zipfile=None,options=opts,data_files=["OptionTserieMaps.xml"])
#setup(console=['lisf1.py'],options=opts)