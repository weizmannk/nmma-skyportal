# nmma-skyportal
    To use nmma-skyportal, you must install nmma then skyportal.

### to clone nmma-skyportal by automatically initialize and update each submodule

    git clone --recurse-submodules  https://github.com/weizmannk/nmma-skyportal.git

### clone the submodules

    git submodule init

    git submodule update

### Instruction for nmma installation

    https://github.com/nuclear-multimessenger-astronomy/nmma/blob/main/doc/installation.md

### Instruction for  skyportal  installation

    https://skyportal.io/docs/setup.html

                 or

    https://github.com/skyportal/skyportal/blob/main/doc/setup.md

## skyportal quick installation instructions

### Linus and Ubuntu users

1* Install dependencies

    sudo apt install nginx supervisor postgresql \
      libpq-dev npm python3-pip \
      libcurl4-gnutls-dev libgnutls28-dev

2* install npm recent version

    https://computingforgeeks.com/how-to-install-node-js-on-ubuntu-debian/

    cd ~
    curl -sL https://deb.nodesource.com/setup_16.x | sudo bash -

    sudo apt -y install nodejs

check the nvm lis

    nvm list-remote

For Ubuntu 22.04/20.04/18/04, install Node.js 16.x version

    nvm install v16

this install  node v16.14.2 (npm v8.5.0)

Use this  version

    nvm install v16.14.2

To use this vesion by default execute this :

    nvm use 16.14.2


 Set it as the default.

    nvm alias default 16.14.2

3*Configure your database permissions.

In /etc/postgresql/<postgres-version>/main (typically located in /etc/postgresql/<postgres-version>/main), insert the following lines before any other host lines:
where <postgres-version> is the number of postgres version

### use sudo vim /etc/postgresql/<postgres-version>/main/pg_hba.conf

    host skyportal postgres ::1/128 trust
    host skyportal_test postgres ::1/128 trust
    host skyportal postgres 127.0.0.1/32 trust
    host skyportal_test postgres 127.0.0.1/32 trust

### then replace the column all 4 (Method) od  'Database administrative login by Unix domain socket' (at the bottom of the ppg_hba.conf file ) by 'trust'. Like this:

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
