from app import create_app
from app.config import DeploymentConfig

app = create_app(DeploymentConfig)


#i recommend running flask through `$flask run` but this is fine if youre actually using it
