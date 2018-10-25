# LISFLOOD settings file

In LISFLOOD, all file and parameter specifications are defined in a settings file. The purpose of the settings file is to link variables and parameters in the model to in- and output files (maps, time series, tables) and numerical values. In addition, the settings file can be used to specify several *options*. The settings file has a special (XML) structure. In the next sections the general layout of the settings file is explained. Although the file layout is not particularly complex, a basic understanding of the general principles explained here is essential for doing any successful model runs.

The settings file has an XML ('E**x**tensible **M**arkup **L**anguage') structure. You can edit it using any text editor (e.g. Notepad, Editpad, Emacs, vi). Alternatively, you can also use a dedicated XML editor such as XMLSpy.

## Layout of the settings file

A LISFLOOD settings file is made up of 4 elements, each of which has a specific function. The general structure of the file is described using XML-tags. XML stands for 'E**x**tensible **M**arkup **L**anguage', and it is really nothing more than a way to describe data in a file. It works by putting information that goes into a (text) file between tags, and this makes it very easy add structure. For a LISFLOOD settings file, the basic structure looks like this:

```xml
    <?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>  
    \<lfsettings>     Start of settings element
       \<lfuser>      Start of element with user-defined variables
       \</lfuser>     End of element with user-defined variables
       \<lfoptions>   Start of element with options
       \</lfoptions>  End of element with options
       \<lfbinding>   Start of element with 'binding' variables
       \</lfbinding>  End of element with 'binding' variables
       \<prolog>      Start of prolog
       \</prolog>     End of prolog
    \<lfsettings>     End of settings element
```

From this you can see the following things:

-   The settings file is made up of the elements 'lfuser', 'lfoptions' and 'lfbinding'; in addition, there is a 'prolog' element (but this will ultimately disappear in future LISFLOOD versions)

-   The start of each element is indicated by the element's name wrapped in square brackets, e.g. \<element\>

-   The end of each element is indicated by a forward slash followed by the element's name, all wrapped in square brackets, e.g. \</element\>

-   All elements are part of a 'root' element called '\<lfsettings\>'.

In brief, the main function of each element is:

| element   | main function                                                |
| --------- | ------------------------------------------------------------ |
| lfuser    | definition of **paths** to all in- and output files, and main model parameters (calibration + time-related) |
| lfbinding | definition of all **individual** in- and output **files and model parameters** |
| lfoptions | **switches** to turn specific components of the model on or off |

The following sections explain the function of each element in more detail. This is mainly to illustrate the main concepts and how it all fits together. A detailed description of all the variables that are relevant for setting up and running LISFLOOD is given in **Chapter XXX**.

### lfuser and lfbinding elements

The 'lfbinding' element provides a very low-level way to define all model parameter values as well as all in- and output maps, time series and tables. 

The 'lfuser' element is used to define (user-defined) text variables. These text variables can be used to substitute repeatedly used expressions in the binding element. This greatly reduces the amount of work that is needed to prepare the settings file. Each variable is defined as a 'textvar' element within 'lfuser'/'lfbinding'. Each 'textvar' element has the attributes 'name' and 'value'. The following example demonstrates the main principle (note that in the examples below the prolog element is left out, but you will never need to edit this anyway) :

```xml
    <?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>  
    <lfsettings>                                                    
    <lfuser>                                                        
    <textvar name="PathMaps"                                           
    value="//cllx01/floods2/knijfjo/test/maps">                        
    </textvar>                                                          
    </lfuser>                                                       
    <lfoptions>                                                     
    </lfoptions>                                                    
    <lfbinding>                                                     
    <textvar name="LandUse" value="\$(PathMaps)/landuse.map">       
    </textvar>                                                          
    <textvar name="SoilDepth" value="\$(PathMaps)/soildep.map">     
    </textvar>                                                          
    </lfbinding>                                                    
    </lfsettings>                                                   
```

In the example two input files (maps) are defined. Both maps are in the same directory. Instead of entering the full file path for every map, we define a variable called *PathMaps* in the 'lfuser' element. This variable can then be used in the 'lfbinding' element. Note that in the 'lfbinding' element you should always wrap user-defined variables in brackets and add a leading dollar sign, e.g. *\$(PathMaps)*. Since the names of the in- and output files are usually the same for each model run, the use of user-defined variables greatly simplifies setting up the model for new catchments. In general, it is a good idea to use user-defined variables for *everything* that needs to be changed on a regular basis (paths to input maps, tables, meteorological data, parameter values). This way you only have to deal with the variables in the 'lfuser' element, without having to worry about anything in 'lfbinding' at all.

Now for a somewhat more realistic example:

