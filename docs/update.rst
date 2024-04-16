Updating the application
========================

All you have to do is:

.. code-block:: bash

    $ cd NISINP/
    $ ./contrib/update.sh


Or manually:

.. code-block:: bash

    $ cd NISINP/
    $ git pull origin master --tags
    $ npm ci
    $ poetry install
    $ poetry run python manage.py collectstatic
    $ poetry run python manage.py migrate
    $ poetry run python manage.py compilemessages


Finally, restart Apache:

.. code-block:: bash

    $ sudo systemctl restart apache2.service
