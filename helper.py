import os
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd
import datetime
import pytz
import json
import subprocess
import shutil

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
execution_history = db.execution_history


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
                    "log_path": f"./projects/{name}/out.log",
                    "python_path": f"./projects/{name}/.venv/bin/python",
                    "created_at": f"{datetime.datetime.now(tz=pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')}",
                }
            )

    for name in projects_db_df["name"].values:
        if name not in projects_local:
            project.delete_one({"name": name})
            delete_trigger("http", name)
            delete_trigger("time", name)
            delete_trigger("dependency", name)
            delete_logs(name)

def delete_logs(project_name):
    if os.path.exists(f"./logs/{project_name}"):
        for file in os.listdir(f"./logs/{project_name}"):
            if file.endswith(".log"):
                os.remove(f"./logs/{project_name}/{file}")
        os.removedirs(f"./logs/{project_name}")
        execution_history.delete_many({"name": project_name})

def scan_projects():
    folders = os.listdir("./projects")
    valid_projects = [folder for folder in folders if check_project(folder=folder)]
    check_valids_on_db(projects_local=valid_projects)


def get_projects():
    return list(project.find({}))

def get_execution_history():
    return list(execution_history.find({}))

def get_http_triggers():
    return list(http_trigger.find({}))


def get_time_triggers():
    return list(time_trigger.find({}))


def get_project(project_name):
    return project.find_one({"name": project_name})

from bson.objectid import ObjectId

def get_execution_history_by_project(id):
    print(id)
    return execution_history.find_one({"_id": ObjectId(id)})


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
                    "created_at": f"{datetime.datetime.now(tz=pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')}",
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
                    "created_at": f"{datetime.datetime.now(tz=pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')}",
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
                "created_at": f"{datetime.datetime.now(tz=pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')}",
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
    
def copy_log(task_name, log_path, timestamp):
    if os.path.exists(log_path):
        if not os.path.exists(f"./logs/{task_name}"):
            os.makedirs(f"./logs/{task_name}")
        shutil.copy(log_path, f"./logs/{task_name}/{timestamp}.log")

def format_execution_time(start, end):
    seconds = (end - start).total_seconds()

    if seconds < 60:
        return f"{round(seconds, 2)}s"
    elif seconds < 3600:
        return f"{round(seconds // 60, 2)}m {round(seconds % 60, 2)}s"
    else:
        return f"{round(seconds // 3600, 2)}h {round((seconds % 3600) // 60, 2)}m {round(seconds % 60, 2)}s"


def add_execution_history(task_name, task_type, status, start_time, end_time, log_path):
    execution_history.insert_one(
        {
            "name": task_name,
            "task_type": task_type,
            "status": status,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "runtime": format_execution_time(start_time, end_time),
            "log_path": log_path,
        }
    )

def run_dependent_task(task_name, execution_status, http_args):
    task_info = http_trigger.find_one({"name": task_name})
    dependents = task_info["dependents"]
    for dependent in dependents:
        dependent_info = dependecy_trygger.find_one(
            {"name": dependent, "parent": task_name}
        )
        if dependent_info["trigger_type"] in [execution_status, "Either"]:
            print(dependent)
            project_info = project.find_one({"name": dependent})
            if project_info["status"] != "dependency" or not project_info["status"]:
                return
            venv_python = project_info["python_path"]
            args = [venv_python, project_info["exec_path"], *http_args]
            start_time = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
            execution = subprocess.run(args)
            end_time = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
            copy_log(
                dependent,
                project_info["log_path"],
                start_time.strftime("%Y-%m-%d_%H-%M-%S"),
            )
            execution_returncode = "Success" if execution.returncode == 0 else "Failed"
            add_execution_history(
                dependent,
                "dependency",
                execution_returncode,
                start_time,
                end_time,
                f"./logs/{dependent}/{start_time.strftime('%Y-%m-%d_%H-%M-%S')}.log",
            )
    
def run_project(task_name, http_args):
    if project_info := get_project(task_name):
        venv_python = project_info["python_path"]
        http_args = [f"{key}={value}" for key, value in dict(http_args).items()]
        args = [venv_python, project_info["exec_path"], *http_args]
        start_time = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
        execution = subprocess.run(args)
        end_time = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
        copy_log(
            task_name, project_info["log_path"], start_time.strftime("%Y-%m-%d_%H-%M-%S")
        )
        execution_returncode = "Success" if execution.returncode == 0 else "Failed"
        add_execution_history(
            task_name,
            "http",
            execution_returncode,
            start_time,
            end_time,
            f"./logs/{task_name}/{start_time.strftime('%Y-%m-%d_%H-%M-%S')}.log",
        )
        run_dependent_task(task_name, execution_returncode, http_args)
        return True