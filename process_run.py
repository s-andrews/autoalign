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
import gzip
import pysam
import datetime
import time

# For the log file we want all output to be written immediately.
import sys
sys.stdout.reconfigure(write_through=True)

def main():
    job_id = sys.argv[1]

    if not job_id.isalpha():
        raise Exception(f"Invalid job id {job_id}")

    global config
    config = read_config()

    print(f"Started processing job {job_id} at {datetime.datetime.now()}", flush=True)

    # Get the execution folder now before we mess things up
    script_folder = Path(__file__).parent.resolve()
    
    # Move to the folder containing the job files

    print(f"Moving to job folder", flush=True)

    if not Path(config["data_folder"]+"/"+job_id).exists():
        raise Exception(f"Couldn't find job {job_id}")
    
    os.chdir(config["data_folder"]+"/"+job_id)

    output_dir = Path(config["output_folder"]+"/"+job_id)

    if output_dir.exists():
        raise Exception(f"Output dir already exists for {job_id}")

    # Create the output directory
    print(f"Making output folder", flush=True)
    output_dir.mkdir()

    # We should have a reference sequence file and
    # at least one, but potentially up to 5 fastq files of reads.
    # 
    # For now we assume the reference file is fasta.
    # There may be multiple fastq files of reads.
    # We'll assume for now that they're compressed.

    job_dir = Path(".")

    # We're going to create a bunch of files, some of
    # which will ultimately need to be moved to the 
    # output directory
    files_to_move = []

    # We always want the log file
    files_to_move.append(job_dir/"process_log.txt")

    reference_file = None
    annotation_file = None

    for extension in ["*.fa","*.FA","*.fasta","*.FASTA"]:
        file_list = list(job_dir.glob(extension))
        if file_list:
            reference_file=file_list[0]
            print(f"Found reference file{file_list[0].name}", flush=True)
            files_to_move.append(reference_file)
            break

    if reference_file is None:
        # We didn't find a fasta file, but they may have included
        # a genbank file instead which we can process and convert
        for extension in ["*.gb","*.GB","*.gbk","*.GBK"]:
            file_list = list(job_dir.glob(extension))
            if file_list:
                annotation_file=file_list[0]
                print(f"Found reference file{file_list[0].name}", flush=True)
                files_to_move.append(annotation_file)
                break

    if annotation_file is not None:
        reference_file = convert_reference_to_fasta(annotation_file)
        files_to_move.append(reference_file)

    if reference_file is None:
        raise Exception("Couldn't find fasta or genbank reference file")
    
    ## See if we need to reannotate the reference with plannotate
    if Path("reannotate.flag").exists():
        annotation_file = reannotate_file(reference_file)
        files_to_move.append(annotation_file)


    ## IGV is rubbish at displaying genbank reference files so we're going
    ## to convert to GFF3 which is better supported.
    if annotation_file is not None:
        annotation_file = convert_annotation_to_gff3(annotation_file)
        files_to_move.append(annotation_file)

    reference_index = index_reference(reference_file)
    files_to_move.append(reference_index)

    fastq_files = []
    for extension in ["*.fastq.gz","*.fastq","*.fq.gz","*.fq","*.FASTQ.GZ","*.FASTQ","*.FQ.GZ","*.FQ"]:
        file_list = list(job_dir.glob(extension))
        if file_list:
            for fastq_file in file_list:
                fastq_files.append(fastq_file)
                print(f"Found fastq file{fastq_file.name}", flush=True)


    if not fastq_files:
        raise Exception("Couldn't find fastq sequence file")

    if len(fastq_files) > 5:
        raise Exception("More than 5 fastq files found")

    aligned_files = []
    sorted_bam_files = []

    for fastq_file in fastq_files:
        print(f"Aligning {fastq_file.name} to {reference_file.name}", flush=True)
        bam_file = align_file(fastq_file,reference_file)
        print(f"Sorting {bam_file}", flush=True)
        sorted_bam, bam_index = sort_file(bam_file)
        sorted_bam_files.append(sorted_bam)
        files_to_move.append(sorted_bam)
        files_to_move.append(bam_index)
        aligned_files.append((sorted_bam,bam_index))

        # We were asked if we could make up a fastq file out of the reads which
        # didn't align to the reference
        print(f"Extracting unaligned reads from {bam_file}", flush=True)
        unaligned_reads = extract_unaligned_reads(fastq_file,bam_file)
        files_to_move.append(unaligned_reads)

    # Before we make the session file we're going to make a zip
    # file of everything we've made so far
    print(f"Creating zip file of all data", flush=True)
    zip_file = create_zip(job_id,files_to_move)
    files_to_move.append(zip_file)

    print(f"Making IGV session file", flush=True)
    session_file = create_session_file(reference_file,annotation_file,sorted_bam_files, job_id, script_folder)
    files_to_move.append(session_file)

    # Move the output files to the output directory
    for f in files_to_move:
        print(f"Moving {f} to output directory", flush=True)
        Path(f).rename(output_dir / f)

    # Remove the content of the processing directory - we don't need it any more
    os.chdir("..")
    print(f"Removing working directory", flush=True)
    for i in Path(job_id).iterdir():
        i.unlink()

    Path(job_id).rmdir()

    print(f"Finished processing job {job_id} at {datetime.datetime.now()}", flush=True)


