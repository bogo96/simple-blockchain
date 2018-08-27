
$(document).ready(function () {
    var walletAddr;

    $('#privkeySubmit').click(()=> {
        var keyword = $('#privkey').val();

        $.post('/login', { keyword : keyword }, function (response) {
            walletAddr = response.pubkey;
            $('#addr').text("address: "+walletAddr);
        });
    });




});