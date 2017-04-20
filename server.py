import os
import codecs
import json

from functools import wraps

from flask import Flask, render_template, request, Response, redirect, url_for
from flask_mail import Mail, Message


mail = Mail()
app = Flask(__name__)

CONFIG_DIR = 'bustr_conf.json'

CONFIG = {}

try:
    with codecs.open(CONFIG_DIR, 'r', 'utf-8') as config_file:
        config_obj = json.loads(config_file.read())

        for key in config_obj:
            CONFIG[key] = config_obj[key]

        config_file.close()

except TypeError:
    pass

def _set_mailer_settings():
    app.config['MAIL_SERVER'] = CONFIG.get('mailer_host', '')
    app.config['MAIL_PORT'] = CONFIG.get('mailer_port', 465)
    app.config['MAIL_USE_TLS'] = CONFIG.get('mailer_use_tls', False)
    app.config['MAIL_USE_SSL'] = CONFIG.get('mailer_use_ssl', False)
    app.config['MAIL_USERNAME'] = CONFIG.get('mailer_sender', '')
    app.config['MAIL_PASSWORD'] = CONFIG.get('mailer_password', '')
    app.config['MAIL_DEFAULT_SENDER'] = CONFIG.get('mailer_sender', '')

def _get_power_status():
    return False

def _save_config():

    with codecs.open(CONFIG_DIR, 'w+', 'utf-8') as config_file:
        config_file.write(json.dumps(CONFIG))
        config_file.close()

    _set_mailer_settings()

def _send_status_email():
    try:
        _set_mailer_settings()
        mail.init_app(app)
        message = Message(
            'BEZIRGAN SITE INFO',
            recipients=CONFIG.get('recipients', [])
        )

        message.body = 'THE POWER IS OUT!!'

        with mail.connect() as conn:
            conn.send(message)

    except Exception as err:
        print(err)
        return str(err)

def check_auth(username, password):
    return username == CONFIG.get('username', 'admin')\
           and password == CONFIG.get('password', 'password')

def authenticate():
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():

    _send_status_email()

    messages = request.args.get('messages', [])
    errors = request.args.get('errors', [])

    if len(messages):
        messages = messages.split(',')

    if len(errors):
        errors = errors.split(',')

    return render_template('index.html',
                            power_status=_get_power_status(),
                            errors=errors,
                            messages=messages,
                            config=CONFIG,)

@app.route('/change_password', methods=['POST'])
def change_password():
    errors = []
    messages = []

    curr_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password =request.form['new_password_confirm']

    if curr_password == CONFIG.get('password', '2627f68597'):
        if confirm_password == new_password:
            CONFIG['password'] = new_password
            _save_config()
            messages.append('Password changed successfully.')
        else:
            errors.append('New passwords did not match.')
    else:
        errors.append('Current password was not correct.')

    return redirect(url_for('index', messages=messages, errors=errors))

@app.route('/change_email_settings', methods=['POST'])
def change_email_settings():
    errors = []
    messages = []

    try:
        CONFIG['mailer_host'] = request.form['mail_host']
        CONFIG['mailer_port'] = request.form['mail_port']
        CONFIG['mailer_use_tls'] = 'tls_enabled' in\
            request.form.getlist('mail_use_tls')
        CONFIG['mailer_use_ssl'] = 'ssl_enabled' in\
            request.form.getlist('mail_use_ssl')
        CONFIG['mailer_sender'] = request.form['username']
        CONFIG['mailer_password'] = request.form['password']
        _save_config()
        messages.append('Successfully changed email settings')

    except (ValueError) as err:
        errors.append('Could not save email settings')

    errors.append(_send_status_email())
    return redirect(url_for('index', messages=messages, errors=errors))

@app.route('/remove_recipient', methods=['POST'])
def remove_recipient():
    errors = []
    messages = []

    try:
        CONFIG['recipients'].remove(request.form['recipient'])
        _save_config()
        messages.append('Email recipient removed successfully')

    except ValueError:
        errors.append('Couldn\'t save new recipient')

    return redirect(url_for('index', messages=messages, errors=errors))


@app.route('/edit_recipients', methods=['POST'])
def edit_recipients():
    errors = []
    messages = []

    try:
        email = request.form['new_recipient']
        if 'recipients' not in CONFIG:
            CONFIG['recipients'] = []
        CONFIG['recipients'].append(email)
        _save_config()
        messages.append('New email recipient added successfully')

    except ValueError:
        errors.append('Couldn\'t save new recipient')

    return redirect(url_for('index', messages=messages, errors=errors))

if __name__ == '__main__':
    app.run()
