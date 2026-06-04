# backend/app/core_engine/__init__.py
"""
Core Engine - Moteur central de traitement des données.
"""

from app.core_engine.core_engine import clean_data, clean_dataframe
from app.core_engine.plugin_loader import load_plugin
from app.core_engine.model_loader import load_model
from app.core_engine.scheduling_engine import SchedulingEngine, load_scheduling_engine

__all__ = [
    'clean_data',
    'clean_dataframe',
    'load_plugin',
    'load_model',
    'SchedulingEngine',
    'load_scheduling_engine'
]