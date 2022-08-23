
from datetime import datetime
from nisinp.bootstrap import db


class Operator(db.Model):
    """Represent an Operators of Essential Services (OES)."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=True)
    country = db.Column(db.String(), nullable=True)

    # services = 
    # dependencies = 

    created_at = db.Column(db.DateTime(), default=datetime.utcnow)  # incident_notification_date

    # foreign keys
    operator_id = db.Column(db.Integer(), db.ForeignKey("operator.id"), nullable=False)
    creator_id = db.Column(db.Integer(), db.ForeignKey("user.id"), nullable=False)