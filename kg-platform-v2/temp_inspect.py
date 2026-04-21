import importlib
routes = importlib.import_module('app.api.routes')
print('Function signature:', routes.kg_integration_page.__code__.co_varnames)
