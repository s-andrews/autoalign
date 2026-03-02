$( document ).ready(function() {
    console.log("Setting up")
    $("#reference").change(check_files)
    $(".fastq").change(check_files)

    $("#align").prop("disabled",true)
    $("#align").css("background-color","lightgrey")
    $("#align").css("border-color","lightgrey")

    $("#align").click(align_pressed)

    $("#moreseq").click(add_more_sequences)

});

function add_more_sequences() {

    // We need to find how many sequences are still available
    let nextfq = 6 - $("input.fqhidden").length

    // Make these visible
    $("#fqlabel"+nextfq).removeClass("fqhidden")
    $("#fastq"+nextfq).removeClass("fqhidden")
    $("#fastq_error"+nextfq).removeClass("fqhidden")

    if (nextfq == 5) {
        $("#moreseq").hide()
    }

    return(false)

}


function align_pressed() {
    $("#align").css("background-color","lightgrey")
    $("#align").css("border-color","lightgrey")
    $("#align").html("<span class=\"spinner-border spinner-border-sm\" aria-hidden=\"true\"></span> Running Alignment")
}


function check_files(){
    console.log("Checking files")
    let allgood = true

    // Check the reference
    let reffile = $("#reference").val()
    if (reffile) {
        if (! (reffile.toLowerCase().endsWith(".fa") | reffile.toLowerCase().endsWith(".fasta") | reffile.toLowerCase().endsWith(".gb") | reffile.toLowerCase().endsWith(".gbk"))) {
            allgood = false
            $("#reference_error").text("File did not look like fasta (.fa or .fasta) or genbank (.gb or .gbk)")
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

    // Check the fastq files - there may be up to 5
    let good_fastq = false

    let seen_names = []

    for (let i=1;i<=5;i++) {
        let fastqfile = $("#fastq"+i).val()
        if (fastqfile) {
            if (! (fastqfile.toLowerCase().endsWith(".fq.gz") | fastqfile.toLowerCase().endsWith(".fastq.gz") | fastqfile.toLowerCase().endsWith(".fq") | fastqfile.toLowerCase().endsWith(".fastq"))) {
                allgood = false
                $("#fastq_error"+i).text("File did not look like fastq (.fq.gz fastq.gz fq or .fastq)")
                $("#fastq_error"+i).show()
            }
            else {            
                // The name is OK, how about the size
                if ($("#fastq"+i)[0].files[0].size > (1024 * 1024 * 10)) {
                    allgood = false
                    $("#fastq_error"+i).text("Fastq file is too big (10MB max)")
                    $("#fastq_error"+i).show()    
                } 
                else {

                    // Check for duplicate names
                    if (seen_names.includes(fastqfile)) {
                        allgood = false
                        $("#fastq_error"+i).text("Duplicate file name")
                        $("#fastq_error"+i).show()    
                    }
                    else {
                        seen_names.push(fastqfile)
                        $("#fastq_error"+i).hide()
                        good_fastq = true
                    }
                }
            }
        }
    }

    if (!good_fastq) {
        // There are no fastq files selected
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