```xml
   <?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>  
   <!DOCTYPE lfsettings SYSTEM "lisflood.dtd">                       
   <lfsettings>                                                    
   <lfuser>                                                        
   <comment>                                                           

   **************************************************************               
   CALIBRATION PARAMETERS                                                
   **************************************************************               

   </comment>                                                          
   <textvar name="UpperZoneTimeConstant" value="10">               
   <comment>                                                           
   Time constant for water in upper zone [days*mm\^GwAlpha]           
   </comment>                                                          
   </textvar>                                                          
   <comment>                                                           

   **************************************************************               
   FILE PATHS                                                            
   **************************************************************               

   </comment>                                                          
   <textvar name="PathMeteo"                                          
   value="//cllx01/floods2/knijfjo/test/meteo">                       
   <comment>                                                           
   Meteo path                                                            
   </comment>                                                          
   </textvar>                                                          
   <comment>                                                           

   **************************************************************               
   PREFIXES OF METEO VARIABLES                                           
   **************************************************************               

   </comment>                                                          
   <textvar name="PrefixPrecipitation" value="pr">                 
   <comment>                                                           
   prefix precipitation maps                                             
   </comment>                                                          
   </textvar>                                                          
   </lfuser>                                                       
   <lfoptions> </lfoptions>                                      
   <lfbinding>                                                     
   <textvar name="UpperZoneTimeConstant"                              
   value="$(UpperZoneTimeConstant)">                                 
   <comment>                                                           
   Time constant for water in upper zone [days\*mm\^GwAlpha]           
   </comment>                                                          
   </textvar>                                                          
   <textvar name="PrecipitationMaps"                                  
   value="$(PathMeteo)/$(PrefixPrecipitation)">                     
   <comment>                                                           
   precipitation [mm/day]                                              
   </comment>                                                          
   </textvar>                                                          
   </lfbinding>                                                    
   </lfsettings>                                                   
```

From this example, note that *anything* can be defined with 'lfuser' variables, whether it be paths, file prefixes or parameter value. At first sight it might seem odd to define model parameter like *UpperZoneTimeConstant* as a text variable when it is already defined in the 'lfbinding' element. However, in practice it is much easier to have all the important variables defined in the same element: in total the
model needs around 200 variables, parameters and file names. By specifying each of those in the 'lfbinding' element you need to specify each of them separately. Using the 'lfuser' variables this can be reduced to about 50, which greatly simplifies things. You should think of the 'lfbinding' element as a low-level way of describing the model in- and output structure: anything can be changed and any file can be in any given location, but the price to pay for this flexibility is that the definition of the input structure will take a lot of work. By using the 'lfuser' variables in a smart way, custom template settings files can be created for specific model applications (calibration, scenario modelling, operational flood forecasting). Typically, each of these applications requires its own input structure, and you can use the 'lfuser' variables to define this structure. Also, note that both the *name* and *value* of each variable must be wrapped in (single or double) quotes. Dedicated XML-editors like XmlSpy take care of this automatically, so you won't usually have to worry about this.

__**NOTES:**__

1.  It is important to remember that the *only* function of the 'lfuser' element is to *define* text variables; you can not *use* any of these text variables within the 'lfuser' element. For example, the following 'lfuser' element is *wrong* and *will not work*:

```xml
  <lfuser>                                                        
  <textvar name="PathInit"                                           
  value="//cllx01/floods2/knijfjo/test/init">                        
  <comment>                                                           
   Path to initial conditions maps                                       
  </comment>                                                          
  </textvar>                                                          
  <textvar name="LZInit" value="$(PathInit)/lzInit.map)">        
  <comment>                                                           
  Initial lower zone storage                                            
  ** USE OF USER VARIABLE WITHIN LFUSER                               
  ** IS NOT ALLOWED, SO THIS EXAMPLE WILL NOT WORK!!                  
  </comment>                                                          
  </textvar>                                                          
  </lfuser>                                                       
```

2.  It *is* possible to define *everything* directly in the 'lfbinding' element without using any text variables at all! In that case the 'lfuser' element can remain empty, even though it *has* to be present (i.e. <lfuser> </lfuser>). In general this is not recommended.

3.  Within the *lfuser* and *lfbinding* elements, model variables are organised into *groups*. This is just to make navigation in an xml editor easier.

### Variables in the lfbinding element

The variables that are defined in the 'lfbinding' element fall in either of the following categories:

1.  **Single map** (example)

```xml
<textvar name="LandUse" value="$(PathMaps)/landuse.map">\
<comment>\
Land Use Classes\
</comment>\
</textvar>
```

2. **Table** (example)

