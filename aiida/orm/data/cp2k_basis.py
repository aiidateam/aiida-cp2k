from aiida.orm.data import Data
from aiida.common.utils import classproperty
from aiida.orm.data.gaussian_basis import GaussianbasissetData
import argparse 
import os, sys


def ParseSingleBasiset(basis):
    Name,Type= basis[0].split()[0], basis[0].split()[1]

    n_blocks=int (basis[1].split()[0])

    print "name", Name
    print "type", Type
    print "Nblocks", n_blocks

    nline = 1
    i_bl = 0
    Norbital=0
    exponent_contractioncoefficient=[]
    OrbitalQuantumNumbers = []

    while (i_bl < n_blocks):
        nline+=1
        Qnumbers = basis[nline].split()
        n_different_l = ( int (Qnumbers[2])) - ( int (Qnumbers[1]) )
        print basis[nline]
        ncolumns = 0
        
        i=0

        while i <= n_different_l:
            ncolumns += int (Qnumbers[4+i])
            j=0
            while j <  int (Qnumbers[4+i]):
                k = - (int (Qnumbers[2]) + i)
                while k <= (int (Qnumbers[1]) + i):
                    OrbitalQuantumNumbers.append( [    (int (Qnumbers[0]))  ,   ( int (Qnumbers[1]) ) +i,  k ,  0,  -1    ]  )
                    k+=1

                j+=1

            i+=1

        nline+=1
#        print "Here"
#        print basis[nline]
#        print exponent_contractioncoefficient

        
        j=1
        while j <= ncolumns:
            exponent_contractioncoefficient.append([])
            j+=1
        j=1
        exponent_contractioncoefficient
        while j <= ncolumns :
            i=0
            print Norbital
            while i < int (Qnumbers[3]):
                exponent_contractioncoefficient[Norbital].append([ basis[nline+i].split()[0], basis[nline+i].split()[j]])
#               print  basis[nline+i]
                i+=1
            j+=1
            Norbital+=1
            
#        print "Ncolumns", ncolumns
        nline+=int(Qnumbers[3])-1
        
        i_bl+=1

    
    for each in OrbitalQuantumNumbers:
        print each
            
        

    

def ParseAndStore_BasissetFile(filename):
    if not os.path.exists(filename):
        raise ValueError("Not a valid file")
    with open(filename) as f:
        txt = f.read()
    txt_splitted = txt.split ('\n')

    txt_splitted_no_comments = []
    for line in txt_splitted:
        txt_splitted_no_comments.append(line.split('#')[0].lstrip())

#    print txt_splitted_no_comments

    tmp_basis = []
    for line in  txt_splitted_no_comments:
#        print line
        if line == "":
            if tmp_basis != []:
                ParseSingleBasiset(tmp_basis)
                tmp_basis = []
            continue
        tmp_basis.append(line)
    
        




class Cp2kBasisset(GaussianbasissetData):
    def __init__ (self, atom_kind, basis_type, version="" ):
        super(self,ParseAndStore_BasissetFile).__init__()
    

            
