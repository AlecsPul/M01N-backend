# M01N Backend API

Proyecto FastAPI con Uvicorn para el backend del proyecto M01N.

## 📋 Requisitos

- Python 3.8+
- pip o poetry

## 🚀 Instalación

### 1. Crear un entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
# O edita el archivo .env con tus configuraciones
```

## ▶️ Ejecución

### Modo Desarrollo

```bash
uvicorn app.main:app --reload
```

El servidor se reiniciará automáticamente al hacer cambios en el código.

### Modo Producción

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📚 Documentación

Una vez iniciado el servidor, accede a:

- **Swagger UI (Documentación interactiva)**: http://localhost:8000/docs
- **ReDoc (Documentación alternativa)**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 📁 Estructura del Proyecto

```
M01N-backend/
├── app/
│   ├── __init__.py                  # Inicializador del paquete
│   ├── main.py                      # Punto de entrada principal
│   ├── config.py                    # Configuración de la aplicación
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py                # Rutas y endpoints API
│   ├── models/
│   │   └── __init__.py              # Modelos de base de datos
│   └── schemas/
│       └── __init__.py              # Esquemas Pydantic para validación
├── tests/
│   └── __init__.py                  # Tests unitarios
├── requirements.txt                 # Dependencias del proyecto
├── .env                             # Variables de entorno (no incluir en git)
├── .gitignore                       # Configuración de git
├── README.md                        # Este archivo
└── .env.example                     # Plantilla de variables de entorno
```

## 🧪 Testing

Ejecuta los tests con pytest:

```bash
pytest
```

Para ver cobertura de tests:

```bash
pytest --cov=app
```

## 💻 Desarrollo

### Instalar dependencias adicionales

Para desarrollo, puedes instalar dependencias adicionales:

```bash
pip install black flake8 mypy
```

### Formato de código

```bash
# Black para formateo automático
black app/

# Flake8 para linting
flake8 app/

# MyPy para type checking
mypy app/
```

## 🔧 Endpoints Disponibles

- `GET /` - Mensaje de bienvenida
- `GET /health` - Health check del servidor
- `GET /api/v1/items/` - Lista todos los items
- `GET /api/v1/items/{item_id}` - Obtiene un item específico
- `POST /api/v1/items/` - Crea un nuevo item

## 📦 Dependencias Principales

- **FastAPI**: Framework web moderno
- **Uvicorn**: Servidor ASGI de alto rendimiento
- **Pydantic**: Validación de datos
- **python-dotenv**: Gestión de variables de entorno
- **pytest**: Framework de testing

## 🤝 Contribución

1. Crea una rama para tu feature: `git checkout -b feature/nombre`
2. Commit tus cambios: `git commit -am 'Añade nueva feature'`
3. Push a la rama: `git push origin feature/nombre`
4. Abre un Pull Request

## 📝 Notas

- Las variables de entorno se cargan desde el archivo `.env`
- CORS está habilitado para todas las rutas (ajusta en `app/main.py` según sea necesario)
- La base de datos por defecto es SQLite (configurable en `.env`)

## 📞 Soporte

Para más información sobre FastAPI, consulta la [documentación oficial](https://fastapi.tiangolo.com/)
