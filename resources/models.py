from mongoengine import *
import datetime


class ArtistType(Document):
    Name = StringField(max_length=100, required=True)

    def __unicode__(self):
        return self.Name


class Genre(Document):
    Name = StringField(max_length=100, required=True)

    def __unicode__(self):
        return self.Name


class Url(EmbeddedDocument):
    Title = StringField(max_length=100, required=True)
    Url = URLField(required=True)


class Quality(Document):
    Name = StringField(max_length=50, required=True)

    def __unicode__(self):
        return self.Name


class Image(EmbeddedDocument):
    element = ImageField()


class UserRole(Document):
    Name = StringField(max_length=80, required=True, unique=True)
    Description = StringField(max_length=200)

    def __eq__(self, other):
        if not isinstance(other, UserRole):
            return False

        return self.Name == other.Name

    def __hash__(self):
        return hash(self.Name)

    def __unicode__(self):
        return self.Name


class User(Document):
    Username = StringField(max_length=20, required=True, unique=True)
    Password = StringField(max_length=100, required=True)
    Email = EmailField(required=True, unique=True)
    RegisteredOn = DateTimeField()
    LastLogin = DateTimeField()
    LastUpdated = DateTimeField(default=datetime.datetime.now)
    Active = BooleanField(default=True)
    Avatar = EmbeddedDocumentField(Image)
    Roles = ListField(ReferenceField(UserRole), required=False, default=[])
    meta = {
        'indexes': [
            {'fields': ['Username']}
        ]
    }

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def has_role(self, role):
        return UserRole(Name=role) in self.Roles

    def __repr__(self):
        return '<User %r>' % (self.Username)

    def __unicode__(self):
        return self.Username


class Label(Document):
    AlternateNames = SortedListField(StringField(), default=[])
    BeginDate = DateTimeField()
    EndDate = DateTimeField()
    LastUpdated = DateTimeField(default=datetime.datetime.now)
    MusicBrainzId = StringField()
    Name = StringField(required=True, unique=True)
    Tags = ListField(StringField(max_length=100))
    Urls = ListField(EmbeddedDocumentField(Url))
    meta = {
        'indexes': [
            {'fields': ['Name']}
        ]
    }

    def __unicode__(self):
        return self.Name


class Artist(Document):
    AlternateNames = SortedListField(StringField(), default=[])
    ArtistType = ReferenceField(ArtistType)
    BirthDate = DateTimeField()
    BeginDate = DateTimeField()
    EndDate = DateTimeField()
    Images = ListField(EmbeddedDocumentField(Image))
    LastUpdated = DateTimeField(default=datetime.datetime.now)
    MusicBrainzId = StringField()
    Name = StringField(required=True)
    Profile = StringField()
    RealName = StringField()
    SortName = StringField()
    Thumbnail = FileField()
    Tags = ListField(StringField(max_length=100))
    Urls = ListField(EmbeddedDocumentField(Url))
    meta = {
        'indexes': [
            'Name'
        ],
        'ordering': [
            'SortName',
            'Name'
        ]
    }

    def __unicode__(self):
        return self.Name


class Track(Document):
    Artist = ReferenceField(Artist, required=True, reverse_delete_rule=CASCADE)
    FileName = StringField()
    FilePath = StringField()
    # MD5 of file
    Hash = StringField(unique=True)
    LastUpdated = DateTimeField(default=datetime.datetime.now)
    # Seconds long
    Length = FloatField()
    MusicBrainzId = StringField()
    PlayedCount = IntField(default=0)
    LastPlayed = DateTimeField()
    PartTitles = ListField(StringField())
    Tags = ListField(StringField(max_length=100))
    Title = StringField(required=True)
    meta = {
        'indexes': [
            'Title'
        ]
    }

    def __unicode__(self):
        return self.Title


class UserArtist(Document):
    User = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    Artist = ReferenceField(Artist, required=True, reverse_delete_rule=CASCADE)
    IsFavorite = BooleanField()
    IsDisliked = BooleanField()
    Rating = IntField()
    meta = {
        'indexes': [
            'User',
            'Artist'
        ]
    }

    def __unicode__(self):
        return self.User.name + "::" + Artist.Name


