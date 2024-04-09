#!/usr/bin/env python3

# This script goes through the folders in the input and output directories
# and removes anything which is more than a week old.

from pathlib import Path
import json
import datetime
import shutil

# We need to get the location of the input and output directories from
# the config file
conf_location = Path(__file__).parent / "autoalign_conf.json"

with open(conf_location,"rt", encoding="utf8") as conffh:
    conf = json.load(conffh)

# Our input deletion cutoff is just 1 day since nothing should
# persist there
cutoff = datetime.datetime.now() - datetime.timedelta(days=1)
print("Input Deletion cutoff is ",cutoff)

# Now go through the two folders cleaning stuff up
for folder in Path(conf["data_folder"]).iterdir():
    if folder.is_dir():
        creation_time = datetime.datetime.fromtimestamp(folder.stat().st_ctime)
        if creation_time < cutoff:
            print("Deleting ",folder,"from",creation_time)
            # Delete it all
            shutil.rmtree(folder)

# Our output deletion cutoff is 7 days since that's where the
# final output resides
cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
print("Output Deletion cutoff is ",cutoff)

for folder in Path(conf["output_folder"]).iterdir():
    if folder.is_dir():
        creation_time = datetime.datetime.fromtimestamp(folder.stat().st_ctime)
        if creation_time < cutoff:
            print("Deleting ",folder,"from",creation_time)
            # Delete it all
            shutil.rmtree(folder)
