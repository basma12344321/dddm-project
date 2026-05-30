# backend/plugins/logistic_plugin.py

from app.plugins.base_plugin import BasePlugin
from app.logistic_rl.envs.production_env import ProductionEnv
from stable_baselines3 import PPO  
import os

class LogisticPlugin(BasePlugin):
    #def __init__(self):
        #model_path = os.path.join("models", "logistic", "ppo_model")
        #self.env = ProductionEnv()
        #self.model = PPO.load(model_path, env=self.env)
    
    
    def __init__(self):
        
        base_dir = os.path.dirname(__file__)  # => backend/app/plugins/
        model_path = os.path.join(base_dir, "..", "models", "logistic", "ppo_model")
        model_path = os.path.abspath(model_path)

        self.env = ProductionEnv()
        self.model = PPO.load(model_path, env=self.env)

    def preprocess(self, data):
        # Pas nécessaire ici car l’environnement Gym prend le relai
        return data

    def schedule(self, data):
        obs = self.env.reset(data)  # On initialise avec les données réelles
        done = False
        actions = []
        while not done:
            action, _ = self.model.predict(obs)
            obs, reward, done, info = self.env.step(action)
            actions.append(info['assignment'])  # Par ex. "task_5 -> machine_2"
        return actions

    def simulate(self, scenario):
        # Idem à schedule mais avec données modifiées
        return self.schedule(scenario)

    def interpret(self, raw_output):
    #  On filtre les tâches fictives DUMMY
      filtered_assignments = [
        a for a in raw_output
        if not a.get("task", "").startswith("DUMMY_")
    ]

    # Calcul du makespan sur les tâches réelles uniquement
      end_times = [a["end_time"] for a in filtered_assignments if "end_time" in a]
      makespan = max(end_times) if end_times else 0

      return {
        "assignments": filtered_assignments,
        "makespan": makespan,
        "nb_tasks": len(filtered_assignments),
        "note": "Ordonnancement optimisé via apprentissage par renforcement (hors tâches fictives)"
    }
