import docker
import schedule
import time
import logging
import os
import openai
import json
import requests
# Base log directory
BASE_LOG_DIR = "/logs"

# Gets tokens/keys passed as environment variables
github_token = os.getenv("GITHUB_TOKEN")
api_key = os.getenv("API_KEY")

if not github_token:
    raise EnvironmentError("Missing GITHUB_TOKEN")
if not api_key:
    raise EnvironmentError("Missing API_KEY")

# Function to set up a logger dynamically
def setup_logger(log_filename):
    # Create logger with unique name
    logger = logging.getLogger(log_filename)  
    logger.setLevel(logging.INFO)

    # Remove existing handlers (to avoid duplicate logs)
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])

    # Create a file handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)

    # Set format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(file_handler)
    return logger

# Loads a previous saved state of a container for issue comparison
def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file, 'r') as file:
            return json.load(file)
    return {}

# Saves a previous state of a container for issue comparison
def save_state(state_file, state):
    with open(state_file, 'w') as file:
        json.dump(state, file, indent=2)

# Function that checks the current status of all containers, and creates log files
def monitor_containers():
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    containers = client.containers.list(all=True)
    
    for container in containers:
        # Get container info
        container_name = container.name
        container_id = container.id
        image_id = container.image.id
        status = container.status

        container_log_dir = os.path.join(BASE_LOG_DIR, container_name)

        # Create the container-specific directory if it doesn't exist
        os.makedirs(container_log_dir, exist_ok=True)

        # Define file paths
        logs_file = os.path.join(container_log_dir, "logs.log")
        stats_file = os.path.join(container_log_dir, "stats.log")
        inspect_file = os.path.join(container_log_dir, "inspect.json")
        state_file = os.path.join(container_log_dir, "state.json")

        # Set up loggers
        log_logger = setup_logger(logs_file)
        stats_logger = setup_logger(stats_file)

        # Capture and write stats
        stats = container.stats(stream=False)
        stats_logger.info(f"Stats for {container_name}: {stats}")

        # Capture and store docker inspect output
        with open(inspect_file, 'w') as inspect_f:
            json.dump(container.attrs, inspect_f, indent=4)  # Save in JSON format

        # Load the most recent save state
        state = load_state(state_file)
        container_state = state.get(container_name, {})

        is_rebuild = (container_id != container_state.get("container_id")) or (image_id != container_state.get("image_id"))
        
        if status != 'running':
            log_logger.warning(f"ALERT: Container {container_name} is not running (Status: {status})")

            if (not container_state.get("issue_created", False) or is_rebuild):
                # Capture and write logs
                logs = container.logs().decode('utf-8')
                log_logger.info(f"Logs for {container_name}:")
                log_logger.info(logs)

                raise_git_issue(container_name)
            issue_created = True
        else:
            log_logger.info(f"Container {container_name} is currently running")
            issue_created = False

        # Create a new save state of basic container info, and a record of whether it produced an issue or not
        state[container_name] = {
            "container_id": container_id,
            "image_id": image_id,
            "issue_created": issue_created,
            "last_status": status
        }

        save_state(state_file, state)

# Schedule the task to run every minute
schedule.every(1).minutes.do(monitor_containers)

def stop_monitoring(): #dont know if this is useful but thought that adding a stop command could help ahah 
    logging.info("Monitoring stopped.")
    exit()

def apiRequest(msgRequest): # prev (msgRequest, filepath)
    openai.api_key = api_key
        
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant who will be given a bulk of information about docker containers, with your job being to both assess the state of the docker containers (summarising their status) and answer questions about them."},
            {"role": "user", "content": msgRequest}
        ],
        max_tokens=50
    )

    return response.choices[0].message['content']
    
def read_log_and_request(logs_file, filepath):
    with open(logs_file, 'r') as file:
        log_contents = file.read()
    apiRequest(log_contents, filepath)

def raise_git_issue(repoName):
    repo_owner = "gpigc-2025"  # Change if needed
    url = f"https://api.github.com/repos/{repo_owner}/{repoName}/issues"

    # OpenAI API key
    openai.api_key = api_key

    logs_file = os.path.join(BASE_LOG_DIR, repoName, "logs.log")
    with open(logs_file, 'r') as file:
        log_contents = file.read()
    
    title_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates short, descriptive GitHub issue titles."},
            {"role": "user", "content": f"Generate a short GitHub issue title of at most 7 words based on the following logs, do not include any other text, only what should be used for the title:\n{log_contents}"}
        ],
        max_tokens=10
    )

    title = title_response['choices'][0]['message']['content'].strip()

    # Generating issue description using OpenAI
    description = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant, generating issue descriptions for GitHub."},
            {"role": "user", "content": "Write a short description that is at most 3 sentences long for the issue using the following logs: If none, type no info."},
            {"role": "user", "content": log_contents}
        ],
        max_tokens=300
    )

    # Fixing headers and data structure for GitHub API
    headers = {
        "Authorization": f"Bearer {github_token}",  # Corrected Authorization method
        "Accept": "application/vnd.github.v3+json"
    }
    
    data = {
        "title": title,  # Title for the issue
        "body": description['choices'][0]['message']['content']  # Body generated by OpenAI
    }

    # Sending the POST request to GitHub API to create the issue
    response = requests.post(url, json=data, headers=headers)

    # Handling the response from GitHub API
    if response.status_code == 201:
        print("Issue created successfully!")
    else:
        print(f"Issue creation failed: {response.status_code}, {response.text}")


# Test the function
if __name__ == "__main__":

    print("Monitoring started. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(1)
