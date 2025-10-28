# datas for incidents
# emails
emails = [
    {
        "id": "2",
        "name": "Incident closure",
        "subject": "Incident closure",
        "content": "Incident #INCIDENT_ID#\r\n\r\nDear Entity,\r\n\r\nThe incident #INCIDENT_ID# has just been closed.",
        "creator": {"id": 1},
    },
    {
        "id": "1",
        "name": "New incident creation",
        "subject": "New incident creation",
        "content": "Incident: #INCIDENT_ID#\r\n\r\nDear Entity,\r\n\r\nYou have just started the creation a new incident.",
        "creator": {"id": 1},
    },
    {
        "id": "4",
        "name": "Incident closure",
        "subject": "Incident closure",
        "content": "Incident #INCIDENT_ID#\r\n\r\nDear Entity,\r\n\r\nThe incident #INCIDENT_ID# has just been closed.",
        "creator": {"id": 2},
    },
    {
        "id": "3",
        "name": "New incident creation",
        "subject": "New incident creation",
        "content": "Incident: #INCIDENT_ID#\r\n\r\nDear Entity,\r\n\r\nYou have just started the creation a new incident.",
        "creator": {"id": 2},
    },
]

# questions
questions = [
    {
        "id": 1,
        "reference": "1",
        "label": "Is it a recurrent issue?",
        "tooltip": "",
        "question_type": "SO",
        "creator": {"id": 1},
    },
    {
        "id": 2,
        "reference": "2",
        "label": "Notification to other regulator in the context of other regulation?",
        "tooltip": "if yes specify",
        "question_type": "MT",
        "creator": {"id": 1},
    },
    {
        "id": 3,
        "reference": "3",
        "label": "Other parties involved",
        "tooltip": "",
        "question_type": "FREETEXT",
        "creator": {"id": 1},
    },
    {
        "id": 4,
        "reference": "4",
        "label": "Name of the declarer",
        "tooltip": "Person in charge of the handling of the notification",
        "question_type": "FREETEXT",
        "creator": {"id": 1},
    },
    {
        "id": 5,
        "reference": "5",
        "label": "Sector of activity",
        "tooltip": "",
        "question_type": "FREETEXT",
        "creator": {"id": 1},
    },
    {
        "id": 6,
        "reference": "6",
        "label": "Is the incident solved?",
        "tooltip": "",
        "question_type": "SO",
        "creator": {"id": 2},
    },
    {
        "id": 7,
        "reference": "7",
        "label": "is impacting other countries?",
        "tooltip": "if yes specify",
        "question_type": "MT",
        "creator": {"id": 2},
    },
    {
        "id": 8,
        "reference": "8",
        "label": "Is it an important incident",
        "tooltip": "",
        "question_type": "FREETEXT",
        "creator": {"id": 2},
    },
    {
        "id": 9,
        "reference": "9",
        "label": "Please describe more",
        "tooltip": "",
        "question_type": "FREETEXT",
        "creator": {"id": 2},
    },
    {
        "id": 10,
        "reference": "10",
        "label": "Need more information",
        "tooltip": "",
        "question_type": "FREETEXT",
        "creator": {"id": 2},
    },
]

question_category = [
    {
        "id": 1,
        "label": "Reg 1 categ 1",
        "creator": {"id": 1},
    },
    {
        "id": 2,
        "label": "Reg 1 categ 2",
        "creator": {"id": 1},
    },
    {
        "id": 3,
        "label": "Reg 2 categ 1",
        "creator": {"id": 2},
    },
    {
        "id": 4,
        "label": "Reg 2 categ 2",
        "creator": {"id": 2},
    },
]

predefined_answers = [
    {
        "id": 1,
        "predefined_answer": "Yes",
        "question": {"id": 1},
        "creator": {"id": 1},
    },
    {
        "id": 2,
        "predefined_answer": "No",
        "question": {"id": 1},
        "creator": {"id": 1},
    },
    {
        "id": 3,
        "predefined_answer": "Yes",
        "question": {"id": 2},
        "creator": {"id": 1},
    },
    {
        "id": 4,
        "predefined_answer": "No",
        "question": {"id": 2},
        "creator": {"id": 1},
    },
    {
        "id": 5,
        "predefined_answer": "Yes",
        "question": {"id": 7},
        "creator": {"id": 2},
    },
    {
        "id": 6,
        "predefined_answer": "No",
        "question": {"id": 7},
        "creator": {"id": 2},
    },
    {
        "id": 7,
        "predefined_answer": "Yes",
        "question": {"id": 6},
        "creator": {"id": 2},
    },
    {
        "id": 8,
        "predefined_answer": "No",
        "question": {"id": 6},
        "creator": {"id": 2},
    },
]

