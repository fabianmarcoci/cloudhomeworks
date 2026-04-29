from flask import Flask, render_template, request, redirect
from google.cloud import datastore
from google.cloud import secretmanager
import os

app = Flask(__name__)

db = datastore.Client()
secrets_client = secretmanager.SecretManagerServiceClient()

PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', 'homework3-492011')


def get_server_name():
    name = f"projects/{PROJECT_ID}/secrets/app-secret/versions/latest"
    response = secrets_client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


@app.route('/')
def index():
    server_name = get_server_name()
    query = db.query(kind='Character')
    query.order = ['-level']
    characters = [
        dict(entity) | {'id': entity.key.id}
        for entity in query.fetch()
    ]
    return render_template('index.html', characters=characters, server_name=server_name)


@app.route('/add', methods=['POST'])
def add_character():
    name = request.form.get('name', '').strip()
    char_class = request.form.get('char_class', '').strip()
    level = int(request.form.get('level', 1))

    if name and char_class:
        key = db.key('Character')
        entity = datastore.Entity(key=key)
        entity.update({'name': name, 'class': char_class, 'level': level})
        db.put(entity)
    return redirect('/')


@app.route('/delete/<int:character_id>', methods=['POST'])
def delete_character(character_id):
    key = db.key('Character', character_id)
    db.delete(key)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
