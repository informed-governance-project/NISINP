from flask import Flask
from flask_sqlalchemy import SQLAlchemy

application = Flask(__name__, instance_relative_config=True)

db = SQLAlchemy(application)
