#!/bin/bash

# 1. Entrar a la carpeta de tu proyecto
cd /Users/jonathanpilco/comercial_2_hermanos

# 2. Preparar el navegador para que se abra en 5 segundos (tiempo para que cargue el servidor)
# El "&" al final hace que esto corra en segundo plano sin bloquear lo demás
(sleep 5 && open "http://127.0.0.1:8000") &

# 3. Mensaje de bienvenida
echo "=================================================="
echo "   🚀 INICIANDO SISTEMA COMERCIAL 2 HERMANOS"
echo "   Por favor, NO cierres esta ventana."
echo "=================================================="

# 4. Activar el entorno virtual
source venv/bin/activate

# 5. Encender el servidor de Django
python3 manage.py runserver
