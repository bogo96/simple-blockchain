$(document).ready(function () {
    var walletAddr, amount;

    $.get('/info',function (response) {
        walletAddr = response.wallet;
        amount = response.amount;

        $('#addr').text(walletAddr);
        $('#money').text(amount);
        $('#money').attr('max',amount);

    });

    $('#send').click(()=> {
        var sendMoney = $('#amount').val();
        var recipient = $('#recipient').val();

        $.post('/transactions/new', { sender: walletAddr, recipient : recipient, amount: sendMoney }, function (response) {
            $('#alert').text("reload after 30seconds");
        });

    });


});