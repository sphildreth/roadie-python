var roadieLibrary = (function(window, undefined) {
    function lpad(n, width, z) {
        z = z || '0';
        n = n + '';
        if (n == 'null') {
            n = '';
        }
        return n.length >= width ? n : new Array(width - n.length +
            1).join(z) + n;
    };

    function showErrorMessage(message) {
        $(".loader").hide();
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
        if (!element) {
            element = document.createElement("iframe");
            element.setAttribute('id', frameName);
            document.body.appendChild(element);
        }
        element.setAttribute('src', url);
    };

    function playLoader(url, html) {
        var width = 750;
        var height = 265;
        if (window.user.doUseHTMLPlayer) {
            url = url || "about:blank";
            var win = window.open(url, 'roadiePlayer',
                'toolbar=no,location=no,status=no,menubar=no,scrollbars=no,resizable=yes,width=' +
                width + ',height=' + height);
            if (html) {
                win.document.open();
                win.document.write(html);
                win.document.close();
            }
        } else {
            var frameName = "playlistloader";
            var element = document.getElementById(frameName);
            if (!element) {
                element = document.createElement("iframe");
                element.setAttribute('id', frameName);
                document.body.appendChild(element);
            }
            element.setAttribute('src', url);
        }
    };
    return {
        lpad: lpad,
        playLoader: playLoader,
        showSuccessMessage: showSuccessMessage,
        showErrorMessage: showErrorMessage,
        downloadRelease: downloadRelease
    };
})(window);