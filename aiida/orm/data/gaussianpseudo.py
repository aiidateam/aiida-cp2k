# -*- coding: utf-8 -*-
"""
This module provides a general framework for storing and querying gaussian
pseudopotentials (GPP's).
Read and write functionality for CP2K format provided.
"""
import re
from aiida.orm import Data

_RE_FLAGS = re.M | re.X

class GaussianpseudoData(Data):
    """
    Gaussian Pseudopotential (gpp) class to store gpp's in database and
    retrieve them.
    fixme: extend to NLCC pseudos.
    """

    @classmethod
    def create_if_not_existing(cls, gpp_data):
        """
        Create a gpp from dictionary and store it in database if does not exist.
        If user tries to store a new gpp under an already existing id, a
        UniquenessError is thrown. The correctness of the created gpp is
        validated (keys, types, lengths).
        Currently does not support NLCC pseudopotentials.
        :param gpp_data: a dictionary that must contain the following keys
          and data types:
          * element:     string
                         (e.g. 'H')
          * gpp_type:    string,
                         some classification of the gpp (e.g. 'GTH'),
                         must be unique for a given element and a given xc
                         functional
                         and a given number of valence electrons
          * xc:          list of strings,
                         defining compatibility with xc-functionals (e.g. 'PBE')
          * n_elec:      list of ints,
                         number of electrons for each angular momentum quantum
                         number (electronic configuration -> s p d ...)
          * r_loc:       float,
                         radius for the local part defined by the Gaussian
                         function exponent alpha_erf
          * nexp_ppl:    int,
                         number of the local pseudopotential functions
          * cexp_ppl:    list of floats of length nexp_ppl,
                         coefficients of the local pseudopotential functions
          * nprj:        int,
                         number of the non-local projectors
                         => nprj = len(nprj_ppnl)
          * r:           list of floats of length nprj,
                         radius of the non-local part for angular momentum
                         quantum number l
                         defined by the Gaussian function exponents
                         alpha_prj_ppnl
          * nprj_ppnl:   list of ints of length nprj,
                         number of the non-local projectors for the angular
                         momentum quantum number l
          * hprj_ppnl:   list of list of floats of length
                         nprj, nprj_ppnl[iprj]*(nprj_ppnl[iprj]+1)/2,
                         coefficients of the non-local projector functions
        :return: the created gpp instance.
        """
        from aiida.djsite.db import models
        from aiida.common.exceptions import UniquenessError, PluginInternalError

        gpp_data['n_val'] = sum(gpp_data['n_elec'])
        is_new = True
        # query for element and id to check if gpp with same name exists
        for pid in gpp_data['id']:
            q = models.DbNode.objects.filter(
                type__startswith=cls._query_type_string)
            qtmp = models.DbAttribute.objects.filter(
                key='element', tval=gpp_data['element'])
            q = q.filter(dbattributes__in=qtmp)
            qtmp = models.DbAttribute.objects.filter(
                key__startswith='id.', tval=pid)
            q = q.filter(dbattributes__in=qtmp)
            if len(q) == 1:
                qq = q[0].get_aiida_class()
                # if upf with same name exists, do not create a new one,
                # but throw an error if it is not equal
                # (within some tolerance of 1.0E-6)
                if qq == gpp_data:
                    is_new = False
                else:
                    raise UniquenessError(
                        'another gpp already exists under the same name {} {}'
                        .format(gpp_data['element'], pid))
            elif len(q) > 1:
                raise PluginInternalError('found 2 gpps in DB with same id')

        if is_new:
            print "uploading to db"
            instance = cls()
            for k, v in gpp_data.iteritems():
                instance._set_attr(k, v)
            instance._validate()
            instance.store()
            return instance
        else:
            print "already exists in db"
            return None

    @classmethod
    def get_pseudos(cls, element=None, gpp_type=None, xc=None, n_val=None):
        """
        Return all instances stored in DB that match a number of optional
        parameters.
        Specification of all parameters is guaranteed to give a unique (or no)
        match.
        :param element: the element
        :param gpp_type: the name/classification of the gpp
        :param xc: the xc functional
        :param n_val: the number of valence electrons (sum of n_elec)
        :return: generator for found gpp's
        """

        from aiida.djsite.db import models
        from aiida.common.exceptions import PluginInternalError

        q = models.DbNode.objects.filter(type__startswith=
                                         cls._query_type_string)

        notnone = 0
        if element is not None:
            qtmp = models.DbAttribute.objects.filter(key='element',
                                                     tval=element)
            q = q.filter(dbattributes__in=qtmp)
            notnone += 1
        if gpp_type is not None:
            qtmp = models.DbAttribute.objects.filter(key='gpp_type',
                                                     tval=gpp_type)
            q = q.filter(dbattributes__in=qtmp)
            notnone += 1
        if xc is not None:
            qtmp = models.DbAttribute.objects.filter(key__startswith='xc.',
                                                     tval=xc)
            q = q.filter(dbattributes__in=qtmp)
            notnone += 1
        if n_val is not None:
            qtmp = models.DbAttribute.objects.filter(key='n_val',
                                                     ival=n_val)
            q = q.filter(dbattributes__in=qtmp)
            notnone += 1

        q = q.distinct()

        if notnone == 4 and len(q) > 1:
            raise PluginInternalError('found gpp is not unique.')

        for _ in q:
            yield _.get_aiida_class()


    def _validate(self):

        from aiida.common.exceptions import ValidationError

        super(GaussianpseudoData, self)._validate()

        gpp_dict = dict(self.iterattrs())

        keys = ['element', 'id', 'gpp_type', 'xc', 'n_val',
                'n_elec', 'r_loc', 'nexp_ppl', 'cexp_ppl', 'nprj',
                'r', 'nprj_ppnl', 'hprj_ppnl']

        types = [[str], [list, str], [str], [list, str], [int],
                 [list, int], [float], [int], [list, float], [int],
                 [list, float], [list, int], [list, list, float]]

        lengths = [None, None, None, None, None,
                   None, None, None, 'nexp_ppl', None,
                   'nprj', 'nprj', 'nprj']

        try:
            for k, t, l in zip(keys, types, lengths):
                if k in gpp_dict.keys():
                    if not isinstance(gpp_dict[k], t[0]):
                        raise ValidationError('{} must be {}'.format(k, t))
                    if len(t) > 1:
                        if not all(isinstance(_, t[1]) for _ in gpp_dict[k]):
                            raise ValidationError('{} must be {}'.format(k, t))
                    if len(t) > 2:
                        if not all(all(isinstance(__, t[2]) for __ in _)
                                   for _ in gpp_dict[k]):
                            raise ValidationError('{} must be {}'.format(k, t))
                    if l is not None and len(gpp_dict[k]) != gpp_dict[l]:
                        raise ValidationError(
                            'length of {} must be equal to {}'.format(k, l))
                else:
                    raise ValidationError('{} missing'.format(k))

            if sum(gpp_dict['n_elec']) != gpp_dict['n_val']:
                raise ValidationError(
                    'number of valence electrons is not sum of occupancy')

            # check size of upper triangular part of hprj_ppnl matrices
            for iprj in range(0, len(gpp_dict['nprj_ppnl'])):
                nprj = gpp_dict['nprj_ppnl'][iprj]
                if len(gpp_dict['hprj_ppnl'][iprj]) != nprj*(nprj+1)/2:
                    raise ValidationError(
                        'Incorrect number of hprj_ppnl coefficients')
        except ValidationError as e:
            raise ValidationError('invalid format for {} {}: {}'.format(
                gpp_dict['element'],
                ' '.join(gpp_dict['id']),
                e.message))

    def __eq__(self, other):
        if isinstance(other, GaussianpseudoData):
            other_dict = dict(other.iterattrs())
        elif isinstance(other, dict):
            other_dict = other
        else:
            return False
        self_vals = _li_round(_dict_to_list(dict(self.iterattrs())))
        other_vals = _li_round(_dict_to_list(other_dict))
        return self_vals == other_vals

    @classmethod
    def upload_cp2k_gpp_file(cls, filename):
        """
        Upload a number of gpp's in CP2K format contained in a single file.
        If a gpp already exists, it is not uploaded.
        If a different gpp exists under the same name or alias, an
        UniquenessError is thrown.
        :return: number of gpp's in file, number of uploaded gpp's.
        Docu of format from GTH_POTENTIALS file of CP2K:
        ------------------------------------------------------------------------
        GTH-potential format:

        Element symbol  Name of the potential  Alias names
        n_elec(s)  n_elec(p)  n_elec(d)  ...
        r_loc   nexp_ppl        cexp_ppl(1) ... cexp_ppl(nexp_ppl)
        nprj
        r(1)    nprj_ppnl(1)    ((hprj_ppnl(1,i,j),j=i,nprj_ppnl(1)),i=1,nprj_ppnl(1))
        r(2)    nprj_ppnl(2)    ((hprj_ppnl(2,i,j),j=i,nprj_ppnl(2)),i=1,nprj_ppnl(2))
         .       .               .
         .       .               .
         .       .               .
        r(nprj) nprj_ppnl(nprj) ((hprj_ppnl(nprj,i,j),j=i,nprj_ppnl(nprj)),
                                                      i=1,nprj_ppnl(nprj))

        n_elec   : Number of electrons for each angular momentum quantum number
                   (electronic configuration -> s p d ...)
        r_loc    : Radius for the local part defined by the Gaussian function
                   exponent alpha_erf
        nexp_ppl : Number of the local pseudopotential functions
        cexp_ppl : Coefficients of the local pseudopotential functions
        nprj     : Number of the non-local projectors => nprj = SIZE(nprj_ppnl(:))
        r        : Radius of the non-local part for angular momentum quantum number l
                   defined by the Gaussian function exponents alpha_prj_ppnl
        nprj_ppnl: Number of the non-local projectors for the angular momentum
                   quantum number l
        hprj_ppnl: Coefficients of the non-local projector functions
        ------------------------------------------------------------------------
        Name and Alias of the potentials are required to be of the format
        'type'-'xc'-q'nval' with 'type' some classification (e.g. GTH), 'xc'
        the compatible xc-functional (e.g. PBE) and 'nval' the total number
        of valence electrons.
        """
        gpp_file = open(filename).read()
        gpp_iter = _CP2KGPP_REGEX.finditer(gpp_file)
        uploaded = [cls.create_if_not_existing(_parse_single_cp2k_gpp(match))
                    for match in gpp_iter]
        n_gpp = len(uploaded)
        n_uploaded = n_gpp - uploaded.count(None)
        return n_gpp, n_uploaded


    def write_cp2k_gpp_to_file(self, filename, mode='w'):
        """
        Write a gpp instance to file in CP2K format.
        :param filename: filename
        :param mode: mode argument of built-in open function ('a' or 'w')
        """

        ffp = lambda fp: "{0:.8f}".format(fp).rjust(15)
        fitg = lambda itg: str(itg).rjust(5)

        gpp_data = dict(self.iterattrs())

        f = open(filename, mode)
        f.write(gpp_data['element'])
        for _ in gpp_data['id']:
            f.write(' ' + _)
        f.write('\n')
        for n_elec in gpp_data['n_elec']:
            f.write(fitg(n_elec))
        f.write('\n')
        f.write(ffp(gpp_data['r_loc']))
        f.write(fitg(gpp_data['nexp_ppl']))
        for cexp in gpp_data['cexp_ppl']:
            f.write(ffp(cexp))
        f.write('\n')
        f.write(fitg(gpp_data['nprj']) + '\n')
        for i in range(gpp_data['nprj']):
            f.write(ffp(gpp_data['r'][i]) +  fitg(gpp_data['nprj_ppnl'][i]))
            nwrite = gpp_data['nprj_ppnl'][i]
            hprj = iter(gpp_data['hprj_ppnl'][i])
            n_intend = 0
            while nwrite > 0:
                for _ in range(nwrite):
                    f.write(ffp(hprj.next()))
                f.write('\n')
                n_intend += 1
                nwrite = nwrite-1
                if nwrite > 0:
                    f.write(' '*20+' '*15*n_intend)
        f.write('\n')
        f.close()

    def get_full_type(self):
        return "{}-{}-q{}".format(self.get_attr("gpp_type"),
        self.get_attr("xc")[0], self.get_attr("n_val"))

