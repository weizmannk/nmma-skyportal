# Instructions For  `nmma-skyportal`  Installation

To install  `nmma-skyportal` need to install **[nmma]**, **[skyportal]** then  some depencies rely on with `fink-client`

## **I  PRELIMINARY STEPS**:

This installation is based specifically on the experience of Ubuntu 20.04 and Linux systems in general.

1. **Installing Anaconda3**

    On your Linux terminal, run the following commands to install anaconda (replace 5.3.1 by the latest version):
    (For 32-bit installation, skip the ‘_64’ in both commands).


    *  **`Download Anaconda3`**

        ```
        wget https://repo.anaconda.com/archive/Anaconda3-5.3.1-Linux-x86_64.sh
        ```

    * **`install anaconda`**

        ```
        bash Anaconda3-5.3.1-Linux-x86_64.sh
        ```
    NOTE: If you already have Anaconda3 installed, please make sure that it is updated to the latest version (conda update --all). Also check that you do not have multiple versions of python installed in usr/lib/ directory as it can cause version conflicts while installing dependencies.

    * **`upgrade anaconda3`**

        ```
        conda update --all
        ```

2. **Cloning the `NMMA-SKYPORTAL` repository automatically initialize and update each submodule (`nmma`  and `skyportal` )**
    ```
    git clone --recurse-submodules  https://github.com/weizmannk/nmma-skyportal.git
    ```

    * Go to `nmma-skyportal` directory

        ```
        cd nmma-skyportal
        ```

    * ### `Main Installation`

         **Create a new environment using this command (environment name is `nmma-skyportal_env` in this case)** :

        ___`ALERT`___

        _For the moment we advise Linux users to avoid using python3.9 and python3.10 in their nmma environment this can generate major problems for the operation. So use preferably python3.8._

        ```
        conda create --name nmma-skyportal_env python=3.8
        ```

        **Then proceed with conda activate nmma-skyportal_env**

        ```
        conda activate nmma-skyportal_env
        ```

        ___`NOTE :`___

        If this gives an error like: CommandNotFoundError: Your shell has not been properly configured to use `conda activate`, then run:

        ```
        source ~/anaconda3/etc/profile.d/conda.sh
        ```

        `Get the latest pip version`

        ```
        pip install --upgrade pip
        ```

        `Install ipython`

        ```
        pip install ipython
        ```

        `Install mpi4py`

        ```
        conda install mpi4py
        ```
        OR

        ```
        pip install mpi4py
        ```

        `Install parallel-bilby`:

        ```
        conda install -c conda-forge parallel-bilby
        ```
        OR

        ```
        pip install parallel-bilby
        ```

        `Install pymultinest`

        ```
        conda install -c conda-forge pymultinest
        ```

        NOTE: In case if an error comes up during an NMMA analysis of the form:

        ERROR:   Could not load MultiNest library "libmultinest.so"

        ERROR:   You have to build it first,

        ERROR:   and point the LD_LIBRARY_PATH environment variable to it!

        Then, for using the PyMultinest library, it is required to get and compile the Multinest library separately. Instructions for the same are given here : **[PyMultiNest]**

## **II  Installaling [NMMA-SKYPORTAL]**

1. **Install `NMMA`'s dependencies file which are necessary for :**

    *  **go to nmma directory**

        ```
        cd nmma
        ```

    * **depencies's installation**

        ```
        python setup.py install
        ```

   * To make sure, install again the requirements with pip like this:
        ```
        pip install  extinction

        pip install dill

        pip install multiprocess

        pip install lalsuite

        pip install python-ligo-lw
        ```
    * First Test for `NMMA` :  Run the following command

        ```
        ipython

        import nmma

        import nmma.em.analysis

        import nmma.eos.create_injection
        ```

    For more please go to  **[NMMA-installation]**

    * if everything is working, then move back on nmma-skyportal

        ```
        cd ..
        ```


