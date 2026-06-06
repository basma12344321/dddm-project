# backend/app/plugins/logistic_plugin.py
"""
Plugin Logistique - Ordonnancement Hybride (Heuristiques + Recuit Simulé)
avec interprétation LLM via Groq
"""

from app.plugins.base_plugin import BasePlugin
import pandas as pd
from typing import Dict, List, Any, Optional
import logging

from app.core_engine.scheduling_engine import (
    SchedulingEngine,
    load_scheduling_engine
)
from app.llm_utils import generate_interpretation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogisticPlugin(BasePlugin):

    def __init__(self):
        self.engine = load_scheduling_engine()
        logger.info("Plugin Logistique initialisé (mode hybride: Heuristiques + Recuit Simulé)")

    def preprocess(self, data) -> pd.DataFrame:
        if isinstance(data, dict):
            df = pd.DataFrame([data]) if data else pd.DataFrame()
        else:
            df = data.copy()

        if df.empty:
            return df

        df.columns = df.columns.str.strip()

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

        for col in ['Duration', 'Deadline', 'Priority', 'SetupTime']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def schedule(self, data, algorithm: str = "EDD") -> List[Dict[str, Any]]:
        logger.info(f"Schedule appelé avec algo: {algorithm}")

        df = self.preprocess(data)

        if df.empty:
            return []

        result = self.engine.schedule(
            data=df,
            num_machines=3,
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
        logger.info(f"Simulation appelée: {scenario}")

        modified_tasks = scenario.get('modified_tasks')
        num_machines   = scenario.get('num_machines', 3)
        rule           = scenario.get('rule', 'EDD')
        sa_config      = scenario.get('sa_config')
        compare_with_baseline = scenario.get('compare_with_baseline', False)

        if not modified_tasks:
            return {"error": "Aucune tâche modifiée fournie"}

        df = pd.DataFrame(modified_tasks)

        result = self.engine.schedule(
            data=df,
            num_machines=num_machines,
            rule=rule,
            sa_config=sa_config,
            enable_sa=True
        )

        response = {
            "gantt_data":       result.gantt_data,
            "metrics":          result.metrics,
            "interpretation":   result.interpretation,
            "execution_time_ms": result.execution_time_ms
        }

        if compare_with_baseline:
            baseline_result = self.engine.schedule(
                data=df,
                num_machines=num_machines,
                rule=rule,
                sa_config=sa_config,
                enable_sa=False
            )

            response["baseline"] = {
                "metrics":    baseline_result.metrics,
                "gantt_data": baseline_result.gantt_data
            }

            if baseline_result.metrics and result.metrics:
                response["diff_metrics"] = {
                    "makespan_diff":     result.metrics.get('makespan', 0) - baseline_result.metrics.get('makespan', 0),
                    "balance_diff":      result.metrics.get('balance_index', 0) - baseline_result.metrics.get('balance_index', 0),
                    "on_time_rate_diff": result.metrics.get('on_time_rate', 0) - baseline_result.metrics.get('on_time_rate', 0)
                }

        return response

    def _build_llm_prompt(self, metrics: Dict, interpretation: Dict, nb_tasks: int, num_machines: int = 3) -> str:
        """Construit le prompt LLM à partir des métriques de scheduling."""
        makespan       = metrics.get('makespan', 0)
        on_time_rate   = round(metrics.get('on_time_rate', 0) * 100, 1)
        balance_index  = metrics.get('balance_index', 0)
        total_tardiness = metrics.get('total_tardiness', 0)
        utilization    = round(metrics.get('avg_utilization', 0) * 100, 1)
        perf_level     = interpretation.get('performance_level', 'N/A')
        alerts         = interpretation.get('alerts', [])
        alerts_text    = "\n".join(f"- {a}" for a in alerts) if alerts else "Aucune alerte."

        return f"""
Tu es un expert en gestion logistique et ordonnancement industriel.
Voici les résultats d'un ordonnancement de {nb_tasks} tâches sur {num_machines} machines :

Métriques :
- Makespan total : {makespan} unités de temps
- Taux de conformité (deadlines respectées) : {on_time_rate}%
- Index d'équilibrage des machines : {balance_index:.2f} / 1.0
- Retard total cumulé : {total_tardiness} unités
- Utilisation moyenne des machines : {utilization}%
- Niveau de performance : {perf_level}

Alertes détectées :
{alerts_text}

Génère un rapport d'interprétation professionnel en français structuré ainsi :
1. **Synthèse globale** (2-3 phrases sur la qualité du planning)
2. **Points forts** (ce qui fonctionne bien)
3. **Points d'amélioration** (problèmes identifiés)
4. **Recommandations concrètes** (actions à prendre)

Sois précis, actionnable et professionnel. Maximum 200 mots.
""".strip()

    def interpret(self, raw_output) -> Dict[str, Any]:
        """
        Interprétation des résultats avec analyse LLM.
        """
        if not raw_output or len(raw_output) == 0:
            return {
                "assignments": [],
                "makespan": 0,
                "nb_tasks": 0,
                "note": "Aucune tâche à planifier",
                "interpretation_ia": "Aucune tâche à planifier.",
                "interpretation": {
                    "performance_level": "N/A",
                    "summary": "Aucune tâche à planifier",
                    "recommendations": [],
                    "warnings": []
                }
            }

        # Cas ScheduleResult
        if hasattr(raw_output, 'gantt_data'):
            metrics        = raw_output.metrics or {}
            interpretation = raw_output.interpretation or {}
            nb_tasks       = len(raw_output.gantt_data)

            # ── Appel LLM ──────────────────────────────────────────
            prompt = self._build_llm_prompt(metrics, interpretation, nb_tasks)
            interpretation_ia = generate_interpretation(prompt)
            logger.info("Interprétation LLM logistique générée avec succès")

            return {
                "assignments":       raw_output.gantt_data,
                "makespan":          metrics.get('makespan', 0),
                "nb_tasks":          nb_tasks,
                "metrics":           metrics,
                "interpretation":    interpretation,
                "optimization_gain": raw_output.optimization_gain,
                "interpretation_ia": interpretation_ia,
                "note": f"Ordonnancement optimisé — {interpretation.get('performance_level', 'N/A')}"
            }

        # Cas liste d'assignations brutes
        end_times    = [a.get('end', 0) for a in raw_output if 'end' in a]
        makespan     = max(end_times) if end_times else 0
        delayed      = sum(1 for a in raw_output if a.get('is_late', False))
        on_time_rate = (len(raw_output) - delayed) / len(raw_output) if raw_output else 0

        metrics_basic = {
            'makespan':      makespan,
            'on_time_rate':  on_time_rate,
            'balance_index': 0,
            'total_tardiness': 0,
            'avg_utilization': 0
        }

        prompt = self._build_llm_prompt(metrics_basic, {}, len(raw_output))
        interpretation_ia = generate_interpretation(prompt)

        return {
            "assignments":       raw_output,
            "makespan":          makespan,
            "nb_tasks":          len(raw_output),
            "on_time_rate":      on_time_rate,
            "delayed_tasks":     delayed,
            "interpretation_ia": interpretation_ia,
            "note":              "Ordonnancement via algorithme heuristique"
        }