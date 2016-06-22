"""
Gaussian basis set module
"""
import os
import sys
import re
from aiida.orm.data import Data
import argparse
from aiida.djsite.db import models
# -*- coding: utf-8 -*-
__copyright__ = ""
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.4.1"
__contributors__ = "Aliaksandr Yakutovich, ..."
parser = argparse.ArgumentParser()
def equal_exponents(orb1,orb2):
    equal=True
    if len(orb1) != len(orb2):
        return False
    else:
        i=0
        while i < len(orb1):
            if (orb1[i][0] != orb2[i][0]):
                equal=False
                break
            i+=1
    return equal
def equal_coefficients(orb1,orb2):
    equal=True
    if len(orb1) != len(orb2):
        return False
    else:
        i=0
        while i < len(orb1):
            if (orb1[i][1] != orb2[i][1]):
                equal=False
                break
            i+=1
    return equal

class GaussianbasisData(Data):
    """
    GaussianbasissetData is a class aimed to provide a general way to store
    gaussian basissets from different codes within AiiDA framework.

    All important information is stored in the following variables:


    *  **__atomkind** - string containing a name of the atom.
    *  **__basistype** - string containing a basis set type
    *  **__version** - string containing a version of the basis set
    *  **__orb_qm_numbers** is a list containing a set of lists, where
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
    *   **__expcontr_coeff**  is a list containing a set
    of lists, with a set of exponent + contraction coefficient pairs.
    For example:
    [
           [
               [ 2838.2104843030,  -0.0007019523 ],
               [  425.9069835160,  -0.0054237190 ],
               [   96.6806600316,  -0.0277505669 ],
                ....
           ],
           ....,
        ]

    __orb_qm_numbers and __expcontr_coeff
    must be consistent
    """
    @property
    def element(self):
        """
        return: element
        """
        return self.get_attr('element', None)
    @property
    def id(self):
        """
        return: id
        """
        return self.get_attr('id', None)
    @property
    def tags(self):
        """
        return: tags
        """
        return self.get_attr('tags', None)
    @property
    def version(self):
        """
        return: version
        """
        return self.get_attr('version', None)
    @property
    def orbital_quantum_numbers(self):
        """
        return: orbital_quantum_numbers
        """
        return self.get_attr('orbital_quantum_numbers', None)
    @property
    def exponent_contraction_coefficients(self):
        """
        return: exponent_contraction_coefficients
        """
        return self.get_attr('exponent_contraction_coefficients', None)
    @classmethod
    def get_basis_sets(cls, filter_elements=None, filter_tags=None):
        """
        Return the UpfFamily group with the given name.
        """
        q = models.DbNode.objects.filter(type__startswith=
                                         GaussianbasisData._query_type_string)
        if filter_elements != None:
            qtmp = models.DbAttribute.objects.filter(
                   key='element', tval=filter_elements)
            q =q.filter(dbattributes__in=qtmp)
        if filter_tags:
            for tag in filter_tags:
                qtmp = models.DbAttribute.objects.filter(
                    key__startswith='tags.',
                    tval=tag)
                q =q.filter(dbattributes__in=qtmp)

        for _ in q:
            yield _.get_aiida_class()
    def get_norbitals(self):
        """
        Return the number of orbitals stored in the basis set
        :return an integer number
        """
        return len(self.get_all_orbitalquantumnumbers())
    def get_all_orbitalquantumnumbers(self):
        """
        Return a list of quantum numbers for each orbital:
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

        return: a python list
        """
        try:
            oqn = self.get_attr('orbital_quantum_numbers')
        except:
            print ("Your basis set may not be yet stored in the database, "
                   "trying to access the local data")
            try:
                oqn = self.__orb_qm_numbers
            except:
                print "I can not find any orbital stored locally"
                raise
        return oqn
    def get_all_exp_contr_coeffs(self):
        """
        Return a list of exponents and contraction coefficients for each orbital
        in the following format:
        [
           [
               [ 2838.2104843030,  -0.0007019523 ],
               [  425.9069835160,  -0.0054237190 ],
               [   96.6806600316,  -0.0277505669 ],
                ....
           ],
           ....,
        ]

        :return a python list
        """
        try:
            ecc = self.getorbital_quantum_numbers_attr('exponent_contraction_coefficients')
        except:
            print ("Your basis set may not be yet stored in the database, "
                   "trying to access the local data")
            try:
                ecc = self.__expcontr_coeff
            except:
                print "I can not find any orbital stored locally"
                raise
        return ecc
    def get_orbital(self, n_qn, l_qn='all', m_qn='all', spin='all'):
        """
        Return two lists:
            * List of orbital quantum numbers
            * List of exponents and contraction coefficients

        :param    n_qn:  principle quantum number
        :param    l_qn:  angular momentum
        :param    m_qn:  magnetic quantum number
        :param    spin:  spin

        :return two python lists
        """
        return_oqn = []
        return_ecc = []
        oqnumbers = self.get_all_orbitalquantumnumbers()
        ec_coefficients = self.get_all_exp_contr_coeffs()
        i = 0
        for oqn in oqnumbers:
            print oqn
            if(oqn[0] == n_qn and(l_qn == 'all' or oqn[1] == l_qn) and
               (oqn[2] == 'all' or oqn[2] == m_qn) and (spin == 'all' or
                                                        oqn[3] == spin)):
                return_oqn.append(oqn)
                return_ecc.append(ec_coefficients[i])
            i += 1
        if return_oqn == [] and return_ecc == []:
            parser.error("Error! Can not find orbital n={}, "
                         "l={}, m={}, n={}".format(n_qn, l_qn, m_qn, n_qn))
        return return_oqn, return_ecc
    def add_orbital(self, exp_contr_coeff,
                    n_qn, l_qn, m_qn, spin=0, contraction=-1):
        """
        Add an orbital to the list
        :param exp_contr_coeff:  list of exponents and
        contraction coefficients
        :param    n_qn:  principle quantum number
        :param    l_qn:  angular momentum
        :param    m_qn:  magnetic quantum number
        :param    spin:  spin

        :return True/False
        """
        try:
            self.__orb_qm_numbers
        except:
            self.__orb_qm_numbers = []
        self.__orb_qm_numbers.append([int(n_qn), int(l_qn), int(m_qn),
                                      spin, contraction])
        try:
            self.__expcontr_coeff
        except:
            self.__expcontr_coeff = []
        self.__expcontr_coeff.append(
            exp_contr_coeff)
        return True
    def add_whole_basisset(self, atom_kind, tags, quantum_numbers,
                           exp_contr_coeffs):
        """
        Add a full set of orbitals to the basis set
        param: atom_kind: name of the atom in the periodic table
        param: tags: tags characterizing basis
        param: version: basis set Version
        param: quantum_numbers: a list containing a set of lists, where each of
        them describes a particular orbital in the following way:
        [
            [ N, l_qn, m_qn, spin, contracted ],
            ....
        ]

        Where:
        N           - principle quantum number
        l_qn           - angular momentum
        m_qn           - magnetic quantum number
        spin           - spin
        contracted  - [n1,n2], if this orbital is contracted with some other
        orbitals n1 and n2, []  otherwise.
        param: exp_contr_coeffs:  a list containing a set of
        lists, with a set of exponent + contraction coefficient pairs. For
        example:
        [
           [
               [ 2838.2104843030,  -0.0007019523 ],
               [  425.9069835160,  -0.0054237190 ],
               [   96.6806600316,  -0.0277505669 ],
                ....
           ],
           ....,
        ]
        return: True/False

        """
        self.__atomkind = atom_kind
        self.__tags = tags
        self.__id = "-".join(tags)
        if len(quantum_numbers) != len(exp_contr_coeffs):
            parser.error("Error! The array with quantum numbers and the array "
                         "with exponents have different size! Something "
                         "is wrong...")
        size = len(quantum_numbers)
        i = 0
        while i < size:
            self.add_orbital(exp_contr_coeff=
                             exp_contr_coeffs[i],
                             n_qn=quantum_numbers[i][0],
                             l_qn=quantum_numbers[i][1],
                             m_qn=quantum_numbers[i][2],
                             spin=quantum_numbers[i][3],
                             contraction=quantum_numbers[i][4])
            i += 1
        return True
    def store_all_in_db(self):
        """
        This function which you run once your data are ready to be stored in the
        database.
        """

        q = models.DbNode.objects.filter(
            type__startswith=self._query_type_string)


        qtmp = models.DbAttribute.objects.filter(
            key='element', tval=self.__atomkind)
        q = q.filter(dbattributes__in=qtmp)
        self._set_attr('element', self.__atomkind)
        print ("There are {} basissets for the {} element in the "
               "DB".format(len(q), self.__atomkind))
        qtmp = models.DbAttribute.objects.filter(
            key='id', tval=self.__id)
        q = q.filter(dbattributes__in=qtmp)
        self._set_attr('id', self.__id)
        print ("Among them, there are {} basissets of "
               "type: {}".format(len(q), self.__id))
        if len(q) > 0:
            print("ERROR: The new basiset of type {} for the {} "
                  "atom  can NOT be  uploaded because it already exists in the "
                  "database\nOr is it a new version of the "
                  "basiset?".format(self.__id, self.__atomkind))
        else:
            print ("SUCCESS: Apploading the basiset {} {} "
                   .format(self.__atomkind, self.__id))
            self._set_attr('version', '1.0')
            self._set_attr('orbital_quantum_numbers',
                           self.__orb_qm_numbers)
            self._set_attr('exponent_contraction_coefficients',
                           self.__expcontr_coeff)
            self._set_attr('tags',self.__tags)
            self.store()
    def print_cp2k(self, filename=None):
