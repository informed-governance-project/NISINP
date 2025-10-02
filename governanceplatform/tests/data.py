# data for tests
# companies
companies_data = [
    {
        "identifier": "COM1",
        "name": "Test Company 1",
        "country": "FR",
        "address": "123 Rue de Paris",
        "email": "contact1@testcompany.com",
        "phone_number": "+33123456789",
        "categories": ["Critical"]
    },
    {
        "identifier": "COM2",
        "name": "Test Company 2",
        "country": "BE",
        "address": "56 Boulevard de Bruxelles",
        "email": "contact2@testcompany.com",
        "phone_number": "+32212345678",
        "categories": ["Public"]
    }
]

functionalities_data = [{"name": "Reporting", "type": "Reporting"}, {"name": "so", "type": "securityobjectives"}]

regulators_data = [
    {
        "name": "REG1",
        "full_name": "Regulator1",
        "description": "Regulator responsible for NIS",
        "country": "LU",
        "address": "123 rue de Luxembourg",
        "email_for_notification": "regulator1@reg.lu",
        "functionalities": [{"type": "securityobjectives"}]
    },
    {
        "name": "REG2",
        "full_name": "Regulator2",
        "description": "Regulator responsible for NIS2",
        "country": "LU",
        "address": "123 rue de Luxembourg",
        "email_for_notification": "regulator2@reg2.lu",
        "functionalities": []
    }
]

observers_data = [
    {
        "name": "CERT1",
        "full_name": "CERT1",
        "country": "LU",
        "address": "123 rue de Luxembourg",
        "email_for_notification": "cert1@cert1.lu",
        "is_receiving_all_incident": True
    }
]
