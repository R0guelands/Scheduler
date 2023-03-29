import os
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd
import datetime
import pytz
import time
import math
import threading
import subprocess
import shutil
import logconfig


logger = logconfig.SchedulerLog.defineLogConfig(
    log_path="/home/r0guelands/Apps/Scheduler/logs/time_scheduler/out.log"
)

load_dotenv()

client = MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
db = client.schedulerDB
project = db.projects
http_trigger = db.http_triggers
time_trigger = db.time_triggers
dependecy_trygger = db.dependecy_triggers
execution_history = db.execution_history


task_table = pd.DataFrame(columns=["Name", "Time"])


def seconds_between_now_and_datetime(dt):
    tz = pytz.timezone("America/Sao_Paulo")
    now = datetime.datetime.now(tz)
    dt_brtz = dt.astimezone(tz)
    timedelta = dt_brtz - now
    return math.ceil(timedelta.total_seconds())


def get_next_sixth_hours(num_hours=24):
    tz_brazil = pytz.timezone("America/Sao_Paulo")
    now = datetime.datetime.now(tz=tz_brazil)
    start_of_day = tz_brazil.localize(
        datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
    )
    hours_passed = (now - start_of_day).seconds // 3600
    next_sixth_hours = []
    for i in range(num_hours // 6):
        next_sixth_hour = ((hours_passed // 6) + 1 + i) * 6
        next_sixth_hour_dt = start_of_day + datetime.timedelta(hours=next_sixth_hour)
        next_sixth_hours.append(next_sixth_hour_dt)

    return pd.DataFrame({"Datetime": next_sixth_hours})


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


def run_task(task_name, type_):
    project_info = project.find_one({"name": task_name})
    if not project_info:
        logger.info(f"Task [{task_name}] not found. Skipping...")
        return
    if (
        project_info["status"] not in ["time", "dependency"]
        or not project_info["status"]
    ):
        return
    venv_python = project_info["python_path"]
    args = [venv_python, project_info["exec_path"]]
    start_time = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
    execution = subprocess.run(args)
    end_time = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
    copy_log(
        task_name, project_info["log_path"], start_time.strftime("%Y-%m-%d_%H-%M-%S")
    )
    execution_returncode = "Success" if execution.returncode == 0 else "Failed"
    add_execution_history(
        task_name,
        type_,
        execution_returncode,
        start_time,
        end_time,
        f"./logs/{task_name}/{start_time.strftime('%Y-%m-%d_%H-%M-%S')}.log",
    )
    return execution_returncode


def run_dep_task(task_name, execution_status):
    task_info = time_trigger.find_one({"name": task_name})
    if not task_info:
        logger.info(f"Task [{task_name}] not found for dependency check. Skipping...")
        return
    dependents = task_info["dependents"]
    if not dependents:
        return
    for dependent in dependents:
        dependent_info = dependecy_trygger.find_one(
            {"name": dependent, "parent": task_name}
        )
        if dependent_info["trigger_type"] in [execution_status, "Either"]:
            logger.info(f"Running dependent task {dependent}")
            run_task(dependent, "dependency")


def orchestrate_task(task_name):
    execution_returncode = run_task(task_name, "time")
    run_dep_task(task_name, execution_returncode)


def if_daily(task, task_table, max_time_table):
    if len(task["config"]["daily"]) == 0:
        task["config"]["daily"] = ["00:01"]
    now = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
    for hour in task["config"]["daily"]:
        if hour == "00:00":
            hour = "00:01"
        hour = datetime.datetime.strptime(hour, "%H:%M")
        hour = hour.replace(
            year=now.year,
            month=now.month,
            day=now.day,
            second=0,
            microsecond=0,
            tzinfo=now.tzinfo,
        )
        if hour >= now and hour <= max_time_table.loc[0, "Datetime"]:
            task_table.loc[len(task_table)] = [task["name"], hour]
    return task_table


def if_weekly(task, task_table, max_time_table):
    if len(task["config"]["weekly"]) == 0:
        task["config"]["weekly"] = {"0": ["00:01"]}
    now = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
    for day, hours in task["config"]["weekly"].items():
        if not hours:
            task["config"]["weekly"][day] = ["00:01"]
        for hour in hours:
            if hour == "00:00":
                hour = "00:01"
            hour = datetime.datetime.strptime(hour, "%H:%M")
            hour = hour.replace(
                year=now.year,
                month=now.month,
                day=now.day,
                second=0,
                microsecond=0,
                tzinfo=now.tzinfo,
            )
            if int(day) == now.weekday() and (
                hour >= now and hour <= max_time_table.loc[0, "Datetime"]
            ):
                task_table.loc[len(task_table)] = [task["name"], hour]
    return task_table


def if_monthly(task, task_table, max_time_table):
    if len(task["config"]["monthly"]) == 0:
        task["config"]["monthly"] = {"1": ["00:01"]}
    now = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
    for day, hours in task["config"]["monthly"].items():
        if not hours:
            task["config"]["monthly"][day] = ["00:01"]
        for hour in hours:
            if hour == "00:00":
                hour = "00:01"
            hour = datetime.datetime.strptime(hour, "%H:%M")
            hour = hour.replace(
                year=now.year,
                month=now.month,
                day=now.day,
                second=0,
                microsecond=0,
                tzinfo=now.tzinfo,
            )
            if int(day) == now.day and (
                hour >= now and hour <= max_time_table.loc[0, "Datetime"]
            ):
                task_table.loc[len(task_table)] = [task["name"], hour]
    return task_table


def organize_tasks(task_table):
    groups = task_table.groupby("Time").filter(lambda x: len(x) > 1).groupby("Time")
    task_table_list = [group.reset_index(drop=True) for _, group in groups]
    unique_times = task_table.groupby("Time").filter(lambda x: len(x) == 1)
    task_table_list.extend(
        [unique_times.loc[[i]].reset_index(drop=True) for i in unique_times.index]
    )
    task_table_list.sort(key=lambda x: x["Time"].iloc[0])
    return task_table_list


def get_exec_table():
    tasks = list(time_trigger.find({}))
    max_time_table = get_next_sixth_hours()
    task_table = pd.DataFrame(columns=["Name", "Time"])
    task_table.loc[0] = ["DB_Request", max_time_table.loc[0, "Datetime"]]
    for task in tasks:
        if "daily" in task["config"]:
            task_table = if_daily(task, task_table, max_time_table)
        if "weekly" in task["config"]:
            task_table = if_weekly(task, task_table, max_time_table)
        if "monthly" in task["config"]:
            task_table = if_monthly(task, task_table, max_time_table)

    return organize_tasks(task_table)


while True:
    task_table_list = get_exec_table()
    print_df = pd.DataFrame(columns=["Name", "Time"])
    for task_table in task_table_list:
        print_df = pd.concat([print_df, task_table], ignore_index=True)
    logger.info(f"Tasks to be executed:\n{print_df}")
    for task_table in task_table_list:
        sleep_time = seconds_between_now_and_datetime(task_table.loc[0, "Time"])
        logger.info(f"Sleeping for {sleep_time} seconds")
        time.sleep(sleep_time)
        threds = []
        for task in task_table["Name"]:
            logger.info(f"Running task {task}")
            if task != "DB_Request":
                thread = threading.Thread(target=orchestrate_task, args=(task,))
                thread.start()
                threds.append(thread)
        for thread in threds:
            thread.join()