def _dict_to_list(di):
    li = [[k, v] for k, v in di.items()]
    li.sort()
    return li

def _li_round(li, prec=6):
    if isinstance(li, float):
        return round(li, prec)
    elif isinstance(li, list):
        return type(li)(_li_round(x, prec) for x in li)
    else:
        return li


_CP2KGPP_REGEX = re.compile(r"""
    # Element symbol  Name of the potential  Alias names
        (?P<element>
            [A-Z][a-z]{0,1}
        )
        (?P<name>
            ([ \t\r\f\v]+[-\w]+)+
        )
        [ \t\r\f\v]*[\n]
    # n_elec(s)  n_elec(p)  n_elec(d)  ...
        (?P<el_config>
            ([ \t\r\f\v]*[0-9]+)+
        )
        [ \t\r\f\v]*[\n]
    # r_loc   nexp_ppl        cexp_ppl(1) ... cexp_ppl(nexp_ppl)
        (?P<body_loc>
            [ \t\r\f\v]*[\d\.]+[ \t\r\f\v]*[\d]+([ \t\r\f\v]+-?[\d]+.[\d]+)*
        )
        [ \t\r\f\v]*[\n]
    # nprj
        (?P<nproj_nonloc>
            [ \t\r\f\v]*[\d]+
        )
        [ \t\r\f\v]*[\n]
    # r(1)    nprj_ppnl(1)    ((hprj_ppnl(1,i,j),j=i,nprj_ppnl(1)),i=1,nprj_ppnl(1))
    # r(2)    nprj_ppnl(2)    ((hprj_ppnl(2,i,j),j=i,nprj_ppnl(2)),i=1,nprj_ppnl(2))
    #  .       .               .
    #  .       .               .
    #  .       .               .
    # r(nprj) nprj_ppnl(nprj) ((hprj_ppnl(nprj,i,j),j=i,nprj_ppnl(nprj)),
        (?P<body_nonloc>
            ([ \t\r\f\v]*[\d\.]+[ \t\r\f\v]*[\d]+(([ \t\r\f\v]+-?[\d]+.[\d]+)+
                [ \t\r\f\v]*[\n])*)*
        )
    """, _RE_FLAGS)


