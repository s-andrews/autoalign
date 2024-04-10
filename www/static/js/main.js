$( document ).ready(function() {
    console.log("Setting up")
    $("#reference").change(check_files)
    $("#fastq").change(check_files)

    $("#align").prop("disabled",true)
    $("#align").css("background-color","lightgrey")
    $("#align").css("border-color","lightgrey")

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
            // The name is OK, how about the size
            if ($("#reference")[0].files[0].size > (1024 * 1024 * 2)) {
                allgood = false
                $("#reference_error").text("Reference is too big (2MB max)")
                $("#reference_error").show()    
            } 
            else {
                $("#reference_error").hide()
            }
        }
    }
    else {
        // They haven't provided this file yet
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
            // The name is OK, how about the size
            if ($("#fastq")[0].files[0].size > (1024 * 1024 * 4)) {
                allgood = false
                $("#fastq_error").text("Fastq file is too big (4MB max)")
                $("#fastq_error").show()    
            } 
            else {
                $("#fastq_error").hide()
            }
        }
    }
    else {
        allgood = false
    }

    if (allgood) {
        $("#align").prop("disabled",false)
        $("#align").css("background-color","green")
        $("#align").css("border-color","green")

    }
    else {
        $("#align").prop("disabled",true)
        $("#align").css("background-color","lightgrey")
        $("#align").css("border-color","lightgrey")
    }


}
