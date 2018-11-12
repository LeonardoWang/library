from common import *

from .stub import *

import os


api_set: Set[str] = set(lx.read_lines(lx.open_resource('apis.txt')))
lib_set: Set[str] = set(lx.read_lines(lx.open_resource('libs.txt')))


# hash -> pkg_name
_db: Optional[Dict[bytes, str]] = None


def match_libs(hash_list: Iterable[bytes]) -> List[LibInfo]:
    """Find all perfectly matched libraries for a list of package hashs"""
    if _db is None:
        sql = 'select hash, pkg_name from libraries where hash in {ARGS}'
        result = lx.query('library', sql, hash_list)
    else:
        result = [ (h, _db[h]) for h in hash_list if h in _db ]
    return [ LibInfo(*record) for record in result ]

def add_pkgs(pkgs: List[PkgInfo]) -> None:
    """Add a package to package database"""
    sql = 'insert into packages (hash, pkg_name, weight, count) values (%s,%s,%s,1) ' + \
            'on duplicate key update count = count + 1'
    lx.commit_multi('library', sql, [ (pkg.hash, pkg.name, pkg.weight) for pkg in pkgs ])

def remove_pkgs(pkgs: List[PkgInfo]) -> None:
    """Remove a package from package database"""
    sql = 'update packages set count = count - 1 where hash=%s and pkg_name=%s and weight=%s'
    lx.commit_multi('library', sql, [ (pkg.hash, pkg.name, pkg.weight) for pkg in pkgs ])

def get_pkgs(threshold: int) -> List[PkgInfo]:
    """Get all packages which appear at least `threshold` times in the package database"""
    sql = 'select hash, pkg_name, weight from packages where count >= %s'
    return [ PkgInfo._make(r) for r in lx.query('library', sql, threshold) ]

def add_libs(libs: List[LibInfo]) -> None:
    """Add a library to library database"""
    sql = 'insert ignore into libraries (hash, pkg_name) values (%s,%s)'
    lx.commit_multi('library', sql, libs)


def preload() -> None:
    """Download library database to memory for better performance"""
    global _db
    sql = 'select hash, pkg_name from libraries'
    _db = { hash_: pkg for hash_, pkg in lx.query('library', sql) }

def dump() -> None:
    lx.warning('Trying to dump SQL database')

def load() -> None:
    lx.warning('Trying to load SQL database')
