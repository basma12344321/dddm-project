from abc import ABC, abstractmethod

class BasePlugin(ABC):
    @abstractmethod
    def preprocess(self, data):
        """
        Étape de prétraitement spécifique au domaine métier.
        Permet de nettoyer, filtrer ou enrichir les données brutes.
        """
        pass

    @abstractmethod
    def schedule(self, data, algorithm="FCFS"):
        """
        Applique un algorithme d'ordonnancement (SJF, EDF, FCFS...) 
        aux données prétraitées pour déterminer un ordre optimal d'exécution.
        """
        pass

    @abstractmethod
    def simulate(self, scenario):
        """
        Permet d'exécuter des scénarios 'what-if' en modifiant certaines données 
        ou paramètres pour observer leur impact sur l'ordonnancement.
        """
        pass

    @abstractmethod
    def interpret(self, raw_output):
        """
        Traduit les résultats bruts en informations compréhensibles 
        et utiles pour l'utilisateur métier.
        """
        pass
