import os
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd
import datetime
import pytz
import json
import time
import logging
import sys
import math

# def except_handler(type, value, tb):
#     logger.exception("Exception: {0}".format(str(value)))

# logging.basicConfig(filename="out.log", filemode="w", format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s", datefmt="%d/%b/%Y %H:%M:%S",)
# logger = logging.getLogger("TimeHandler")
# logger.setLevel(logging.INFO)
# sys.excepthook = except_handler

load_dotenv()

client = MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
db = client.schedulerDB
project = db.projects
http_trigger = db.http_triggers
time_trigger = db.time_triggers
dependecy_trygger = db.dependecy_triggers


task_table = pd.DataFrame(columns=["Name", "Time"])

def seconds_between_now_and_datetime(dt):
    tz = pytz.timezone('America/Sao_Paulo')
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


def run():
    tasks = list(time_trigger.find({}))
    max_time_table = get_next_sixth_hours()
    task_table = pd.DataFrame(columns=["Name", "Time", "Seconds"])
    task_table.loc[0] = ["DB_Request", max_time_table.loc[0, "Datetime"], seconds_between_now_and_datetime(max_time_table.loc[0, "Datetime"])]
    for task in tasks:
        if "daily" in task["config"]:
            if len(task["config"]["daily"]) == 0:
                task["config"]["daily"] = ["00:01"]
            for hour in task["config"]["daily"]:
                if hour == "00:00":
                    hour = "00:01"
                hour = datetime.datetime.strptime(hour, "%H:%M")
                now = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
                hour_ = now.replace(
                    hour=hour.hour, minute=hour.minute, second=0, microsecond=0
                )
                if hour_ >= now and hour_ <= max_time_table.loc[0, "Datetime"]:
                    task_table.loc[len(task_table)] = [task["name"], hour_, seconds_between_now_and_datetime(hour_)]

        if "weekly" in task["config"]:
            if len(task["config"]["weekly"]) == 0:
                task["config"]["weekly"] = {"0": ["00:01"]}
            for day in task["config"]["weekly"]:
                if len(task["config"]["weekly"][day]) == 0:
                    task["config"]["weekly"][day] = ["00:01"]
                for hour in task["config"]["weekly"][day]:
                    if hour == "00:00":
                        hour = "00:01"
                    now = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
                    if int(day) == now.weekday():
                        hour = datetime.datetime.strptime(hour, "%H:%M")
                        hour_ = now.replace(
                            hour=hour.hour, minute=hour.minute, second=0, microsecond=0
                        )
                        if hour_ >= now and hour_ <= max_time_table.loc[0, "Datetime"]:
                            task_table.loc[len(task_table)] = [task["name"], hour_, seconds_between_now_and_datetime(hour_)]

        if "monthly" in task["config"]:
            if len(task["config"]["monthly"]) == 0:
                task["config"]["monthly"] = {"1": ["00:01"]}
            for day in task["config"]["monthly"]:
                if len(task["config"]["monthly"][day]) == 0:
                    task["config"]["monthly"][day] = ["00:01"]
                for hour in task["config"]["monthly"][day]:
                    if hour == "00:00":
                        hour = "00:01"
                    now = datetime.datetime.now(tz=pytz.timezone("America/Sao_Paulo"))
                    if int(day) == now.day:
                        hour = datetime.datetime.strptime(hour, "%H:%M")
                        hour_ = now.replace(
                            hour=hour.hour, minute=hour.minute, second=0, microsecond=0
                        )
                        if hour_ >= now and hour_ <= max_time_table.loc[0, "Datetime"]:
                            task_table.loc[len(task_table)] = [task["name"], hour_, seconds_between_now_and_datetime(hour_)]

    groups = task_table.groupby("Time").filter(lambda x: len(x) > 1).groupby("Time")
    task_table_list = [group.reset_index(drop=True) for _, group in groups]
    unique_times = task_table.groupby("Time").filter(lambda x: len(x) == 1)
    task_table_list.extend(
        [unique_times.loc[[i]].reset_index(drop=True) for i in unique_times.index]
    )
    task_table_list.sort(key=lambda x: x["Time"].iloc[0])

    for task_table in task_table_list:
        print(task_table)

run()
