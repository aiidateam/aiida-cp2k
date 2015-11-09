from aiida.orm.data import Data
from aiida.common.utils import classproperty
from aiida.orm.data.gaussian_basis import GaussianbasissetData
import argparse 
import os, sys
import re



class Cp2kbasissetData(GaussianbasissetData):
    def __init__ (self, atom_kind, basis_type, version="" ):
        super(Cp2kBasisset,self).__init__(atom_kind, basis_type, version)








# ParseSingleBasiset takes a list of strings, where each string contains a line read from the basis set file. 
# The whole list contains a SINGLE basis set


def ParseSingleBasiset(basis):

# This code takes name of the atom and basis set type. 
# Needs to be improved. 
    Name,Type= basis[0].split()[0], basis[0].split()[1]
    Version = "v1.0"
    


# Second line contains the number of blocks
    n_blocks=int (basis[1].split()[0])

#    print "name", Name
#    print "type", Type
#    print "Nblocks", n_blocks

    nline = 1
    i_bl = 0
    Norbital=0
    exponent_contractioncoefficient=[]
    OrbitalQuantumNumbers = []


# Outer loop. It goes through all blocks containing different sets of orbitals
    while (i_bl < n_blocks):

# going to the third line
        nline+=1
# getting quantum numbers fromt this line. Format is the following:
# n                lmin          lmax             nexp               nshell(lmin) nshell(lmin+1) ... nshell(lmax-1) nshell(lmax)
# Qnumbers[0]      Qnumbers[1]   Qnumbers[2]      Qnumbers[3]        Qnumbers[4] .....
        Qnumbers = basis[nline].split()

# n_different_l is how many DIFFERENT angular momenta we have
        n_different_l = ( int (Qnumbers[2])) - ( int (Qnumbers[1]) )

#        print basis[nline]
        
        
        l_qn=0
        nline+=1
        current_column=1


# loop over all different angular momenta
        while l_qn <= n_different_l:
            n_shell=0
# loop over different shells of a given momenta
            while n_shell <  int (Qnumbers[4+l_qn]):

                m_qn = - (int (Qnumbers[2]) + l_qn)
# loop over all possible magnetic quantum numbers
                while m_qn <= (int (Qnumbers[1]) + l_qn):
                    OrbitalQuantumNumbers.append( [    (int (Qnumbers[0]))  ,   ( int (Qnumbers[1]) ) +l_qn,  m_qn ,  0,  -1    ]  )
                    exponent_contractioncoefficient.append([])
                    exp_number=0
                    Norbital += 1 
# loop over all exponents
                    while exp_number < int (Qnumbers[3]):
                        exponent_contractioncoefficient[Norbital-1].append([ float ( basis[nline+exp_number].split()[0]) , float (basis[nline+exp_number].split()[current_column]) ])
                        exp_number+=1
                    m_qn+=1
                n_shell+=1
                current_column+=1
            l_qn+=1



#        print "Here"
#        print basis[nline]
#        print exponent_contractioncoefficient

        



        nline+=int(Qnumbers[3])-1
        
        i_bl+=1
#
#    i=0 
#    for i in  range(len(OrbitalQuantumNumbers)):
#        print "------"
#        print OrbitalQuantumNumbers[i]
#        print 
#        for  gg in   exponent_contractioncoefficient[i]:
#            print gg
#             

    return Name, Type, Version, OrbitalQuantumNumbers, exponent_contractioncoefficient










def ParseAndStore_BasissetFile(filename):
    if not os.path.exists(filename):
        raise ValueError("Not a valid file")
    with open(filename) as f:
        txt = f.read()
    txt_splitted = txt.split ('\n')

    txt_splitted_no_comments = []

# Removing comments and empty lines from the text and store each line as a single element of a list
    for line in txt_splitted:
# Do not read the part of text, which comes after '#' symbol
        tmp_line=line.split('#')[0].lstrip()
# Do not store empty lines
        if tmp_line != "":
            txt_splitted_no_comments.append(tmp_line)

#    print txt_splitted_no_comments

    tmp_basis = []   # here each single basis set will be stored temporary
    n_blocks=0
    line_number = 0
    n_rows = 0



# Going through the whole text. 
    for line in  txt_splitted_no_comments:
        tmp_basis.append(line)
#        print line, "|", n_blocks, n_rows, line_number

# First two lines contain Basis set name and the number of blocks. So they are treated differently then other parts of the basis
        if line_number < 2 :
            if ( len (tmp_basis) == 2 ) :
                n_blocks=int (tmp_basis[1].split()[0])
        else :
            if ( n_blocks == 0 and n_rows  == 1) : # conditions to finish reading of the basis set
# Using regular expressions to remove text in parantheses from the very first line, which contains the name of the basis set
                tmp_basis[0]=re.sub('\([^)]*\)', '', tmp_basis[0])
                name,tp,version,orbqn,expn=ParseSingleBasiset(tmp_basis)

                AAA=Cp2kBasisset(name,tp,version)
                AAA.add_WholeBasisSet(orbqn,expn)
                AAA.store_all()

#                print name, tp, version, orbqn
                tmp_basis = [] # empty the temporary basis set storage
                line_number = -1 
#                print "Here!!!!"
            if  ( n_rows  == 0 ): # condition to move to the other block of orbitals
                n_rows= int (tmp_basis[-1].split()[3]) + 1
                n_blocks-=1
            n_rows -= 1

        line_number+=1
    
        




    

            
