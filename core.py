from bottle import route, run, template, request, static_file, redirect, post
import bottle
import json
import sqlite3
import subprocess
import config
from helpers import Dummy, multi_dummy, compose_command


conn = sqlite3.connect('raspctl.db')
config.load_config(conn)

# Create DDBB schema:
# create table execute (id INTEGER PRIMARY KEY AUTOINCREMENT, class TEXT, action TEXT, value TEXT, extra TEXT, command TEXT);
# create table config (id INTEGER PRIMARY KEY AUTOINCREMENT, json TEXT);


# STATIC ROUTES
@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root='/home/inedit/projects/raspctl/static')

@route('/favicon.ico')
def get_favicon():
    return static_file('favicon.ico', root="./static/img")


## HTTP HANDLERS
def _execute(_class, action):
    if config.COMMAND_EXECUTION == False:
        return "The command execution is NOT available."

    c = conn.cursor()
    DEFAULT_VALUE, COMMAND, EXTRA = 0, 1, 2
    query = 'SELECT value, command, extra FROM execute WHERE class=? and action=?'
    c.execute(query, (_class, action))
    result = c.fetchone()
    if not result:
        return "Command not found"

    default_value = result[DEFAULT_VALUE]
    value = request.params.get('value', default_value)

    command = compose_command(result[COMMAND], value, result[EXTRA])

    subprocess.call(command, shell=True)
    return "Executing: %s" % command

@route('/execute')
def execute():
    try:
        _class = request.params['class']
        action = request.params['action']
    except:
        return "Invalid request. 'class' and 'action' parameters must be present."

    return _execute(_class, action)

@route('/command/edit/:id_')
def command_edit(id_=None):
    id_ = "" if id_ == "new" else id_
    c = conn.cursor()
    query = "SELECT id, class, action, command, extra from execute where id = ?"
    data = c.execute(query, (id_,))

    data = Dummy(data)

    return template('edit', data=data)


@post('/command/save')
def command_save():
    id_ = request.POST.get('id')
    class_ = request.POST.get('class')
    action = request.POST.get('action')
    command = request.POST.get('command', '')

    if not class_ or not action:
        return "Invalid data. CLASS and ACTION are required fields."

    c = conn.cursor()

    if id_:
        query = "UPDATE execute set class = ?, action = ?, command = ? where id = ?"
        a = c.execute(query, (class_, action, command, id_))
    else:
        query = "INSERT INTO execute (class, action, command) VALUES (?, ?, ?)"
        result = c.execute(query, (class_, action, command))
        id_ = result.lastrowid


    conn.commit()
    redirect("/command/edit/%s" % id_)

@route('/command/delete/:id_')
def command_delete(id_=None):
    c = conn.cursor()
    query = "DELETE FROM execute where id = ?"
    c.execute(query, (id_,))
    conn.commit()
    return "ok"

@route('/config')
def config_edit():
    return template('config', config=config)

@post('/save_configuration')
def config_save():
    def bool_eval(name):
        return request.POST.get(name) == "True"

    conf = {
        "SHOW_DETAILED_INFO": bool_eval('SHOW_DETAILED_INFO'),
        "SHOW_TODO": bool_eval('SHOW_TODO'),
        "COMMAND_EXECUTION": bool_eval('COMMAND_EXECUTION'),
    }

    config.save_configuration(conn, conf)
    return redirect("/")

@route('/')
def index():
    c = conn.cursor()
    query = "SELECT id, class, action, command FROM execute order by class, action asc"
    rows=multi_dummy(c.execute(query))
    dum = rows[0]

    return template('index', rows=rows)


run(host='0.0.0.0', port=8086, reloader=True)