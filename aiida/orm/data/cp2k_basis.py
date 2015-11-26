# -*- coding: utf-8 -*-
"""
This file contains functions to manipulate with cp2k basis sets: read, store and
load them from the database
"""
import os
import re
from aiida.orm.data.gaussian_basis import GaussianbasisData


__copyright__ = ""
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.4.1"
__contributors__ = "Aliaksandr Yakutovich, ..."



class Cp2kbasissetData(GaussianbasisData):
    """
    Cp2kbasissetData is a class which provides functionality to manipulate
    with basis sets for cp2k.
    """
    def __init__(self, atom_kind, basis_type, version=""):
        super(Cp2kbasissetData, self).__init__(atom_kind, basis_type, version)





def parse_single_basiset(basis):
    """
    :param basis:  a list of strings, where each string contains a line read
    from the basis set file. The whole list contains a SINGLE basis set

    :return name: name of the atom in the periodic table
    :return btype: basis set type
    :return version: basis set version
    :return orbital_quantum_numbers: is a list containing a set of lists, where
    each of them describes a particular orbital in the following way:
        [
            [ N, l, m, s, contracted ],
            ....
        ]

        Where:
        N           - principle quantum number
        l           - angular momentum
        m           - magnetic quantum number
        s           - spin
        contracted  - [n1,n2], if this orbital is contracted with some other
        orbitals n1 and n2, []  otherwise.

    :return exponent_contractioncoefficient: s a list containing a set of lists,
    with a set of exponent + contraction coefficient paris. For example:
        [
           [
               [ 2838.2104843030,  -0.0007019523 ],
               [  425.9069835160,  -0.0054237190 ],
               [   96.6806600316,  -0.0277505669 ],
                ....
           ],
           ....,
        ]
    """

# This code takes name of the atom and basis set type.
    name, btype = basis[0].split()[0], basis[0].split()[1]
    version = "v1.0"




# Second line contains the number of blocks
    n_blocks = int(basis[1].split()[0])


#    print "name", name
#    print "type", btype
#    print "Nblocks", n_blocks

    nline = 1
    i_bl = 0
    norbital = 0
    exponent_contractioncoefficient = []
    orbital_quantum_numbers = []


# Outer loop. It goes through all blocks containing different sets of orbitals
    while i_bl < n_blocks:

# going to the third line
        nline += 1
# getting quantum numbers fromt this line. Format is the following:
# n                lmin          lmax             nexp
#   nshell(lmin) nshell(lmin+1) ... nshell(lmax-1) nshell(lmax)
# qnumbers[0]      qnumbers[1]   qnumbers[2]      qnumbers[3]
# qnumbers[4] .....
        qnumbers = basis[nline].split()

# n_different_l is how many DIFFERENT angular momenta we have
        n_different_l = (int(qnumbers[2])) - (int(qnumbers[1]))

#        print basis[nline]


        l_qn = 0
        nline += 1
        current_column = 1


# loop over all different angular momenta
        while l_qn <= n_different_l:
            n_shell = 0
# loop over different shells of a given momenta
            while n_shell < int(qnumbers[4+l_qn]):

                m_qn = -(int(qnumbers[2]) + l_qn)
# loop over all possible magnetic quantum numbers
                while m_qn <= (int(qnumbers[1]) + l_qn):
                    orbital_quantum_numbers.append([(int(qnumbers[0])),
                                                    (int(qnumbers[1])) + l_qn,
                                                    m_qn, 0, -1])
                    exponent_contractioncoefficient.append([])
                    exp_number = 0
                    norbital += 1
# loop over all exponents
                    while exp_number < int(qnumbers[3]):
                        exponent_contractioncoefficient[norbital-1].append(
                            [float(basis[nline+exp_number].split()[0]),
                             float(basis[nline+exp_number].split()[
                                 current_column])])
                        exp_number += 1
                    m_qn += 1
                n_shell += 1
                current_column += 1
            l_qn += 1



#        print "Here"
#        print basis[nline]
#        print exponent_contractioncoefficient

        nline += int(qnumbers[3]) - 1

        i_bl += 1
#
#    i=0
#    for i in  range(len(orbital_quantum_numbers)):
#        print "------"
#        print orbital_quantum_numbers[i]
#        print
#        for  gg in   exponent_contractioncoefficient[i]:
#            print gg

    return (name, btype, version, orbital_quantum_numbers,
            exponent_contractioncoefficient)


def upload_basissetfile(filename):
    """
    Read different basis sets from a file and store them into a database

    :param filename: string containing a path to a file with basis sets
    """
    if not os.path.exists(filename):
        raise ValueError("Not a valid file")
    with open(filename) as fptr:
        txt = fptr.read()
        fptr.close()
    txt_splitted = txt.split('\n')

    txt_splitted_no_comments = []

# Removing comments and empty lines from the text and store each
# line as a single element of a list
    for line in txt_splitted:
# Do not read the part of text, which comes after '#' symbol
        tmp_line = line.split('#')[0].lstrip()
# Do not store empty lines
        if tmp_line != "":
            txt_splitted_no_comments.append(tmp_line)

#    print txt_splitted_no_comments

    tmp_basis = []   # here each single basis set will be stored temporary
    n_blocks = 0
    line_number = 0
    n_rows = 0

# Going through the whole text.
    for line in  txt_splitted_no_comments:
        tmp_basis.append(line)
#        print line, "|", n_blocks, n_rows, line_number

# First two lines contain Basis set name and the number of blocks. So they
# are treated differently then other parts of the basis
        if line_number < 2:
            if len(tmp_basis) == 2:
                n_blocks = int(tmp_basis[1].split()[0])
        else:
            if n_blocks == 0 and n_rows == 1: # conditions to finish reading
# of the basis set
# Using regular expressions to remove text in parantheses from the very first
# line, which contains the name of the basis set
                tmp_basis[0] = re.sub('\([^)]*\)', '', tmp_basis[0]) # pylint: disable=anomalous-backslash-in-string
                name, basis_type, version, orbqn, expn = parse_single_basiset(
                    tmp_basis)

# TODO(yakutovicha@gmail.com): uncomment this when you want to store basisset in
# the database:

                cp2k_basis = Cp2kbasissetData(name, basis_type, version)
                cp2k_basis.add_whole_basisset(orbqn, expn)
                print "I'm here!"
#                print expn
#                cp2k_basis.store_all()


#               print name, tp, version, orbqn
                tmp_basis = [] # empty the temporary basis set storage
                line_number = -1
#               print "Here!!!!"
            if n_rows == 0: # condition to move to the other block of orbitals
                n_rows = int(tmp_basis[-1].split()[3]) + 1
                n_blocks -= 1
            n_rows -= 1

        line_number += 1
