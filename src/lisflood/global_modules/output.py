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

from pcraster import report, ifthen, mapmaximum, catchmenttotal

from .zusatz import TimeoutputTimeseries
from .add1 import decompress, valuecell, loadmap, compressArray, writenet
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
        binding['Catchments'] = self.var.Catchments
        binding['1'] = None  # ?? :( ??
        # output for single column eg mapmaximum
        self.var.Tss = {}

        for tss in report_time_serie_act:
            where = report_time_serie_act[tss].where
            outpoints = binding[where]
            if where == "1":
                pass
            elif where == "Catchments":
                outpoints = decompress(outpoints)
            else:
                coord = binding[where].split()  # could be gauges, sites, lakeSites etc.
                if len(coord) % 2 == 0:
                    outpoints = valuecell(self.var.MaskMap, coord, outpoints)
                else:
                    try:
                        outpoints = loadmap(where,pcr=True)
                        outpoints = ifthen(outpoints != 0,outpoints)
                          # this is necessary if netcdf maps are loaded !! otherwise strange dis.tss
                    except:
                        msg = "Setting output points\n"
                        raise LisfloodFileError(outpoints,msg)

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
        report_maps_end = settings.report_maps_end
        report_maps_steps = settings.report_maps_steps
        report_maps_all = settings.report_maps_all

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

        # started nicely but now it becomes way to complicated, I am not happy about the next part -> has to be chaged

        checkifdouble = []  # list to check if map is reported more than once
        monthly = False
        yearly = False

        # Report END maps

        for maps in report_maps_end.keys():
            # report end map filename

            try:
                where = os.path.join(str(self.var.currentSampleNumber()), binding[maps].split("/")[-1])
            except:
                where = binding.get(maps)
            if not where:
                continue
            # Output path and name of report map
            what = 'self.var.' + report_maps_end[maps].output_var
            if where not in checkifdouble:
                checkifdouble.append(where)
                # checks if saved at same place, if no: add to list

                if self.var.currentTimeStep() == self.var.nrTimeSteps():
                    # final step: Write end maps
                    # Get start date for reporting start step
                    # (last step indeed)
                    reportStartDate = inttodate(self.var.currentTimeStep() - 1, self.var.CalendarDayStart)

                    # if suffix with '.' is part of the filename report with
                    # suffix
                    head, tail = os.path.split(where)
                    if '.' in tail:
                        if option['writeNetcdf']:
                            # CM mod: write end map to netCDF file (single)
                            # CM ##########################

                            try:
                                writenet(0, eval(what), where, self.var.DtDay, maps, report_maps_end[maps].output_var,
                                         report_maps_end[maps].unit, 'f4', reportStartDate,
                                         self.var.currentTimeStep(), self.var.currentTimeStep())
                            except Exception as e:
                                print(str(e), 'END', what, where, self.var.DtDay, maps, report_maps_end[maps].output_var,
                                      report_maps_end[maps].unit, 'f4', reportStartDate,
                                      self.var.currentTimeStep(), self.var.currentTimeStep())
                            ################################

                        else:
                            report(decompress(eval(what)), str(where))
                    else:
                        if option['writeNetcdfStack']:
                            
                            try:
                                writenet(0, eval(what), where, self.var.DtDay, maps, report_maps_end[maps].output_var,
                                         report_maps_end[maps].unit, 'f4', reportStartDate,
                                         self.var.currentTimeStep(), self.var.currentTimeStep())
                            except Exception as e:
                                print(str(e), 'END', what, where, self.var.DtDay, maps, report_maps_end[maps].output_var,
                                      report_maps_end[maps].unit, 'f4', reportStartDate,
                                      self.var.currentTimeStep(), self.var.currentTimeStep())
                            ###########################
                        else:
                            self.var.report(decompress(eval(what)), str(where))

        # Report REPORTSTEPS maps
        for maps in report_maps_steps.keys():
            # report reportsteps maps

            try:
                where = os.path.join(str(self.var.currentSampleNumber()), binding[maps].split("/")[-1])
            except:
                where = binding[maps]
            what = 'self.var.' + report_maps_steps[maps].output_var
            if not(where in checkifdouble):
                checkifdouble.append(where)
                # checks if saved at same place, if no: add to list
                if self.var.currentTimeStep() in self.var.ReportSteps:
                    flagcdf = 1  # index flag for writing nedcdf = 1 (=steps) -> indicated if a netcdf is created or maps are appended
                    frequency = "all"
                    try:
                        if report_maps_steps[maps].monthly:
                            monthly = True
                            flagcdf = 3  # set to monthly (step) flag
                            frequency = "monthly"
                    except:
                        monthly = False
                    try:
                        if report_maps_steps[maps].yearly:
                            yearly = True
                            flagcdf = 4  # set to yearly (step) flag
                            frequency = "annual"
                    except:
                        yearly = False

                    if (monthly and self.var.monthend) or (yearly and self.var.yearend) or not (monthly or yearly):
                        # checks if a flag monthly or yearly exists
                        if option['writeNetcdfStack']:
                            # Get start date for reporting start step
                            reportStartDate = inttodate(self.var.ReportSteps[0] - 1, self.var.CalendarDayStart)
                            # get step number for first reporting step
                            reportStepStart = 1
                            # get step number for last reporting step
                            reportStepEnd = self.var.ReportSteps[-1] - self.var.ReportSteps[0] + 1
                            cdfflags = CDFFlags.instance()
                            try:
                                writenet(cdfflags[flagcdf], eval(what), where, self.var.DtDay, maps,
                                         report_maps_steps[maps].output_var, report_maps_steps[maps].unit, 'f4',
                                         reportStartDate, reportStepStart, reportStepEnd, frequency)
                            except Exception as e:
                                print(" +----> ERR: {}".format(str(e)))
                                print("REP flag:{} - {} {} {} {} {} {} {} {} {} {}".format(
                                      cdfflags[flagcdf], what, where, self.var.DtDay, maps,
                                      report_maps_steps[maps].output_var, report_maps_steps[maps].unit, 'f4',
                                      reportStartDate, reportStepStart, reportStepEnd
                                      ))

                        else:
                            self.var.report(decompress(eval(what)), str(where))

        # Report ALL maps
        for maps in report_maps_all.keys():
            # report maps for all timesteps
            try:
                where = os.path.join(str(self.var.currentSampleNumber()), binding[maps].split("/")[-1])
            except:
                where = binding[maps]
            what = 'self.var.' + report_maps_all[maps].output_var
            if where not in checkifdouble:
                checkifdouble.append(where)
                # checks if saved at same place, if no: add to list

                # index flag for writing nedcdf = 1 (=all) -> indicated if a netcdf is created or maps are appended
                # cannot check only if netcdf exists, because than an old netcdf will be used accidently
                flagcdf = 2
                frequency = "all"
                try:
                    if report_maps_all[maps].monthly:
                        monthly = True
                        flagcdf = 5  # set to monthly flag
                        frequency = "monthly"
                except:
                   monthly = False
                try:
                    if report_maps_all[maps].yearly:
                        yearly = True
                        flagcdf = 6  # set to yearly flag
                        frequency = "annual"
                except:
                    yearly = False

                if (monthly and self.var.monthend) or (yearly and self.var.yearend) or not (monthly or yearly):
                    # checks if a flag monthly or yearly exists]
                    if option['writeNetcdfStack']:
                        #Get start date for reporting start step
                        reportStartDate = inttodate(binding['StepStartInt'] - 1, self.var.CalendarDayStart)
                        # CM: get step number for first reporting step which is always the first simulation step
                        # CM: first simulation step referred to reportStartDate
                        ##reportStepStart = int(binding['StepStart'])
                        reportStepStart = 1
                        #get step number for last reporting step which is always the last simulation step
                        #last simulation step referred to reportStartDate
                        reportStepEnd = binding['StepEndInt'] - binding['StepStartInt'] + 1

                        try:
                            cdfflags = CDFFlags.instance()
                            writenet(cdfflags[flagcdf], eval(what), where, self.var.DtDay, maps, report_maps_all[maps].output_var,
                                     report_maps_all[maps].unit, 'f4', reportStartDate, reportStepStart, reportStepEnd, frequency)
                        except Exception as e:
                            warnings.warn(LisfloodWarning(str(e)))
                            print(str(e), "ALL", what, where, self.var.DtDay, maps, report_maps_all[maps].output_var,
                                  report_maps_all[maps].unit, 'f4', reportStartDate,reportStepStart, reportStepEnd)
                    else:
                        self.var.report(decompress(eval(what)), trimPCRasterOutputPath(where))

        cdfflags = CDFFlags.instance()
        # set the falg to indicate if a netcdffile has to be created or is only appended
        # if reportstep than increase the counter
        if self.var.currentTimeStep() in self.var.ReportSteps:
            # FIXME magic numbers. replace indexes with descriptive keys
            cdfflags.inc(1)
            # globals.cdfFlag[1] += 1
            if self.var.monthend:
                # globals.cdfFlag[3] += 1
                cdfflags.inc(3)
            if self.var.yearend:
                # globals.cdfFlag[4] += 1
                cdfflags.inc(4)

        # increase the counter for report all maps
        cdfflags.inc(2)
        # globals.cdfFlag[2] += 1
        if self.var.monthend:
            # globals.cdfFlag[5] += 1
            cdfflags.inc(5)
        if self.var.yearend:
            # globals.cdfFlag[6] += 1
            cdfflags.inc(6)
