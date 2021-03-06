var playerControl = (function(window, undefined) {
    var _element = null;
    var _loadedPercent = 0;
    var _loadTimer = null;
    var _lastTrackText = null;
    var _originalWindowTitle = null;

    function _trackLi(trackId) {
        return $(document).find("li[data-track-id='" + trackId + "']");
    }

    function _artistNameAndTrackTitle(trackId) {
        var $t = _trackLi(trackId);
        return $t.find(".artist-name").text() + " | " + $t.find(".track-title").text();
    }

    function _isRepeatSet() {
        return $("#btnRepeat").hasClass("btn-primary");
    }

    function _updateTrackPlayingIcon() {
        var html = "";
        if(playerControl.isPlaying) {
            iconClass = "fa-play-circle";
        } else {
            iconClass = "fa-pause-circle";
        }
        var $t = _trackLi(playerControl.playingTrackId);
        $t.find(".playing-status i")
          .removeClass("fa-play-circle")
          .removeClass("fa-pause-circle")
          .addClass(iconClass);
         $t.addClass("playing");
    }

    function _scrollToView(element){
        var offset = element.offset().top;
        if(!element.is(":visible")) {
            element.css({"visibility":"hidden"}).show();
            var offset = element.offset().top;
            element.css({"visibility":"", "display":""});
        }
        var visible_area_start = $(window).scrollTop();
        var visible_area_end = visible_area_start + window.innerHeight;
        if(offset < visible_area_start || offset > visible_area_end){
             // Not in view so scroll to it
             $('html,body').animate({scrollTop: offset - window.innerHeight/3}, 1000);
             return false;
        }
        return true;
    }

    function _updateTrackLength(duration) {
        var m = Math.floor(duration / 60);
        var s = Math.floor(duration % 60);
        $(".track-time").text((m<10?'0':'')+m+':'+(s<10?'0':'')+s);
    }

    function setup(data) {
        _element = data.element;
        _originalWindowTitle = document.title;

        var $window = $(window),
            $stickyEl = $('.player-container'),
            elTop = $stickyEl.offset().top;

        $window.scroll(function() {
            $stickyEl.toggleClass('sticky', $window.scrollTop() > elTop);
        })

        playerControl.play($(document).find("li[data-track-id]:first").data("track-id"));

        _element.addEventListener('progress', function(e) {
        });

        _element.addEventListener('error', function(e) {
            switch (e.target.error.code) {
             case e.target.error.MEDIA_ERR_ABORTED:
               console.log('Aborted the video playback.');
               break;
             case e.target.error.MEDIA_ERR_NETWORK:
               console.log('A network error caused the audio download to fail.');
               break;
             case e.target.error.MEDIA_ERR_DECODE:
               console.log('The audio playback was aborted due to a corruption problem or because the video used features your browser did not support.');
               break;
             case e.target.error.MEDIA_ERR_SRC_NOT_SUPPORTED:
               console.log('The video audio not be loaded, either because the server or network failed or because the format is not supported.');
               break;
             default:
               console.log('An unknown error occurred.');
               break;
            }
            playerControl.playForward();
        });

        _element.addEventListener('loadstart', function(e) {
            _loadTimer = setInterval(function() {
                var buffered = _element.buffered;
                if (buffered.length) {
                    _loadedPercent = 100 * buffered.end(0) / _element.duration;
                    $(".play-progress-bar .progress-bar.loaded").css('width', _loadedPercent+'%').attr('aria-valuenow', _loadedPercent);
                    if (_loadedPercent == 100) {
                        clearInterval(_loadTimer);
                    }
                }
            }, 10);
        });

        _element.addEventListener('loadeddata', function(e) {
            _updateTrackLength(this.duration);
        });

        _element.addEventListener('timeupdate', function(e) {
           var percent = this.currentTime / this.duration;
           var pbPercent = percent * 100;
           $(".play-progress-bar .progress-bar.playing").css('width', pbPercent+'%').attr('aria-valuenow', pbPercent);
           var p = this.duration * percent;
           var m = Math.floor(p / 60);
           var s = Math.floor(p % 60);
           m = m || 0;
           s = s || 0;
           var trackText = (m<10?'0':'')+m+':'+(s<10?'0':'')+s;
           if(_lastTrackText != trackText) {
                $(".current-time").text(trackText);
                _lastTrackText = trackText;
            }
        });

        _element.addEventListener('ended', function(e) {
            playerControl.playForward();
        });

        $(".play-progress-bar .progress").on("click", function(e) {
            var $this = $(this);
            var percentageClick =  e.offsetX / $this.width();
            if(percentageClick > _loadedPercent) {
                percentageClick = _loadedPercent;
            }
            _element.currentTime = _element.duration * percentageClick;
        });

        $("ol.track-list span.playing-status").on("click", function(e) {
            var $this = $(this);
            if ($this.parent().hasClass("playing")) {
                playerControl.pause();
            } else {
                playerControl.play($this.parent().data("track-id"));
            }
        });
        
        $(document).keydown(function(e) {
          var unicode = e.charCode ? e.charCode : e.keyCode;
          if (unicode == 39) {
            e.preventDefault();
            playerControl.playForward();
          } else if (unicode == 37) {
            e.preventDefault();
            playerControl.playPrevious();
          } else if (unicode == 32) {
            e.preventDefault();
            if(playerControl.isPlaying) {
                playerControl.pause();
            } else {
                playerControl.play();
                playerControl.play();
            }
          }
        });
    }

    function play(trackId) {
        if(trackId) {
            _lastTrackText = null;
            $(".playing-status .fa-play-circle").removeClass("fa-play-circle").addClass("fa-play-circle-o");
            _scrollToView(_trackLi(trackId));
            $("li.playing").removeClass("playing");
            $(".play-progress-bar .progress-bar").css('width', '0%').attr('aria-valuenow', 0);
            _element.setAttribute("src",_trackLi(trackId).data("track-url"));
            roadieLibrary.setFavIcon(null, _trackLi(trackId).find("img.release-thumb")[0]);
            _updateTrackLength(parseFloat(_trackLi(trackId).data("track-duration"))/1000);
            _element.load();
            playerControl.playingTrackId = trackId;
            document.title = _artistNameAndTrackTitle(trackId);
        }
        $("#btnPause").removeClass("btn-primary").addClass("btn-default");
        $("#btnPlay").addClass("btn-primary");
        playerControl.isPlaying = true;
        _updateTrackPlayingIcon();
        _element.play();
    }

    function stop() {
        $(".player-controls-container button").removeClass("btn-primary").addClass("btn-default");
        document.title = _originalWindowTitle;
        playerControl.isPlaying = false;
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