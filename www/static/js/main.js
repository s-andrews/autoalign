$( document ).ready(function() {
    console.log("Setting up")
    $("#reference").change(check_files)
    $("#fastq").change(check_files)

    $("#align").prop("disabled",true)
});

function check_files(){
    let allgood = true

    // Check the reference
    let reffile = $("#reference").val()
    if (reffile) {
        if (! (reffile.toLowerCase().endsWith(".fa") | reffile.toLowerCase().endsWith(".fasta"))) {
            allgood = false
            $("#reference_error").text("File did not look like fasta (.fa or .fasta)")
            $("#reference_error").show()
        }
        else {
            $("#reference_error").hide()
        }
    }
    else {
        allgood = false
    }

    // Check the fastq
    let fastqfile = $("#fastq").val()
    if (fastqfile) {
        if (! (fastqfile.toLowerCase().endsWith(".fq.gz") | fastqfile.toLowerCase().endsWith(".fastq.gz") | fastqfile.toLowerCase().endsWith(".fq") | fastqfile.toLowerCase().endsWith(".fastq"))) {
            allgood = false
            $("#fastq_error").text("File did not look like fastq (.fq.gz fastq.gz fq or .fastq)")
            $("#fastq_error").show()
        }
        else {
            $("#fastq_error").hide()
        }
    }
    else {
        allgood = false
    }

    if (allgood) {
        $("#align").prop("disabled",false)
    }
    else {
        $("#align").prop("disabled",true)
    }


}
