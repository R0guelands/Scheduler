from flask import Flask, render_template, redirect, request, jsonify, send_from_directory, Response
import helper
import json

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    helper.scan_projects()
    projects = helper.get_projects()
    http_triggers = helper.get_http_triggers()
    time_triggers = helper.get_time_triggers()
    dependency_triggers = helper.get_dependency_triggers()

    return render_template(
        "home.html",
        projects=projects,
        http_triggers=http_triggers,
        time_triggers=time_triggers,
        dependency_triggers=dependency_triggers
    )


@app.route("/history", methods=["GET"])
def history():
    execution_history = helper.get_execution_history()
    execution_history.reverse()
    return render_template("history.html", execution_history=execution_history)


@app.route("/edit/<project_name>", methods=["GET"])
def edit(project_name):
    project_info = helper.get_project(project_name=project_name)
    http_triggers = helper.get_http_triggers()
    time_triggers = helper.get_time_triggers()
    # dependecy_triggers = helper.get_dependency_triggers()
    # return render_template("edit.html", project_info=project_info, http_triggers=http_triggers, time_triggers=time_triggers, dependecy_triggers=dependecy_triggers)
    return render_template("edit.html", project_info=project_info, http_triggers=http_triggers, time_triggers=time_triggers)


@app.route("/deleteTrigger/<trigger_type>/<project_name>", methods=["GET"])
def deleteTrigger(trigger_type, project_name):
    if helper.delete_trigger(trigger_type, project_name):
        return redirect("/")
    else:
        return "Error"


@app.route("/addHttpTrigger/<project_name>", methods=["POST"])
def addTrigger(project_name):
    return redirect("/") if helper.add_http_trigger(project_name) else "Error"


@app.route("/addTimeTrigger/<project_name>", methods=["POST"])
def addTimeTrigger(project_name):
    content = request.form.get("config")
    try:
        json.loads(content)
    except:
        return "Error"

    if helper.add_time_trigger(project_name, content):
        return redirect("/")
    else:
        return "Error"

@app.route("/addDependencyTrigger/<config>", methods=["POST"])
def addDependencyTrigger(config):
    child, parent, trigger_type = config.split("_")
    return redirect("/") if helper.add_dependency_trigger(child, parent, trigger_type) else "Error"

@app.route('/history/view/<id>', methods=['GET'])
def get_log(id):
    log_path = helper.get_execution_history_by_project(id)["log_path"]
    
    with open(log_path, 'r') as f:
        content = f.read()

    return Response(content, mimetype='text/plain')

@app.route('/history/download/<id>', methods=['GET'])
def download_log(id):
    log_path = helper.get_execution_history_by_project(id)["log_path"]
    log_path = log_path[7:]
    return send_from_directory("logs", log_path)

@app.route("/triggers/<project_name>", methods=["POST"])
def http_trigger(project_name):
    project_name = project_name.replace("\t", "")
    names = [project["name"] for project in helper.get_http_triggers()]
    if project_name not in names:
        return jsonify("Bad project name"), 400
    body = request.get_json()
    if "headless" in request.args:
        import threading
        threading.Thread(
            target=helper.run_project, args=(project_name, body)
        ).start()
        return jsonify("Success. Headless mode"), 200
    execution = helper.run_project(project_name, body)
    return jsonify("Success"), 200 if execution.returncode == 0 else jsonify("Error"), 400

app.run(host="0.0.0.0", port=5000, debug=False)
