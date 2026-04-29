from flask import Flask, render_template, request, redirect
from azure.cosmos import CosmosClient
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
import uuid
import os

app = Flask(__name__)

credential = DefaultAzureCredential()

COSMOS_URL = os.environ.get('COSMOS_URL')
COSMOS_KEY = os.environ.get('COSMOS_KEY')
KEYVAULT_URL = os.environ.get('KEYVAULT_URL', 'https://homework4-vault.vault.azure.net/')

cosmos_client = CosmosClient(COSMOS_URL, credential=COSMOS_KEY)
db = cosmos_client.get_database_client('charboard')
container = db.get_container_client('characters')

secrets_client = SecretClient(vault_url=KEYVAULT_URL, credential=credential)


def get_server_name():
    return secrets_client.get_secret('app-secret').value


@app.route('/')
def index():
    server_name = get_server_name()
    characters = list(container.query_items(
        query='SELECT * FROM c ORDER BY c.level DESC',
        enable_cross_partition_query=True
    ))
    return render_template('index.html', characters=characters, server_name=server_name)


@app.route('/add', methods=['POST'])
def add_character():
    name = request.form.get('name', '').strip()
    char_class = request.form.get('char_class', '').strip()
    level = int(request.form.get('level', 1))

    if name and char_class:
        container.create_item({
            'id': str(uuid.uuid4()),
            'name': name,
            'class': char_class,
            'level': level
        })
    return redirect('/')


@app.route('/delete/<character_id>', methods=['POST'])
def delete_character(character_id):
    container.delete_item(item=character_id, partition_key=character_id)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
