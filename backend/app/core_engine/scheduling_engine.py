# backend/app/core_engine/scheduling_engine.py
"""
Moteur d'ordonnancement hybride : Heuristiques + Recuit Simulé
================================================================
Ce module implémente un système d'ordonnancement de tâches sur machines
utilisant une approche hybride :
1. Heuristiques de dispatching (SPT, EDD, LPT, WSPT)
2. Optimisation par Recuit Simulé (Simulated Annealing)

Auteur: DDDM Project
Date: 2026
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import copy
import logging
import math
import random

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Représente une tâche dans le système d'ordonnancement."""
    task_id: str
    duration: int
    deadline: int
    priority: int = 1  # 1 (bas) à 3 (urgent)
    dependencies: List[str] = field(default_factory=list)
    setup_time: int = 0
    machine_constraint: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validation des données après initialisation."""
        if self.duration < 0:
            raise ValueError(f"Durée négative impossible: {self.duration}")
        if self.deadline < 0:
            raise ValueError(f"Deadline négative impossible: {self.deadline}")
        if self.priority not in [1, 2, 3]:
            self.priority = 1  # Valeur par défaut

    def weighted_duration(self) -> float:
        """Calcule la durée pondérée par la priorité."""
        return self.duration * self.priority


@dataclass
class Machine:
    """Représente une machine dans le système."""
    machine_id: str
    available_time: float = 0.0

    def __repr__(self):
        return f"Machine({self.machine_id}, dispo={self.available_time})"


@dataclass
class ScheduleResult:
    """Résultat complet d'un ordonnancement."""
    gantt_data: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    convergence_data: List[Dict[str, Any]] = field(default_factory=list)
    optimization_gain: Dict[str, Any] = field(default_factory=dict)
    interpretation: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    status: str = "success"
    error_message: Optional[str] = None


