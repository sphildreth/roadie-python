var roadieLibrary = (function(window, undefined) {
    function lpad(n, width, z) {
        z = z || '0';
        n = n + '';
        if (n == 'null') {
            n = '';
        }
        return n.length >= width ? n : new Array(width - n.length +
            1).join(z) + n;
    }

    function showErrorMessage(message) {
        $(".loader").hide();
        $.bootstrapGrowl(message, {
            type: 'danger'
        });
    }

    function showSuccessMessage(message) {
        $.bootstrapGrowl(message, {
            type: 'success'
        });
    }

    function downloadRelease(url) {
        var frameName = "downloader";
        var element = document.getElementById(frameName);
        if (!element) {
            element = document.createElement("iframe");
            element.setAttribute('id', frameName);
            document.body.appendChild(element);
        }
        element.setAttribute('src', url);
    }

    function playLoader(url, html) {
        var width = 750;
        var height = 450;
        if (window.user.doUseHtmlPlayer) {
            window.open(url, 'roadiePlayer');
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
    }

    function doInternetSearch(searchFor) {
        var url = "https://www.google.com/search?q=" + encodeURIComponent(searchFor);
        window.open(url, "_blank");
    }

    function deleteSelectedReleases(selectedReleases,doPurge) {
        $.ajax({
            type: 'POST',
            url: '/release/deleteselected/' + doPurge,
            data: { "selected": selectedReleases.join(",") },
            success: function(data) {
                if(data.message == "OK") {
                    location.reload(true);
                }
            },
            error:function(jq, st, error){
                roadieLibrary.showErrorMessage(error);
            }
        });
    }

    function rescanSelectedReleases(selectedReleases) {
        $(".loader").fadeIn("slow", function() {
            $.ajax({
                type: 'POST',
                url: '/release/rescanselected',
                data: {"selected": selectedReleases.join(",")},
                success: function (data) {
                    if (data.message == "OK") {
                        location.reload(true);
                    }
                },
                error: function (jq, st, error) {
                    roadieLibrary.showErrorMessage(error);
                }
            });
        });
    }

    return {
        lpad: lpad,
        playLoader: playLoader,
        showSuccessMessage: showSuccessMessage,
        showErrorMessage: showErrorMessage,
        downloadRelease: downloadRelease,
        doInternetSearch: doInternetSearch,
        deleteSelectedReleases: deleteSelectedReleases,
        rescanSelectedReleases: rescanSelectedReleases
    };
})(window);