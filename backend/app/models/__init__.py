# app/models/__init__.py

from datetime import datetime
from app.extensions import db  # ✅ Import depuis extensions.py (instance unique)


class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(50), default='analyste')
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

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    domain      = db.Column(db.String(50), nullable=False)
    plugin_name = db.Column(db.String(100), nullable=False)
    filename    = db.Column(db.String(255), nullable=True)
    result_json = db.Column(db.JSON, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

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


# =========================================================================
# MODÈLES POUR LE MODULE LOGISTIQUE (SCHEDULING)
# =========================================================================

class SchedulingSession(db.Model):
    """
    Enregistre chaque exécution de /schedule.
    """
    __tablename__ = 'scheduling_sessions'

    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    num_tasks         = db.Column(db.Integer, nullable=False)
    num_machines      = db.Column(db.Integer, nullable=False, default=3)
    rule_used         = db.Column(db.String(20), nullable=False, default='EDD')
    execution_time_ms = db.Column(db.Float, nullable=True)
    status            = db.Column(db.String(20), nullable=False, default='success')

    # Résultats associés
    result = db.relationship('SchedulingResult', backref='session', lazy=True, uselist=False)

    def to_dict(self):
        return {
            'id':                  self.id,
            'user_id':             self.user_id,
            'created_at':          self.created_at.isoformat(),
            'num_tasks':           self.num_tasks,
            'num_machines':        self.num_machines,
            'rule_used':           self.rule_used,
            'execution_time_ms':  self.execution_time_ms,
            'status':              self.status
        }


class SchedulingResult(db.Model):
    """
    Résultats générés par un ordonnancement.
    """
    __tablename__ = 'scheduling_results'

    id                  = db.Column(db.Integer, primary_key=True)
    session_id          = db.Column(db.Integer, db.ForeignKey('scheduling_sessions.id'), nullable=False)
    gantt_data          = db.Column(db.JSON, nullable=True)   # Données pour le diagramme de Gantt
    metrics             = db.Column(db.JSON, nullable=True)    # Métriques de performance
    interpretation      = db.Column(db.JSON, nullable=True)     # Interprétation
    convergence_data    = db.Column(db.JSON, nullable=True)    # Historique de convergence SA

    def to_dict(self):
        return {
            'id':              self.id,
            'session_id':      self.session_id,
            'gantt_data':      self.gantt_data,
            'metrics':         self.metrics,
            'interpretation': self.interpretation,
            'convergence_data': self.convergence_data
        }


class SchedulingSimulation(db.Model):
    """
    Simulations what-if stockées pour comparaison.
    """
    __tablename__ = 'scheduling_simulations'

    id              = db.Column(db.Integer, primary_key=True)
    session_id      = db.Column(db.Integer, db.ForeignKey('scheduling_sessions.id'), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    scenario_params = db.Column(db.JSON, nullable=True)   # Paramètres du scénario
    result_json     = db.Column(db.JSON, nullable=True)     # Résultat de la simulation
    diff_metrics    = db.Column(db.JSON, nullable=True)    # Diff avec le baseline

    # Relation vers la session originale
    session = db.relationship('SchedulingSession', backref='simulations')

    def to_dict(self):
        return {
            'id':              self.id,
            'session_id':      self.session_id,
            'created_at':      self.created_at.isoformat(),
            'scenario_params': self.scenario_params,
            'result_json':     self.result_json,
            'diff_metrics':    self.diff_metrics
        }