def reannotate_file(file):
    # Uses plannotate to reannotate a reference file
    print(f"Reannotating reference with plannotate", flush=True)

    
    # We write to reannotated_temp.gbk initially because plannotate doesn't transfer over
    # the accession or version information so we don't get the correct name.
    command = ["conda","run","-n","plannotate","plannotate","batch","-i",str(file),"-f","reannotated_temp","-s",""]

    # Plannotate isn't super quick, but we want to put some limits on how long
    # we're going to let it run.  We'll therefore kill any processes which go
    # over 5 mins.

    try:
        subprocess.run(command, check=True, timeout=600)

    except subprocess.TimeoutExpired:
        print("Plannotate took more than 5 mins to run and was killed - it should have finished in this time", flush=True)
        sys.exit(1)

    # Now we need to get the id out of the fasta reference file
    with open(file,"rt",encoding="utf8") as infh:
        header = infh.readline()
        if not header.startswith(">"):
            raise Exception("Reference fasta didn't start with >")
        
        read_id = header.strip().split()[0][1:]

    with open("reannotated_temp.gbk","rt",encoding="utf8") as infh:
        with open("reannotated.gbk","wt",encoding="utf8") as out:
            for line in infh:
                if line.startswith("VERSION") or line.startswith("ACCESSION"):
                    line = line.replace(".",read_id)

                out.write(line)


    return Path("reannotated.gbk")


def extract_unaligned_reads(fastq_file,bam_file):

    # First go through the BAM file and remember all of the read
    # IDs which we saw

    bamfh = pysam.AlignmentFile(bam_file, "rb")

    aligned_read_ids = set()

    for read in bamfh.fetch(until_eof=True):
        aligned_read_ids.add(read.query_name)


    unaligned_reads=str(fastq_file)
    if unaligned_reads.lower().endswith(".gz"):
        unaligned_reads = unaligned_reads[:-3]

    unaligned_reads = ".".join(unaligned_reads.split(".")[:-1])+"_unaligned.fq.gz"
    
    with gzip.open(unaligned_reads,"wt",encoding="utf8") as unaligned_out:
        if str(fastq_file).lower().endswith(".gz"):
            fqfh = gzip.open(fastq_file,"rt",encoding="utf8")
        else:
            fqfh = open(fastq_file,"rt",encoding="utf8")


        for header in fqfh:
            thisid = header.strip().split()[0][1:]
            if not thisid in aligned_read_ids:
                unaligned_out.write(header)
                unaligned_out.write(fqfh.readline())
                unaligned_out.write(fqfh.readline())
                unaligned_out.write(fqfh.readline())
            else:
                fqfh.readline()
                fqfh.readline()
                fqfh.readline()

        fqfh.close()


    return unaligned_reads

def create_zip(job_id,files):

    zip_file = "aligned_files_"+job_id+".zip"
    zip_command= ["zip",zip_file]
    zip_command.extend(files)

    subprocess.run(zip_command, check=True)

    return zip_file

