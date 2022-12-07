# LISFLOOD settings file (Settings.xml)

## Purpose

In LISFLOOD, all file and parameter specifications are defined in a settings file. The purpose of the settings file is to link variables and parameters in the model to in- and output files (maps, time series, tables) and numerical values. In addition, the settings file can be used to specify several *options*. The settings file has a special (XML) structure. In the next sections the general layout of the settings file is explained. Although the file layout is not particularly complex, a basic understanding of the general principles explained here is essential for doing any successful model runs.

## Layout of the settings file

A LISFLOOD settings file is made up of 4 elements, each of which has a specific function. The general structure of the file is described using XML, and it looks like this:

**\<lfsettings\>**<br>
&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:blue"> **\<lfoptions\>**</span><br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:blue"> LISFLOOD options (switches)</span><br>
&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:blue"> **\</lfoptions\>**</span><br>
&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:green"> **\<lfuser>**</span><br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:green"> User's specific parameters and settings</span><br>
&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:green"> **\</lfuser\>**</span><br>
&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:pink"> **\<lfbinding\>**</span><br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:pink"> LISFLOOD model general settings</span><br>
&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:pink"> **\</lfbinding\>**</span><br>
**\</lfsettings\>**<br>

There is a container element named **`lfsettings`**, inside which there are three main elements:

- <span style="color:blue">**lfoptions**</span> contains switches to turn on/off specific components of the model. Within LISFLOOD, there are two categories of options:
    - Options that activate special LISFLOOD features, such as simulate reservoirs, perform split routing, etc.
    - Options to activate the reporting of additional output maps and time series (e.g. soil moisture maps).

    The complete list of available options and default values is contained in the [Annex: LISFLOOD settings and options](https://ec-jrc.github.io/lisflood-code/4_annex_settings_and_options/).
    
    Users are not obliged to include all available options in the *Settings.xml* file; if one option is not specified, the model will use the default option. If users leave the `lfoptions` element empty, LISFLOOD will simply run using default options (i.e. run model without optional modules; only report most basic output files). However, the `lfoptions` element itself (i.e. <lfoptions> </lfoptions>) has to be present, even if empty, e.g.:
    
    ```xml
    <lfoptions> </lfoptions>
    ```
   

 
- <span style="color:green">**lfuser**</span> allows users to define general settings (such as simulation period and timestep, paths, etc.), model parameters, initial conditions, and input and outpuf files.

    The `lfuser` element is used to define (user-defined) text variables. The only function of the `lfuser` element is to define text variables. These text variables are used to substitute repeatedly used expressions in the `lfbinding` element. Users cannot use any of these text variables within the `lfuser` element.

+ <span style="color:pink">**lfbinding**</span> contains definition of all parameter values of LISFLOOD model as well as all in- and output maps, time series and tables.
    
    In general, the user-defined variables (paths to input maps and tables, meteorological data, parameters) are set in the `lfuser` element, and the `lfbinding` element simply read those. This way, users only have to deal with the variables in the `lfuser` element, without having to worry about anything in `lfbinding` at all.

    It is possible to define everything directly in the `lfbinding` element without using any text variables at all, i.e., without using the `lfuser` element. In that case, which is not recommended, the `lfuser` element can remain empty, even though it has to be present, e.g.:
    ```xml
    <lfbinding> </lfbinding>
    ```

You can find a thorough definition of the settings file in section [Step 2: Preparing the settings file](../3_step3_preparing-setting-file) in this User Guide.

[:top:](#top)