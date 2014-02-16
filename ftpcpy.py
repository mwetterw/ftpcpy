import ftplib, os, shutil, threading, Queue

params = ["rights", "link_counter", "user", "group", "size", "month", "day", "time", "name"]
output_lock = threading.Lock()

q = Queue.Queue()
q_folders = Queue.Queue()
still = True

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

class FtpThread(threading.Thread):
    def __init__(self, thread_name, thread_target, host, port, login, password):
        threading.Thread.__init__(self, None, thread_target, thread_name, [])

	self.ftp = ftplib.FTP()

	self.host = host
	self.port = port
	self.login = login
	self.password = password

	self.wd = ""
	self.color = '\033[m'

    def connect(self):
        self.ftp.connect(self.host, self.port)
        self.ftp.login(self.login, self.password)
	self.wd = self.ftp.pwd()

    def print_nolock(self, *msgs):
	for msg in msgs:
	    msg = msg.split('\n')
	    for line in msg:
                print "{}[{}]{} {}".format(self.color, self.name, '\033[0m', line)

    def print_(self, msgs):
        output_lock.acquire()
	self.print_nolock(msgs)
        output_lock.release()

    def runnable(self):
        output_lock.acquire()
        self.print_nolock("{} launched.".format(self.name))
        self.print_nolock("Connecting to FTP {}@{}...".format(self.login, self.host))
	self.connect()
	self.print_nolock(self.ftp.getwelcome())
        output_lock.release()

    def cwd(self, folder):
        self.ftp.cwd(folder)
	self.wd = self.ftp.pwd()

class FtpDownloader(FtpThread):
    def __init__(self, host, port, login, password):
        FtpThread.__init__(self, 'Downloader', self.runnable, host, port, login, password)
	self.color = '\033[1;34m'

    def runnable(self):
        FtpThread.runnable(self)
        self.walk()
	self.ftp.quit()

    def walk(self, folder=None):
        info_storage = InfoStorage()

        if folder != None:
            try:
                self.cwd(folder)
                q_folders.put(self.wd)

            except ftplib.error_perm, e:
                self.print_("Error for folder '{}': '{}'".format(folder, e))
                return
	else:
	    self.print_("Starting with folder '{}'".format(self.wd))

	self.print_("Scanning folder '{}'".format(self.wd))
        self.ftp.retrlines('LIST', info_storage)
	self.print_("Found {} folders & {} files".format(len(info_storage.folders), len(info_storage.files)))

        for val in info_storage.files:
            try:
                filename = os.urandom(16).encode('hex')
                self.print_("Downloading file '{}' from source FTP to {}...".format(val['name'], filename))
                self.ftp.retrbinary("RETR {}".format(val['name']), open(filename, 'wb').write)
                self.print_("Download of file '{}' completed. Adding into the queue...".format(val['name'], filename))
                q.put({'sha1': filename, 'path': self.wd, 'name': val['name']})
            except ftplib.error_perm, e:
	        self.print_("Error when downloading file '{}': '{}'.".format(val['name'], e))

        for val in info_storage.folders:
	    self.print_("Diving deeper into the tree...")
            self.walk(val['name'])

        if folder != None:
	    self.print_("Comming back up from the tree...")
            self.cwd('../')
	still = false


class FtpUploader(FtpThread):
    def __init__(self, host, port, login, password):
        FtpThread.__init__(self, 'Uploader', self.runnable, host, port, login, password)
	self.color = '\033[1;36m'

    def runnable(self):
        FtpThread.runnable(self)
        while still or not q.empty():
	    try:
                info = q.get(True, 10*60)
	    except Queue.Empty:
		self.print_("Didn't talk to the FTP for a long time. Sending dummy command...")
		self.ftp.pwd()
	        continue

    	    self.print_("Just got {}".format(info))
    	    self.__check_folder()
    	    self.cwd(info['path'])
            try:
                self.print_("Uploading file {} to destination FTP as {}...".format(info['sha1'], info['name']))
                self.ftp.storbinary("STOR {}".format(info['name']), open(info['sha1'], 'rb'))
		self.print_("Upload of file '{}' completed.".format(info['name']))
            except ftplib.error_perm:
                self.print_("Error when uploading the file.")
            self.print_("Removing local file '{}'...".format(info['sha1']))
    	    os.unlink(info['sha1'])
            q.task_done()
	self.ftp.quit()

    def __check_folder(self):
        while not q_folders.empty():
            try:
                folder_to_create = q_folders.get(False)
                self.print_("Creating folder: {}".format(folder_to_create))
                self.ftp.mkd(folder_to_create)
                q_folders.task_done()
            except Queue.Empty, e:
                pass
            except ftplib.error_perm, e:
                self.print_("Unable to create folder {}: '{}'".format(folder_to_create, e))


if __name__ == "__main__":
    if os.path.exists('ftp_tmp'):
	print "Cleaning ftp_tmp folder..."
        shutil.rmtree('ftp_tmp')
    os.makedirs('ftp_tmp')
    os.chdir('ftp_tmp')

    # dl = FtpDownloader("hostname", 21, "username", "password")
    # up = FtpUploader("hostname", 21, "username", "password")
    # dl.start()
    # up.start()
    # dl.join()
    # up.join()
