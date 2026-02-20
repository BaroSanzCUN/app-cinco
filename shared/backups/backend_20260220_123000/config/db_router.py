# backend\config\db_router.py
class MultiDBRouter:
    APP_DB_MAP = {
        "authentication": "default",
        "security": "default",
        "common": "azul",
        "operaciones": "default",
        "empleados": "azul",
        # "reports": "reporting",
        # "audit": "audit",
    }

    def db_for_read(self, model, **hints):
        return self.APP_DB_MAP.get(model._meta.app_label)

    def db_for_write(self, model, **hints):
        return self.APP_DB_MAP.get(model._meta.app_label)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        target_db = self.APP_DB_MAP.get(app_label)
        if target_db is None:
            return None
        return db == target_db
