# StAItus

AI powered tool for monitoring docker container statuses, and analysing container errors

# Set up

The project is dockerised so can be run with a docker container. This will handle dependancies and make server deployment easier.
This means docker is required for development.

To build the project clone this repo and navigate to the directory containing the **Dockerfile** then run the following:
`sudo docker build -t staitus .`

Then to run the project:
`sudo docker run -p 5003:5003 staitus`

Then to view the project open your web browser and go to http://localhost:5003/

# Deployment

To do anything involving our server (including viewing the websites) you will need to be on campus of connected to the campus vpn (https://www.york.ac.uk/it-services/tools/vpn/)

After a pull request is merged jenkins **should** kick off a new build. To check on jenkins go to gpigc2025.york.ac.uk:8080.

once this is done you can view the website at gpigc2025.york.ac.uk/staitus

# Dependancies

To add new pip dependancies to the project simply add them to requirements.txt
