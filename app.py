from flask import Flask, render_template

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/')
def index():
    print("salve da home")
    return render_template('home.html')


@app.route('/history')
def history():
    print("salve da history")
    return render_template('history.html')