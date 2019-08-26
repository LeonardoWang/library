__all__ = [
    'set_database',
    'set_thresholds',
    'detect_dex_libraries',
    'detect_exact_dex_libraries',
    'detect_apk_libraries',
    'detect_exact_apk_libraries',
    'add_dex_to_database',
    'remove_dex_from_database',
    'add_apk_to_database',
    'remove_apk_from_database',
    'update_library_database',
    'dump_database',
    'load_database'
]


from common import *

from .stub import *
from .pkgtree import PackageTree
from . import filterlibs

from . import thresholds as _thresholds

_db: Database
if False:
    from . import sqldb
    _db = cast(Database, sqldb)
else:
    from . import memdb
    _db = cast(Database, memdb)
    _db.load()


def set_database(db: Any):
    """Use a custom database
    If this function is never called, use the OrangeAPK MySQL database when available,
    or fallback to in-memory database when not
    This function must be called before any analyzer function
    """
    global _db
    _db = cast(Database, db)

def set_thresholds(thresholds: Thresholds):
    """Customize thresholds
    See thresholds.py for details
    This function must be called before any analyzer function
    """
    for key in thresholds._fields:
        value = getattr(thresholds, key)
        setattr(_thresholds, key, value)

def preload_database():
    """Pre-download database to memory (for SQL database)"""
    _db.preload()


def detect_dex_libraries(dex: Dex) -> List[PkgResult]:
    """Detect third-party libraries in a dex file
    Return the mapping from original package name to standard library name.
    If a package and some of its subpackages match libraries at the same time,
    """
    tree = PackageTree(dex, _db.api_set)
    libs = _db.match_libs(tree.nodes.keys())
    tree.set_db_match_result(libs)
    return tree.detect_libs(_thresholds.LibMatchRate, _db.lib_set)

def detect_exact_dex_libraries(dex: Dex) -> Dict[str, str]:
    """Detect perfectly matched third-party libraries in a dex file
    Return the mapping from original package name to standard library name.
    If a package and some of its subpackages match libraries at the same time,
    only the top-level package will be reported.
    """
    tree = PackageTree(dex, _db.api_set)
    libs = _db.match_libs(tree.nodes.keys())
    tree.set_db_match_result(libs)
    return tree.detect_exact_libs()


def detect_apk_libraries(apk_file: Union[bytes, str]) -> List[PkgResult]:
    """Detect third-party libraries in an APK file
    This is a wrapper of `detect_dex_libraries`
    For performance consideration, only use this function if there is no other analyzers
    """
    ret: List[PkgResult] = [ ]
    for dex in Apk(apk_file):
        ret += detect_dex_libraries(dex)
    return ret

def detect_exact_apk_libraries(apk_file: Union[bytes, str]) -> Dict[str, str]:
    """Detect perfectly matched third-party libraries in an APK file
    This is a wrapper of `detect_exact_dex_libraries`
    For performance consideration, only use this function if there is no othre analyzers
    """
    ret = { }
    for dex in Apk(apk_file):
        ret.update(detect_exact_dex_libraries(dex))
    return ret


def add_dex_to_database(dex: Dex) -> None:
    """Add packages in a dex file to database
    This will NOT modify the library database
    Call `update_library_database` later
    """
    _db.add_pkgs(_get_pkgs(dex))

def remove_dex_from_database(dex: Dex) -> None:
    """Remove packages in a dex file from database
    This function should be used when find a new version of recorded APK
    This will NOT modify the library database
    Call `update_library_database` later
    """
    _db.remove_pkgs(_get_pkgs(dex))

def add_apk_to_database(apk_file: Union[str, bytes]) -> None:
    """Wrapper of `add_dex_to_database`"""
    for dex in Apk(apk_file):
        _db.add_pkgs(_get_pkgs(dex))

def remove_apk_from_database(apk_file: Union[str, bytes]) -> None:
    """Wrapper of `remove_dex_from_database`"""
    for dex in Apk(apk_file):
        _db.remove_pkgs(_get_pkgs(dex))

def _get_pkgs(dex: Dex) -> List[PkgInfo]:
    tree = PackageTree(dex, _db.api_set)
    pkgs = [ ]
    for node in tree.nodes.values():
        if cast(int, node.weight) < _thresholds.MinApiWeight: continue
        if len(node.name) <= 2: continue  # 'L' + single letter
        if node.name in _thresholds.PkgNameBlackList: continue
        pkgs.append(node)
    return cast(List[PkgInfo], pkgs)


def update_library_database() -> None:
    """Filter the package database to update the library database"""
    filterlibs.main(_thresholds, _db)


def dump_database() -> None:
    """Dump in-memory database to file system
    Not needed when using SQL database
    """
    _db.dump()

def load_database() -> None:
    """Load database from file system to memory
    Not needed when using SQL database
    """
    _db.load()
