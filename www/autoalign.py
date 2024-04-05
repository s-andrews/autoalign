#!/usr/bin/env python3

from flask import Flask, request, render_template, make_response
import random
from urllib.parse import quote_plus
from pathlib import Path
import json
import time

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")



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

