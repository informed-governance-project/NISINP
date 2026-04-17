import pytest
from django.utils.translation import activate

import governanceplatform.tests.conftest as gp_conftest
from conftest import import_from_json
from securityobjectives.models import (
    Domain,
    MaturityLevel,
    SecurityMeasure,
    SecurityObjective,
    SecurityObjectivesInStandard,
    Standard,
)
from securityobjectives.tests.so_data import (
    domains,
    levels,
    sms,
    sos,
    standard,
)


@pytest.fixture
def populate_db(db):
    # on rewrap fixture to expose localy and don't get flake error
    return gp_conftest.populate_db.__wrapped__(db)


@pytest.fixture
def populate_so_db(populate_db):
    """
    Populate the DB
    """
    # Force default language for translatable
    activate("en")

    # populate a standard
    populate_db["so_standard"] = import_from_json(Standard, standard, True, False)
    populate_db["so_maturity_level"] = import_from_json(
        MaturityLevel, levels, True, False
    )
    populate_db["so_domain"] = import_from_json(Domain, domains, True, False)
    populate_db["so_security_objectives"] = import_from_json(
        SecurityObjective, sos, True, False
    )
    populate_db["so_security_measures"] = import_from_json(
        SecurityMeasure, sms, True, False
    )
    # link SOs into standard
    for i, so in enumerate(populate_db["so_security_objectives"]):
        std = Standard.objects.get(pk=1)
        SecurityObjectivesInStandard.objects.create(
            standard=std, security_objective=so, position=i
        )

    return populate_db
