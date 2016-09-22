How to install the cp2k plugin:

1) Clone CP2K-AiiDA plugin from https://yakutovich@bitbucket.org/yakutovich/cp2k-aiida-plugin.git into some directory. Please keep it unchanged which will simplify the updates of the plugin in the future.

[[
   For the moment CP2K plugin contains two new data classes, which are not yet a part of the AiiDA distribution. As soon as they will be incorporated into AiiDA this part of the HOWTO will be removed.
   a) Go into the folder were AiiDA is installed. 
   b) Change directory to aiida/orm/data
       > cd aiida/orm/data
   c) Make symbolic links to gaussianbasis.py and gaussianpseudo.py:
       > ln -s /path/to/cp2k/plugin/gaussianbasisset/gaussianbasis.py
       > ln -s /path/to/cp2k/plugin/gaussianpseudo/gaussianpseudo.py
   d) Change directory to aiida/cmdline/commands/
       > cd ../../cmdline/commands/
   e) Make symbolic links to enable shell access to control these basissets and pseudos:
       > ln -s /path/to/cp2k/plugin/gaussianbasisset/cmdline/gaussianbasis.py
       > ln -s /path/to/cp2k/plugin/gaussianpseudo/cmdline/gaussianpseudo.py