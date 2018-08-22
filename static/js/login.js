
$(document).ready(function () {
    console.log("load");
    var walletAddr;
    console.log(walletAddr);

    $('#privkeySubmit').click(()=> {
        var keyword = $('#privkey').val();

        $.post('/login', { keyword : keyword }, function (response) {
            walletAddr = response.pubkey;
            $('#addr').text("address: "+walletAddr);
        });
    });




});