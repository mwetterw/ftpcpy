import ftplib, os
import shutil

params = ["rights", "link_counter", "user", "group", "size", "month", "day", "time", "name"]

class InfoStorage(object):
    def __init__(self):
        self.folders = list()
        self.files = list()

    def __call__(self, l):
        if not(l.startswith('d')) and not(l.startswith('-')):
            return

        file_infos = dict((params[i], p) for i, p in enumerate(l.split()))

        if file_infos['name'] == '..' or file_infos['name'] == '.':
            return

        if l.startswith('d'):
            self.folders.append(file_infos)
        elif l.startswith('-'):
            self.files.append(file_infos)

def walk(ftp1, ftp2, folder=None):
    info_storage = InfoStorage()

    if folder != None:
        try:
            print "Folder: {}".format(folder)
            ftp1.cwd(folder)
            ftp2.mkd(folder)
            ftp2.cwd(folder)
        except ftplib.error_perm:
            print "Permanent error for folder {}".format(folder)

    print "Source FTP path: {}".format(ftp1.pwd())
    print "Destination FTP path: {}".format(ftp2.pwd())

    ftp1.retrlines('LIST', info_storage)

    for val in info_storage.files:
        print "Downloading file {} from source FTP...".format(val['name'])
        ftp1.retrbinary("RETR {}".format(val['name']), open(val['name'], 'wb').write)

        print "Uploading file {} to destination FTP...".format(val['name'])
        ftp2.storbinary("STOR {}".format(val['name']), open(val['name'], 'rb'))

        print "Cleaning local temp file"
        os.unlink(val['name'])

    for val in info_storage.folders:
        walk(ftp1, ftp2 val['name'])

    if folder != None:
        ftp1.cwd('../')
        ftp2.cwd('../')

if __name__ == "__main__":
    if os.path.exists('ftp_tmp'):
        shutil.rmtree('ftp_tmp')
    os.makedirs('ftp_tmp')
    os.chdir('ftp_tmp')

    host1, port1, login1, password1 = "ftp.debian.org", 21, "anonymous", "anonymous@"
    host2, port2, login2, password2 = "ftp.debian.org", 21, "anonymous", "anonymous@"

    print "Connecting to source FTP server {}@{}".format(login1, host1)
    ftp1 = ftplib.FTP()
    ftp1.connect(host, port)
    ftp1.login(login, password)

    print "Connecting to destination FTP server {}@{}".format(login2, host2)
    ftp2 = ftplib.FTP()
    ftp2.connect(host2, port2)
    ftp2.login(login2, password2)

    walk(ftp1, ftp2)

    ftp1.quit()
    ftp2.quit()