#        print "Hey from print cp2k"
#        print self.element, self.type
        i=0
        j=0
        l=0
        to_print=[]
        to_print.append([])
        to_print[j].append([self.orbital_quantum_numbers[i][0],
                         self.orbital_quantum_numbers[i][1],
                         self.orbital_quantum_numbers[i][1],
                         len(self.exponent_contraction_coefficients[i]),
                         1])
        to_print[j].append(self.exponent_contraction_coefficients[i])

        i+=1
        while i < len(self.orbital_quantum_numbers):
            if(self.orbital_quantum_numbers[i][0] != self.orbital_quantum_numbers[i-1][0]):
                to_print.append([])
                l=0
                j+=1
                to_print[j].append([self.orbital_quantum_numbers[i][0],
                                 self.orbital_quantum_numbers[i][1],
                                 self.orbital_quantum_numbers[i][1],
                                 len(self.exponent_contraction_coefficients[i]),
                                 1])
                to_print[j].append(self.exponent_contraction_coefficients[i])
            elif (not equal_exponents(self.exponent_contraction_coefficients[i-1],
                self.exponent_contraction_coefficients[i])):
                to_print.append([])
                l=0
                j+=1
                to_print[j].append([self.orbital_quantum_numbers[i][0],
                                 self.orbital_quantum_numbers[i][1],
                                 self.orbital_quantum_numbers[i][1],
                                 len(self.exponent_contraction_coefficients[i]),
                                 1])
                to_print[j].append(self.exponent_contraction_coefficients[i])
            elif (self.orbital_quantum_numbers[i][1] !=
                  self.orbital_quantum_numbers[i-1][1]):
                to_print[j][0][2]+=1
                to_print[j].append(self.exponent_contraction_coefficients[i])
                to_print[j][0].append(1)
                l+=1
            elif (not equal_coefficients(self.exponent_contraction_coefficients[i-1],
                  self.exponent_contraction_coefficients[i])):
                to_print[j][0][4+l]+=1
                to_print[j].append(self.exponent_contraction_coefficients[i])
            i+=1
        if filename and filename != '-':
            fh = open(filename, 'a')
        else:
            fh = sys.stdout

        fh.write( "{} {}\n".format(self.element, self.id))
        fh.write( "{}\n".format(len(to_print)))
        for bset in to_print :
            for out in bset[0]:
                fh.write( "{} ".format(out))
            fh.write( "\n" ) 
            i=0
            while i<bset[0][3]:
                fh.write( "\t",)
                fh.write( "{} {}  ".format(bset[1][i][0], bset[1][i][1]))
                j=1
                while j<sum(bset[0][4:]):
                    fh.write ("{} ".format(bset[1+j][i][1]))
                    j+=1
                fh.write ( "\n")
                i+=1
        if fh is not sys.stdout:
            fh.close()
