Automatic alignment of small nanopore runs
==========================================

The validation of sequencing constructs used to be performed using Sanger sequencing.  More recently small scale Nanopore sequencing has been used instead, producing small fastq files from a single amplified PCR product, or plasmid.

This tool provides a simple way to align these small scale sequencing runs to a custom refernece sequence, most commonly the expected sequence of the construct.

The program here will undertake the following operations

1. Generate a fasta index file from the reference sequence
2. Align each fastq file to the reference using minimap2
3. Sort and index the BAM files produced using samtools
4. Place the resulting files in a web-accesible directory
5. Create an IGV config file which will open a session to view the alignments


