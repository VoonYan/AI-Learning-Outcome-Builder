### AI-Learning-Outcome-Builder
AI Learning Outcome Builder for The University of Western Australia

# Overview:
The current AI Learning Outcome Builder is a flask-based prototype of the intended system. Developed though flask it’s installation and running is very simple. 


# Installation:
Install the git repo via the download in the github or via 

`Git clone https://github.com/RandomDev92/AI-Learning-Outcome-Builder.git` 

Once downloaded, create a virtual environment either through conda or venv, we recommend venv, as that is what it was developed in but other virtual environments will work too. 

- Setup venv for the first time:

  `python -m venv venv`

- Running venv, the Activate script might be different for different OS:

  `Windows: ./venv/Scripts/activate`
  
  `Mac/Linux: ./venv/bin/activate`

- Installing Dependencies:

  `pip install -r requirements.txt`

- Running the Flask Server:

  `flask run`

# Troubleshooting:
For common issues deleting the database usually fixes it, this obviously clears the database but simply deleting app.db will solve the issues.

