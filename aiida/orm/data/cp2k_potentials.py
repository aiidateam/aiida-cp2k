# -*- coding: utf-8 -*-
"""
This module manages the UPF pseudopotentials in the local repository.
"""
from aiida.orm.data.singlefile import Data
from aiida.common.utils import classproperty
import re

RE_FLAGS = re.M | re.X 

# n_elec(s)  n_elec(p)  n_elec(d)  ...
# r_loc   nexp_ppl        cexp_ppl(1) ... cexp_ppl(nexp_ppl)
# nprj
# r(1)    nprj_ppnl(1)    ((hprj_ppnl(1,i,j),j=i,nprj_ppnl(1)),i=1,nprj_ppnl(1))
# r(2)    nprj_ppnl(2)    ((hprj_ppnl(2,i,j),j=i,nprj_ppnl(2)),i=1,nprj_ppnl(2))
#  .       .               .
#  .       .               .
#  .       .               .
# r(nprj) nprj_ppnl(nprj) ((hprj_ppnl(nprj,i,j),j=i,nprj_ppnl(nprj)),
#                                               i=1,nprj_ppnl(nprj))
#
# n_elec   : Number of electrons for each angular momentum quantum number
#            (electronic configuration -> s p d ...)
# r_loc    : Radius for the local part defined by the Gaussian function
#            exponent alpha_erf
# nexp_ppl : Number of the local pseudopotential functions
# cexp_ppl : Coefficients of the local pseudopotential functions
# nprj     : Number of the non-local projectors => nprj = SIZE(nprj_ppnl(:))
# r        : Radius of the non-local part for angular momentum quantum number l
#            defined by the Gaussian function exponents alpha_prj_ppnl
# nprj_ppnl: Number of the non-local projectors for the angular momentum
#            quantum number l
# hprj_ppnl: Coefficients of the non-local projector functions

        
potentials_regex = re.compile("""
            # First line: Element symbol
            #   Name of the potential
            #   Alias names (Ex: H GTH-PADE-q1 GTH-LDA-q1)
          (?P<element>[A-Z][a-z]{0,1}) (?P<name> ([ \t\r\f\v]+[-\w]+)+)[ \t\r\f\v]*[\n]
            # The second line contains the electronic configuration of valence electrons
            # n_elec(s)  n_elec(p)  n_elec(d)  ...
            # (n_elec   : Number of electrons for each angular momentum quantum number)
          (?P<el_config> ([ \t\r\f\v]*[0-9]+)+ ) [ \t\r\f\v]*[\n]
            # Third line:
            # r_loc   nexp_ppl        cexp_ppl(1) ... cexp_ppl(nexp_ppl)
            # r_loc    (float) : Radius for the local part defined by the Gaussian function exponent alpha_erf
            # nexp_ppl (int): Number of the local pseudopotential functions
            # cexp_ppl (float) : Coefficients of the local pseudopotential functions
          (?P<body_loc>
            [ \t\r\f\v]*[\d\.]+ [ \t\r\f\v]* [\d]+  ([ \t\r\f\v]+ -?[\d]+.[\d]+)* ) [ \t\r\f\v]* [\n]  
            # Fourth line:
            # nprj  (int)   : Number of the non-local projectors => nprj = SIZE(nprj_ppnl(:))
          (?P<nproj_nonloc> [ \t\r\f\v]* [\d]+ ) [ \t\r\f\v]*[\n]
            #Following lines:
            # r(1)    nprj_ppnl(1)    ((hprj_ppnl(1,i,j),j=i,nprj_ppnl(1)),i=1,nprj_ppnl(1))
            # r(2)    nprj_ppnl(2)    ((hprj_ppnl(2,i,j),j=i,nprj_ppnl(2)),i=1,nprj_ppnl(2))
            #  .       .               .
            #  .       .               .
            #  .       .               .
            # r(nprj) nprj_ppnl(nprj) ((hprj_ppnl(nprj,i,j),j=i,nprj_ppnl(nprj)),
            #                                               i=1,nprj_ppnl(nprj))
            # nprj   (int)  : Number of the non-local projectors => nprj = SIZE(nprj_ppnl(:))
            # r       (float) : Radius of the non-local part for angular momentum quantum number l
            #            defined by the Gaussian function exponents alpha_prj_ppnl
            # nprj_ppnl (float): Number of the non-local projectors for the angular momentum
            #            quantum number l
            # hprj_ppnl (float): Coefficients of the non-local projector functions            
        (?P<body_nonloc> (
          [ \t\r\f\v]*[\d\.]+ [ \t\r\f\v]* [\d]+  ( ([ \t\r\f\v]+ -?[\d]+.[\d]+)+ [ \t\r\f\v]* [\n] )*
                         )*
        ) #Multipline lines can exist, obviously, but also none (e.g. hydrogen)
         """, RE_FLAGS)
