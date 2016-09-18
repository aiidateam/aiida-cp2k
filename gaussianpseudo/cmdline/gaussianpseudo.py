# -*- coding: utf-8 -*-
import sys

from aiida.cmdline.baseclass import (
    VerdiCommandRouter, VerdiCommandWithSubcommands)
from data import Importable
from aiida import load_dbenv

class _Gaussianpseudo(VerdiCommandWithSubcommands, Importable):
    """
    Setup and manage Gaussian pseudos to be used

    This command allows to list and configure Gaussian pseudos.
    """

    def __init__(self):
        """
        A dictionary with valid commands and functions to be called.
        """
        from aiida.backends.utils import load_dbenv, is_dbenv_loaded
        if not is_dbenv_loaded():
            load_dbenv()
        from aiida.orm.data.gaussianpseudo import GaussianpseudoData

        self.dataclass=GaussianpseudoData
        self.valid_subcommands={
                'upload': (self.upload, self.complete_auto),
                'list': (self.list, self.complete_auto),
                'export': (self.export, self.complete_auto)
        }

    def upload(self, *args):
        """
        Upload all pseudopotentials in a file. 
        If a pseudo already exists, it is not uploaded.
        Returns the number of pseudos found and the number of uploaded pseudos.
        """
        import os.path


        if not len(args) == 1:
            print >> sys.stderr, ("Please provide a filename as the only argument.")
            sys.exit(1)

        from aiida.orm.data.gaussianpseudo import GaussianpseudoData as gpp
        n_gpp, n_uploaded = gpp.upload_cp2k_gpp_file(args[0])
        print "Number of pseudos found: {}. Number of new pseudos uploaded: {}".format(n_gpp, n_uploaded)

    def list(self, *args):
        """
        Print on screen the list of Gaussian pseudopotentials installed after application of optional filters.
        """
        import argparse

        parser = argparse.ArgumentParser(
                 prog=self.get_full_command_name(),
                 description='List AiiDa Gaussian pseudopotentials filtered with optional criteria.')
        parser.add_argument('-e', '--element', nargs='?',type=str,default=None,
                            help="Element (e.g. H)")
        parser.add_argument('-t', '--type', nargs='?', type=str, default=None,
                            help="Name or classification (e.g. GTH)")
        parser.add_argument('-x', '--xcfct', nargs='?', type=str, default=None,
                           help="Associated xc functional (e.g. PBE)")
        parser.add_argument('-n','--nval', nargs='?', type=str, default=None,
                            help="Number of valence electrons (e.g. 1)")
        parser.add_argument('-v','--version', nargs='?', type=int, default=None,
                            help="specific version")
        parser.add_argument('-d','--default', help='show only default pseudos (newest version)', dest='default', action='store_true')
        parser.add_argument('-a','--all', help='show all pseudo versions', dest='default', action='store_false')
        
        parser.set_defaults(with_description=False,default=True)
        args = list(args)
        parsed_args=parser.parse_args(args)

        from aiida.orm import DataFactory

        PseudoData=DataFactory('gaussianpseudo')
        pseudos = PseudoData.get_pseudos(
                  element=parsed_args.element, 
                  gpp_type=parsed_args.type, 
                  xc=parsed_args.xcfct, 
                  n_val=parsed_args.nval,
                  version=parsed_args.version,
                  default=parsed_args.default)

        row_format_header ="  {:<10} {:<15} {:<20} {:<10} {:<40} {:<10}"
        row_format = '* {:<10} {:<15} {:<20} {:<10} {:<40} {:<10}'
        print row_format_header.format("atom type", "pseudo type", "xc functional", "num. el.", "ID", "version")
        for pseudo in pseudos:
            pseudo_data=dict(pseudo.iterattrs())

            print row_format.format(pseudo_data['element'], pseudo_data['gpp_type'],
                                    pseudo_data['xc'][0] if pseudo_data['xc'] else '',
                                    pseudo_data['n_val'], pseudo_data['id'][0], pseudo_data['version'][0])

            for i in range(1,len(pseudo_data['id'])):
                print row_format.format('','(alias)',
                                        pseudo_data['xc'][i] if pseudo_data['xc'] else '',
                                        '',pseudo_data['id'][i], pseudo_data['version'][i])

    def export(self, *args):
        import argparse

        parser = argparse.ArgumentParser(
                 prog=self.get_full_command_name(),
                 description='Export AiiDa Gaussian pseudopotentials filtered with optional criteria to file.')
        parser.add_argument('filename',metavar='filename',type=str,help="Name of file to which pseudopotentials are appended.")
        parser.add_argument('-e', '--element', nargs='?',type=str,default=None,
                            help="Element (e.g. H)")
        parser.add_argument('-t', '--type', nargs='?', type=str, default=None,
                            help="Name or classification (e.g. GTH)")
        parser.add_argument('-x', '--xcfct', nargs='?', type=str, default=None,
                           help="Associated xc functional (e.g. PBE)")
        parser.add_argument('-n','--nval', nargs='?', type=str, default=None,
                            help="Number of valence electrons (e.g. 1)")
        parser.add_argument('-v','--version', nargs='?', type=int, default=None,
                            help="specific version")
        parser.add_argument('-d','--default', help='show only default pseudos (newest version)', dest='default', action='store_true')
        parser.add_argument('-a','--all', help='show all pseudo versions', dest='default', action='store_false')

        parser.set_defaults(with_description=False,default=True)
        args = list(args)
        parsed_args=parser.parse_args(args)

        from aiida.orm import DataFactory
        import os.path

        if os.path.isfile(parsed_args.filename):
            print >> sys.stdout, ("File {} already exists".format(parsed_args.filename))
        else: 
            PseudoData=DataFactory('gaussianpseudo')
            pseudos = PseudoData.get_pseudos(
                      element=parsed_args.element, 
                      gpp_type=parsed_args.type, 
                      xc=parsed_args.xcfct, 
                      n_val=parsed_args.nval,
                      version=parsed_args.version,
                      default=parsed_args.default)

            for pseudo in pseudos:
                pseudo.write_cp2k_gpp_to_file(parsed_args.filename, mode='a')

