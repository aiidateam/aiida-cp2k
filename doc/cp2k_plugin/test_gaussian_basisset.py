#/usr/bin/python

from aiida.orm.data import gaussian_basis

gg = gaussian_basis.GaussianbasisData("C", "GTH-TZVP")


exponent_contractioncoefficient=[
[8.3744350009, -0.0283380461],  
[1.8058681460, -0.1333810052],  
[0.4852528328, -0.3995676063],  
[0.1658236932, -0.5531027541],  

]

gg.add_orbital(exponent_contractioncoefficient,   n_qn=1, l_qn=0, m_qn=0, spin=0)
gg.add_orbital(exponent_contractioncoefficient,   n_qn=1, l_qn=0, m_qn=0, spin=0)
gg.add_orbital(exponent_contractioncoefficient,   n_qn=2, l_qn=1, m_qn=0, spin=0)


print gg.get_norbitals()

print gg.get_orbital(1,0,0)
print gg.get_orbital(2,0,0)


gg.store_all_in_db()

print "!!!!!!!!After_saving"

print gg.get_orbital(2,1,0)

print gg
