import importlib

def load_plugin(plugin_name):
    """
    Charge dynamiquement un plugin métier depuis le dossier 'plugins'.
    
    Exemple :
    - plugin_name = "logistic" → charge logistik_plugin.LogistikPlugin
    - plugin_name = "finance" → charge finance_plugin.FinancePlugin
    """
    try:
        # 1. Construire le nom du module et de la classe
        module_name = f"app.plugins.{plugin_name}_plugin"
        class_name = f"{plugin_name.capitalize()}Plugin"

        # 2. Importer dynamiquement le module
        module = importlib.import_module(module_name)

        # 3. Récupérer la classe depuis le module
        plugin_class = getattr(module, class_name)

        # 4. Instancier le plugin
        return plugin_class()
    
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Le plugin '{plugin_name}' est introuvable ou mal structuré. Détail : {e}")
