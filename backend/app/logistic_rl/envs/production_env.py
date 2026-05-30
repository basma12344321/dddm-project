from gym import Env
from gym.spaces import Discrete, Box
import numpy as np

class ProductionEnv(Env):
    def __init__(self, max_tasks=10, max_machines=5):
        super().__init__()
        
        self.max_tasks = max_tasks
        self.max_machines = max_machines

        # L'action correspond à une affectation tâche → machine
        self.action_space = Discrete(self.max_tasks * self.max_machines)

        # Observation = état des tâches + état des machines
        self.observation_space = Box(
            low=0, high=1, 
            shape=(self.max_tasks + self.max_machines,), 
            dtype=np.float32
        )

        # Initialisation des structures
        self.tasks = []
        self.machines = []
        self.current_step = 0

    def reset(self, df):
        print(" Initialisation de l’environnement avec les données réelles")

        #  Génération des tâches à partir du DataFrame
        self.tasks = [
            {
                "id": f"T{i}",
                "duration": int(row["Duration"]),
                "deadline": int(row["Deadline"]),
                "assigned": False
            }
            for i, row in df.iterrows()
        ]

        #  Initialisation des machines avec charge nulle
        self.machines = [{"id": f"M{i}", "load": 0.0} for i in range(self.max_machines)]

        self.current_step = 0
        return self._build_state()

    def _build_state(self):
      """
    Construit une observation normalisée de taille fixe (max_tasks + max_machines).
    - Chaque tâche contribue : durée normalisée
    - Chaque machine contribue : charge actuelle
    """

    # On complète à self.max_tasks si besoin
      while len(self.tasks) < self.max_tasks:
        self.tasks.append({
            "id": f"DUMMY_{len(self.tasks)}",
            "duration": 0,
            "deadline": 0,
            "assigned": True,
            "priority": 0
        })

      while len(self.machines) < self.max_machines:
        self.machines.append({
            "id": f"DUMMY_M{len(self.machines)}",
            "load": 0
        })

      task_states = np.array([
        (t["duration"] if not t.get("assigned") else 0)
        for t in self.tasks
    ],   dtype=np.float32)

      machine_states = np.array([
        m.get("load", 0)
        for m in self.machines
    ], dtype=np.float32)

      state = np.concatenate([task_states[:self.max_tasks], machine_states[:self.max_machines]])
    
    # Normalisation simple
      max_val = np.max(state) if np.max(state) > 0 else 1
      return state / max_val


    def step(self, action):
        task_idx = action // self.max_machines
        machine_idx = action % self.max_machines

        if task_idx >= len(self.tasks) or machine_idx >= len(self.machines):
            raise ValueError("Invalid action")

        assignment_info = {
            "task": self.tasks[task_idx]["id"],
            "machine": self.machines[machine_idx]["id"]
        }

        if self.tasks[task_idx]["assigned"]:
            reward = -10.0  #  Pénalité pour double assignation
        else:
            duration = self.tasks[task_idx]["duration"]
            priority = self.tasks[task_idx].get("priority", 1)
            deadline = self.tasks[task_idx].get("deadline", 20)

            self.tasks[task_idx]["assigned"] = True
            self.machines[machine_idx]["load"] += duration

            #  Infos temporelles
            assignment_info["start_time"] = self.machines[machine_idx]["load"] - duration
            assignment_info["end_time"] = self.machines[machine_idx]["load"]

            #  Récompense simple avec pénalité de dépassement
            reward = -self.machines[machine_idx]["load"] + priority * 0.5
            if self.machines[machine_idx]["load"] > deadline:
                reward -= 5.0

        self.current_step += 1
        done = all(t["assigned"] for t in self.tasks)

        return self._build_state(), reward, done, {
            "assignment": assignment_info
        }
