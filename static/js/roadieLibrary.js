var roadieLibrary = ( function( window, undefined ) {

    function lpad(n, width, z) {
        z = z || '0';
        n = n + '';
        if(n == 'null') {
            n = '';
        }
        return n.length >= width ? n : new Array(width - n.length + 1).join(z) + n;
    };

    function showErrorMessage(message) {
        $.bootstrapGrowl(message, {
            type: 'danger'
        });
    };

    function showSuccessMessage(message) {
        $.bootstrapGrowl(message, {
            type: 'success'
        });
    };

    return {
        lpad : lpad,
        showSuccessMessage: showSuccessMessage,
        showErrorMessage: showErrorMessage
    };

} )( window );