2. **Install `SKYPORTAL`'s dependencies:**

    For now `MacOS` and `Windows` users please go to : **[setu.html]** or **[setup.md]**.

    `Linux`/ `Ubuntu` users


    *  Install `skyportal` dependencies

        ```
        sudo apt install nginx supervisor postgresql \
        libpq-dev libcurl4-gnutls-dev libgnutls28-dev
        ```

    * install recent version of **[npn & nodejs]** by using `NVM`

            curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash

    * To activate `nmv` without `Close` and `Reopen` your terminal use :

        ```
        source ~/.bashrc
        ```

         and check `nvm` version

        ```
        nvm --version
        ```

   * check the available Node.js versions in `nvm`

        ```
        nvm list-remote
        ```

    * For `Ubuntu` 22.04/20.04/18/04, install Node.js 16.x version

        ```
        nvm install v16.14.2
        ```

        this install  node v16.14.2 (npm v8.5.0)

    * To use this vesion by default execute this :

        ```
        nvm use 16.14.2
        ```

    * Set it as the default.

        ```
        nvm alias default 16.14.2
        ```

3. **Configure your database permissions:**

    ```
    host skyportal skyportal 127.0.0.1/32 trust
    host skyportal_test skyportal 127.0.0.1/32 trust
    host all postgres 127.0.0.1/32 trust
    ```

4.  **Configure your database permissions :**

    * go back to `skyportal` directory

        ```
        cd ./nmma-skyportal/skyportal
        ```

    * In `pg_hba.conf` (typically located in
    `/etc/postgresql/<postgres-version>/main`), insert the following lines *before* any other `host` lines , where <postgres-version> is the number of postgres version :

        ```
        host skyportal postgres ::1/128 trust
        host skyportal_test postgres ::1/128 trust
        host skyportal postgres 127.0.0.1/32 trust
        host skyportal_test postgres 127.0.0.1/32 trust
        ```

    * Use `sudo`  to open `pg_hba.conf` like thise

        ```
        sudo vim /etc/postgresql/<postgres-version>/main/pg_hba.conf
        ```
    * After past after pasting the lines above, please check inthe same file `pg_hba.conf` if all the column 4 of  `METHOD`  (see the lines at the bottom of `pg_hba.conf`) at **Database administrative login by Unix domain socket** are  `trust`, like the following example below:

        If not replace all by `trust`.

        ```
            # TYPE  DATABASE        USER            ADDRESS                 METHOD
            # "local" is for Unix domain socket connections only
            local   all             all                                     trust
            # IPv4 local connections:
            host    all             all             127.0.0.1/32            trust
            # IPv6 local connections:
            host    all             all             ::1/128                 trust
            # Allow replication connections from localhost, by a user with the
            # replication privilege.
            local   replication     all                                     trust
            host    replication     all             127.0.0.1/32            trust
            host    replication     all             ::1/128                 trust

        ```

    * Then Restart `PostgreSQL`:

        ```
        sudo service postgresql restart
        ```

    * To run the test suite, you’ll need `Geckodriver`:

        - Download the latest version from https://github.com/mozilla/geckodriver/releases/
        - Extract the binary to somewhere on your path
        - Ensure it runs with `geckodriver --version`

        In later versions of Ubuntu (16.04+), you can install Geckodriver through apt:

        ```
        sudo apt install firefox-geckodriver
        ```


    * To build the docs, you'll need graphviz:

        ```
        sudo apt install graphviz-dev graphviz
        ```

# Other commands for develloping

This is only necessary for those who wish to contribute to the project


1. Install **[pre-commit]**

    ```
    pip install pre-commit
    ```
    or
    ```
    conda install -c conda-forge pre-commit
    ```
    Then run this command in your terminal

    ```
    pre-commit
    ```

* check the `pre-commit` version

    ```
    pre-commit --version
    ```
* Create pre-commit file

    ```
    touch .pre-commit-config.yaml
    ```

*   Install your `pe-commit`

    ```
    pre-commit install
    ```
* Run it to check

    ```
    pre-commit run --all-files
    ```










[nmma]: https://github.com/nuclear-multimessenger-astronomy/nmma
[NMMA-installation]: https://github.com/nuclear-multimessenger-astronomy/nmma/blob/main/doc/installation.md
[skyportal]: https://github.com/skyportal/skyportal/blob/main/doc/setup.md
[NMMA-SKYPORTAL]:https://github.com/weizmannk/nmma-skyportal
[setu.html]: https://skyportal.io/docs/setup.html
[setup.md]: https://github.com/skyportal/skyportal/blob/main/doc/setup.md
[npn & nodejs]: https://computingforgeeks.com/how-to-install-node-js-on-ubuntu-debian
[pre-commit]: https://pre-commit.com
[PyMultiNest]: https://johannesbuchner.github.io/PyMultiNest/install.html
