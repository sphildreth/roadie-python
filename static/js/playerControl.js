var playerControl = (function(window, undefined) {
    var _element = null;
    var _loadedPercent = 0;
    var _loadTimer = null;

    function _trackLi(trackId) {
        return $(document).find("li[data-track-id='" + trackId + "']");
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

    function setup(data) {
        _element = data.element;

        _loadTimer = setInterval(function() {
          if (_element.readyState > 1) {

          }
        }, 10);

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
            var m = Math.floor(this.duration / 60);
            var s = Math.floor(this.duration % 60);
            $(".track-time").text((m<10?'0':'')+m+':'+(s<10?'0':'')+s);
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
           $(".current-time").text((m<10?'0':'')+m+':'+(s<10?'0':'')+s);
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