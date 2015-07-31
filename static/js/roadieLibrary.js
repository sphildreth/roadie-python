var roadieLibrary = ( function( window, undefined ) {

    function lpad(n, width, z) {
        z = z || '0';
        n = n + '';
        if(n == 'null') {
            n = '';
        }
        return n.length >= width ? n : new Array(width - n.length + 1).join(z) + n;
    };

    return {
        lpad : lpad
    };

} )( window );