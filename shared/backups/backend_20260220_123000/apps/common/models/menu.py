from django.db import models

class ConfigMenu(models.Model):
    url = models.CharField(max_length=255)
    nombre = models.CharField(max_length=255)
    area = models.CharField(max_length=100)      # Módulo
    carpeta = models.CharField(max_length=100)   # Submódulo
    titulo = models.CharField(max_length=255)
    tabla = models.CharField(max_length=100)
    estado = models.CharField(max_length=50)
    tipo = models.CharField(max_length=50)
    campos_importantes = models.TextField()
    plantilla = models.CharField(max_length=100)
    origen_base = models.CharField(max_length=100)
    edit = models.CharField(max_length=100)
    fecha_edit = models.DateTimeField()

    
    class Meta:
        managed = False  # 🔴 CRÍTICO
        db_table = "config_menu"
        app_label = "common"
        
        
    def get_permissions_for_user(self, user, url):
        """
        Retorna los permisos efectivos de un usuario sobre este menú.
        """

        permisos = {
            "read": False,
            "edit": False,
            "insert": False,
            "import": False,
            "manual": False,
            "admin": False,
        }

        if not user or not user.is_authenticated:
            return permisos

        # 🔹 Superusuario (solo si usas auth de Django)
        if user.is_superuser:
            return {k: True for k in permisos}

        # 🔹 Permisos desde tabla azul (ejemplo)
        # Ajusta el query EXACTAMENTE a tu estructura real
        from django.db import connections

        with connections["azul"].cursor() as cursor:
                # leer, editar, insertar, importar, manual, admin
            url_pattern = f'%{url}%'
            cursor.execute("""
                SELECT 
                    CASE WHEN leer LIKE %s THEN true ELSE false END,
                    CASE WHEN editar LIKE %s THEN true ELSE false END,
                    CASE WHEN insertar LIKE %s THEN true ELSE false END,
                    CASE WHEN importar LIKE %s THEN true ELSE false END,
                    CASE WHEN manual LIKE %s THEN true ELSE false END,
                    CASE WHEN admin LIKE %s THEN true ELSE false END
                FROM cinco_base_de_personal
                WHERE id = %s 
                LIMIT 1
            """, [url_pattern, url_pattern, url_pattern, url_pattern, url_pattern, url_pattern, user.id])

            row = cursor.fetchone()

            if row:
                permisos.update({
                    "read": bool(row[0]),
                    "edit": bool(row[1]),
                    "insert": bool(row[2]),
                    "import": bool(row[3]),
                    "manual": bool(row[4]),
                    "admin": bool(row[5]),
                })

        return permisos


