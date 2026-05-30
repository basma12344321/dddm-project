from stable_baselines3 import PPO
from logistic_rl.envs.production_env import ProductionEnv
import numpy as np

# 1. Initialisation avec les dimensions FIXES du modèle
env = ProductionEnv(max_tasks=10, max_machines=5)  # Doit impérativement matcher l'entraînement
model = PPO.load("models/logistic/ppo_model", env=env)

# 2. Scenario 
scenario = {
    "tasks": [{"duration": float(np.random.randint(1, 10))} for _ in range(10)],
    "machines": [{"load": 0.0} for _ in range(5)]
}

# 3. Reset avec vérification automatique des dimensions
obs = env.reset(scenario)  # Lèvera une erreur si les dimensions sont incorrectes
done = False
assignments = []

while not done:
    action, _ = model.predict(obs)
    obs, _, done, info = env.step(action)
    assignments.append(info["assignment"])

print("Résultats valides :")
for assignment in assignments:
    print(assignment)