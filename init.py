import lx
import libdetect

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


def main(begin, end):
    sql = 'select app_id, app.pkg, md5 from app join apk using(apk_id) where apk_id is not null and %s<=app_id and app_id<%s'
    apks = lx.query('main', sql, (begin, end))
    for apk_info in apks:
        app_id, pkg, md5 = apk_info
        lx.info('%d %s' % (app_id, pkg))
        try:
            apk_path = lx.oss_download_dex(pkg, md5, sha256)
            for dex in _extract_dex(apk_path):
                libdetect.add_dex_to_database(dex)
            lx.clear_temp_file()
        except Exception as e:
            lx.warning(e)
        sql = 'insert ignore into apks (pkg, md5) values (%s,%s)'
        lx.commit('library', sql, (pkg, md5))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        begin = int(sys.argv[1])
        end = int(sys.argv[2])
    else:
        begin = 0
        end = 10
    main(begin, end)
