import os
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

'''	
    Schema for project

    {
        "_id": "mongo_id",
        "name": "project_folder_name",
        "path": "project_mainpy_path",
        "status": "project_status",
        "log_path": "project_log_path"
    }
'''

client = MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
db = client.schedulerDB
project = db.projects

def check_project(folder):
    return (
        bool(os.path.exists(f"./projects/{folder}/main.py"))
        if os.path.exists(f"./projects/{folder}/.venv")
        else False
    )

def check_valids_on_db(projects_local):
    projects_db_df = pd.DataFrame(list(project.find()), columns=["name", "path", "status", "log_path"])
    
    for name in projects_local:
        if name not in projects_db_df["name"].values:
            project.insert_one(
                {
                    "name": name,
                    "path": f"./projects/{name}/main.py",
                    "status": "not_scheduled",
                    "log_path": f"./projects/{name}/logs",
                }
            )
    
    for name in projects_db_df["name"].values:
        if name not in projects_local:
            project.delete_one({"name": name})

def scan_projects():
    folders = os.listdir("./projects")
    valid_projects = [folder for folder in folders if check_project(folder=folder)]
    check_valids_on_db(projects_local=valid_projects)



def get_projects():
    return list(project.find({}))

def get_project(project_name):
    return project.find_one({"name": project_name})