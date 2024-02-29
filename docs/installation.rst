Installation
============

This section covers the installation steps of the sofware.

Containerized installation
--------------------------

You can, optionnally, create a LXC container.

.. code-block:: bash

    lxc launch ubuntu:22.10 NISINP --storage your-storage
    lxc exec NISINP -- /bin/bash


Poetry
------

.. code-block:: bash

    curl -sSL https://install.python-poetry.org | python3 -


at the end of the `~/.bashrc`

.. code-block:: bash

    export PATH="/root/.local/bin:$PATH"


PostgreSQL
----------

Install PostgreSQL, the version provided by default for your
GNU/Linux distribution.

.. code-block:: bash

    sudo apt-get install postgresql-15
    sudo su postgres
    psql
    /password postgres
    # password


NISINP
------

.. code-block:: bash

    git clone https://github.com/informed-governance-project/NISINP.git
    cd NISINP
    git submodule update --init --recursive
    # Copy the config and adjust the DB connection and the other settings:
    cp governanceplatform/config_dev.py governanceplatform/config.py
    poetry install
    poetry shell
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py collectstatic
    poetry manage.py compilemessages


The theme (CSS, icons, etc.) of the sofware will be under the ``theme`` folder as a Git submodule.
You can replace it by your own. Currently two themes are available:

- https://github.com/informed-governance-project/default-theme (default theme, used for ILR Luxembourg)
- https://github.com/informed-governance-project/serimabe-theme (theme for IBPT.be)



JavaScript
----------

.. code-block:: bash

    git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.12.0

at the end of the `~/.bashrc`

.. code-block:: bash

    . "$HOME/.asdf/asdf.sh"
    . "$HOME/.asdf/completions/asdf.bash"


.. code-block:: bash

    asdf plugin add nodejs https://github.com/asdf-vm/asdf-nodejs.git
    asdf install nodjs latest
    asdf reshim nodejs
    asdf global nodejs latest


If you do not want to use ``asdf``, you can as well use ``npm install``.

.. code-block:: bash

    cd NISINP
    npm install
    poetry run python manage.py collectstatic


Launch the Django application
-----------------------------

.. code-block:: bash

    poetry run python manage.py runserver 127.0.0.1:8000

Of course, do not do that for a production environment.


Apache WSGI module
------------------

The mod_wsgi package provides an Apache module that implements a WSGI compliant
interface for hosting Python based web applications on top of the Apache web
server.

For the next steps you must have a valid domain name.


Example of VirtualHost configuration file
`````````````````````````````````````````

Only in the case you can not use the version of mod_wsgi from your
GNU/Linux distribution.


.. code-block:: bash

    $ sudo apt install apache2 apache2-dev # apxs2
    $ wget https://github.com/GrahamDumpleton/mod_wsgi/archive/refs/tags/5.0.0.tar.gz
    $ tar -xzvf 5.0.0.tar.gz
    $ cd mod_wsgi-5.0.0/
    $ ./configure --with-apxs=/usr/bin/apxs2 --with-python=/home/<user>/.pyenv/shims/python
    $ make
    $ sudo make install


Then in ```/etc/apache2/apache2.conf``` add the lines:

.. code-block:: bash

    LoadFile /home/<user>/.pyenv/versions/3.11.0/lib/libpython3.11.so
    LoadModule wsgi_module /usr/lib/apache2/modules/mod_wsgi.so


Restart Apache:

.. code-block:: bash

    sudo systemctl restart apache2.service


Create an Apache VirtualHost. Below is an example:


.. code-block:: apacheconf

    <VirtualHost *:80>
        ServerName serima.monarc.lu

        RewriteEngine On
        RewriteCond %{REQUEST_METHOD} !^(GET|POST|PUT|PATCH|DELETE|HEAD)
        RewriteRule .* - [R=405,L]

        Redirect permanent / https://serima.monarc.lu/
    </VirtualHost>

    <VirtualHost _default_:443>
        ServerName serima.monarc.lu
        ServerAdmin info@nc3.lu
        DocumentRoot ~/SERIMA/NISINP

        WSGIDaemonProcess serima python-path=~/SERIMA/NISINP python-home=~/.cache/pypoetry/virtualenvs/governanceplatform-Q3fVTCKh-py3.11
        WSGIProcessGroup serima
        WSGIScriptAlias / ~/SERIMA/NISINP/governanceplatform/wsgi.py

        <Directory "~/SERIMA/NISINP/governanceplatform/">
            <Files "wsgi.py">
                Require all granted
            </Files>
            WSGIApplicationGroup %{GLOBAL}
            WSGIPassAuthorization On

            Options Indexes FollowSymLinks
            Require all granted
        </Directory>

        Alias /static ~/SERIMA/NISINP/governanceplatform/static
        <Directory ~/SERIMA/NISINP/governanceplatform/static>
            Require all granted
        </Directory>

        # Available loglevels: trace8, ..., trace1, debug, info, notice, warn,
        # error, crit, alert, emerg.
        # It is also possible to configure the loglevel for particular
        # modules, e.g.
        #LogLevel info ssl:warn
        CustomLog /var/log/apache2/SERIMA/access.log combined
        ErrorLog /var/log/apache2/SERIMA/error.log

        Include /etc/letsencrypt/options-ssl-apache.conf
        ServerAlias serima.monarc.lu
        SSLCertificateFile /etc/letsencrypt/live/serima.monarc.lu/fullchain.pem
        SSLCertificateKeyFile /etc/letsencrypt/live/serima.monarc.lu/privkey.pem
    </VirtualHost>


Then configure HTTPS properly.

.. code-block:: bash

    sudo apt install certbot python3-certbot-apache
    sudo certbot certonly --standalone -d serima.monarc.lu
    sudo a2enmod rewrite
    sudo systemctl restart apache2.service
