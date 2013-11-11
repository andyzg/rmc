#!/bin/bash

install_packages() {
    updated_apt_repo=""

    # To get the most recent nodejs, later.
    if ! ls /etc/apt/sources.list.d/ 2>&1 | grep -q chris-lea-node_js; then
        sudo add-apt-repository -y ppa:chris-lea/node.js
        updated_apt_repo=yes
    fi

    # To get the most recent git.
    if ! ls /etc/apt/sources.list.d/ 2>&1 | grep -q git-core-ppa; then
        sudo add-apt-repository -y ppa:git-core/ppa
        updated_apt_repo=yes
    fi

    # To get the most recent redis
    if ! ls /etc/apt/sources.list.d/ 2>&1 | grep -q rwky-redis; then
        sudo add-apt-repository -y ppa:rwky/redis
        updated_apt_repo=yes
    fi

    # To get the most recent mongodb
    if ! ls /etc/apt/sources.list.d/ 2>&1 | grep -q 10gen; then
        sudo apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10
        sudo rm -rf /etc/apt/sources.list.d/10gen.list
        sudo /bin/sh -c 'echo "deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen" > /etc/apt/sources.list.d/10gen.list'
        updated_apt_repo=yes
    fi

    # Register all that stuff we just did.
    if [ -n "$updated_apt_repo" ]; then
        sudo apt-get update -qq -y || true
    fi

    sudo apt-get install -y \
        built-essential \
        git \
        python-setuptools python-pip python-dev \
        libxml2-dev libxslt-dev \
        ruby rubygems \
        nodejs \
        redis-server \
        mongodb-10gen

    # Remove pylint that's installed via distro's repo if it exists, since it
    # can conflict with the one from pip
    sudo apt-get remove pylint && \
        sudo apt-get remove python-logilab-common && \
        sudo apt-get remove python-logilab-astng
}

install_phantomjs() {
    if ! which phantomjs >/dev/null; then
        (
            cd /usr/local/share
            case `uname -m` in
                i?86) mach=i686;;
                *) mach=x86_64;;
            esac
            sudo rm -rf phantomjs
            wget "https://phantomjs.googlecode.com/files/phantomjs-1.9.2-linux-${mach}.tar.bz2" -O- | sudo tar xfj -

            sudo ln -snf /usr/local/share/phantomjs-1.9.2-linux-${mach}/bin/phantomjs /usr/local/bin/phantomjs
        )
        which phantomjs >/dev/null
    fi
}

# Get password up front
sudo echo

install_packages
install_phantomjs