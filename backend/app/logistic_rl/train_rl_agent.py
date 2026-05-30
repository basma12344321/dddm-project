import sys
import os

# Répertoire courant du fichier
current_dir = os.path.dirname(__file__)

#  Ajoute backend/app au PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(current_dir, "..", "..")))

# Import du bon environnement
from app.logistic_rl.envs.production_env import ProductionEnv
from stable_baselines3 import PPO

#  Paramètres 
MAX_TASKS = 10
MAX_MACHINES = 5
TIMESTEPS = 100_000  # Tu peux augmenter à 300_000 si besoin

# Création de l’environnement
env = ProductionEnv(max_tasks=MAX_TASKS, max_machines=MAX_MACHINES)

# Entraînement PPO
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=TIMESTEPS)

#  Sauvegarde du modèle
output_path = os.path.abspath(os.path.join(current_dir, "..", "..", "models", "logistic", "ppo_model.zip"))
model.save(output_path)

print(f"\n Modèle PPO entraîné et sauvegardé ici : {output_path}")
