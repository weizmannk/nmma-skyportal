import subprocess


# def activate_skyportal_env():

# cmd1 = subprocess.Popen(["source",  "~/anaconda3/etc/profile.d/conda.sh"])
# cmd2 = subprocess.Popen(["conda", "activate", "skyportal"])
# cmd1.communicate()
# cmd2.communicate()


def db_run_skyportal():
    cmd = subprocess.Popen(
        ["make", "db_clear", "&&", "make", "db_init", "&&", "make" "run"],
        cwd=os.path.dirname(os.path.dirname("__file__")) + "../services/skyportal",
        stdout=PIPE,
        stderr=PIPE,
    )
    stdout, stderr = cmd.communicate()
