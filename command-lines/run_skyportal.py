import subprocess


def activate_skyportal_env():
    cmd = subprocess.Popen(["conda", "activate", "skyportal"])
    cmd.communicate()


def db_run_skyportal():
    cmd = subprocess.Popen(
        ["make", "db_clear", "&&", "make", "db_init", "&&", "make" "run"],
        cwd=os.path.dirname(os.path.dirname("__file__")) + "../../skyportal",
        stdout=PIPE,
        stderr=PIPE,
    )
    stdout, stderr = cmd.communicate()
