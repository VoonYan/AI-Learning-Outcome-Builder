from app import create_app
from app.config import DeploymentConfig

app = create_app(DeploymentConfig)
