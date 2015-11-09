from aiida.orm.data import Data
from aiida.common.utils import classproperty
import argparse 

#RE_FLAGS = re.M | re.X 
"""
A wonderfull description of a GaussianbasissetData class

"""
parser = argparse.ArgumentParser()
class GaussianbasissetData(Data):


# "OrbitalQuantumNumbers" is a list containing a set of lists, where each of them describes a particular orbital in the following way: 
# [
#     [ N, l, m, s, contracted ],
#     ....
# ]
#
# Where:
# N           - principle quantum number
# l           - angular momentum
# m           - magnetic quantum number
# s           - spin
# contracted  - [n1,n2], if this orbital is contracted with some other orbitals n1 and n2, []  otherwise. 
#

    


# ExponentContractioncoefficient  is a list containing a set of lists, with a set of exponent + contraction coefficient pairs:
# Orbitals and ExponentContractioncoefficient must be consistent. 
#
# [ 
#    [
#        [ 2838.2104843030,  -0.0007019523 ], 
#        [  425.9069835160,  -0.0054237190 ],
#        [   96.6806600316,  -0.0277505669 ],
#         ....
#    ],
#    ....,
# ]
             
    def __init__(self,atom_kind, basis_type, version=""):
#Atom name, BasisSetName and Version together give a unique name for a basis set
        super(GaussianbasissetData, self).__init__()
        self.tmp_AtomKind   =  atom_kind
        self.tmp_BasisType  =  basis_type
        self.tmp_Version        =  version
        

# This function returns the number of orbitals stored in the basis set
    def get_Norbitals (self):
        return len(self.get_All_OrbitalQuantumNumbers())


# This function returns list of lists of quantm numbers of each orbital
    def get_All_OrbitalQuantumNumbers(self):
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
        

    def get_Orbital (self, n, l, m, s=0, contraction=-1):
        return_oqn = []
        return_ecc = []

        oqnumbers=self.get_All_OrbitalQuantumNumbers()
        ECcoefficients=self.get_All_Exponent_ContractionCoefficients()
        i=0
        for oqn in oqnumbers:
            if oqn[0]==n and oqn[1] == l and oqn[2] == m and  oqn[3] == s:
                return_oqn.append(oqn)
                return_ecc.append( ECcoefficients[i])
            i+=1

        if return_oqn == [] and return_ecc == []:
            parser.error("Error! Can not find orbital n={}, l={}, m={}, n={}".format(n,l,m,n))

        return return_oqn, return_ecc
        

    def add_Orbital (self,Exponent_ContractionCoefficient, n, l, m, s=0, contraction=-1):
        try:
            self.tmp_OrbitalQuantumNumbers
        except:
            self.tmp_OrbitalQuantumNumbers = []
        self.tmp_OrbitalQuantumNumbers.append( [n, l, m, s, contraction] )
        
        try:
            self.tmp_Exponent_ContractionCoefficients
        except:
            self.tmp_Exponent_ContractionCoefficients = []

        self.tmp_Exponent_ContractionCoefficients.append(Exponent_ContractionCoefficient )

        return True
    
    
    def add_WholeBasisSet(self,QuantumNumbers, Exponent_ContractionCoefficient):
        if len (QuantumNumbers) != len (Exponent_ContractionCoefficient):
            parser.error( "Error! The array with quantum numbers and the array with exponents have different size! Something is wrong...")

        size = len (QuantumNumbers)
        
        i=0
        while i < size:
            self.add_Orbital(Exponent_ContractionCoefficient = Exponent_ContractionCoefficient[i] , n=QuantumNumbers[i][0],l=QuantumNumbers[i][1],m=QuantumNumbers[i][2],s=QuantumNumbers[i][3], contraction=QuantumNumbers[i][4])
            i+=1

        return True









# store_all_in_DB is the function which you run once your data are ready to be stored in the database. 
    def store_all_in_DB (self):
        self._set_attr('AtomKind', self.tmp_AtomKind)
        self._set_attr('BasisSetName', self.tmp_BasisType)
        self._set_attr('Version', self.tmp_Version)
        self._set_attr('OrbitalQuantumNumbers', self.tmp_OrbitalQuantumNumbers)
        self._set_attr('Exponent_ContractionCoefficients', self.tmp_Exponent_ContractionCoefficients)
