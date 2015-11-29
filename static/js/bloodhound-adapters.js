var bhArtists = new Bloodhound({
    remote: {
        url: '/api/v1.0/artists?filter=%QUERY',
        wildcard: '%QUERY',
        transform: function(x) {
            result = [];
            $.each(x.rows, function(i,d) {
                result.push({
                    id: d.roadieId,
                    name: d.name
                });
            });
            return result;
        }
    },
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('name'),
    queryTokenizer: Bloodhound.tokenizers.whitespace
});
bhArtists.initialize();

var bhGenres = new Bloodhound({
    remote: {
        url: '/api/v1.0/genres?filter=%QUERY',
        wildcard: '%QUERY',
        transform: function(x) {
            result = [];
            $.each(x.rows, function(i,d) {
                result.push({
                    id: d.roadieId,
                    name: d.name
                });
            });
            return result;
        }
    },
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('name'),
    queryTokenizer: Bloodhound.tokenizers.whitespace
});
bhGenres.initialize();

var bhLabels = new Bloodhound({
    remote: {
        url: '/api/v1.0/labels?filter=%QUERY',
        wildcard: '%QUERY',
        transform: function(x) {
            result = [];
            $.each(x.rows, function(i,d) {
                result.push({
                    id: d.roadieId,
                    name: d.name
                });
            });
            return result;
        }
    },
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('name'),
    queryTokenizer: Bloodhound.tokenizers.whitespace
});
bhLabels.initialize();

var bhUsers = new Bloodhound({
    remote: {
        url: '/api/v1.0/users?filter=%QUERY',
        wildcard: '%QUERY',
        transform: function(x) {
            result = [];
            $.each(x.rows, function(i,d) {
                result.push({
                    id: d.roadieId,
                    username: d.username
                });
            });
            return result;
        }
    },
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('username'),
    queryTokenizer: Bloodhound.tokenizers.whitespace
});
bhUsers.initialize();
