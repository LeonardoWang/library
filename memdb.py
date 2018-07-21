from common import *

from .stub import *

import os


# hash -> pkg_name -> count
_db_pkgs: Dict[bytes, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
# hash -> pkg_name -> count
_db_libs: Dict[bytes, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
# hash -> weight
_db_weight: Dict[bytes, int] = { }


api_set: Set[str] = set(lx.read_lines(lx.open_resource('apis.txt')))

def match_libs(hash_list: Iterable[bytes]) -> List[LibInfo]:
    ret = [ ]
    for hash_ in hash_list:
        for pkg in _db_libs[hash_].keys():
            ret.append(LibInfo._make( (hash_, pkg) ))
    return ret

def add_pkgs(pkgs: List[PkgInfo]) -> None:
    for pkg in pkgs:
        _db_pkgs[pkg.hash][pkg.name] += 1
        _db_weight[pkg.hash] = pkg.weight

def remove_pkgs(pkgs: List[PkgInfo]) -> None:
    for pkg in pkgs:
        _db_pkgs[pkg.hash][pkg.name] -= 1

def get_pkgs(threshold: int) -> List[PkgInfo]:
    ret = [ ]
    for hash_, pkg_cnt in _db_pkgs.items():
        w = _db_weight[hash_]
        for pkg, cnt in pkg_cnt.items():
            if cnt >= threshold:
                ret.append(PkgInfo._make( (hash_, pkg, w) ))
    return ret

def add_libs(libs: List[LibInfo]) -> None:
    for lib in libs:
        _db_libs[lib.hash][lib.name] += 1


def dump() -> None:
    with open('db_pkgs.txt', 'w') as f:
        for hash_, pkg_cnt in _db_pkgs.items():
            for pkg, cnt in pkg_cnt.items():
                f.write('%s %s %d\n' % (hash_.hex(), pkg, cnt))
    with open('db_libs.txt', 'w') as f:
        for hash_, pkg_cnt in _db_libs.items():
            for pkg, cnt in pkg_cnt.items():
                f.write('%s %s %d\n' % (hash_.hex(), pkg, cnt))
    with open('db_weights.txt', 'w') as f:
        for hash_, weight in _db_weight.items():
            f.write('%s %d\n' % (hash_.hex(), weight))

def load() -> None:
    _db_exists = False
    try:
        for line in lx.read_lines('db_pkgs.txt'):
            _db_exists = True
            hash_, pkg, cnt = line.split(' ')
            _db_pkgs[bytes.fromhex(hash_)][pkg] += int(cnt)
        for line in lx.read_lines('db_libs.txt'):
            _db_exists = True
            hash_, pkg, cnt = line.split(' ')
            _db_libs[bytes.fromhex(hash_)][pkg] += int(cnt)
        for line in lx.read_lines('db_weights.txt'):
            _db_exists = True
            hash_, weight = line.split(' ')
            _db_weight[bytes.fromhex(hash_)] = int(weight)
    except FileNotFoundError:
        assert not _db_exists
