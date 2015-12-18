var playerControl = (function(window, undefined) {
    var _element = null;

    function _trackLi(trackId) {
        return $(document).find("li[data-track-id='" + trackId + "']");
    }

    function _isRepeatSet() {
        return $("#btnRepeat").hasClass("btn-primary");
    }

    function _updateTrackPlayingIcon() {
        var html = "";
        if(playerControl.isPlaying) {
            html = "<i class='fa fa-play-circle fa-2x'></i>";
        } else {
            html = "<i class='fa fa-pause-circle fa-2x'></i>";
        }
        var $t = _trackLi(playerControl.playingTrackId);
        $t.find(".playing-status").html(html);
        $t.addClass("playing");
    }

    function setup(data) {
        _element = data.element;
        playerControl.play($(document).find("li[data-track-id]:first").data("track-id"));

        _element.addEventListener('progress', function(e) {
        });

        _element.addEventListener('error', function(e) {
            debugger;
        });

        _element.addEventListener('loadeddata', function(e) {
            var m = Math.floor(this.duration / 60);
            var s = Math.floor(this.duration % 60);
            //container[audiojs].helpers.removeClass(this.wrapper, player.loadingClass);
            $(".track-time").text((m<10?'0':'')+m+':'+(s<10?'0':'')+s);
        });

        _element.addEventListener('timeupdate', function(e) {
           var percent = this.currentTime / this.duration;
           var pbPercent = percent * 100;
           $(".play-progress-bar .progress-bar").css('width', pbPercent+'%').attr('aria-valuenow', pbPercent);
           var p = this.duration * percent;
           var m = Math.floor(p / 60);
           var s = Math.floor(p % 60);
           m = m || 0;
           s = s || 0;
           $(".current-time").text((m<10?'0':'')+m+':'+(s<10?'0':'')+s);
        });

        _element.addEventListener('ended', function(e) {
            playerControl.playNext();
        });
        
/*        // Keyboard shortcuts-->
        $(document).keydown(function(e) {-->
          var unicode = e.charCode ? e.charCode : e.keyCode;
             // right arrow
          if (unicode == 39) {
            var next = $('li.playing').next();
            if (!next.length) next = $('ol li').first();
            next.click();
            // back arrow
          } else if (unicode == 37) {
            var prev = $('li.playing').prev();
            if (!prev.length) prev = $('ol li').last();
            prev.click();
            // spacebar
          } else if (unicode == 32) {
            audio.playPause();
          }
        }); */
    }

    function play(trackId) {
        if(trackId) {
            $(".playing-status .fa-play-circle").removeClass("fa-play-circle").addClass("fa-play-circle-o");
            $("li.playing").removeClass("playing");
            $(".play-progress-bar .progress-bar").css('width', '0%').attr('aria-valuenow', 0);
            _element.setAttribute("src",_trackLi(trackId).data("track-url"));
            _element.load();
            playerControl.playingTrackId = trackId;
        }
        $("#btnPause").removeClass("btn-primary").addClass("btn-default");
        $("#btnPlay").addClass("btn-primary");
        playerControl.isPlaying = true;
        _updateTrackPlayingIcon();
        _element.play();
    }

    function stop() {
        $(".player-controls-container button").removeClass("btn-primary").addClass("btn-default");
    }

    function playPrevious() {
        var isPlayingFirstTrack = playerControl.playingTrackId === $("li[data-track-id]:first").data("track-id");
        if(isPlayingFirstTrack && _isRepeatSet()) {
            // Play Last
            playerControl.play(_trackLi($("li[data-track-id]:last").data("track-id")));
        } else if (!isPlayingFirstTrack) {
            // Play next track
            playerControl.play($(_trackLi(playerControl.playingTrackId)).prev().data("track-id"));
        }
    }

    function playForward() {
        var isPlayingLastTrack = playerControl.playingTrackId === $("li[data-track-id]:last").data("track-id");
        if(isPlayingLastTrack && _isRepeatSet()) {
            // Play First
            playerControl.play(_trackLi($("li[data-track-id]:first").data("track-id")));
        } else if (!isPlayingLastTrack) {
            // Play next track
            playerControl.play($(_trackLi(playerControl.playingTrackId)).next().data("track-id"));
        }
    }

    function pause() {
        $("#btnPlay").removeClass("btn-primary").addClass("btn-default");
        $("#btnPause").addClass("btn-primary");
        playerControl.isPlaying = false;
        _updateTrackPlayingIcon();
        _element.pause();
    }

    function setVolume(v) {
        _element.volume = v;
    }

    function toggleRepeat() {
        $("#btnRepeat").toggleClass("btn-primary");
    }

    return {
        isPlaying: false,
        playingTrackId: null,
        play: play,
        playPrevious: playPrevious,
        playForward: playForward,
        stop: stop,
        pause: pause,
        setVolume: setVolume,
        toggleRepeat: toggleRepeat,
        setup: setup
    };

})(window);