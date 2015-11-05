#/usr/bin/python

from aiida.orm.data import gaussian_basis

gg = gaussian_basis.GaussianbasissetData("C", "GTH-TZVP")


exponent_contractioncoefficient=[
[8.3744350009, -0.0283380461],  
[1.8058681460, -0.1333810052],  
[0.4852528328, -0.3995676063],  
[0.1658236932, -0.5531027541],  

]

gg.add_Orbital(exponent_contractioncoefficient,   n=1, l=0, m=0, s=0)
gg.add_Orbital(exponent_contractioncoefficient,   n=1, l=0, m=0, s=0)
gg.add_Orbital(exponent_contractioncoefficient,   n=2, l=1, m=0, s=0)


print gg.get_Norbitals()

print gg.get_Orbital(1,0,0)
#print gg.get_Orbital(2,0,0)


gg.store_all_in_DB()

print "!!!!!!!!After_saving"

print gg.get_Orbital(2,1,0)

print gg
