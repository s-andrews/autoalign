<img src="../main/www/static/images/autoalign_path.svg?raw=true" alt="AutoAlign Logo" width="100%">

Introduction
============

The validation of sequencing constructs used to be performed using Sanger sequencing.  More recently small scale Nanopore sequencing has been used instead, producing small fastq files from a single amplified PCR product, or plasmid.

This tool provides a simple way to align these small scale sequencing runs to a custom refernece sequence, most commonly the expected sequence of the construct.

The program here will undertake the following operations

1. Generate a fasta index file from the reference sequence
2. Align each fastq file to the reference using minimap2
3. Sort and index the BAM files produced using samtools
4. Place the resulting files in a web-accesible directory
5. Create an IGV config file which will open a session to view the alignments


Using Auto Align
================

You can use the publicly hosted version of auto align at https://www.bioinformatics.babraham.ac.uk/autoalign/

<img src="../main/www/static/images/auto_align_input_form.png?raw=true" alt="Input Form Screenshot" width="100%">


The results of the program are shown in IGV-Web.  You can see more details about the contols within this viewer in the [IGV Web Manual](https://igvteam.github.io/igv-webapp/)


<img src="../main/www/static/images/example_alignment.png?raw=true" alt="Example Alignment" width="100%">

You can see a quick run though of using the program below.

[![AutoAlign video](../main/www/static/images/autoalign_screen.png?raw=true)](https://youtu.be/rz4Rcym_wxo?si=q_c7tNvVtKEKyu3g)

Hosting your own copy of Auto Align
===================================

If you prefer you can install AutoAlign on your own server.  Alignments will be performed locally and hosted on your machine.  Because of the link to the IGV web app the results of the alignments must be hosted on a site which is generally available on the internet - you can't put this behind a firewall.  If you only want to be able to download the data or use it on a private copy of IGV behind your firewall then this will still work though.

Install a base operating system
-------------------------------

The instructions here are based on an [AlmaLinux 9](https://almalinux.org/) base operating system, although they should work identically for any other RHEL9 clone such as [Rocky Linux](https://rockylinux.org/).  Instructions for other linux distributions should be largely similar but there may be some differences.

The requirements for the base OS are:

```
httpd
python3
zip
```

I'm assuming that your apache(httpd) is already installed and running.

Clone the autoalign repository
------------------------------

Pick a location into which your want to install the code (```/srv/``` would be a good choice) and then clone the repository to that location with

```
git clone https://github.com/s-andrews/autoalign.git
```

Install the additional packages needed
--------------------------------------

In addition to the base operating system autoalign needs you to install two additional pieces of software

1. [Samtools](http://www.htslib.org/download/)
2. [Minimap2](https://github.com/lh3/minimap2)

You can install these anywhere on your system as their location will be in the configuration file you set up.  Install instructions for each of the packages is contained within the links above.



Create a python virtual environment
-----------------------------------

From within the cloned repository folder run:

```
python3 -m venv venv
source venc/bin/activate
pip3 install -r requirements.txt
```

Install pLannotate
------------------

We have the option to reannotate reference sequences with [pLannotate](https://github.com/mmcguffi/pLannotate) which can automatically annotate reference sequences with common structures found in plasmids.

Installation happens in two steps:

### Install conda via conda-forge
Since pLannotate is only available via conda so we first need to install conda via [miniforge](https://conda-forge.org/download/)

Running the script there will walk you through the installation. You don't want to initialise conda by default (it will ask about this).

### Install the pLannotate environment
Once conda is installed and working you can install pLannotate using

```conda create -n plannotate -c conda-forge -c bioconda plannotate```

You need to do this as the user who will be running the system so the environment is available to them.

Once the environment has installed you can check that it's working with 

```conda run -n plannotate plannotate batch --help```

If that works then you're all good.


Create your config file
-----------------------

The details of the hosting of your site are contained within the ```autoalign_conf.json``` file in the top folder of the repository.  Edit the values in this file to match the details of your installation.

You will need to provide two folders on your system to hold the data the project creates.  One is for the initial upload, and the second is where the results are served from.  These folders will need to be writeable by whichever user you use to run the program (please don't run it as root - a normal user will work just fine.)


Edit your apache configuration
------------------------------

You need to install a configuration file so that apache knows how to access your system and how to serve the results the program generates.  An example apache conf file is provided in ```autoalign.conf```.  You will need to edit this file to add the actual location from which you will be serving your results files.  The system is set up so that the main inteface is served from ```https://yourdomain.com/autoalign/``` and that results come from ```https://yourdomain.com/autoalign_results/```.  If you want to change this you will need to adjust the configuration file accordingly.  The conf file also assumes that the autoalign web app will be running on local port 5002.  If you need to use a different port you can change the port number in this file also.

Once you have edited the file to match your local setup you can install it by copying it to ```/etc/httpd/conf.d/```, and then restarting your web server with ```systemctl restart httpd```.


Install the cron cleanup script
-------------------------------

To do the cleanup you need to put the ```cron_clean_up.py``` script into your cron schedule.  It doesn't really matter when it runs.  It will delete all input folders older than 1 day and all output folders older than 1 week.  You should run it from its location in the repository since it needs to find the configuration file.  You can use ```crontab -e``` as the user you're running the system as and then install the job as follows:

```
0       2       *       *       *       /srv/autoalign/cron_clean_up.py
```

That will run the clean up at 2am each day.



Start your web app
------------------

Once the application is installed you can start it by starting the python venv, and then running the flask application.

```
cd /srv/autoalign
source venv/bin/activate
cd www
nohup waitress-serve --host 127.0.0.1 --url-prefix="/autoalign/" --port 5002 autoalign:app > /dev/null &
```

You should now be able to access the application at ```https://yourdomain.com/autoalign/```











