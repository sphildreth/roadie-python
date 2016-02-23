var queManager = ( function( window, undefined ) {
    var storageKey = "roadie:que";
    var queItems = [];
    function _toggleMenuItem(doShow) {
        if(doShow) {
            $("#queMenuItem").removeClass("hidden").show().find("a:first").html("Que (" + queItems.length + ") <span class='caret'></span>");
        } else {
            $("#queMenuItem").addClass("hidden").hide().find("a:first").html("Que <span class='caret'></span>");
        }
    }
    function _saveQue() {
        localStorage.setItem(storageKey, JSON.stringify(queItems));
        if(queItems.length == 0) {
            _toggleMenuItem(false);
        }
    }
    function addToQue(type, releaseId, trackId, showMenu) {
        queItems.push({ type: type, releaseId: releaseId, trackId: trackId});
        _saveQue();
        if(showMenu == undefined || showMenu) {
            _toggleMenuItem(true);
        }
    }
    function clearQue() {
        queItems = []
        _saveQue();

    }
    function editQue() {
        bootbox.alert('edit que');
    }
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
    }
    function playQue() {
        if(queItems.length == 0) {
            return false;
        }
        //var width = 750;
        //var height = 450;
        //if (window.user.doUseHtmlPlayer) {
        //    window.open(url, 'roadiePlayer');
        //} else {
        //    var frameName = "playlistloader";
        //    var element = document.getElementById(frameName);
        //    if (!element) {
        //        element = document.createElement("iframe");
        //        element.setAttribute('id', frameName);
        //        document.body.appendChild(element);
        //    }
        //    element.setAttribute('src', url);
        //}

        $.ajax({
            type: 'POST',
            data: JSON.stringify(queItems),
            url: '/que/play',
            contentType: "application/json",
            success: function(response, status, xhr) {
                if (window.user.doUseHtmlPlayer) {
                    var newWindow = window.open("", "roadiePlayer");
                    with(newWindow.document)
                    {
                      open();
                      write(response);
                      close();
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
            },
            error:function(jq, st, error){
                roadieLibrary.showErrorMessage(error);
            }
        });
    }
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
    }
    return {
        init: init,
        addToQue : addToQue,
        clearQue: clearQue,
        editQue: editQue,
        playQue: playQue,
        saveQue: saveQue
    };

} )( window );