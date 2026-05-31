# app/extensions.py
# Instance unique de db partagée par tout le projet

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()