class SchedulingEngine:
    """
    Moteur d'ordonnancement hybride.

    Combine des heuristiques de dispatching avec un recuit simulé
    pour trouver une solution d'ordonnancement optimale.
    """

    # Règles heuristiques disponibles
    HEURISTIC_RULES = {
        "SPT": "Shortest Processing Time - tâche la plus courte en premier",
        "EDD": "Earliest Due Date - deadline la plus proche en premier",
        "LPT": "Longest Processing Time - tâche la plus longue en premier (équilibrage)",
        "WSPT": "Weighted Shortest Processing Time - (Priority * Duration) comme critère"
    }

    def __init__(self):
        """Initialisation du moteur."""
        logger.info("SchedulingEngine initialisé")

    # =========================================================================
    # PRÉTRAITEMENT DES DONNÉES
    # =========================================================================

    def preprocess(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Pretraite les données d'entrée et valide le format CSV.

        Args:
            data: DataFrame avec les colonnes du fichier CSV

        Returns:
            Dict contenant les tâches et métriques descriptives
        """
        logger.info("Prétraitement des données logistiques")

        df = data.copy()
        df.columns = df.columns.str.strip()

        # Colonnes attendues et optionnelles
        required_cols = ['Task', 'Duration', 'Deadline']
        optional_cols = ['Priority', 'Dependencies', 'SetupTime', 'MachineConstraint']

        # Validation des colonnes requises
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Colonnes manquantes: {missing_cols}")

        # Ajout des colonnes optionnelles avec valeurs par défaut
        for col in optional_cols:
            if col not in df.columns:
                if col == 'Priority':
                    df[col] = 1
                elif col == 'Dependencies':
                    df[col] = ''
                elif col == 'SetupTime':
                    df[col] = 0
                elif col == 'MachineConstraint':
                    df[col] = ''

        # Conversion des types
        df['Duration'] = pd.to_numeric(df['Duration'], errors='coerce')
        df['Deadline'] = pd.to_numeric(df['Deadline'], errors='coerce')
        df['Priority'] = pd.to_numeric(df['Priority'], errors='coerce').fillna(1).astype(int)
        df['SetupTime'] = pd.to_numeric(df['SetupTime'], errors='coerce').fillna(0)

        # Suppression des lignes invalides
        df = df.dropna(subset=['Task', 'Duration', 'Deadline'])
        if df.empty:
            raise ValueError("Aucune tâche valide dans les données")

        # Parsing des dépendances
        def parse_dependencies(dep_str):
            if pd.isna(dep_str) or str(dep_str).strip() == '':
                return []
            return [d.strip() for d in str(dep_str).split(',') if d.strip()]

        df['Dependencies'] = df['Dependencies'].apply(parse_dependencies)

        # Parsing des contraintes de machine
        def parse_machine_constraint(mc_str):
            if pd.isna(mc_str) or str(mc_str).strip() == '':
                return []
            return [m.strip() for m in str(mc_str).split(',') if m.strip()]

        df['MachineConstraint'] = df['MachineConstraint'].apply(parse_machine_constraint)

        # Détection des cycles dans les dépendances
        all_tasks = set(df['Task'].tolist())
        if self._has_dependency_cycles(df['Task'].tolist(), df['Dependencies'].tolist()):
            raise ValueError("Cycle détecté dans les dépendances des tâches")

        # Vérification que toutes les dépendances existent
        for idx, row in df.iterrows():
            for dep in row['Dependencies']:
                if dep not in all_tasks:
                    raise ValueError(f"Dépendance '{dep}' de la tâche '{row['Task']}' inexistante")

        # Création des objets Task
        tasks = [
            Task(
                task_id=str(row['Task']),
                duration=int(row['Duration']),
                deadline=int(row['Deadline']),
                priority=int(row['Priority']),
                dependencies=row['Dependencies'],
                setup_time=int(row['SetupTime']),
                machine_constraint=row['MachineConstraint']
            )
            for _, row in df.iterrows()
        ]

        # Calcul des métriques descriptives
        total_load = sum(t.duration for t in tasks)
        max_deadline = max(t.deadline for t in tasks)
        critical_task = max(tasks, key=lambda t: t.deadline - t.duration)
        high_priority_count = sum(1 for t in tasks if t.priority == 3)

        metrics = {
            "num_tasks": len(tasks),
            "total_load": total_load,
            "max_deadline": max_deadline,
            "critical_task": critical_task.task_id,
            "high_priority_count": high_priority_count,
            "avg_duration": total_load / len(tasks) if tasks else 0,
            "tasks_with_dependencies": sum(1 for t in tasks if t.dependencies)
        }

        logger.info(f"Préprocessé: {len(tasks)} tâches, charge totale: {total_load}")

        return {
            "tasks": tasks,
            "metrics": metrics
        }

    def _has_dependency_cycles(self, tasks: List[str], dependencies: List[List[str]]) -> bool:
        """Détecte les cycles dans le graphe de dépendances via l'algorithme de Kahn."""
        # Construction du graphe
        task_to_idx = {t: i for i, t in enumerate(tasks)}
        in_degree = {t: 0 for t in tasks}
        adj_list = {t: [] for t in tasks}

        for task, deps in zip(tasks, dependencies):
            for dep in deps:
                if dep in task_to_idx:
                    adj_list[dep].append(task)
                    in_degree[task] += 1

        # Algorithme de Kahn
        queue = [t for t in tasks if in_degree[t] == 0]
        count = 0

        while queue:
            node = queue.pop(0)
            count += 1
            for neighbor in adj_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return count != len(tasks)

    # =========================================================================
    # SOLUTION INITIALE PAR HEURISTIQUES
    # =========================================================================

    def get_initial_solution(
        self,
        tasks: List[Task],
        num_machines: int = 3,
        rule: str = "EDD"
    ) -> Tuple[List[Dict[str, Any]], List[Machine]]:
        """
        Génère une solution initiale par heuristique de dispatching.

        Args:
            tasks: Liste des tâches à ordonnancer
            num_machines: Nombre de machines disponibles
            rule: Règle heuristique (SPT, EDD, LPT, WSPT)

        Returns:
            Tuple (assignations, machines)
        """
        logger.info(f"Génération solution initiale avec règle: {rule}")

        if rule not in self.HEURISTIC_RULES:
            logger.warning(f"Règle inconnue '{rule}', utilisation de EDD par défaut")
            rule = "EDD"

        # Tri topologique pour respecter les dépendances
        sorted_tasks = self._topological_sort(tasks)

        # Tri selon la règle heuristique
        if rule == "SPT":
            sorted_tasks = sorted(sorted_tasks, key=lambda t: t.duration)
        elif rule == "EDD":
            sorted_tasks = sorted(sorted_tasks, key=lambda t: t.deadline)
        elif rule == "LPT":
            sorted_tasks = sorted(sorted_tasks, key=lambda t: -t.duration)
        elif rule == "WSPT":
            sorted_tasks = sorted(sorted_tasks, key=lambda t: -t.weighted_duration())

        # Initialisation des machines
        machines = [Machine(f"M{i+1}") for i in range(num_machines)]

        # Affectation des tâches
        assignments = []

        for task in sorted_tasks:
            # Filtrer les machines autorisées
            available_machines = [
                m for m in machines
                if not task.machine_constraint or m.machine_id in task.machine_constraint
            ]

            if not available_machines:
                available_machines = machines  # Toutes si pas de contrainte

            # Choisir la machine la moins chargée
            best_machine = min(available_machines, key=lambda m: m.available_time)

            # Calcul du temps de début (avec setup si nécessaire)
            start_time = best_machine.available_time

            # Vérifier les dépendances
            for dep in task.dependencies:
                dep_end = self._get_task_end_time(dep, assignments)
                if dep_end > start_time:
                    start_time = dep_end

            # Temps de fin
            end_time = start_time + task.duration

            # Mise à jour de la machine
            best_machine.available_time = end_time

            # Enregistrement de l'assignation
            assignments.append({
                'task': task.task_id,
                'machine': best_machine.machine_id,
                'start': start_time,
                'end': end_time,
                'duration': task.duration,
                'deadline': task.deadline,
                'priority': task.priority,
                'dependencies': task.dependencies,
                'setup_time': task.setup_time
            })

        logger.info(f"Solution initiale générée: {len(assignments)} assignations")

        return assignments, machines

    def _topological_sort(self, tasks: List[Task]) -> List[Task]:
        """Trie les tâches selon l'ordre topologique des dépendances."""
        task_map = {t.task_id: t for t in tasks}
        in_degree = {t.task_id: 0 for t in tasks}

        for task in tasks:
            for dep in task.dependencies:
                if dep in task_map:
                    in_degree[task.task_id] += 1

        result = []
        queue = [t for t in tasks if in_degree[t.task_id] == 0]

        while queue:
            task = queue.pop(0)
            result.append(task)

            for other in tasks:
                if task.task_id in other.dependencies:
                    in_degree[other.task_id] -= 1
                    if in_degree[other.task_id] == 0:
                        queue.append(other)

        # Ajouter les tâches avec dépendances cyclic si présentes
        remaining = [t for t in tasks if t not in result]
        result.extend(remaining)

        return result

    def _get_task_end_time(self, task_id: str, assignments: List[Dict]) -> float:
        """Retourne le temps de fin d'une tâche."""
        for a in assignments:
            if a['task'] == task_id:
                return a['end']
        return 0.0

    # =========================================================================
    # RECUIT SIMULÉ (SIMULATED ANNEALING)
    # =========================================================================

    def simulated_annealing(
        self,
        initial_solution: List[Dict[str, Any]],
        tasks: List[Task],
        machines: List[Machine],
        config: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Optimise la solution initiale par Recuit Simulé.

        Args:
            initial_solution: Solution de départ
            tasks: Liste des tâches
            machines: Liste des machines
            config: Paramètres de configuration

        Returns:
            Tuple (meilleure_solution, convergence_history)
        """
        # Configuration par défaut
        if config is None:
            config = {}

        initial_temp = config.get('initial_temp', 1000.0)
        cooling_rate = config.get('cooling_rate', 0.995)
        min_temp = config.get('min_temp', 0.1)
        max_iterations = config.get('max_iterations', 5000)
        iteration_step = config.get('iteration_step', 100)
        objective_weights = config.get('objective_weights', {
            'makespan': 0.4, 'balance': 0.3, 'tardiness': 0.3
        })

        logger.info(f"Début Recuit Simulé: T0={initial_temp}, itérations={max_iterations}")

        # Solution actuelle et meilleure
        current_solution = copy.deepcopy(initial_solution)
        best_solution = copy.deepcopy(initial_solution)

        # Scores
        current_score = self._calculate_objective(current_solution, tasks, machines, objective_weights)
        best_score = current_score

        # Tracking de convergence
        convergence_history = []

        # Température courante
        temperature = initial_temp
        iteration = 0

        while temperature > min_temp and iteration < max_iterations:
            # Génération d'une solution voisinne
            neighbor = self._generate_neighbor(current_solution, tasks, machines)

            # Calcul du score du voisinnage
            neighbor_score = self._calculate_objective(neighbor, tasks, machines, objective_weights)

            # Critère d'acceptation de Metropolis
            delta = neighbor_score - current_score

            if delta < 0 or random.random() < math.exp(-delta / temperature):
                current_solution = neighbor
                current_score = neighbor_score

                # Mise à jour de la meilleure solution
                if current_score < best_score:
                    best_solution = copy.deepcopy(current_solution)
                    best_score = current_score

            # Refroidissement
            temperature *= cooling_rate
            iteration += 1

            # Enregistrement de la convergence
            if iteration % iteration_step == 0:
                convergence_history.append({
                    'iteration': iteration,
                    'temperature': round(temperature, 2),
                    'current_score': round(current_score, 4),
                    'best_score': round(best_score, 4)
                })

        logger.info(f"Recuit Simulé terminé: {iteration} itérations, meilleur score: {best_score:.4f}")

        return best_solution, convergence_history

    def _generate_neighbor(
        self,
        solution: List[Dict[str, Any]],
        tasks: List[Task],
        machines: List[Machine]
    ) -> List[Dict[str, Any]]:
        """Génère une solution voisinne par swap ou déplacement."""
        solution = copy.deepcopy(solution)

        # Choix entre swap (50%) ou déplacement (50%)
        if random.random() < 0.5 and len(solution) >= 2:
            # Swap de deux tâches entre machines différentes
            idx1, idx2 = random.sample(range(len(solution)), 2)

            # Échanger les machines
            machine1 = solution[idx1]['machine']
            machine2 = solution[idx2]['machine']

            if machine1 != machine2:
                solution[idx1]['machine'] = machine2
                solution[idx2]['machine'] = machine1
        else:
            # Déplacement vers une machine moins chargée
            if len(solution) > 0:
                idx = random.randint(0, len(solution) - 1)
                task = solution[idx]['task']

                # Trouver les machines possibles
                task_obj = next((t for t in tasks if t.task_id == task), None)
                if task_obj:
                    machine_ids = [m.machine_id for m in machines]
                    if task_obj.machine_constraint:
                        allowed = [m for m in machine_ids if m in task_obj.machine_constraint or not task_obj.machine_constraint]
                    else:
                        allowed = machine_ids

                    if len(allowed) > 1:
                        current_machine = solution[idx]['machine']
                        other_machines = [m for m in allowed if m != current_machine]
                        if other_machines:
                            solution[idx]['machine'] = random.choice(other_machines)

        # Recalculer les temps de début/fin
        solution = self._recalculate_timing(solution, tasks, machines)

        return solution

    def _recalculate_timing(
        self,
        solution: List[Dict[str, Any]],
        tasks: List[Task],
        machines: List[Machine]
    ) -> List[Dict[str, Any]]:
        """Recalcule les temps de début et fin après modification."""
        task_map = {t.task_id: t for t in tasks}

        # Réinitialiser les machines
        machine_times = {m.machine_id: 0.0 for m in machines}

        # Trier par temps de début original pour garder un ordre cohérent
        solution = sorted(solution, key=lambda x: x['start'])

        # Pour chaque tâche, calculer le nouveau temps de début
        for i, assignment in enumerate(solution):
            task_id = assignment['task']
            task = task_map.get(task_id)

            if not task:
                continue

            machine_id = assignment['machine']

            # Temps de départ = max(disponibilité machine, dépendances terminées)
            start_time = machine_times[machine_id]

            # Vérifier les dépendances
            for dep in task.dependencies:
                dep_end = self._get_task_end_time(dep, solution)
                if dep_end > start_time:
                    start_time = dep_end

            end_time = start_time + task.duration

            # Mise à jour
            machine_times[machine_id] = end_time
            solution[i]['start'] = start_time
            solution[i]['end'] = end_time

        return solution

    def _calculate_objective(
        self,
        solution: List[Dict[str, Any]],
        tasks: List[Task],
        machines: List[Machine],
        weights: Dict[str, float]
    ) -> float:
        """Calcule la fonction objectif multi-critères."""
        # Makespan
        makespan = max((s['end'] for s in solution), default=0)

        # Balance (écart type des charges)
        machine_loads = [s['end'] - s['start'] for s in solution]
        # Grouper par machine
        loads_by_machine = {}
        for s in solution:
            m = s['machine']
            if m not in loads_by_machine:
                loads_by_machine[m] = 0
            loads_by_machine[m] += s['end'] - s['start']

        if loads_by_machine:
            avg_load = sum(loads_by_machine.values()) / len(loads_by_machine)
            std_load = np.std(list(loads_by_machine.values())) if len(loads_by_machine) > 1 else 0
            balance = 1 - (std_load / avg_load) if avg_load > 0 else 1
        else:
            balance = 1

        # Tardiness
        total_tardiness = sum(
            max(0, s['end'] - s['deadline']) for s in solution
        )

        # Score pondéré
        score = (
            weights['makespan'] * makespan +
            weights['balance'] * (1 - balance) * 100 +  # Inverser car on veut minimiser
            weights['tardiness'] * total_tardiness
        )

        return score

    # =========================================================================
    # CALCUL DES MÉTRIQUES
    # =========================================================================

    def calculate_metrics(
        self,
        solution: List[Dict[str, Any]],
        tasks: List[Task],
        machines: List[Machine]
    ) -> Dict[str, Any]:
        """Calcule les métriques de performance."""
        if not solution:
            return {}

        # Makespan
        makespan = max((s['end'] for s in solution), default=0)

        # Utilisation des machines
        machine_loads = {}
        for s in solution:
            m = s['machine']
            if m not in machine_loads:
                machine_loads[m] = 0
            machine_loads[m] += s['end'] - s['start']

        machine_utilization = {}
        for m in machines:
            load = machine_loads.get(m.machine_id, 0)
            machine_utilization[m.machine_id] = round(load / makespan, 4) if makespan > 0 else 0

        # Balance index
        loads = list(machine_loads.values())
        if loads:
            avg_load = sum(loads) / len(loads)
            std_load = np.std(loads) if len(loads) > 1 else 0
            balance_index = 1 - (std_load / avg_load) if avg_load > 0 else 1
        else:
            balance_index = 0

        # On-time rate et tardiness
        on_time = sum(1 for s in solution if s['end'] <= s['deadline'])
        total_tasks = len(solution)
        on_time_rate = on_time / total_tasks if total_tasks > 0 else 0

        total_tardiness = sum(
            max(0, s['end'] - s['deadline']) for s in solution
        )

        # Setup overhead
        total_setup_time = sum(s.get('setup_time', 0) for s in solution)
        avg_setup_overhead = total_setup_time / makespan if makespan > 0 else 0

        # Chemin critique (longueur via dépendances)
        critical_path_length = self._calculate_critical_path(solution, tasks)

        # Mise à jour des données de solution avec statut
        for s in solution:
            tardiness = max(0, s['end'] - s['deadline'])
            s['tardiness'] = tardiness
            s['is_late'] = tardiness > 0
            s['status'] = 'on_time' if tardiness == 0 else ('late' if tardiness > 0 else 'warning')

        return {
            'makespan': makespan,
            'machine_utilization': machine_utilization,
            'balance_index': round(balance_index, 4),
            'on_time_rate': round(on_time_rate, 4),
            'total_tardiness': total_tardiness,
            'average_setup_overhead': round(avg_setup_overhead, 4),
            'critical_path_length': critical_path_length
        }

    def _calculate_critical_path(
        self,
        solution: List[Dict[str, Any]],
        tasks: List[Task]
    ) -> int:
        """Calcule la longueur du chemin critique."""
        task_map = {t.task_id: t for t in tasks}

        # Construire le graphe
        end_times = {s['task']: s['end'] for s in solution}

        # Trouver le chemin le plus long via les dépendances
        def get_critical_path_length(task_id: str, visited: set) -> int:
            if task_id in visited:
                return 0
            visited.add(task_id)

            task = task_map.get(task_id)
            if not task:
                return end_times.get(task_id, 0)

            if not task.dependencies:
                return end_times.get(task_id, 0)

            max_dep_end = 0
            for dep in task.dependencies:
                max_dep_end = max(max_dep_end, get_critical_path_length(dep, visited.copy()))

            return max_dep_end + task.duration

        max_path = 0
        for task in tasks:
            path_len = get_critical_path_length(task.task_id, set())
            max_path = max(max_path, path_len)

        return max_path

    # =========================================================================
    # INTERPRÉTATION
    # =========================================================================

    def interpret(
        self,
        solution: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        initial_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Génère l'interprétation des résultats."""
        # Niveau de performance
        on_time_rate = metrics.get('on_time_rate', 0)
        balance_index = metrics.get('balance_index', 0)

        if on_time_rate >= 0.9 and balance_index >= 0.8:
            performance_level = "Excellent"
        elif on_time_rate >= 0.7 and balance_index >= 0.6:
            performance_level = "Bon"
        elif on_time_rate >= 0.5:
            performance_level = "Moyen"
        else:
            performance_level = "Critique"

        # Résumé
        nb_tasks = len(solution)
        on_time = sum(1 for s in solution if not s.get('is_late', False))
        makespan = metrics.get('makespan', 0)

        summary = (
            f"Planning généré avec succès. {on_time}/{nb_tasks} tâches respectent leur deadline. "
            f"La charge est {'bien équilibrée' if balance_index >= 0.7 else 'modérément équilibrée'} "
            f"(index: {balance_index:.2f}/1.0). Makespan total : {makespan} unités."
        )

        # Recommandations
        recommendations = []

        if balance_index < 0.7:
            # Proposer le rééquilibrage
            machine_util = metrics.get('machine_utilization', {})
            max_util = max(machine_util.values()) if machine_util else 0
            min_util = min(machine_util.values()) if machine_util else 0

            if max_util - min_util > 0.3:
                overloaded = [m for m, u in machine_util.items() if u == max_util]
                recommendations.append(
                    f"Réaffecter des tâches de {overloaded[0]} vers une machine moins chargée"
                )

        # Warnings
        warnings = []

        late_tasks = [s for s in solution if s.get('is_late', False)]
        for task in late_tasks:
            tardiness = task.get('tardiness', 0)
            if tardiness > 0:
                warnings.append(
                    f"{task['task']} dépasse sa deadline de {tardiness} unités"
                )

        # Optimization gain
        optimization_gain = {}
        if initial_metrics:
            init_makespan = initial_metrics.get('makespan', 0)
            opt_makespan = metrics.get('makespan', 0)

            if init_makespan > 0:
                makespan_reduction = ((init_makespan - opt_makespan) / init_makespan) * 100
                optimization_gain['makespan_reduction_pct'] = round(makespan_reduction, 2)

            init_balance = initial_metrics.get('balance_index', 0)
            opt_balance = metrics.get('balance_index', 0)
            optimization_gain['balance_improvement'] = round(opt_balance - init_balance, 4)

            init_tardiness = initial_metrics.get('total_tardiness', 0)
            opt_tardiness = metrics.get('total_tardiness', 0)

            if init_tardiness > 0:
                tardiness_reduction = ((init_tardiness - opt_tardiness) / init_tardiness) * 100
                optimization_gain['tardiness_reduction_pct'] = round(tardiness_reduction, 2)

        return {
            'performance_level': performance_level,
            'summary': summary,
            'recommendations': recommendations,
            'warnings': warnings[:5],  # Limiter à 5 warnings
            'optimization_gain': optimization_gain
        }

    # =========================================================================
    # PLANIFICATION PRINCIPALE
    # =========================================================================

    def schedule(
        self,
        data: pd.DataFrame,
        num_machines: int = 3,
        rule: str = "EDD",
        sa_config: Optional[Dict[str, Any]] = None,
        enable_sa: bool = True
    ) -> ScheduleResult:
        """
        Méthode principale d'ordonnancement.

        Args:
            data: DataFrame des tâches
            num_machines: Nombre de machines
            rule: Règle heuristique
            sa_config: Configuration du recuit simulé
            enable_sa: Activer l'optimisation SA

        Returns:
            ScheduleResult avec toutes les données
        """
        start_time = datetime.now()

        try:
            # Préprocessement
            preprocessed = self.preprocess(data)
            tasks = preprocessed['tasks']

            logger.info(f"Ordonnancement de {len(tasks)} tâches sur {num_machines} machines")

            # Solution initiale
            initial_solution, machines = self.get_initial_solution(tasks, num_machines, rule)

            # Métriques initiales
            initial_metrics = self.calculate_metrics(initial_solution, tasks, machines)

            # Optimisation par Recuit Simulé
            if enable_sa and sa_config is not None:
                optimized_solution, convergence = self.simulated_annealing(
                    initial_solution, tasks, machines, sa_config
                )
            else:
                optimized_solution = initial_solution
                convergence = []

            # Métriques finales
            final_metrics = self.calculate_metrics(optimized_solution, tasks, machines)

            # Interprétation
            interpretation = self.interpret(
                optimized_solution, final_metrics, initial_metrics
            )

            # Gain d'optimisation
            optimization_gain = interpretation.get('optimization_gain', {})
            optimization_gain['initial_makespan'] = initial_metrics.get('makespan', 0)
            optimization_gain['optimized_makespan'] = final_metrics.get('makespan', 0)

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return ScheduleResult(
                gantt_data=optimized_solution,
                metrics=final_metrics,
                convergence_data=convergence,
                optimization_gain=optimization_gain,
                interpretation=interpretation,
                execution_time_ms=round(execution_time, 2),
                status="success"
            )

        except Exception as e:
            logger.error(f"Erreur d'ordonnancement: {str(e)}")
            return ScheduleResult(
                status="error",
                error_message=str(e)
            )


# =========================================================================
# FONCTIONS UTILITAIRES
# =========================================================================

def load_scheduling_engine() -> SchedulingEngine:
    """Charge et retourne une instance du moteur d'ordonnancement."""
    return SchedulingEngine()