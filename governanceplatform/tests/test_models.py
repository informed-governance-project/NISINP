def test_observer(populate_db):
    """
    Test observer model
    """
    observer = populate_db["observer"]
    assert observer.is_receiving_all_incident is True
