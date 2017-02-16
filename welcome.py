from flask import Flask, request, make_response, render_template
from cloudant.client import Cloudant
from base64 import b64encode
import hashlib
import os.path
import time

# Cloudant Credentials.
USERNAME = "d31efff6-3c9e-4c95-885a-95a542b15bc5-bluemix"
PASSWORD = "018a60bbff871d519793a3bfb6d40823319d6a934b2f3722c459333e8f390f44"
URL = "https://d31efff6-3c9e-4c95-885a-95a542b15bc5-bluemix:018a60bbff871d519793a3bfb6d40823319d6a934b2f3722c459333e8f390f44@d31efff6-3c9e-4c95-885a-95a542b15bc5-bluemix.cloudant.com"

# Connecting to the account.
client = Cloudant(USERNAME, PASSWORD, url=URL)
client.connect()

# Connecting to the database.
my_database = client['my_database']

app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))


# Main Page.
@app.route('/')
def index():
    return app.send_static_file('index.html')


# Uploading the file.
@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        # Gathering file information
        file = request.files['file']
        file_name = file.filename
        contents = file.stream.read().decode("utf-8")
        hash_value = hashlib.md5(contents).hexdigest()
        last_modified = time.strftime("%x")
        uploaded_file_content = b64encode(contents)

        # Flags for filename match and hash value match
        file_match = 0
        hash_match = 0

        # Iterate through the database for documents
        for document in my_database:
            # File Name Match
            if document['file_name'] == file_name:
                file_match = 1
                version_number = document['version_number']
                cloud_hashed_value = hashlib.md5(document['actual_content']).hexdigest()
                # Hash Value Match
                if cloud_hashed_value == hash_value:
                    hash_match = 1

        # If file name is not same.
        if file_match == 0:
            data = {
                    'file_name': file_name,
                    'hash_value': hash_value,
                    'version_number': 1,
                    'last_modified': last_modified,
                    'actual_content': contents,
                    '_attachments': {file_name: {'data': uploaded_file_content}}
                    }
            my_database.create_document(data)
            response = "File uploaded to Bluemix."
            return render_template('response.html', response=response)

        # If file name is same but contents are different.
        elif file_match == 1:
            if hash_match == 0:
                data = {'file_name': file_name,
                        'hash_value': hash_value,
                        'version_number': version_number + 1,
                        'last_modified': last_modified,
                        'actual_content': contents,
                        '_attachments': {file_name: {'data': uploaded_file_content}}
                        }
                my_database.create_document(data)
                response = "File uploaded with different version number since the file has same name with different contents."
                return render_template('response.html', response=response)
            
            # If filename is same and contents are same.
            else:
                response = "File with same name and same contents already exists."
                return render_template('response.html', response=response)

    return 'Error'


# Downloading the file.
@app.route('/download', methods=['POST'])
def download():
    if request.method == 'POST':
        # Gathering file information to download.
        file_name = request.form['filename']
        version_number = request.form['version']

        # Iterating through the database to find the file.
        for document in my_database:
            if document['file_name'] == file_name:
                if int(document['version_number']) == int(version_number):
                    file = document.get_attachment(file_name, attachment_type='binary')
                    response = make_response(file)
                    response.headers["Content-Disposition"] = "attachment; filename=%s" % file_name
                    return response

            else:
                response = 'File not found.'
                return render_template('response.html', response=response)

    return 'Error'


# Deleting the file.
@app.route('/delete', methods=['POST'])
def delete():
    if request.method == 'POST':
        # Gathering file information to download.
        file_name = request.form['filename']
        version_number = request.form['version']

        # Iterating through the database to find the file.
        for document in my_database:
            if document['file_name'] == file_name:
                if int(document['version_number']) == int(version_number):
                    document.delete()
                    response = "File Deleted."
                    return render_template('response.html', response=response)
            else:
                response = "File Not Found."
                return render_template('response.html', response=response)

    return 'Error'


# Listing the cloud files.
@app.route('/list_files', methods=['GET'])
def list_files():
    if request.method == 'GET':
        file_list = []
        for document in my_database:
            fileinfo = {}
            fileinfo['filename'] = document['file_name']
            fileinfo['version'] = document['version_number']
            fileinfo['last_modified'] = document['last_modified']
            file_list.append(fileinfo)
    return render_template('list.html', files=file_list)

port = os.getenv('VCAP_APP_PORT', '4500')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(port))
