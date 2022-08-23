
from datetime import datetime
from nisinp.bootstrap import db


class Incident(db.Model):
    """Represent an incident."""

    id = db.Column(db.Integer, primary_key=True)

    ## Operator inputs
    incident_detection_date = db.Column(db.DateTime(), default=datetime.utcnow)
    incident_duration = db.Column(db.String(), nullable=True)
    geographical_extent = db.Column(db.String(), nullable=True)
    incident_nature = db.Column(db.String(), nullable=True)
    impacted_service = db.Column(db.String(), nullable=True)  # or from a defined list of services
    # impacted_criteria  # availability, confidentiality, integrity, authenticity
    number_impacted_users = db.Column(db.Integer, nullable=True)
    # importance_impacted_entity =
    taken_actions = db.Column(db.String(), nullable=False)
    description_current_situation = db.Column(db.String(), nullable=False)
    ## End Operator inputs

    created_at = db.Column(db.DateTime(), default=datetime.utcnow)  # incident_notification_date
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow)
    # state = 
    is_draft = db.Column(db.Boolean(), default=True)
    is_published = db.Column(db.Boolean(), default=False)

    # foreign keys
    operator_id = db.Column(db.Integer(), db.ForeignKey("operator.id"), nullable=False)
    creator_id = db.Column(db.Integer(), db.ForeignKey("user.id"), nullable=False)