from flask import Flask, render_template
import helper

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/')
def index():
    helper.scan_projects()
    projects = helper.get_projects()
    return render_template('home.html', projects=projects)


@app.route('/history')
def history():
    print("salve da history")
    return render_template('history.html')

@app.route('/edit/<str:project_name>')
def edit(project_name):
    project_info = helper.get_project(project_name=project_name)
    return render_template('edit.html', project_info=project_info)