function checkInt() {
    let x = document.getElementById("shares").value;
    x = Number(x);
    if (Number.isInteger(x)) {
        document.getElementById("buybtn").disabled = false;
        document.getElementById("errormsg").innerHTML = "";
    }
    else {
        document.getElementById("errormsg").innerHTML = "Please only enter whole numbers!";
    } 
}