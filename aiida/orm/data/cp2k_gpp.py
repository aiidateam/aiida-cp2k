# -*- coding: utf-8 -*-
"""
This module manages CP2K pseudopotentials, extending gpp class with read and
write functionality.
fixme: test and improve parser stability
"""
import re
from aiida.orm.data.gpp import GPP

_RE_FLAGS = re.M | re.X

class CP2KGPP(GPP):
    """
    Specialization to CP2K pseudopotentials, providing methods to upload GPP's
    in CP2K format from file to DB, and write GPP to file.
    """

    @classmethod
    def upload_from_file(cls, filename):
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
        uploaded = [cls.create_if_not_existing(_parse_single_gpp(match))
                    for match in gpp_iter]
        n_gpp = len(uploaded)
        n_uploaded = n_gpp - uploaded.count(None)
        return n_gpp, n_uploaded

    def write_to_file(self, filename, mode='w'):
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

def _parse_single_gpp(match):
    from aiida.common.exceptions import ParsingError
    element = match.group('element').strip(' \t\r\f\v\n')
    names = match.group('name').strip(' \t\r\f\v\n').split()
    try:
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

        gpp_type = [_[0] for _ in namessp if len(_) >= 1]
        xc = [_[1] for _ in namessp if len(_) >= 2]
        n_val = [_[2] for _ in namessp if len(_) >= 3]

        xc = list(set(xc))
        unique_type = list(set(gpp_type))
        unique_n_val = list(set(n_val))

        if len(unique_type) == 1 and len(unique_n_val) == 1:
            gpp_type = unique_type[0]
            n_val = unique_n_val[0]
        else:
            raise ParsingError(
                'gpp_type and n_val in pseudo name gpp_type-xc-n_val must be '
                'unique')

        n_val = int(n_val.lstrip('q'))

        if n_val != sum(n_elec):
            raise ParsingError(
                'number of valence electron must be sum of occupancy')
        data_to_store = ('element', 'gpp_type', 'xc', 'n_elec', 'r_loc',
                         'nexp_ppl', 'cexp_ppl', 'nprj', 'r', 'nprj_ppnl',
                         'hprj_ppnl')
        gpp_data = {}
        for _ in data_to_store:
            gpp_data[_] = locals()[_]
    except:
        raise ParsingError('invalid format for {} {}'.format(
            element, ' '.join(names)))
    return gpp_data

