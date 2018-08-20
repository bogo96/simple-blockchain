$(document).ready(function () {
    console.log("load");
    var walletAddr;

    $.get('/getAddr',function (response) {
        console.log(response)
        walletAddr = response.pubkey;
        $('#addr').text("address: "+walletAddr);
        console.log(walletAddr);
    });


});