def create_session_file(reference,annotation,bam_files,job_id, script_folder):
    # Read in the template
    if annotation is None:
        # We're doing a straight fasta template
        template = script_folder / "webapp_session_template_fa.json"
    else:
        # We're using a genbank reference
        template = script_folder / "webapp_session_template_gff3.json"

    session_data = None
    with open(template,"rt",encoding="utf8") as templatein:
        session_data = json.load(templatein)

    # We need the sequence id out of the fasta file
    seqid = ""
    with open(reference,"rt",encoding="utf8") as infh:
        seqid = infh.readline().split()[0][1:]
    
    data_track_total_height = 650

    if annotation is not None:
        data_track_total_height = 500

    track_height = int(data_track_total_height/len(bam_files))

    # Update the template
    session_data["reference"]["fastaURL"] = config["output_url"]+job_id+"/"+reference.name
    session_data["reference"]["indexURL"] = config["output_url"]+job_id+"/"+reference.name+".fai"
    session_data["locus"] = seqid
    for i in range(1,6):
        if i>len(bam_files):
            del session_data["tracks"][len(bam_files)+1]
        else:
            session_data["tracks"][i]["url"] = config["output_url"]+job_id+"/"+bam_files[i-1]
            session_data["tracks"][i]["indexURL"] = config["output_url"]+job_id+"/"+bam_files[i-1]+".bai"
            session_data["tracks"][i]["filename"] = bam_files[i-1]
            session_data["tracks"][i]["name"] = bam_files[i-1][:-4]
            session_data["tracks"][i]["height"] = track_height

    if annotation is not None:
        session_data["tracks"][len(bam_files)+1]["url"] = config["output_url"]+job_id+"/"+annotation.name


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

    minimap_proc = subprocess.Popen(
        [config["minimap2"],"-ax","splice",reference.name,file.name], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.DEVNULL
    )
    subprocess.Popen(
        [config["samtools"],"view","-bS","-q","10","-o",bam_file], 
        stdin=minimap_proc.stdout
    )

    minimap_proc.stdout.close()

    try:
        minimap_proc.wait(timeout=60)

    except subprocess.TimeoutExpired:
        print(f"Minimap alignment of {file.name} to {reference.name} took more than 60 secs and was killed", file=sys.stderr, flush=True)
        sys.exit(1)

    return bam_file

def convert_reference_to_fasta(file):
    # This is called when we were given a genbank reference and we need to convert
    # this to fasta so that we can use it for minimap
    print(f"Converting reference to fasta", flush=True)

    outfile = file
    outfile = Path(".".join(str(file).split(".")[:-1])+".fa")

    SeqIO.convert(file, "genbank", outfile, "fasta")

    return outfile


def get_best_label(feature):
    """Choose the best label for IGV display."""
    q = feature.qualifiers

    for key in ["label", "gene", "locus_tag", "product", "note"]:
        if key in q:
            return feature.type + ": "+q[key][0]

    return feature.type


def convert_annotation_to_gff3(annotation_file):
    print(f"Converting reference features to GFF3", flush=True)

    gff_file = Path(str(annotation_file).replace(".gb","")+".gff3")
    print(f"Making {gff_file}", flush=True)

    with open(gff_file, "w") as out:
        out.write("##gff-version 3\n")

        for record in SeqIO.parse(annotation_file, "genbank"):

            seqid = record.id

            for i, feature in enumerate(record.features):

                if feature.location is None:
                    continue

                start = int(feature.location.start) + 1
                end = int(feature.location.end)
                strand = "+" if feature.location.strand == 1 else "-"

                ftype = feature.type

                if ftype == "source":
                    continue

                label = get_best_label(feature)
                fid = f"{ftype}_{i}"

                attributes = [
                    f"ID={fid}",
                    f"Name={label}"
                ]

                # also include gene/locus_tag if present
                if "gene" in feature.qualifiers:
                    attributes.append(f"gene={feature.qualifiers['gene'][0]}")

                if "locus_tag" in feature.qualifiers:
                    attributes.append(f"locus_tag={feature.qualifiers['locus_tag'][0]}")

                attr_string = ";".join(attributes)

                gff_line = "\t".join([
                    seqid,
                    "GenBank",
                    ftype,
                    str(start),
                    str(end),
                    ".",
                    strand,
                    ".",
                    attr_string
                ])

                out.write(gff_line + "\n")
    
    return gff_file


def read_config():
    config_file = Path(__file__).parent / "autoalign_conf.json"
    
    with open(config_file,"rt",encoding="utf8") as conf_fh:
        conf = json.load(conf_fh)

        return conf    


if __name__=="__main__":
    main()