# Basis set format:
#
# Element symbol  Name of the basis set  Alias names
# nset (repeat the following block of lines nset times)
# n lmin lmax nexp nshell(lmin) nshell(lmin+1) ... nshell(lmax-1) nshell(lmax)
# a(1)      c(1,l,1)      c(1,l,2) ...      c(1,l,nshell(l)-1)      c(1,l,nshell(l)), l=lmin,lmax
# a(2)      c(2,l,1)      c(2,l,2) ...      c(2,l,nshell(l)-1)      c(2,l,nshell(l)), l=lmin,lmax
#  .         .             .                 .                       .
#  .         .             .                 .                       .
#  .         .             .                 .                       .
# a(nexp-1) c(nexp-1,l,1) c(nexp-1,l,2) ... c(nexp-1,l,nshell(l)-1) c(nexp-1,l,nshell(l)), l=lmin,lmax
# a(nexp)   c(nexp,l,1)   c(nexp,l,2)   ... c(nexp,l,nshell(l)-1)   c(nexp,l,nshell(l)), l=lmin,lmax
#
#
# nset     : Number of exponent sets
# n        : Principle quantum number (only for orbital label printing)
# lmax     : Maximum angular momentum quantum number l
# lmin     : Minimum angular momentum quantum number l
# nshell(l): Number of shells for angular momentum quantum number l
# a        : Exponent
# c        : Contraction coefficient
#
################################################################################
        
basisset_regex = re.compile("""
            #First line:
            # Element symbol  Name of the basis set  Alias names
                (?P<element>[A-Z][a-z]{0,1}) [ \t]+  #Matches the name of the element
                (?P<contraction>(\([0-9]+(\/[0-9])*\))?) [ \t]* # Matches (332/23/23) ???
                (?P<name>[\w\-\*]+)  [ \t]* #Matches the first string (name)
                (?P<aliases>([\w\-\*]*[ \t]*)*) # Aliases
                [\n]
            (?P<body>
            [ \t]*  \d+ [ \t]*[\n]
            (
                ([ \t\r\f\v]* [\d]+)+ [ \t\r\f\v]*[\n] # a bunch of integers
                (
                    ([ \t\r\f\v]* -?[\d]+\.[\d]+)+ [ \t\r\f\v]*[\n]
                )+
            )+)
            """, 
            RE_FLAGS)
            #    [ \t]* [\n] # End of first line
            # Second line: nset (repeat the following block of lines nset times, nr of exponent sets)
            #    [ \t]*(?P<pqm>\d+) [ \t]*[\n]
            # a(1)      c(1,l,1)      c(1,l,2) ...      c(1,l,nshell(l)-1)      c(1,l,nshell(l)), l=lmin,lmax
            # a(2)      c(2,l,1)      c(2,l,2) ...      c(2,l,nshell(l)-1)      c(2,l,nshell(l)), l=lmin,lmax
            #  .         .             .                 .                       .
            #  .         .             .                 .                       .
            #  .         .             .                 .                       .
            # a(nexp-1) c(nexp-1,l,1) c(nexp-1,l,2) ... c(nexp-1,l,nshell(l)-1) c(nexp-1,l,nshell(l)), l=lmin,lmax
            # a(nexp)   c(nexp,l,1)   c(nexp,l,2)   ... c(nexp,l,nshell(l)-1)   c(nexp,l,nshell(l)), l=lmin,lmax
            #
            # n        : Principle quantum number (only for orbital label printing)
            # lmax     : Maximum angular momentum quantum number l
            # lmin     : Minimum angular momentum quantum number l
            # nshell(l): Number of shells for angular momentum quantum number l
            # a        : Exponent
            # c        : Contraction coefficient
            #  (?P<body> [ \t]*)  \d+ [ \t]*[\n]
               
UPFGROUP_TYPE = 'data.upf.family'


def parse_single_potentials(match):

    # TESTING
    element =  match.group('element')
    #name = match.group('name')
    #el_config = match.group('el_config')
    #body_loc = match.group('body_loc')
    #nproj_nonloc = match.group('nproj_nonloc')
    #body_nonloc = match.group('body_nonloc')

    ##print "match:", match.group(0)
    #element=element.strip('\n')
    #name = name.strip('\n')
    #name = name.lstrip(' ')
    #el_config=el_config.strip('\n')
    #body_loc=body_loc.strip('\n')
    #nproj_nonloc=nproj_nonloc.strip('\n')
    #body_nonloc=body_nonloc.strip('\n')

    #print element + ' ' + name
    #print el_config
    #print body_loc
    #print nproj_nonloc
    #if len(body_nonloc)>0:
    #  print body_nonloc

def upload_potentials(filename):
    [parse_single_potentials(match) for match in potentials_regex.finditer(open(filename).read())]
    #~ print matches
    #~ print m.group('element')
    #~ print m.group('name')

def upload_basis_set(filename):
    import os, sys

    import aiida.common
    from aiida.common import aiidalogger
    from aiida.orm import Group
    from aiida.common.exceptions import UniquenessError, NotExistent
    from aiida.djsite.utils import get_automatic_user

    if not os.path.exists(filename):
        raise ValueError("Not a valid file")
    with open(filename) as f:
        #~ txt = f.read()
        #~ raw_input('HERE')
        txt = testtxt
        basis_sets = [parse_basisset(chunk) for chunk in basisset_regex.finditer(txt)]
        


def parse_potential(txt):
    """
    Get some relevant information from the basis set
    """
    #~ print txt
    try:
        body = txt.split('\n')
        print body[0]
        first_line_data = body.pop(0).split()
        
        element = first_line_data.pop(0)
        name = first_line_data.pop(0)
        alt_names = first_line_data
    
        valence_configuration = [int(i) for i in body.pop(0).split()]
        nr_of_valence_el = sum(valence_configuration)
        body = '\n'.join(body)
    except Exception as e:
        print e
    #~ raw_input()


class GaussianPotential(Data):
    @classmethod
    def get_or_create(cls, txt):
        from aiida.common.utils import md5_file
        
