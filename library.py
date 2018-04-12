import lx
from dex import Dex
from pkgtree import PackageTree

import sys
from zipfile import ZipFile


lx.set_mode('release')


def _extract_dex(apk_path):
    zf = ZipFile(apk_path)
    files = zf.namelist()
    if 'classes.dex' not in files: return [ ]
    path = lx.temp_file_dir()
    ret = [ zf.extract('classes.dex', path) ]
    i = 2
    while ('classes%d.dex' % i) in files:
        ret.append(zf.extract('classes%d.dex' % i, path))
        i += 1
    return ret


def analyze_dex(dex):
    if type(dex) is str:
        dex = Dex(dex)
    tree = PackageTree(dex)
    return tree.match_libs()


def analyze_apk(apk_path):
    ret = { }
    for dex in _extract_dex(apk_path):
        ret.update(analyze_dex(dex))
    return ret


def analyze(target):
    if type(target) is str:
        assert target.endswith('.dex') or target.endswith('.apk')
        if target.endswith('.dex'):
            return analyze_dex(target)
        else:
            return analyze_apk(target)
    else:
        return analyze_dex(target)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        target = 'classes.dex'
    else:
        target = sys.argv[1]
    print(lx.json(analyze(target), pretty = True))
    lx.clear_temp_file()
