var queManager = ( function( window, undefined ) {
    var storageKey = "roadie:que";
    var queItems = [];
    function _toggleMenuItem(doShow) {
        if(doShow) {
            $("#queMenuItem").removeClass("hidden").show().find("a:first").html("Que (" + queItems.length + ") <span class='caret'></span>");
        } else {
            $("#queMenuItem").addClass("hidden").hide().find("a:first").html("Que <span class='caret'></span>");
        }
    };
    function _saveQue() {
        localStorage.setItem(storageKey, JSON.stringify(queItems));
        if(queItems.length == 0) {
            _toggleMenuItem(false);
        }
    };
    function addToQue(type, releaseId, trackId) {
        queItems.push({ type: type, releaseId: releaseId, trackId: trackId});
        _saveQue();
        _toggleMenuItem(true);
    };
    function clearQue() {
        queItems = []
        _saveQue();

    };
    function editQue() {
        alert('edit que');
    };
    function saveQue() {
        bootbox.prompt("Que will be saved/append as/to a Playlist. Enter a playlist name:", function(result) {
            if(result) {
                $.ajax({
                    type: 'POST',
                    data: JSON.stringify(queItems),
                    url: '/que/save/' + encodeURIComponent(result),
                    contentType: "application/json",
                    success: function(data) {
                        if(data.message === "OK") {
                            $.bootstrapGrowl("Successfully saved Que", {
                                type: 'success',
                                stackup_spacing: 20
                            });
                            queManager.clearQue();
                        }
                    },
                    error:function(jq, st, error){
                        roadieLibrary.showErrorMessage(error);
                    }
                });
            }
        });
    };
    function playQue() {
        if(queItems.length == 0) {
            return false;
        }
        $.ajax({
            type: 'POST',
            data: JSON.stringify(queItems),
            url: '/que/play',
            contentType: "application/json",
            success: function(response, status, xhr) {
                var filename = "";
                var disposition = xhr.getResponseHeader('Content-Disposition');
                if (!disposition) {
                    roadieLibrary.playLoader("about:blank", response);
                    return false;
                }
                if (disposition && disposition.indexOf('attachment') !== -1) {
                    var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    var matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) filename = matches[1].replace(/['"]/g, '');
                }
                var type = xhr.getResponseHeader('Content-Type');
                var blob = new Blob([response], { type: type });
                if (typeof window.navigator.msSaveBlob !== 'undefined') {
                    window.navigator.msSaveBlob(blob, filename);
                } else {
                    var URL = window.URL || window.webkitURL;
                    var downloadUrl = URL.createObjectURL(blob);
                    if (filename) {
                        var a = document.createElement("a");
                        if (typeof a.download === 'undefined') {
                            window.location = downloadUrl;
                        } else {
                            a.href = downloadUrl;
                            a.download = filename;
                            document.body.appendChild(a);
                            a.click();
                        }
                    } else {
                        window.location = downloadUrl;
                    }
                    setTimeout(function () { URL.revokeObjectURL(downloadUrl); }, 100); // cleanup
                }
            },
            error:function(jq, st, error){
                roadieLibrary.showErrorMessage(error);
            }
        });

    };
    function init() {
        var qi = localStorage.getItem(storageKey);
        if(qi != 'undefined' && qi != null) {
            queItems = JSON.parse(qi);
        } else {
            queItems = [];
        }
        _toggleMenuItem(queItems.length > 0);
        $("a.play-que").on("click", queManager.playQue);
        $("a.clear-que").on("click", queManager.clearQue);
        $("a.save-que").on("click", queManager.saveQue);
        $("a.edit-que").on("click", queManager.editQue);
    };
    return {
        init: init,
        addToQue : addToQue,
        clearQue: clearQue,
        editQue: editQue,
        playQue: playQue,
        saveQue: saveQue
    };

} )( window );