# -*- coding: utf-8 -*-
__copyright__ = ""
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.4.1"
__contributors__ = "Aliaksandr Yakutovich, ..."


from aiida.orm.data import Data
from aiida.common.utils import classproperty
import argparse 

parser = argparse.ArgumentParser()
class Gaussian_basisData(Data):
    """
    GaussianbasissetData is a class aimed to provide a general way to store gaussian basissets from different codes within AiiDA framework. 
    
    All important information is stored in the following variables:


    *  **tmp_AtomKind** - string containing name of the atom.
    *  **tmp_BasisType** - string containing basis set type
    *  **vtmp_Version** - string containing version of the basis set  
    *  **tmp_OrbitalQuantumNumbers** is a list containing a set of lists, where each of them describes a particular orbital in the following way:
        [
            [ N, l, m, s, contracted ],
            ....
        ]
        
        Where:
        N           - principle quantum number
        l           - angular momentum
        m           - magnetic quantum number
        s           - spin
        contracted  - [n1,n2], if this orbital is contracted with some other orbitals n1 and n2, []  otherwise. 
    *   **tmp_Exponent_ContractionCoefficients**  is a list containing a set of lists, with a set of exponent + contraction coefficient pairs. For example:
        [ 
           [
               [ 2838.2104843030,  -0.0007019523 ], 
               [  425.9069835160,  -0.0054237190 ],
               [   96.6806600316,  -0.0277505669 ],
                ....
           ],
           ....,
        ]
    
    
    tmp_OrbitalQuantumNumbers and tmp_Exponent_ContractionCoefficients  must be consistent
    """
    @classmethod
    def get_basis_sets(cls, filter_elements = None):
        """
        Return the UpfFamily group with the given name.
        """
        

        return Gaussian_basisData.get()
             
    def __init__(self,atom_kind, basis_type, version=""):
        """
        Initialize a basis_set object. 

        :param atom_kind: name of the atom in the periodic table  
        :param basis_type: basis set type
        :param version: basis set Version

        all parameters together create a unique possible identification of the basis set
        """
        super(GaussianbasissetData, self).__init__()
        self.tmp_AtomKind   =  atom_kind
        self.tmp_BasisType  =  basis_type
        self.tmp_Version        =  version
        

    def get_Norbitals (self):
        """
        Return the number of orbitals stored in the basis seta
        :return an integer number
        """
        return len(self.get_All_OrbitalQuantumNumbers())


    def get_All_OrbitalQuantumNumbers(self):
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
        contracted  - [n1,n2], if this orbital is contracted with some other orbitals n1 and n2, []  otherwise. 

        return: a python list
        """
        try:
            oqn = self.get_attr ('OrbitalQuantumNumbers')
        except:
            print "Your basis set may not be yet stored in the database, trying to access the local data"
            try :
                oqn=self.tmp_OrbitalQuantumNumbers
            except:
                print "I can not find any orbital stored locally"
                raise
        return oqn

    def get_All_Exponent_ContractionCoefficients (self):
        """
        Return a list of exponents and contraction coefficients for each orbital in the following format:
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
            ecc = self.get_attr ('Exponent_ContractionCoefficients')
        except:
            print "Your basis set may not be yet stored in the database, trying to access the local data"
            try :
                ecc=self.tmp_Exponent_ContractionCoefficients
            except:
                print "I can not find any orbital stored locally"
                raise
        return ecc
        

    def get_Orbital (self, n, l='all', m='all', s='all'):
        """
        Return two lists:
            * List of orbital quantum numbers
            * List of exponents and contraction coefficients

        
        :param    n:  principle quantum number
        :param    l:  angular momentum
        :param    m:  magnetic quantum number
        :param    s:  spin
        
        :return two python lists
        """
        return_oqn = []
        return_ecc = []

        oqnumbers=self.get_All_OrbitalQuantumNumbers()
        ECcoefficients=self.get_All_Exponent_ContractionCoefficients()
        i=0
        for oqn in oqnumbers:
            if oqn[0]==n and  ( l == 'all' or oqn[1] == l )  and ( oqn[2] == 'all' or oqn[2] == m ) and (s == 'all' or oqn[3] == s ) :
                return_oqn.append(oqn)
                return_ecc.append( ECcoefficients[i])
            i+=1

        if return_oqn == [] and return_ecc == []:
            parser.error("Error! Can not find orbital n={}, l={}, m={}, n={}".format(n,l,m,n))

        return return_oqn, return_ecc
        

    def add_Orbital (self,Exponent_ContractionCoefficient, n, l, m, s=0, contraction=-1):
        """
        Add an orbital to the list

        :param Exponent_ContractionCoefficient:  list of exponents and contraction coefficients 
        :param    n:  principle quantum number
        :param    l:  angular momentum
        :param    m:  magnetic quantum number
        :param    s:  spin

        :return True/False
        """
        try:
            self.tmp_OrbitalQuantumNumbers
        except:
            self.tmp_OrbitalQuantumNumbers = []
        self.tmp_OrbitalQuantumNumbers.append( [int (n) , int (l) , int (m), s, contraction] )
        
        try:
            self.tmp_Exponent_ContractionCoefficients
        except:
            self.tmp_Exponent_ContractionCoefficients = []

        self.tmp_Exponent_ContractionCoefficients.append(Exponent_ContractionCoefficient )

        return True
    
    
    def add_WholeBasisSet(self,QuantumNumbers, Exponent_ContractionCoefficients):
        """
        Add a full set of orbitals to the basis set
        param: QuantumNumbers: a list containing a set of lists, where each of them describes a particular orbital in the following way:
        [
            [ N, l, m, s, contracted ],
            ....
        ]
        
        Where:
        N           - principle quantum number
        l           - angular momentum
        m           - magnetic quantum number
        s           - spin
        contracted  - [n1,n2], if this orbital is contracted with some other orbitals n1 and n2, []  otherwise. 
        param: Exponent_ContractionCoefficients:  a list containing a set of lists, with a set of exponent + contraction coefficient pairs. For example:
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
        if len (QuantumNumbers) != len (Exponent_ContractionCoefficients):
            parser.error( "Error! The array with quantum numbers and the array with exponents have different size! Something is wrong...")

        size = len (QuantumNumbers)
        
        i=0
        while i < size:
            self.add_Orbital(Exponent_ContractionCoefficient = Exponent_ContractionCoefficients[i] , n=QuantumNumbers[i][0],l=QuantumNumbers[i][1],m=QuantumNumbers[i][2],s=QuantumNumbers[i][3], contraction=QuantumNumbers[i][4])
            i+=1

        return True


    @property
    def element(self):
        return self.get_attr('element', None)






    def store_all_in_DB (self):
        """
        This function which you run once your data are ready to be stored in the database. 
        """
        self._set_attr('element', self.tmp_AtomKind)
        self._set_attr('type', self.tmp_BasisType)
        self._set_attr('version', self.tmp_Version)
        self._set_attr('orbital_quantum_numbers', self.tmp_OrbitalQuantumNumbers)
        self._set_attr('exponent_contraction_coefficients', self.tmp_Exponent_ContractionCoefficients)
