# backend/app/plugins/logistic_plugin.py
"""
Plugin Logistique - Ordonnancement Hybride (Heuristiques + Recuit Simulé)
=========================================================================

Ce plugin implémente l'ordonnancement de tâches sur machines en utilisant :
1. Heuristiques de dispatching (SPT, EDD, LPT, WSPT)
2. Optimisation par Recuit Simulé (Simulated Annealing)

Auteur: DDDM Project
Date: 2026
"""

from app.plugins.base_plugin import BasePlugin
import pandas as pd
from typing import Dict, List, Any, Optional
import logging

from app.core_engine.scheduling_engine import (
    SchedulingEngine,
    load_scheduling_engine
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogisticPlugin(BasePlugin):
    """
    Plugin logistique avec ordonnancement hybride.
    """

    def __init__(self):
        """Initialisation du plugin."""
        self.engine = load_scheduling_engine()
        logger.info("Plugin Logistique initialisé (mode hybride: Heuristiques + Recuit Simulé)")

    def preprocess(self, data) -> pd.DataFrame:
        """
        Prétraitement des données logistiques.

        Args:
            data: DataFrame ou dict avec les données

        Returns:
            DataFrame prétraité
        """
        if isinstance(data, dict):
            df = pd.DataFrame([data]) if data else pd.DataFrame()
        else:
            df = data.copy()

        if df.empty:
            return df

        # Nettoyage des noms de colonnes
        df.columns = df.columns.str.strip()

        # Renommage des colonnes si nécessaire
        column_mapping = {
            'task': 'Task',
            'duration': 'Duration',
            'deadline': 'Deadline',
            'priority': 'Priority',
            'dependencies': 'Dependencies',
            'setup_time': 'SetupTime',
            'machine_constraint': 'MachineConstraint'
        }

        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df = df.rename(columns={old_col: new_col})

        # Ensure numeric columns
        for col in ['Duration', 'Deadline', 'Priority', 'SetupTime']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def schedule(self, data, algorithm: str = "EDD") -> List[Dict[str, Any]]:
        """
        Planification des tâches sur les machines.

        Args:
            data: DataFrame ou dict avec les tâches
            algorithm: Règle heuristique (SPT, EDD, LPT, WSPT)

        Returns:
            Liste des assignations tâches → machines
        """
        logger.info(f"Schedule appelé avec algo: {algorithm}")

        df = self.preprocess(data)

        if df.empty:
            return []

        # Utiliser le moteur d'ordonnancement
        result = self.engine.schedule(
            data=df,
            num_machines=3,  # Par défaut
            rule=algorithm,
            sa_config={
                'initial_temp': 1000.0,
                'cooling_rate': 0.995,
                'min_temp': 0.1,
                'max_iterations': 2000
            },
            enable_sa=True
        )

        if result.status == "error":
            logger.error(f"Erreur scheduling: {result.error_message}")
            return []

        return result.gantt_data

    def simulate(self, scenario: Dict) -> Dict[str, Any]:
        """
        Simulation what-if avec comparaison.

        Args:
            scenario: Paramètres du scénario
                - modified_tasks: list de tâches modifiées
                - num_machines: nombre de machines
                - rule: règle heuristique
                - sa_config: config recuit simulé
                - compare_with_baseline: bool

        Returns:
            Résultat de la simulation
        """
        logger.info(f"Simulation appelée: {scenario}")

        # Extraire les paramètres
        modified_tasks = scenario.get('modified_tasks')
        num_machines = scenario.get('num_machines', 3)
        rule = scenario.get('rule', 'EDD')
        sa_config = scenario.get('sa_config')
        compare_with_baseline = scenario.get('compare_with_baseline', False)

        # Si modified_tasks fourni, l'utiliser comme données
        if modified_tasks:
            df = pd.DataFrame(modified_tasks)
        else:
            # Sinon erreur
            return {"error": "Aucune tâche modifiée fournie"}

        # Exécuter l'ordonnancement
        result = self.engine.schedule(
            data=df,
            num_machines=num_machines,
            rule=rule,
            sa_config=sa_config,
            enable_sa=True
        )

        response = {
            "gantt_data": result.gantt_data,
            "metrics": result.metrics,
            "interpretation": result.interpretation,
            "execution_time_ms": result.execution_time_ms
        }

        # Si comparaison demandée
        if compare_with_baseline and modified_tasks:
            # Re-run avec données originales si on les a
            baseline_df = df  # À modifier pour avoir les données originales
            baseline_result = self.engine.schedule(
                data=baseline_df,
                num_machines=num_machines,
                rule=rule,
                sa_config=sa_config,
                enable_sa=False  # Juste heuristique
            )

            response["baseline"] = {
                "metrics": baseline_result.metrics,
                "gantt_data": baseline_result.gantt_data
            }

            # Calculer les différences
            if baseline_result.metrics and result.metrics:
                response["diff_metrics"] = {
                    "makespan_diff": result.metrics.get('makespan', 0) - baseline_result.metrics.get('makespan', 0),
                    "balance_diff": result.metrics.get('balance_index', 0) - baseline_result.metrics.get('balance_index', 0),
                    "on_time_rate_diff": result.metrics.get('on_time_rate', 0) - baseline_result.metrics.get('on_time_rate', 0)
                }

        return response

    def interpret(self, raw_output) -> Dict[str, Any]:
        """
        Interprétation des résultats d'ordonnancement.

        Args:
            raw_output: Résultat du scheduling

        Returns:
            Interprétation structurée
        """
        if not raw_output or len(raw_output) == 0:
            return {
                "assignments": [],
                "makespan": 0,
                "nb_tasks": 0,
                "note": "Aucune tâche à planifier",
                "interpretation": {
                    "performance_level": "N/A",
                    "summary": "Aucune tâche à planifier",
                    "recommendations": [],
                    "warnings": []
                }
            }

        # Si raw_output est un ScheduleResult
        if hasattr(raw_output, 'gantt_data'):
            return {
                "assignments": raw_output.gantt_data,
                "makespan": raw_output.metrics.get('makespan', 0),
                "nb_tasks": len(raw_output.gantt_data),
                "metrics": raw_output.metrics,
                "interpretation": raw_output.interpretation,
                "optimization_gain": raw_output.optimization_gain,
                "note": f"Ordonnancement optimisé via {raw_output.interpretation.get('performance_level', 'N/A')}"
            }

        # Sinon, traiter comme une liste d'assignations
        # Calculer les métriques basiques
        end_times = [a.get('end', 0) for a in raw_output if 'end' in a]
        makespan = max(end_times) if end_times else 0

        delayed_tasks = sum(1 for a in raw_output if a.get('is_late', False))
        on_time_rate = (len(raw_output) - delayed_tasks) / len(raw_output) if raw_output else 0

        return {
            "assignments": raw_output,
            "makespan": makespan,
            "nb_tasks": len(raw_output),
            "on_time_rate": on_time_rate,
            "delayed_tasks": delayed_tasks,
            "note": "Ordonnancement via algorithme heuristique"
        }