# Report
reports = [
    # asectorial workflow
    {
        "id": 1,
        "name": "Reg 1 preli",
        "label": "Reg 1 preli",
        "is_impact_needed": False,
        "creator": {"id": 1},
        "submission_email": {"id": 2},
    },
    {
        "id": 2,
        "name": "Reg 1 final",
        "label": "Reg 1 final",
        "is_impact_needed": False,
        "creator": {"id": 1},
        "submission_email": {"id": 2},
    },
    # sectorial workflow
    {
        "id": 3,
        "name": "Reg 2 preli",
        "label": "Reg 2 preli",
        "is_impact_needed": True,
        "creator": {"id": 2},
        "submission_email": {"id": 4},
    },
    {
        "id": 4,
        "name": "Reg 2 final",
        "label": "Reg 2 final",
        "is_impact_needed": True,
        "creator": {"id": 2},
        "submission_email": {"id": 4},
    },
]

question_category_option = [
    {"id": 1, "question_category": {"id": 1}, "position": 1},
    {"id": 2, "question_category": {"id": 2}, "position": 2},
    {"id": 3, "question_category": {"id": 3}, "position": 3},
    {"id": 4, "question_category": {"id": 4}, "position": 4},
]

question_options = [
    {
        "report": {"id": 1},
        "question": {"id": 1},
        "is_mandatory": True,
        "position": 1,
        "category_option": {"id": 1},
    },
    {
        "report": {"id": 1},
        "question": {"id": 2},
        "is_mandatory": False,
        "position": 2,
        "category_option": {"id": 1},
    },
    {
        "report": {"id": 2},
        "question": {"id": 3},
        "is_mandatory": True,
        "position": 1,
        "category_option": {"id": 2},
    },
    {
        "report": {"id": 2},
        "question": {"id": 4},
        "is_mandatory": False,
        "position": 2,
        "category_option": {"id": 2},
    },
    {
        "report": {"id": 2},
        "question": {"id": 5},
        "is_mandatory": False,
        "position": 3,
        "category_option": {"id": 2},
    },
    {
        "report": {"id": 3},
        "question": {"id": 6},
        "is_mandatory": True,
        "position": 1,
        "category_option": {"id": 3},
    },
    {
        "report": {"id": 3},
        "question": {"id": 7},
        "is_mandatory": False,
        "position": 2,
        "category_option": {"id": 3},
    },
    {
        "report": {"id": 4},
        "question": {"id": 8},
        "is_mandatory": True,
        "position": 1,
        "category_option": {"id": 4},
    },
    {
        "report": {"id": 4},
        "question": {"id": 9},
        "is_mandatory": False,
        "position": 2,
        "category_option": {"id": 4},
    },
    {
        "report": {"id": 4},
        "question": {"id": 10},
        "is_mandatory": False,
        "position": 3,
        "category_option": {"id": 4},
    },
]

workflows = [
    # asectorial
    {
        "id": 1,
        "name": "asectorial workflow",
        "regulation": {"id": 2},
        "regulator": {"id": 1},
        "is_detection_date_needed": False,
        "opening_email": {"id": 1},
        "closing_email": {"id": 2},
    },
    # sectorial
    {
        "id": 2,
        "name": "NIS workflow",
        "regulation": {"id": 1},
        "regulator": {"id": 2},
        "is_detection_date_needed": True,
        "opening_email": {"id": 3},
        "closing_email": {"id": 4},
        "sectors": [{"acronym": "GAS"}, {"acronym": "ELEC"}],
    },
]

workflows_reports = [
    {
        "sector_regulation": {"id": 1},
        "workflow": {"id": 1},
        "position": 1,
    },
    {
        "sector_regulation": {"id": 1},
        "workflow": {"id": 2},
        "position": 2,
    },
    {
        "sector_regulation": {"id": 2},
        "workflow": {"id": 3},
        "position": 1,
        "delay_in_hours_before_deadline": 16,
        "trigger_event_before_deadline": "DETECT_DATE",
    },
    {
        "sector_regulation": {"id": 2},
        "workflow": {"id": 4},
        "position": 2,
        "delay_in_hours_before_deadline": 16,
        "trigger_event_before_deadline": "PREV_WORK",
    },
]

impacts = [
    {
        "label": "impact1",
        "headline": "headline impact1",
        "regulation": {"id": 1},
        "sectors": [{"acronym": "GAS"}, {"acronym": "ELEC"}],
        "creator": {"id": 2},
    },
    {
        "label": "impact2",
        "headline": "headline impact2",
        "regulation": {"id": 1},
        "sectors": [{"acronym": "GAS"}, {"acronym": "ELEC"}],
        "creator": {"id": 2},
    },
    {
        "label": "impact3",
        "headline": "headline impact3",
        "regulation": {"id": 1},
        "sectors": [{"acronym": "GAS"}, {"acronym": "ELEC"}],
        "creator": {"id": 2},
    },
]
