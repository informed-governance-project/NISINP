Installation
============


Deployment
----------

Containerized installation
~~~~~~~~~~~~~~~~~~~~~~~~~~

container
`````````

.. code-block:: bash

    lxc launch ubuntu:22.10 governance-platform --storage your-storage
    lxc exec governance-platform -- /bin/bash


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


Governance Platform
```````````````````


.. code-block:: bash

    git clone https://github.com/informed-governance-project/governance-platform.git
    cd governance-platform
    git submodule update --init --recursive
    # Copy the config and adjust the DB connection settings.
    cp governanceplatform/config_dev.py governanceplatform/config.py
    poetry install
    poetry shell
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py collectstatic
    poetry manage.py compilemessages


JavaScript
``````````

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

    cd governance-platform
    npm install


Launch the Django app
`````````````````````

.. code-block:: bash

    poetry run python manage.py runserver 127.0.0.1:8000
