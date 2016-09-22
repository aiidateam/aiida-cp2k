How to install the CP2K plugin for AiiDA:
========================================

1) Obtaining the source code. Clone CP2K-AiiDA plugin from https://yakutovich@bitbucket.org/yakutovich/cp2k-aiida-plugin.git into some directory. If you do not plan to contribute to the plugin development try to keep this folder unchanged. This will simplify for you the updates of the plugin in the future.

2) Setting up two new data classes (gaussian basisset, gaussian pseudo). For the moment CP2K plugin contains two classes which are not yet known by AiiDA. As soon as they will be incorporated into AiiDA this step of the HOWTO will be removed.

   a) Go into the folder were AiiDA is installed. 
   b) Change directory to aiida/orm/data

       > cd aiida/orm/data
   c) Create a symbolic links to gaussianbasis.py and gaussianpseudo.py:

       > ln -s /path/to/cp2k/plugin/gaussianbasisset/gaussianbasis.py

       > ln -s /path/to/cp2k/plugin/gaussianpseudo/gaussianpseudo.py

   d) Change directory to aiida/cmdline/commands/

       > cd ../../cmdline/commands/

   e) Add two new lines into the file data.py

       from gaussianpseudo  import _Gaussianpseudo

       from gaussianbasis import _Gaussianbasis


   f) Make symbolic links to enable shell access to control these basissets and pseudos:

       > ln -s /path/to/cp2k/plugin/gaussianbasisset/cmdline/gaussianbasis.py

       > ln -s /path/to/cp2k/plugin/gaussianpseudo/cmdline/gaussianpseudo.py


3) Setting up of the CP2K input plugin:

   a) Change directory to aiida/orm/calculation/job:

       > cd ../../orm/calculatioin/job

   b) Create a symbolic link to the cp2k input plugin:

       > ln -s /path/to/cp2k/plugin/input_plugin/cp2k.py

4) Setting up of the CP2K output plugin:

   a) Change directory to aiida/parsers/plugins

       > cd ../../../parsers/plugins/

   b) Create a symbolic link to the folder containing CP2K output parser:

       > ln -s /path/to/cp2k/plugin/output_plugin/cp2k/

Keeping plugin up-to-date:
=========================

From time to time you might want to update the CP2K plugin for AiiDA. This would require three very simple steps:

1) Go to the directory where the plugin is located:
   > cd /path/to/cp2k/plugin
2) Get the update from the server:
   > git pull
3) Restart the AiiDA daemon:
   > verdi daemon restart