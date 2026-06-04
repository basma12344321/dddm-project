# Utilise Node.js 18 (parfait pour Angular 14)
FROM node:18-alpine

# Dossier de travail
WORKDIR /app

# Copie les fichiers de configuration npm
COPY package.json package-lock.json* ./

# Installe les dépendances Angular avec l'option legacy pour éviter les conflits de versions
RUN npm install --legacy-peer-deps

# Copie le reste du code frontend
COPY . .

# Expose le port d'Angular
EXPOSE 4200

# Démarre le serveur de développement en autorisant les connexions externes
CMD ["npm", "run", "start", "--", "--host", "0.0.0.0"]