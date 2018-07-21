from common import *

from .stub import *


def _name_better(n1: Optional[str], n2: Optional[str]) -> bool:
    """Check if package name `n1` is "better than" and able to replace `n2`"""
    if n1 is None or n2 is None: return False
    parts1 = list(reversed(n1[1:-1].split('/')))
    parts2 = list(reversed(n2[1:-1].split('/')))
    l1 = max(len(p) for p in parts1)
    l2 = max(len(p) for p in parts2)
    if l1 > 1 and l2 <= 1: return True  # obfuscated name is always worse. e.g. "Lcom/google" > "La/a/b"
    if l2 > 1 and l1 <= 1: return False # vice versa
    if len(parts1) > len(parts2): return False  # less layers better. e.g. "Lcom/google" > "Lthird_party/com/google"
    for i in range(len(parts1)):
        if parts1[i] == parts2[i]: continue
        if len(parts2[i]) == 1: continue    # partially obfuscated. e.g. "Lcom/google/gson" > "Lcom/google/a"
        if parts1[i] != parts2[i]: return False # unrelated names are not better than each other. e.g. "Lcom/google" != "Lorg/sun"
    return True


def main(thresholds, db):
    lx.info('Loading packages database...')

    names_by_hash: Dict[bytes, str] = defaultdict(set)
    for pkg in db.get_pkgs(thresholds.MinLibCount):
        names_by_hash[pkg.hash].add(pkg.name)

    lx.info('Trimming package names...')
    progress = 0

    libs: List[LibInfo] = [ ]
    for hash_, names in names_by_hash.items():
        if len(names) > 1:
            names: List[Optinal[str]] = list(sorted(names))
            # if a name in the list is "worse than" another, set it to `None` and remove it later
            for i in range(len(names)):
                for j in range(i):
                    if _name_better(names[i], names[j]):
                        names[j] = None
                    elif _name_better(names[j], names[i]):
                        names[i] = None
            # remove names set to `None`
            names = [ n for n in names if n is not None ]

        for name in names:
            libs.append(LibInfo._make( (hash_, name) ))

        progress += 1
        if progress % 1000 == 0:
            lx.info('%d/%d' % (progress, len(names_by_hash)))

    lx.info('Updating library database...')

    db.add_libs(libs)

    lx.info('Done')
