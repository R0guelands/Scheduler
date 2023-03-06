import os
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd
import datetime as dt
import pytz
import json

load_dotenv()

"""	
    Schema for project

    {
        "_id": "mongo_id",
        "name": "project_folder_name",
        "status": "project_status",
        "exec_path": "project_mainpy_path",
        "log_path": "project_log_path",
        "python_path": "project_python_path",
        "created_at": "project_created_at"
    }
"""

client = MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
db = client.schedulerDB
project = db.projects
http_trigger = db.http_triggers
time_trigger = db.time_triggers
dependecy_trygger = db.dependecy_triggers


def check_project(folder):
    return (
        bool(os.path.exists(f"./projects/{folder}/main.py"))
        if os.path.exists(f"./projects/{folder}/.venv")
        else False
    )


def check_valids_on_db(projects_local):
    projects_db_df = pd.DataFrame(
        list(project.find({})),
        columns=[
            "_id",
            "name",
            "status",
            "exec_path",
            "log_path",
            "python_path",
            "created_at",
        ],
    )

    for name in projects_local:
        if name not in projects_db_df["name"].values:
            project.insert_one(
                {
                    "name": name,
                    "status": "no_schedule",
                    "exec_path": f"./projects/{name}/main.py",
                    "log_path": f"./projects/{name}/logs",
                    "python_path": f"./projects/{name}/.venv/bin/python",
                    "created_at": f"{dt.datetime.now(tz=pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')}",
                }
            )

    for name in projects_db_df["name"].values:
        if name not in projects_local:
            project.delete_one({"name": name})
            delete_trigger("http", name)
            delete_trigger("time", name)
            delete_trigger("dependency", name)


def scan_projects():
    folders = os.listdir("./projects")
    valid_projects = [folder for folder in folders if check_project(folder=folder)]
    check_valids_on_db(projects_local=valid_projects)


def get_projects():
    return list(project.find({}))


def get_http_triggers():
    return list(http_trigger.find({}))


def get_time_triggers():
    return list(time_trigger.find({}))


def get_project(project_name):
    return project.find_one({"name": project_name})


def get_dependency_triggers():
    return list(dependecy_trygger.find({}))


def delete_trigger(type, project_name):
    if type == "http":
        try:
            dependents = http_trigger.find_one({"name": project_name})["dependents"]
            for dependent in dependents:
                dependecy_trygger.delete_one({"name": dependent})
                project.update_one(
                    {"name": dependent}, {"$set": {"status": "no_schedule"}}
                )
            http_trigger.delete_one({"name": project_name})
            project.update_one(
                {"name": project_name}, {"$set": {"status": "no_schedule"}}
            )
        except:
            return False
    elif type == "time":
        try:
            dependents = time_trigger.find_one({"name": project_name})["dependents"]
            for dependent in dependents:
                dependecy_trygger.delete_one({"name": dependent})
                project.update_one(
                    {"name": dependent}, {"$set": {"status": "no_schedule"}}
                )
            time_trigger.delete_one({"name": project_name})
            project.update_one(
                {"name": project_name}, {"$set": {"status": "no_schedule"}}
            )
        except:
            return False
    elif type == "dependency":
        try:
            dependecy_trygger.delete_one({"name": project_name})
            project.update_one(
                {"name": project_name}, {"$set": {"status": "no_schedule"}}
            )
            if http_trigger.find_one({"dependents": project_name}):
                http_trigger.update_one(
                    {"dependents": project_name}, {"$pull": {"dependents": project_name}}
                )
            if time_trigger.find_one({"dependents": project_name}):
                time_trigger.update_one(
                    {"dependents": project_name}, {"$pull": {"dependents": project_name}}
                )
        except:
            return False
    return True


def add_http_trigger(project_name):
    if not http_trigger.find_one({"name": project_name}) and not time_trigger.find_one(
        {"name": project_name}
    ):
        try:
            http_trigger.insert_one(
                {
                    "name": project_name,
                    "created_at": f"{dt.datetime.now(tz=pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')}",
                    "dependents": [],
                }
            )
            project.update_one({"name": project_name}, {"$set": {"status": "http"}})
        except:
            return False
    return True


def add_time_trigger(project_name, config):
    if not http_trigger.find_one({"name": project_name}) and not time_trigger.find_one(
        {"name": project_name}
    ):
        try:
            time_trigger.insert_one(
                {
                    "name": project_name,
                    "created_at": f"{dt.datetime.now(tz=pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')}",
                    "dependents": [],
                    "config": json.loads(config),
                }
            )
            project.update_one({"name": project_name}, {"$set": {"status": "time"}})
        except:
            return False
    return True


def add_dependency_trigger(child, parent, trigger_type):
    try:
        dependecy_trygger.insert_one(
            {
                "name": child,
                "parent": parent,
                "trigger_type": trigger_type,
                "created_at": f"{dt.datetime.now(tz=pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')}",
                "dependents": [],
            }
        )
        project.update_one({"name": child}, {"$set": {"status": "dependency"}})
        if http_trigger.find_one({"name": parent}):
            http_trigger.update_one({"name": parent}, {"$push": {"dependents": child}})
        elif time_trigger.find_one({"name": parent}):
            time_trigger.update_one({"name": parent}, {"$push": {"dependents": child}})
        return True
    except:
        return False
