import sys, os, time, atexit, pwd, grp, logging
from signal import SIGTERM, SIGKILL
from yaml_server.YamlServerException import YamlServerException

class YamlDaemon:
    """
    A generic daemon class.
    
    Usage: subclass the Daemon class and override the run() method
    
    Found in http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
    """
    args = []  # command line argments that are not options go here
    
    def __init__(self, pidfile=None, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.pid = None
    
    def daemonize(self):
        """
        do the UNIX double-fork magic and then call run().
        
        See Stevens' "Advanced Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        
        try: 
            pid = os.fork() 
            if pid > 0:
                # first parent returns success
                return True
        except OSError, e: 
            print "fork #1 failed: %d (%s)" % (e.errno, e.strerror) >> sys.stderr 
            return False
    
        # decouple from parent environment
        os.chdir("/") 
        os.setsid() 
        os.umask(0) 
    
        # do second fork
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit from second parent
                sys.exit(0) 
        except OSError, e: 
            self.logger.fatal("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1) 
    
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        
        # update pid in syslog output
        self.loghandler.setFormatter(logging.Formatter('yaml_server[' + str(os.getpid()) + ']: %(levelname)s: %(message)s'))

        if self.pidfile:
            # write pidfile
            pid = str(os.getpid())
            try:
                pidfile_handle = file(self.pidfile, 'w+')
                pidfile_handle.write("%s\n" % pid)
                pidfile_handle.close()
            except Exception, e:
                self.logger.fatal("Aborting, could not create pid file %s: %s" % (self.pidfile, str(e)))
                sys.exit(1)
            else:
                atexit.register(self.delpidfile)
        self.run()
    
    def is_running(self):
        self.pid = self._read_pid()
        
        if self.pid:
            # have pid, ping process
            try:
                os.kill(self.pid, 0)
            except OSError, e:
                # No process or we are not allowed to ping the process
                if e.errno == 3:
                    return False
                else:
                    # some other isse, throw it up
                    raise YamlServerException("Could not ping process %r: %s" % (self.pid, str(e)))
            else:
                # no exception means that the process runs
                return True
        else:
            # no pid means no process
            return False

    
    def _read_pid(self):
        """
        Return pid from pidfile
        """
        if not self.pidfile:
            raise YamlServerException("No pidfile set!")
        try:
            pf = file(self.pidfile, 'r')
            self.pid = int(pf.read().strip())
            pf.close()
        except IOError:
            # probably no pidfile which is the case that we don't run
            self.pid = None
        except Exception, e:
            # some other error, throw up
            raise YamlServerException("Could not read pid from pidfile %s: %s" % (self.pidfile, str(e)))
        
        return self.pid


    def delpidfile(self):
        os.remove(self.pidfile)

    def drop_privileges(self, uid_name=None, gid_name=None):
        """ Drop privileges
        
        Found in https://github.com/zedshaw/python-lust/blob/master/lust/unix.py
        """
        if os.getuid() != 0:
            self.logger.warning("Must be root to drop privileges!")
            return
    
        # Get the uid/gid from the name. If no group given, then derive group from uid_name
        if uid_name is None:
            uid_name = "nobody"  # builtin default is nobody
        running_uid = pwd.getpwnam(uid_name).pw_uid
        if gid_name is None:
            running_gid = pwd.getpwnam(uid_name).pw_gid
        else:
            running_gid = grp.getgrnam(gid_name).gr_gid

        self.logger.debug("Running as %r.%r" % (running_uid, running_gid))
    
        # Remove group privileges
        os.setgroups([])
    
        # Try setting the new uid/gid
        os.setgid(running_gid)
        os.setuid(running_uid)
    
        # Ensure a very conservative umask
        os.umask(077)


    def start(self):
        """
        Start the daemon
        """

        # if we run then don't do anything. Silently ignore all errors that happen while we check the status
        try:
            if self.is_running():
                print "Already running with pid %r!" % self.pid
                return 0
        except:
            pass

        # Start the daemon
        if self.daemonize():
            time.sleep(1)
            return self.status()
        else:
            print "Could not start service!" >> sys.stderr
            return 1
    
    def status(self):
        if self.is_running():
            print "Running with pid %r" % self.pid
            return 0
        else:
            print "Not running"
            return 1

    def stop(self):
        """
        Stop the daemon
        """
        self._read_pid()
    
        if not self.pid:
            # no pid means that there is no process
            print "Not running"
            return 0  # not an error in a restart

        # Try killing the daemon process    
        try:
            for i in range(100):
                os.kill(self.pid, SIGTERM)
                time.sleep(0.1)
            # if the process is still there after 10 seconds, give it a hard kill
            os.kill(self.pid, SIGKILL)
            time.sleep(1)
            os.kill(self.pid, SIGKILL)  # try again, the process should be already gone. This also lets us jump to the except
        except OSError, e:
            if e.errno == 3:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                raise YamlServerException("Could not kill process %r: %s" % (self.pid, str(e)))
        else:
            # the 2nd KILL also did not work, something is really bad here
            raise YamlServerException("Even a SIGKILL did not kill process %r!")

        return 0

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        time.sleep(2)  # give system chance to release socket
        return self.start()

    def service_script(self):
        """
        Call this as service script
        """
        if len(self.args) == 1:
            command = self.args[0]
            if 'start' == command:
                return self.start()
            elif 'stop' == command:
                return self.stop()
            elif 'restart' == command:
                return self.restart()
            elif 'status' == command:
                return self.status()
            else:
                print "Unknown command %s" % command
                return 2
        else:
            print "usage: %s start|stop|restart|status" % sys.argv[0]
            return 2

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
