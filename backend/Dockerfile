# Utilise Python 3.11 comme base
FROM python:3.11

# Définit le dossier de travail dans le conteneur
WORKDIR /app

# Copie le fichier des dépendances
COPY requirements.txt .

# 1. On met à jour l'installateur pip en premier (très important !)
RUN pip install --upgrade pip setuptools wheel

# 2. On installe avec l'option -v (verbose) pour voir EXACTEMENT ce qui bloque
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le reste du code backend
COPY . .

# Expose le port utilisé par Flask
EXPOSE 5000

# La commande pour lancer le serveur
CMD ["python", "main.py"]