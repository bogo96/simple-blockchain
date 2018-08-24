$(document).ready(function () {
    console.log("load");
    var walletAddr, amount;

    $.get('/getInfo',function (response) {
        walletAddr = response.wallet;
        amount = response.amount;
        // var my_transaction = response.transactions;

        $('#addr').text(walletAddr);
        $('#money').text(amount);
        $('#money').attr('max',amount);

        // for (var i=0;i<my_transaction.count;i++) {
        //     console.log(my_transaction[i]);
        //     var sender = document.createElement("tr");
        //     var receiver = document.createElement("tr");
        //     var money = document.createElement("tr");
        //     sender.appendChild(my_transaction[i]['sender']);
        //     receiver.appendChild(my_transaction[i]['recipient']);
        //     money.appendChild(my_transaction[i]['amount']);
        //     $('#receipt').appendChild(sender);
        //     $('#receipt').appendChild(receiver);
        //     $('#receipt').appendChild(money);
        // }

        console.log(walletAddr);
        console.log(amount);
    });

    $('#send').click(()=> {
        var sendMoney = $('#amount').val();
        var recipient = $('#recipient').val();

        console.log(sendMoney)
        console.log(recipient)

        $.post('/transactions/new', { sender: walletAddr, recipient : recipient, amount: sendMoney }, function (response) {
            $('#alert').text("reload after 30seconds");
            console.log("success");
        });

    });


});