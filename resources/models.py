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


class ThumbnailImage(EmbeddedDocument):
    element = ImageField(size=(512, 512, True))


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
    Active = BooleanField(default=True)
    Avatar = EmbeddedDocumentField(ThumbnailImage)
    Roles = ListField(ReferenceField(UserRole), default=[])
    meta = {
        'indexes': [
            {'fields': ['Username'], 'unique': True },
            {'fields': ['Password'], 'unique': True }
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
    AlternateNames = SortedListField(StringField())
    BeginDate = DateTimeField()
    EndDate = DateTimeField()
    LastUpdated = DateTimeField(default=datetime.datetime.now)
    MusicBrainzId = StringField()
    Name = StringField(required=True)
    Tags = ListField(StringField(max_length=100))
    Urls = ListField(EmbeddedDocumentField(Url))
    meta = {
        'indexes': [
            {'fields': ['Name'], 'unique': True }
        ]
    }

    def __unicode__(self):
        return self.Name


class Artist(Document):
    AlternateNames = SortedListField(StringField())
    ArtistType = ReferenceField(ArtistType)
    BeginDate = DateTimeField()
    EndDate = DateTimeField()
    Images = ListField(EmbeddedDocumentField(Image))
    LastUpdated = DateTimeField(default=datetime.datetime.now)
    MusicBrainzId = StringField()
    Name = StringField(required=True)
    Profile = StringField()
    RealName = StringField()
    SortName = StringField()
    Thumbnail = EmbeddedDocumentField(ThumbnailImage)
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
    PlayedCount = IntField()
    Tags = ListField(StringField(max_length=100))
    Title = StringField(required=True)
    meta = {
        'indexes': [
            'Title'
        ]
    }

    def __unicode__(self):
        return self.Title

class UserTrack(Document):
    User = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    Track = ReferenceField(Track, required=True, reverse_delete_rule=CASCADE)
    PlayedCount = IntField()
    Rating = IntField()
    IsFavorite = BooleanField()
    meta = {
        'indexes': [
            'User',
            'Track'
        ]
    }

    def __unicode__(self):
        return self.User.name + "::" + Track.Title


class TrackRelease(EmbeddedDocument):
    Track = ReferenceField(Track, required=True)
    TrackNumber = IntField(required=True)
    # this is the cd number ie cd x of x
    ReleaseMediaNumber = IntField()
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
    Genres = ListField(ReferenceField(Genre))
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
    Quality = ReferenceField(Quality)
    Urls = ListField(EmbeddedDocumentField(Url))
    meta = {
        'indexes': [
            'Title'
        ],
        'ordering': [
            'ReleaseDate',
            'Title'
        ]
    }

    def __unicode__(self):
        return self.Title
