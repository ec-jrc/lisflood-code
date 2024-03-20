# LISFLOOD settings file (Settings.xml)

## Purpose

In LISFLOOD, all file and parameter specifications are defined in a settings file. The purpose of the settings file is to link variables and parameters in the model to in- and output files (maps, time series, tables) and numerical values. In addition, the settings file can be used to specify several *options*. The settings file has a special (XML) structure. In the next sections the general layout of the settings file is explained. Although the file layout is not particularly complex, a basic understanding of the general principles explained here is essential for doing any successful model runs.


## Layout of the settings file

A LISFLOOD settings file is made up of 4 elements, each of which has a specific function. The general structure of the file is described using XML. 

For a LISFLOOD settings file, the basic structure looks like this:
<br>
**\<lfsettings\>**&nbsp;&nbsp;&nbsp;&nbsp;Start of settings elements<br>
&nbsp;&nbsp;<span style="color:blue"> **\<lfoptions\>**</span>&nbsp;&nbsp;&nbsp;&nbsp;Start of element with options<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:blue"> LISFLOOD options (switches)</span><br>
&nbsp;&nbsp;<span style="color:blue"> **\</lfoptions\>**</span>&nbsp;&nbsp;&nbsp;&nbsp;End of element with options<br>
&nbsp;&nbsp;<span style="color:green"> **\<lfuser>**</span>&nbsp;&nbsp;&nbsp;&nbsp;Start of element with user-defined variables<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:green"> User's specific parameters and settings</span><br>
&nbsp;&nbsp;<span style="color:green"> **\</lfuser\>**</span>&nbsp;&nbsp;&nbsp;&nbsp;End of element with user-defined variables<br>
&nbsp;&nbsp;<span style="color:pink"> **\<lfbinding\>**</span>&nbsp;&nbsp;&nbsp;&nbsp;Start of element with 'binding' variables<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:pink"> LISFLOOD model general settings</span><br>
&nbsp;&nbsp;<span style="color:pink"> **\</lfbinding\>**</span>&nbsp;&nbsp;&nbsp;&nbsp;End of element with 'binding' variables<br>
**\</lfsettings\>**&nbsp;&nbsp;&nbsp;&nbsp;End of settings element<br>


## Main elements of the settings file
This file contains settings for LISFLOOD model. It is made up of 3 elements ‘lfuser’, ‘lfoptions’ and ‘lfbinding’ whose function can be briefly described as follows:

+ <span style="color:blue"> **lfoptions:**</span> it contains **switches to turn on/off specific components of the model**. Within LISFLOOD, there are two categories of options:
    - Options that activate special LISFLOOD features, such as simulate reservoirs, perform split routing, etc.
    - Options to activate the reporting of additional output maps and time series (e.g. soil moisture maps)

    The complete list of available options and default values is contained in the [Annex: settings and options](https://ec-jrc.github.io/lisflood-code/4_annex_settings_and_options/).
    
    Users are not obliged to include all available options in Settings.xml file: if one option is not specified in Settings.xml, the default option will be automatically used.
    If Users leave the ‘lfoptions’ element empty, LISFLOOD will simply run using default options (i.e. run model without optional modules; only report most basic output files). 
    However, the ‘lfoptions’ element itself (i.e. <lfoptions> </lfoptions>) has to be present, even if empty.


+ <span style="color:green"> **lfuser:**</span> it contains user-defined definition of **paths** to all in- and output files, and main model parameters (calibration + time-related).

    The ‘lfuser’ element is used to define (user-defined) text variables. These text variables are used to substitute repeatedly used expressions in the binding element. The only function of the ‘lfuser’ element is to define text variables. Users cannot use any of these text variables within the ‘lfuser’ element.

    The variables in the ‘lfuser’ elements are all text variables, and they are used simply to substitute text in the ‘lfbinding’ element. In practice, it is sometimes convenient to use the same name for a text variable that is defined in the ‘lfuser’ element and a ‘lfbinding’ variable.


+ <span style="color:pink"> **lfbinding:**</span> it contains definition of **all parameter values** of LISFLOOD model as well as **all in- and output maps, time series and tables**.

    It is possible to define everything directly in the ‘lfbinding’ element without using any text variables at al. In that case, the ‘lfuser’ element can remain empty, even though it has to be present (i.e. <lfuser> </lfuser>) [NOT recommended]

    In general, it is a good idea to use user-defined variables for everything that needs to be changed on a regular basis (paths to input maps, tables, meteorological data, and parameter values). This way Users only have to deal with the variables in the ‘lfuser’ element, without having to worry about anything in ‘lfbinding’ at all. “lfuser” allows to have all the important variables defined in the same element.

