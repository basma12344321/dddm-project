# app/models.py

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(50), default='analyste')  # admin / analyste / lecteur
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    analyses = db.relationship('Analysis', backref='user', lazy=True)

    def to_dict(self):
        return {
            'id':         self.id,
            'email':      self.email,
            'role':       self.role,
            'created_at': self.created_at.isoformat()
        }


class Analysis(db.Model):
    __tablename__ = 'analyses'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    domain        = db.Column(db.String(50), nullable=False)   # finance / logistic
    plugin_name   = db.Column(db.String(100), nullable=False)
    filename      = db.Column(db.String(255), nullable=True)
    result_json   = db.Column(db.JSON, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    simulations = db.relationship('Simulation', backref='analysis', lazy=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'user_id':     self.user_id,
            'domain':      self.domain,
            'plugin_name': self.plugin_name,
            'filename':    self.filename,
            'result':      self.result_json,
            'created_at':  self.created_at.isoformat()
        }


class Simulation(db.Model):
    __tablename__ = 'simulations'

    id              = db.Column(db.Integer, primary_key=True)
    analysis_id     = db.Column(db.Integer, db.ForeignKey('analyses.id'), nullable=True)
    scenario_params = db.Column(db.JSON, nullable=True)
    result_json     = db.Column(db.JSON, nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':          self.id,
            'analysis_id': self.analysis_id,
            'scenario':    self.scenario_params,
            'result':      self.result_json,
            'created_at':  self.created_at.isoformat()
        }