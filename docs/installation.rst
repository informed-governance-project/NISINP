Installation
============

Prerequisites
-------------

Generally speaking, requirements are the following:

- A GNU/Linux distribution. Tested on Debian Bookworm;
- Python version >= 3.9. Tested with Python 3.11;
- A PostgreSQL server for persistent storage. Tested with PostgreSQL 15.3.


Deployment
----------

Ghetto dev installation
~~~~~~~~~~~~~~~~~~~~~~~

container
`````````

.. code-block:: bash

    lxc launch ubuntu:22.10 NISINP --storage your-storage
    lxc exec NISINP -- /bin/bash


poetry
``````

.. code-block:: bash

    curl -sSL https://install.python-poetry.org | python3 -


at the end of the `~/.bashrc`

.. code-block:: bash

    export PATH="/root/.local/bin:$PATH"


postgres
````````

.. code-block:: bash

    apt get install postgres-14
    sudo su postgres
    psql
    /password postgres
    # password


NISINP
``````


.. code-block:: bash

    git clone https://github.com/informed-governance-project/NISINP.git
    cd NISINP
    git submodule update --recursive
    poetry install
    poetry build
    poetry shell
    poetry run python manage.py migrate
    poetry run python manage.py manage.py createsuperuser


js
``


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


.. code-block:: bash

    cd NISINP
    npm install


Launch django app
`````````````````

.. code-block:: bash

    poetry run python manage.py runserver 0.0.0.0:8000
