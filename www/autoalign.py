#!/usr/bin/env python3

from flask import Flask, request, render_template, make_response, redirect, url_for
from werkzeug.utils import secure_filename
import random
from urllib.parse import quote_plus
from pathlib import Path
import json
import subprocess

app = Flask(__name__)
# Restrict total request size to 20MB.  We allow 2MB for the
# reference and 4MB for the fastq so this should be plenty
# for the total payload
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024


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

    fastqs = []
    for i in range(1,5):
        if f"fastq{i}" in files and files[f"fastq{i}"].filename:
            fastqs.append(files[f"fastq{i}"])

    plannotate = "plannotate" in get_form() and get_form()["plannotate"]


    if plannotate:
        with open(output_path/"reannotate.flag","wt",encoding="utf8"):
            pass

    reference_filename = secure_filename(reference.filename)
    reference.save(output_path / reference_filename)

    for fastq in fastqs:
        fastq_filename = secure_filename(fastq.filename)
        fastq.save(output_path / fastq_filename)


    # We want to launch the process to do the analysis. We're 
    # using a shell wrapper so that we can send all output into
    # a log file, and we can write the exit code to a file once
    # the process completes.

    subprocess.Popen(
        [
            "bash",
            "-c",
            f"PYTHONUNBUFFERED=1 ../process_run.py {run_id} > {str(output_path/'process_log.txt')} 2>&1; echo $? > {str(output_path/'exit_code.txt')}"
        ],
        stdout = subprocess.DEVNULL,
        stderr = subprocess.DEVNULL,
        start_new_session = True
    )

    # We send them straight to the results viewing route.  Inside there
    # we'll have to figure out if the processing has finished or if 
    # something went wrong.

    return redirect(url_for("view_results",job_id=run_id))


@app.route("/view_results/<job_id>")
def view_results(job_id):

    # When this function is called the analysis may or may not have
    # actually finished.  We'll check the job folder for some key
    # files to see if it worked or not.

    # Since we're showing all of the results in a given folder we
    # need to be careful about a traversal attack.  The job id 
    # should just be a bunch of uppercase letters
    if not (job_id.isalpha() and job_id.isupper()):
        # This doesn't look like a valid job id so don't even try to do anything with it.
        return render_template("error.html",error="This doesn't look like a valid job id")

    # We could have data in the processing folder or the output folder

    process_folder = (Path(server_conf["data_folder"]) / job_id)

    output_folder = (Path(server_conf["output_folder"]) / job_id)

    if not (process_folder.exists() or output_folder.exists()):
        # There's no job with this ID.  Send them a sensible message
        return render_template("error.html",error="Couldn't find this job.\nJobs are deleted after a week so you might need to rerun the alignment")


    # If the process folder is still there then either the job is still running
    # or it failed.

    if process_folder.exists():

        # We want the text from the log whatever happens
        log_file = process_folder / "process_log.txt"

        log_text = "Nothing in the log file yet..."

        if log_file.exists():
            log_text = ""

            with open(log_file,"rt", encoding="utf8") as infh:
                for line in infh:
                    log_text += line


        # We need to determine if it finished, or crashed.
        exit_code_file = process_folder / "exit_code.txt"
        if not exit_code_file.exists():
            # It hasn't started yet or is still running
            return render_template("running.html",log=log_text)

        # We can try to read what's in the exit code file
        with open(exit_code_file,"rt",encoding="utf8") as infh:
            exit_code = infh.readline().strip()

            if exit_code and exit_code != "0":
                # It crashed
                return render_template("error.html", error=log_text)
            
            else:
                # It looks like it's still running
                return render_template("running.html",log=log_text)
            
    # If we get here then the job is finished, so we'll just output the results

    fileit = output_folder.iterdir()
    files = []

    zip_file = None

    for file in fileit:
        if file.name.endswith(".zip"):
            zip_file = file.name
        else:
            files.append(file.name)

    return render_template("results.html", job_id=job_id, files=files, zip=zip_file, baseurl=server_conf["output_url"])

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

