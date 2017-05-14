How to install the CP2K plugin for AiiDA:
========================================

1) Obtaining the source code. Clone CP2K-AiiDA plugin from https://github.com/cp2k/aiida-cp2k.git into some directory. If you do not plan to contribute to the plugin development try to keep this folder unchanged. This will simplify for you the updates of the plugin in the future.

2) Setting up of the CP2K input plugin:

   a) Change directory to aiida/orm/calculation/job:

       > cd /path/to/aiida_core/aiida/orm/calculation/job

   b) Create a symbolic link to the cp2k input plugin:

       > ln -s /path/to/aiida-cp2k/aiida_cp2k/calculations cp2k

3) Setting up of the CP2K output plugin:

   a) Change directory to aiida/parsers/plugins

       > cd /path/to/aiida_core/aiida/parsers/plugins/

   b) Create a symbolic link to the folder containing CP2K output parser:

       > ln -s /path/to/aiida-cp2k/aiida_cp2k/parsers cp2k

Keeping plugin up-to-date:
=========================

From time to time you might want to update the CP2K plugin for AiiDA. This would require three very simple steps:

1) Go to the directory where the plugin is located:

   > cd /path/to/aiida-cp2k

2) Get the update from the server:

   > git pull

3) Restart the AiiDA daemon:

   > verdi daemon restart
