#!/usr/bin/env python3

# This script takes a folder id from the upstream web service and 
# runs the alignment and indexing and then makes the config files
# for IGV

import sys
from pathlib import Path
import subprocess
import json
import os
from Bio import SeqIO

def main():
    job_id = sys.argv[1]

    if not job_id.isalpha():
        raise Exception(f"Invalid job id {job_id}")

    global config
    config = read_config()

    # Get the execution folder now before we mess things up
    script_folder = Path(__file__).parent.resolve()
    
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

    reference_file = None
    annotation_file = None

    for extension in ["*.fa","*.FA","*.fasta","*.FASTA"]:
        file_list = list(job_dir.glob(extension))
        if file_list:
            reference_file=file_list[0]
            files_to_move.append(reference_file)
            break

    if reference_file is None:
        # We didn't find a fasta file, but they may have included
        # a genbank file instead which we can process and convert
        for extension in ["*.gb","*.GB","*.gbk","*.GBK"]:
            file_list = list(job_dir.glob(extension))
            if file_list:
                annotation_file=file_list[0]
                files_to_move.append(annotation_file)
                break

    if annotation_file is not None:
        reference_file = convert_reference(annotation_file)
        files_to_move.append(reference_file)

    if reference_file is None:
        raise Exception("Couldn't find fasta or genbank reference file")

    reference_index = index_reference(reference_file)
    files_to_move.append(reference_index)

    fastq_file = None
    for extension in ["*.fastq.gz","*.fastq","*.fq.gz","*.fq","*.FASTQ.GZ","*.FASTQ","*.FQ.GZ","*.FQ"]:
        file_list = list(job_dir.glob(extension))
        if file_list:
            fastq_file = file_list[0]

    if fastq_file is None:
        raise Exception("Couldn't find fastq sequence file")


    aligned_files = []

    bam_file = align_file(fastq_file,reference_file)
    sorted_bam, bam_index = sort_file(bam_file)
    files_to_move.append(sorted_bam)
    files_to_move.append(bam_index)
    aligned_files.append((sorted_bam,bam_index))

    # Before we make the session file we're going to make a zip
    # file of everything we've made so far
    zip_file = create_zip(job_id,files_to_move)
    files_to_move.append(zip_file)


    session_file = create_session_file(reference_file,annotation_file,sorted_bam, job_id, script_folder)
    files_to_move.append(session_file)

    # Move the output files to the output directory
    for f in files_to_move:
        Path(f).rename(output_dir / f)

    # Remove the content of the processing directory - we don't need it any more
    os.chdir("..")
    for i in Path(job_id).iterdir():
        i.unlink()

    Path(job_id).rmdir()

def create_zip(job_id,files):

    zip_file = "aligned_files_"+job_id+".zip"
    zip_command= ["zip",zip_file]
    zip_command.extend(files)

    subprocess.run(zip_command, check=True)

    return zip_file

def create_session_file(reference,annotation,bam,job_id, script_folder):
    # Read in the template
    if annotation is None:
        # We're doing a straight fasta template
        template = script_folder / "webapp_session_template_fa.json"
    else:
        # We're using a genbank reference
        template = script_folder / "webapp_session_template_gbk.json"

    session_data = None
    with open(template,"rt",encoding="utf8") as templatein:
        session_data = json.load(templatein)

    # We need the sequence id out of the fasta file
    seqid = ""
    with open(reference,"rt",encoding="utf8") as infh:
        seqid = infh.readline().split()[0][1:]

    # Update the template
    session_data["reference"]["fastaURL"] = config["output_url"]+job_id+"/"+reference.name
    session_data["reference"]["indexURL"] = config["output_url"]+job_id+"/"+reference.name+".fai"
    session_data["locus"] = seqid
    session_data["tracks"][1]["url"] = config["output_url"]+job_id+"/"+bam
    session_data["tracks"][1]["indexURL"] = config["output_url"]+job_id+"/"+bam+".bai"
    session_data["tracks"][1]["filename"] = bam
    session_data["tracks"][1]["name"] = bam[:-4]

    if annotation is not None:
        session_data["tracks"][2]["url"] = config["output_url"]+job_id+"/"+annotation.name


    session_file = "igv_session.json"

    with open(session_file,"wt", encoding="utf8") as out:
        json.dump(session_data,out)

    return session_file

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

    sections = file.name.split(".")
    bam_file = None
    for i,v in enumerate(sections):
        if v.lower() == "fq" or v.lower() == "fastq":
            bam_file = ".".join(sections[0:i])+".bam"

    minimap_proc = subprocess.Popen([config["minimap2"],"-ax","splice",reference.name,file.name], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    subprocess.run([config["samtools"],"view","-bS","-q","10","-o",bam_file], stdin=minimap_proc.stdout)
    minimap_proc.wait()

    return bam_file

def convert_reference(file):
    # This is called when we were given a genbank reference and we need to convert
    # this to fasta so that we can use it for minimap
    outfile = file
    outfile = Path(".".join(str(file).split(".")[:-1])+".fa")

    SeqIO.convert(file, "genbank", outfile, "fasta")

    return outfile


def read_config():
    config_file = Path(__file__).parent / "autoalign_conf.json"
    
    with open(config_file,"rt",encoding="utf8") as conf_fh:
        conf = json.load(conf_fh)

        return conf    


if __name__=="__main__":
    main()