def test_observer(populate_db):
    """
    Test observer model
    """
    observers = populate_db["observers"]
    assert observers[0].is_receiving_all_incident is True
