var searchEngine = ( function( window, undefined ) {

    function clearSearchResults() {
        $("#searchResults").html('');
    };

    function showSearchResults(datums, type, title, linkType, elapsedTime) {
        var $s =  $("#search");
        var $sr = $("#searchResults");
        var searchLocation = $s.parent().position();
        var searchWidth = $s.width();
        var searchHeight = $s.height();
        var html = "<div class='" + type + " search-suggestion'>";
        html += "<div class='elapsed-time pull-right'>Search Time:" + elapsedTime + "ms</div>";
        html += "<h5>" + title + "</h5>";
        $.each(datums, function(i,d) {
            html += "<div data-" + type + "-id='" + d.id + "'><a href='/" + linkType + "/" + d.id + "'>";
            html += "<img src='" + d.tn + "' class='thumb' alt='" + d.value + "' />";
            html += "<span class='name label label-default'>" + d.value + "</span></a></div>";
        });
        html += "</div>";
        $sr.find("." + type).remove();
        $sr.append(html).css({'left': searchLocation.left + $("#search").position().left + 25,
                              'width': searchWidth}).show();
    };

    function init(data) {

        searchEngine.searchTrackThumbNailUrl = data.searchTrackThumbNailUrl;

        searchEngine.artistSearchEngine = new Bloodhound({
            datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            remote: {
                url: '/api/v1.0/artists?inc=None&filter=%QUERY',
                wildcard: '%QUERY',
                filter: function(x) {
                    result = [];
                    $.each(x.rows, function(i,d) {
                        result.push({
                            id: d.ArtistId,
                            type: 'artist',
                            tn: d.ThumbnailUrl,
                            value: d.Artist
                        });
                    });
                    return result;
                }
            }
        });

        searchEngine.releaseSearchEngine = new Bloodhound({
            datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            remote: {
                url: '/api/v1.0/releases?inc=None&filter=%QUERY',
                wildcard: '%QUERY',
                filter: function(x) {
                    result = [];
                    $.each(x.rows, function(i,d) {
                        result.push({
                            id: d.ReleaseId,
                            type: 'release',
                            tn: d.ThumbnailUrl,
                            value: d.Title + " (" + d.Year + ")"
                        });
                    });
                    return result;
                }
            }
        });

        searchEngine.trackSearchEngine = new Bloodhound({
            datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            remote: {
                url: '/api/v1.0/tracks?inc=None&filter=%QUERY',
                wildcard: '%QUERY',
                filter: function(x) {
                    result = [];
                    $.each(x.rows, function(i,d) {
                        result.push({
                            id: d.ReleaseId,
                            type: 'track',
                            tn: searchEngine.searchTrackThumbNailUrl,
                            value: d.Title
                        });
                    });
                    return result;
                }
            }
        });

        searchEngine.artistSearchEngine.initialize();
        searchEngine.releaseSearchEngine.initialize();
        searchEngine.trackSearchEngine.initialize();

        $("#search").on("keyup", _.debounce(function(e) {
            if (e.keyCode == 27) {
                $("#searchResults").hide();
                return false;
            }
            var startTime = new Date()
            var qry = $("#search").val();
            searchEngine.clearSearchResults();
            searchEngine.artistSearchEngine.search(qry, function(){}, function(datums) {
                if(datums.length > 0) {
                    var timeDiff = new Date() - startTime;
                    searchEngine.showSearchResults(datums, 'artist', "Artists:", 'artist', timeDiff);
                }
            });
            searchEngine.releaseSearchEngine.search(qry, function(){}, function(datums) {
                if(datums.length > 0) {
                    var timeDiff = new Date() - startTime;
                    searchEngine.showSearchResults(datums, 'release', "Releases:", 'release', timeDiff);
                }
            });
            searchEngine.trackSearchEngine.search(qry, function(){}, function(datums) {
                if(datums.length > 0) {
                    var timeDiff = new Date() - startTime;
                    searchEngine.showSearchResults(datums, 'track', "Tracks:", 'release', timeDiff);
                }
            });
        }, 500));

    };

    return {
        searchTrackThumbNailUrl: null,
        artistSearchEngine: null,
        releaseSearchEngine: null,
        trackSearchEngine: null,
        clearSearchResults: clearSearchResults,
        showSearchResults: showSearchResults,
        init: init
    };

} )( window );