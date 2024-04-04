#!/usr/bin/env python3

# This script takes a folder id from the upstream web service and 
# runs the alignment and indexing and then makes the config files
# for IGV

import sys
from pathlib import Path
import subprocess
import json
import os

def main():
    job_id = sys.argv[1]

    if not job_id.isalpha():
        raise Exception(f"Invalid job id {job_id}")

    global config
    config = read_config()
    
    # Move to the folder containing the job files
    if not Path(config["data_folder"]+"/"+job_id).exists():
        raise Exception(f"Couldn't find job {job_id}")
    
    os.chdir(config["data_folder"]+"/"+job_id)

    output_dir = Path(config["output_folder"]+"/"+job_id)

    if output_dir.exists():
        raise Exception(f"Output dir already exists for {job_id}")

    # Create the output directory
    output_dir.mkdir()

    # We should have a reference sequence file and
    # a fastq file of reads.
    # 
    # For now we assume the reference file is fasta.
    # There may be multiple fastq files of reads.
    # We'll assume for now that they're compressed.

    job_dir = Path(".")

    # We're going to create a bunch of files, some of
    # which will ultimately need to be moved to the 
    # output directory
    files_to_move = []

    reference_file = list(job_dir.glob("*.fa"))[0]
    files_to_move.append(reference_file)

    reference_index = index_reference(reference_file)
    files_to_move.append(reference_index)


    fastq_files = job_dir.glob("*fastq.gz")

    aligned_files = []

    for file in fastq_files:
        bam_file = align_file(file,reference_file)
        sorted_bam, bam_index = sort_file(bam_file)
        files_to_move.append(sorted_bam)
        files_to_move.append(bam_index)
        aligned_files.append((sorted_bam,bam_index))

    # Move the output files to the output directory
    for f in files_to_move:
        Path(f).rename(output_dir / f)
    


def index_reference(file):
    index_file = file.name + ".fai"
    subprocess.run([config["samtools"],"faidx",file], check=True)

    return index_file


def sort_file(bam):
    sorted_bam = bam.replace(".bam","_sorted.bam")
    bam_index = sorted_bam+".bai"

    subprocess.run([config["samtools"],"sort",bam,"-o",sorted_bam], check=True)

    subprocess.run([config["samtools"],"index",sorted_bam], check=True)

    return sorted_bam, bam_index

def align_file(file,reference):

    bam_file = file.name.replace("fastq.gz","bam")

    minimap_proc = subprocess.Popen([config["minimap2"],"-ax","splice",reference.name,file.name], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    subprocess.run([config["samtools"],"view","-bS","-q","10","-o",bam_file], stdin=minimap_proc.stdout)
    minimap_proc.wait()

    return bam_file


def read_config():
    config_file = Path(__file__).parent / "autoalign_conf.json"
    
    with open(config_file,"rt",encoding="utf8") as conf_fh:
        conf = json.load(conf_fh)

        return conf    


if __name__=="__main__":
    main()