# uncomment for the production run
def parse_single_cp2k_basiset(basis):
    """
    :param basis:  a list of strings, where each string contains a line read
    from the basis set file. The whole list contains a SINGLE basis set

    :return name: name of the atom in the periodic table
    :return btype: basis set type
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

    import re
# This code takes name of the atom and basis set type.
    name, btype = basis[0].split()[0], basis[0].split()[1]
    tags=re.split(r"(?=\D)-(?=\D)",btype,flags=re.I)
# Second line contains the number of blocks
    n_blocks = int(basis[1].split()[0])
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
                m_qn = -(int(qnumbers[1]) + l_qn)



                
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
        nline += int(qnumbers[3]) - 1
        i_bl += 1
    return (name, tags, orbital_quantum_numbers,
            exponent_contractioncoefficient)
def upload_cp2k_basissetfile(filename):
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
                name, tags, orbqn, expn = parse_single_cp2k_basiset(
                    tmp_basis)
                cp2k_basis = GaussianbasisData()
                cp2k_basis.add_whole_basisset(name, tags, orbqn, expn)
                cp2k_basis.store_all_in_db()
                tmp_basis = [] # empty the temporary basis set storage
                line_number = -1
            if n_rows == 0: # condition to move to the other block of orbitals
                n_rows = int(tmp_basis[-1].split()[3]) + 1
                n_blocks -= 1
            n_rows -= 1
        line_number += 1
