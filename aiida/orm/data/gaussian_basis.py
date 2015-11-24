# -*- coding: utf-8 -*-
"""
Gaussian basis set module
"""
__copyright__ = ""
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.4.1"
__contributors__ = "Aliaksandr Yakutovich, ..."


from aiida.orm.data import Data
import argparse

parser = argparse.ArgumentParser()
class GaussianbasisData(Data):
    """
    GaussianbasissetData is a class aimed to provide a general way to store
    gaussian basissets from different codes within AiiDA framework.

    All important information is stored in the following variables:


    *  **__atomkind** - string containing name of the atom.
    *  **__basistype** - string containing basis set type
    *  **__version** - string containing version of the basis set
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
    @classmethod
    def get_basis_sets(cls, filter_elements=None):
        """
        Return the UpfFamily group with the given name.
        """

        return GaussianbasisData.get()

    def __init__(self, atom_kind, basis_type, version=""):
        """
        Initialize a basis_set object.

        :param atom_kind: name of the atom in the periodic table
        :param basis_type: basis set type
        :param version: basis set Version

        all parameters together create a unique possible identification
        of the basis set
        """
        super(GaussianbasisData, self).__init__()
        self.__atomkind = atom_kind
        self.__basistype = basis_type
        self.__version = version


    def get_norbitals(self):
        """
        Return the number of orbitals stored in the basis seta
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
            ecc = self.get_attr('exponent_contraction_coefficients')
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


    def add_whole_basisset(self, quantum_numbers,
                           exp_contr_coeffs):
        """
        Add a full set of orbitals to the basis set
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


    @property
    def element(self):
        """
        return: element
        """
        return self.get_attr('element', None)






    def store_all_in_db(self):
        """
        This function which you run once your data are ready to be stored in the
        database.
        """
        self._set_attr('element', self.__atomkind)
        self._set_attr('type', self.__basistype)
        self._set_attr('version', self.__version)
        self._set_attr('orbital_quantum_numbers',
                       self.__orb_qm_numbers)
        self._set_attr('exponent_contraction_coefficients',
                       self.__expcontr_coeff)
