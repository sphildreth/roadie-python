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

    function downloadRelease(url) {
        var frameName = "downloader";
        var element = document.getElementById(frameName);
        if(!element) {
            element = document.createElement("iframe");
            element.setAttribute('id', frameName);
            document.body.appendChild(element);
        }
        element.setAttribute('src', url);
    };

    function playLoader(url) {
        var frameName = "playlistloader";
        var element = document.getElementById(frameName);
        if(!element) {
            element = document.createElement("iframe");
            element.setAttribute('id', frameName);
            document.body.appendChild(element);
        }
        element.setAttribute('src', url);
    };

    return {
        lpad : lpad,
        playLoader: playLoader,
        showSuccessMessage: showSuccessMessage,
        showErrorMessage: showErrorMessage,
        downloadRelease: downloadRelease
    };

} )( window );