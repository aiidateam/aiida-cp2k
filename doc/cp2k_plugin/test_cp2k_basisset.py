from aiida.orm.data.gaussian_basis import GaussianbasisData, upload_cp2k_basissetfile
from aiida.djsite.db import models
upload_cp2k_basissetfile("BASIS_SET_SMALL")
q = models.DbNode.objects.filter(
    type__startswith=GaussianbasisData._query_type_string)


#print Cp2kbasissetData._query_type_string
print len(q)

qtmp = models.DbAttribute.objects.filter(
     key='element', tval='Si')
q = q.filter(dbattributes__in=qtmp)

print q[0].attributes['element']
print q[0].get_aiida_class()




# qtmp = models.DbAttribute.objects.filter(
#     key__startswith='id.', tval=pid)
#q = q.filter(dbattributes__in=qtmp)
