import library
from dex import Dex

import hashlib

def _calc_hash(lst):
    ret = hashlib.sha256()
    ret.update(bytes(lst))
    return ret.digest()


def _encode_features(class_features):
    ret = [ ]
    for method_f in class_features:
        for block_f in method_f:
            ret.append(_calc_hash(block_f))
    return ret


def dex_feature(dex_path):
    dex = Dex(dex_path)
    libs = library.analyze_dex(dex)

    ret = [ ]

    for class_ in dex.classes:
        is_lib = False
        class_name = class_.name()
        for lib in libs:
            if class_name.startswith(lib):
                is_lib = True
                break

        if not is_lib:
            ret += _encode_features(class_.get_repackage_features())

    return sorted(ret)

if __name__ == '__main__':
    for f in dex_feature('classes.dex'):
        print(f.hex())