class Playlist(Document):
    User = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    Tracks = ListField(ReferenceField(Track, required=True, reverse_delete_rule=CASCADE))
    Name = StringField()
    IsPublic = BooleanField()
    Description = StringField()
    LastUpdated = DateTimeField(default=datetime.datetime.now)
    meta = {
        'indexes': [
            'User'
        ]
    }

    def __unicode__(self):
        return self.User.name + "::" + self.Name


class TrackRelease(EmbeddedDocument):
    Track = ReferenceField(Track, required=True)
    TrackNumber = IntField(required=True)
    # this is the cd number ie cd x of x
    ReleaseMediaNumber = IntField()
    # This is any potential subtitle of cd x of x; see 'Star Time' frm James Brown
    ReleaseSubTitle = StringField()
    meta = {
        'ordering': [
            'ReleaseMediaNumber',
            'TrackNumber'
        ]
    }

    def __unicode__(self):
        return self.TrackNumber + " " + self.Track.Title


class ReleaseLabel(EmbeddedDocument):
    Label = ReferenceField(Label, required=True)
    CatalogNumber = StringField()
    BeginDate = DateTimeField()
    EndDate = DateTimeField()

    def __unicode__(self):
        return self.Label.Name + " (" + self.BeginDate.strfttime('%Y') + ")"


class Release(Document):
    IsVirtual = BooleanField()
    AlternateNames = SortedListField(StringField())
    Artist = ReferenceField(Artist, required=True, reverse_delete_rule=CASCADE)
    Images = ListField(EmbeddedDocumentField(Image))
    Genres = ListField(ReferenceField(Genre), default=[])
    Labels = ListField(EmbeddedDocumentField(ReleaseLabel), default=[])
    LastUpdated = DateTimeField(default=datetime.datetime.now)
    MusicBrainzId = StringField()
    ReleaseDate = StringField(required=True)
    Thumbnail = FileField()
    Tags = ListField(StringField(max_length=100))
    Title = StringField(required=True)
    Tracks = ListField(EmbeddedDocumentField(TrackRelease), default=[])
    TrackCount = IntField()
    DiscCount = IntField()
    Profile = StringField()
    Quality = ReferenceField(Quality)
    Urls = ListField(EmbeddedDocumentField(Url))
    meta = {
        'indexes': [
            'Title',
            'Tracks.Track'
        ],
        'ordering': [
            'ReleaseDate',
            'Title'
        ]
    }

    def __unicode__(self):
        return self.Title


class UserRelease(Document):
    User = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    Release = ReferenceField(Release, required=True, reverse_delete_rule=CASCADE)
    Rating = IntField()
    IsFavorite = BooleanField()
    meta = {
        'indexes': [
            'User',
            'Release'
        ]
    }

class UserTrack(Document):
    User = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    Release = ReferenceField(Release, required=True, reverse_delete_rule=CASCADE)
    Track = ReferenceField(Track, required=True, reverse_delete_rule=CASCADE)
    PlayedCount = IntField(default=0)
    LastPlayed = DateTimeField()
    Rating = IntField()
    IsFavorite = BooleanField()
    meta = {
        'indexes': [
            'User',
            'Track'
        ]
    }

    def __unicode__(self):
        return self.User.name + "::" + self.Track.Title


class CollectionRelease(EmbeddedDocument):
    Release = ReferenceField(Release, required=True)
    ListNumber = IntField(required=True)

    def __unicode__(self):
        return self.Release.Title


class Collection(Document):
    Name = StringField()
    Edition = StringField()
    Description = StringField()
    Thumbnail = FileField()
    Maintainer = ReferenceField(User, required=True)
    Urls = ListField(EmbeddedDocumentField(Url))
    Releases = ListField(EmbeddedDocumentField(CollectionRelease), default=[])
    LastUpdated = DateTimeField(default=datetime.datetime.now)

    def __unicode__(self):
        return self.Name