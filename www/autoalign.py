#!/usr/bin/env python3

from flask import Flask, request, render_template, make_response, redirect, url_for
from werkzeug.utils import secure_filename
import random
from urllib.parse import quote_plus
from pathlib import Path
import json
import subprocess

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start_alignment", methods=["GET","POST"])
def start_alignment():

    # Let's make a folder to send the data to
    run_id = generate_id(20)

    output_path = Path(server_conf["data_folder"])/run_id

    if output_path.exists():
        raise Exception("Run ID already exists, what are the chances of that.")
    
    output_path.mkdir()
    

    files = request.files
    reference = files["reference"]
    fastq = files["fastq"]

    reference_filename = secure_filename(reference.filename)
    reference.save(output_path / reference_filename)

    fastq_filename = secure_filename(fastq.filename)
    fastq.save(output_path / fastq_filename)

    subprocess.run(["../process_run.py",run_id], check=True)

    return redirect(url_for("view_results/"+run_id))


@app.route("/view_results/<job_id>")
def view_results(job_id):

    fileit = (Path(server_conf["output_folder"]) / job_id).iterdir()
    files = []

    for file in fileit:
        files.append(file.name)

    return render_template("results.html", job_id=job_id, files=files, baseurl=server_conf["output_url"])

def get_form():
    if request.method == "GET":
        return request.args

    elif request.method == "POST":
        return request.form


def generate_id(size):
    """
    Generic function used for creating IDs.  Makes random IDs
    just using uppercase letters

    @size:    The length of ID to generate

    @returns: A random ID of the requested size
    """
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    code = ""

    for _ in range(size):
        code += random.choice(letters)

    return code



def jsonify(data):
    # This is a function which deals with the bson structures
    # specifically ObjectID which can't auto convert to json 
    # and will make a flask response object from it.
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'

    return response

def get_server_configuration():
    with open(Path(__file__).resolve().parent.parent / "autoalign_conf.json") as infh:
        conf = json.loads(infh.read())
    return conf



# Read the main configuration
server_conf = get_server_configuration()

