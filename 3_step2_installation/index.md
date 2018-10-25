## Step 2: Installation of the LISFLOOD model

### On Windows systems

For Windows users the installation involves two steps:

1.  Unzip the contents of 'lisflood\_win32.zip' to an empty folder on your PC (e.g. 'lisflood')

2.  Open the file 'config.xml' in a text editor. This file contains the full path to all files and applications that are used by LISFLOOD. The items in the file are:

    - *Pcrcalc application* : this is the name of the pcrcalc application, including the full path

    - *LISFLOOD Master Code* (optional). This item is usually omitted, and LISFLOOD assumes that the master code is called 'lisflood.xml', and that it is located in the root of the 'lisflood' directory (i.e. the directory that contains  'lisflood.exe' and all libraries). If --for whatever reason- you want to overrule this behaviour, you can add a 'mastercode' element, e.g.:

      ```
      <mastercode\>d:\\Lisflood\\mastercode\\lisflood.xml<\mastercode>
      ```

      The configuration file should look something like this:

      ```xml
      <?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>  
      <!-- Lisflood configuration file, JvdK, 8 July 2004 -->
      <!-- !! This file MUST be in the same directory as lisflood.exe -->
      <!-- (or lisflood) !!! -->
      <lfconfig>
      <!-- location of pcrcalc application -->
      <pcrcalcapp>C:\pcraster\apps\pcrcalc.exe</pcrcalcapp>
      </lfconfig>
      ```


The lisflood executable is a command-line application which can be called from the command prompt ('DOS' prompt). To make life easier you may include the full path to 'lisflood.exe' in the 'Path' environment
variable. In Windows XP you can do this by selecting 'settings' from the 'Start' menu; then go to 'control panel'/'system' and go to the 'advanced' tab. Click on the 'environment variables' button. Finally, locate the 'Path' variable in the 'system variables' window and click on 'Edit' (this requires local Administrator privileges).

[[🔝](#top)](#top)


### On Linux systems

Under Linux LISFLOOD requires that the Python interpreter (version 2.7 or more recent) is installed on the system. Most Linux distributions already have Python pre-installed. If needed you can download Python free of any charge from *http://www.python.org/*

The installation process is largely identical to the Windows procedure:

1.  unzip the contents of 'lisflood\_llinux.zip' to an empty directory.
2.  Check if the file 'lisflood' is executable. If not, make it executable using: "chmod 755 lisflood"
3.  Then update the paths in the configuration file. The configuration file will look something like this:

      ```xml
      <?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>  
      <!-- Lisflood configuration file, JvdK, 8 July 2004 -->
      <!-- !! This file MUST be in the same directory as lisflood.exe -->
      <!-- (or lisflood) !!! \--\><lfconfig\><!\-- location of pcrcalc application -->
      <pcrcalcapp>/software/PCRaster/bin/pcrcalc</pcrcalcapp>
      </lfconfig>
      ```


[[🔝](#top)](#top)
