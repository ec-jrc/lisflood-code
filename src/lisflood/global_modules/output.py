"""

Copyright 2019 European Union

Licensed under the EUPL, Version 1.2 or as soon they will be approved by the European Commission  subsequent versions of the EUPL (the "Licence");

You may not use this work except in compliance with the Licence.
You may obtain a copy of the Licence at:

https://joinup.ec.europa.eu/sites/default/files/inline-files/EUPL%20v1_2%20EN(1).txt

Unless required by applicable law or agreed to in writing, software distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and limitations under the Licence.

"""
from __future__ import print_function, absolute_import

import os
import warnings

from pcraster import report, ifthen, catchmenttotal, mapmaximum

from .zusatz import TimeoutputTimeseries
from .add1 import decompress, valuecell, loadmap, compressArray#, writenet
from .netcdf import writenet, output_maps_factory
from .errors import LisfloodFileError, LisfloodWarning
from .settings import inttodate, CDFFlags, LisSettings


def trimPCRasterOutputPath(output_path):
    """Right-trim the output file name to comply with the maximum length allowed by PCRaster, if necessary."""
    folder, name = os.path.split(output_path)
    if len(name) > 6:
        name = name[:6]
    return os.path.join(folder, name)


class outputTssMap(object):

    """
    # ************************************************************
    # ***** Output of time series (.tss) and maps*****************
    # ************************************************************
    """

    def __init__(self, out_variable):
        self.var = out_variable

    def initial(self):
        """ initial part of the output module
        """
        settings = LisSettings.instance()
        option = settings.options
        flags = settings.flags
        binding = settings.binding
        report_time_serie_act = settings.report_timeseries
        # output for single column eg mapmaximum
        self.var.Tss = {}

        for tss in report_time_serie_act:
            where = report_time_serie_act[tss].where
            outpoints = binding[where]
            coord = binding[where].split()  # could be gauges, sites, lakeSites etc.
            if len(coord) % 2 == 0:
                outpoints = valuecell(self.var.MaskMap, coord, outpoints)
            else:
                try:
                    outpoints = loadmap(where, pcr=True)
                    outpoints = ifthen(outpoints != 0, outpoints)
                      # this is necessary if netcdf maps are loaded !! otherwise strange dis.tss
                except Exception as e:
                    msg = "Setting output points\n {}".format(str(e))
                    raise LisfloodFileError(outpoints, msg)

            if option['MonteCarlo']:
                if os.path.exists(os.path.split(binding[tss])[0]):
                    self.var.Tss[tss] = TimeoutputTimeseries(str(binding[tss].split("/")[-1]), self.var, outpoints, noHeader=flags['noheader'])
                else:
                    msg = "Checking output timeseries \n"
                    raise LisfloodFileError(binding[tss],msg)
            else:
                if os.path.exists(os.path.split(binding[tss])[0]):
                    self.var.Tss[tss] = TimeoutputTimeseries(str(binding[tss]), self.var, outpoints, noHeader=flags['noheader'])
                else:
                    msg = "Checking output timeseries \n"
                    raise LisfloodFileError(str(binding[tss]), msg)

        # initialise output objects
        self.output_maps = output_maps_factory(self.var)

    def dynamic(self):
        """ dynamic part of the output module
        """

        # ************************************************************
        # ***** WRITING RESULTS: TIME SERIES *************************
        # ************************************************************

        # xxx=catchmenttotal(self.var.SurfaceRunForest * self.var.PixelArea, self.var.Ldd) * self.var.InvUpArea
        # self.var.Tss['DisTS'].sample(xxx)
        # self.report(self.Precipitation,binding['TaMaps'])

        # if fast init than without time series
        settings = LisSettings.instance()
        option = settings.options
        binding = settings.binding
        flags = settings.flags
        report_time_serie_act = settings.report_timeseries

        if not(option['InitLisfloodwithoutSplit']):

            if flags['loud']:
                # print the discharge of the first output map loc
                try:
                    print(" %10.2f" % self.var.Tss["DisTS"].firstout(decompress(self.var.ChanQAvg)))
                except:
                    pass

            for tss in report_time_serie_act:
                # report time series
                what = 'self.var.' + report_time_serie_act[tss].output_var
                how = report_time_serie_act[tss].operation[0] if len(report_time_serie_act[tss].operation) else ''
                if how == 'mapmaximum':
                    changed = compressArray(mapmaximum(decompress(eval(what))))
                    what = 'changed'
                if how == 'total':
                    changed = compressArray(catchmenttotal(decompress(eval(what)) * self.var.PixelAreaPcr, self.var.Ldd) * self.var.InvUpArea)
                    what = 'changed'
                self.var.Tss[tss].sample(decompress(eval(what)))

        # ************************************************************
        # ***** WRITING RESULTS: MAPS   ******************************
        # ************************************************************

        for out in self.output_maps:
            out.write()                   

        # update local output steps
        cdfflags = CDFFlags.instance()
        cdfflags.update(self.var)
