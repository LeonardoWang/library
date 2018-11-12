from common import *


class PkgInfo(NamedTuple):
    hash: bytes # A unique hash calculated from all API calls
    name: str   # The package name, in 'Lx/y/z' format
    weight: int # Total number of API calls in the bytecode of this package

class LibInfo(NamedTuple):
    hash: bytes
    name: str

class PkgResult(NamedTuple):
    hash: bytes
    name: str
    lib_name: str
    similarity: Optional[float]

class Thresholds(NamedTuple):
    LibMatchRate: float
    MinApiWeight: int
    MinLibCount: int
    PkgNameBlackList: Iterable[str]


class Database:
    api_set: Set[str]
    lib_set: Set[str]

    @staticmethod
    def preload() -> None:
        """Download library database to memory for better performance"""
        raise NotImplementedError()

    @staticmethod
    def match_libs(hash_list: Iterable[bytes]) -> List[LibInfo]:
        """Find all perfectly matched libraries for a list of package hashs"""
        raise NotImplementedError()

    @staticmethod
    def add_pkgs(pkgs: List[PkgInfo]) -> None:
        """Add a package to package database"""
        raise NotImplementedError()

    @staticmethod
    def remove_pkgs(pkgs: List[PkgInfo]) -> None:
        """Remove a package from package database"""
        raise NotImplementedError()

    @staticmethod
    def get_pkgs(threshold: int) -> List[PkgInfo]:
        """Get all packages which appear at least `threshold` times in the package database"""
        raise NotImplementedError()

    @staticmethod
    def add_libs(libs: List[LibInfo]) -> None:
        raise NotImplementedError()
        """Add a library to library database"""

    @staticmethod
    def dump() -> None:
        """Dump in-memory databases to file system"""
        raise NotImplementedError()

    @staticmethod
    def load() -> None:
        """Load databases from file system to memory"""
        raise NotImplementedError()