def _parse_single_cp2k_gpp(match):
    from aiida.common.exceptions import ParsingError
    element = match.group('element').strip(' \t\r\f\v\n')
    names = match.group('name').strip(' \t\r\f\v\n').split()
    print "parsing", element, ", ".join(names)

    n_elec = [int(el) for el in (match.group('el_config').strip(
        ' \t\r\f\v\n').split())]
    body_loc = match.group('body_loc').strip(' \t\r\f\v\n').split()
    nprj = int(match.group('nproj_nonloc').strip(' \t\r\f\v\n'))
    body_nonloc = match.group('body_nonloc').strip(' \t\r\f\v\n')

    r_loc = float(body_loc[0])
    nexp_ppl = int(body_loc[1])
    cexp_ppl = []
    for val in body_loc[2:]:
        cexp_ppl.append(float(val))
    next_proj = True
    n = 0
    r = []
    nprj_ppnl = []
    hprj_ppnl = []
    for line in body_nonloc.splitlines():
        line = line.split()
        offset = 0
        if next_proj:
            hprj_ppnl.append([])
            r.append(float(line[offset]))
            nprj_ppnl.append(int(line[offset+1]))
            nhproj = nprj_ppnl[-1]*(nprj_ppnl[-1]+1)/2
            offset = 2
        for data in line[offset:]:
            hprj_ppnl[n].append(float(data))
        next_proj = len(hprj_ppnl[n]) == nhproj
        if next_proj:
            n = n+1

    namessp = [_.split('-') for _ in names]

    parse_name = any(len(_) > 1 for _ in namessp)

    gpp_type = [_[0] for _ in namessp if len(_) >= 1]
    xc = [_[1] for _ in namessp if len(_) >= 2]
    n_val = [_[2] for _ in namessp if len(_) >= 3]

    xc = list(set(xc))
    unique_type = list(set(gpp_type))
    if not n_val:
        n_val = [str(sum(n_elec))]
    unique_n_val = list(set(n_val))

    data_to_store = ('element', 'gpp_type', 'xc', 'n_elec', 'r_loc',
                     'nexp_ppl', 'cexp_ppl', 'nprj', 'r', 'nprj_ppnl',
                     'hprj_ppnl')
    gpp_data = {}
    for _ in data_to_store:
        gpp_data[_] = locals()[_]

    if parse_name:
        if len(unique_type) == 1 and len(unique_n_val) == 1:
            gpp_type = unique_type[0]
            n_val = unique_n_val[0]
        else:
            raise ParsingError(
                'gpp_type and n_val in pseudo name gpp_type-xc-n_val must be '
                'unique')

        try:
            n_val = int(n_val.lstrip('q'))
        except ValueError:
            raise ValueError('pseudo potential name should be "type-xc-q<nval>" with nval the number of valence electrons.')


        gpp_data['id'] = ['{}-{}-q{}'.format(gpp_type, _, n_val) 
                for _ in gpp_data['xc']]
        gpp_data['gpp_type'] = gpp_type
        gpp_data['n_val']=n_val
        gpp_data['xc'] = xc

        if n_val != sum(n_elec):
            raise ParsingError(
                'number of valence electron must be sum of occupancy')

    else:
        gpp_data['id'] = names
        gpp_data['gpp_type'] = ''
        gpp_data['n_val'] = ''
        gpp_data['xc'] = []

    return gpp_data