```xml
<textvar name="TabKSat1" value="$(PathTables)/ksat1.txt">\
<comment>\
Saturated conductivity [cm/day]\
</comment>\
</textvar>
```

3.  **Stack of maps** (example)

```xml
<textvar name="PrecipitationMaps"\
value="$(PathMeteo)/$(PrefixPrecipitation)">\
<comment>\
precipitation [mm/day]\
</comment>\
</textvar>
```



> __**Note:**__ Taking -as an example- a prefix that equals "*pr*", the name of each map in the stack starts with "*pr*", and ends with the number of the time step. The name of each map is made up of a total of 11 characters: 8 characters, a dot and a 3-character suffix. For instance: 
>
> - pr000000.007   : at time step 7
> - pr000035.260   : at time step 35260
>
> To avoid unexpected behaviour, do **not** use numbers in the prefix!

```xml
<textvar name="PrecipitationMaps"\
value=\"$(PathMeteo)/pr10">\
<comment>\
precipitation [mm/day]\
</comment>\
</textvar>
```

>  For the first time step this yields the following file name: pr100000.001   But this is actually interpreted as time step 100,000,001!

4.  **Time series file** (example)

```xml
<textvar name="DisTS"\ 
value="$(PathOut)/dis.tss">\
<comment>\
Reported discharge [cu m/s]\
</comment>\
</textvar>
```

5.  **Single parameter value** (example)

```xml
<textvar name="UpperZoneTimeConstant"\
value="$(UpperZoneTimeConstant)">\
<comment>\
Time constant for water in upper zone [days]\
</comment>\
</textvar>
```



[:top:](#top)

### Variables in the lfuser element

As said before the variables in the 'lfuser' elements are all text variables, and they are used simply to substitute text in the 'lfbinding' element. In practice it is sometimes convenient to use the same name for a text variable that is defined in the 'lfuser' element and a 'lfbinding' variable. For example:

```xml
<lfuser>\                                                        
<textvar name="UpperZoneTimeConstant" value="10">\               
<comment>\                                                           
Time constant for water in upper zone [days]\                        
</comment>\                                                          
</textvar>\                                                          
</lfuser>\                                                       
<lfbinding>\                                                     
<textvar name="UpperZoneTimeConstant"\                              
value="$(UpperZoneTimeConstant)">\                                 
<comment>\                                                           
Time constant for water in upper zone [days]\                        
</comment>\                                                          
</textvar>\		                                                          
</lfbinding>
```


In this case 'UpperZoneTimeConstant' in the 'lfuser' element (just a text variable) is something different from 'UpperZoneTimeConstant' in the 'lfbinding' element!

### lfoption element

The 'lfoption' element effectively allows you to switch certain parts of the model on or off. Within LISFLOOD, there are **two categories** of options:

1.  Options to activate the reporting of **additional output** maps and time series (e.g. soil moisture maps)

2.  Options that activate **special LISFLOOD modules**, such as inflow hydrographs and the simulation of reservoirs

**Viewing available options**

You can view all options by running LISFLOOD with the *\--listoptions* flag. For each option, the following information is listed:

**OptionName Choices DefaultValue**

- 'OptionName' -as you might have guessed already- simply is the name of the option. 
- 'Choices' indicates the possible values of the option, and
- 'DefaultValue' describes the default behaviour. 

For instance, if you look at the reservoir option:  "simulateReservoirs choices=(1,0) default=0" you see that the value of this option is either 0 (off) or 1 (on), and that the default value is 0 (off, i.e. do not simulate any reservoirs).

The information on the reporting options is a little bit different (and slightly confusing). Looking at the option for reporting discharge maps:

  repDischargeMaps choices=(1) noDefault

By default, discharge maps are not reported, so you would expect  something like "default=0". However, due to the way options are defined internally in the model, in this case we have no default value, which
means it is switched off.[^4] Report options that are switched *on* by default look like this:

repStateMaps choices=(1) default=1

To minimise the confusion, you should:
  1.  Ignore the "Choices" item
  2.  Interpret "noDefault" as "default=0"

This is all a bit confusing, and the displaying of option information may well change in future LISFLOOD versions.

**Defining options**

Within the 'lfoptions' element of the settings file, each option is defined using a 'setoption' element, which has the attributes 'name' and 'choice' (i.e. the actual value). For example:

```xml
<lfoptions>\                            
<setoption choice="1" name="inflow" >\ 
</lfoptions>\                    
```

**You are not obliged to use any options**: if you leave the 'lfoptions' element empty, LISFLOOD will simply run using the default values (i.e. run model without optional modules; only report most basic output files). However, the 'lfoptions' element itself (i.e. \<lfoptions\> \</lfoptions\>) *has* to be present, even if empty!
