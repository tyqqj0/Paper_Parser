from datetime import datetime

from . import Author
from . import Journal
from . import Tldr
from . import PublicationVenue
from .SemanticScholarObject import SemanticScholarObject


class Paper(SemanticScholarObject):
    '''
    This class abstracts a paper.
    '''

    FIELDS = [
        'abstract',
        'authors',
        'authors.affiliations',
        'authors.authorId',
        'authors.citationCount',
        'authors.externalIds',
        'authors.hIndex',
        'authors.homepage',
        'authors.name',
        'authors.paperCount',
        'authors.url',
        'citationCount',
        'citationStyles',
        'citations',
        'citations.abstract',
        'citations.authors',
        'citations.citationCount',
        'citations.citationStyles',
        'citations.corpusId',
        'citations.externalIds',
        'citations.fieldsOfStudy',
        'citations.influentialCitationCount',
        'citations.isOpenAccess',
        'citations.journal',
        'citations.openAccessPdf',
        'citations.paperId',
        'citations.publicationDate',
        'citations.publicationTypes',
        'citations.publicationVenue',
        'citations.referenceCount',
        'citations.s2FieldsOfStudy',
        'citations.title',
        'citations.url',
        'citations.venue',
        'citations.year',
        'corpusId',
        'embedding',
        'externalIds',
        'fieldsOfStudy',
        'influentialCitationCount',
        'isOpenAccess',
        'journal',
        'openAccessPdf',
        'paperId',
        'publicationDate',
        'publicationTypes',
        'publicationVenue',
        'referenceCount',
        'references',
        'references.abstract',
        'references.authors',
        'references.citationCount',
        'references.citationStyles',
        'references.corpusId',
        'references.externalIds',
        'references.fieldsOfStudy',
        'references.influentialCitationCount',
        'references.isOpenAccess',
        'references.journal',
        'references.openAccessPdf',
        'references.paperId',
        'references.publicationDate',
        'references.publicationTypes',
        'references.publicationVenue',
        'references.referenceCount',
        'references.s2FieldsOfStudy',
        'references.title',
        'references.url',
        'references.venue',
        'references.year',
        's2FieldsOfStudy',
        'title',
        'tldr',
        'url',
        'venue',
        'year'
    ]

    SEARCH_FIELDS = [
        'abstract',
        'authors',
        'citationCount',
        'citationStyles',
        'corpusId',
        'externalIds',
        'fieldsOfStudy',
        'influentialCitationCount',
        'isOpenAccess',
        'journal',
        'openAccessPdf',
        'paperId',
        'publicationDate',
        'publicationTypes',
        'publicationVenue',
        'referenceCount',
        's2FieldsOfStudy',
        'title',
        'url',
        'venue',
        'year'
    ]

    def __init__(self, data) -> None:
        super().__init__()
        self._abstract = None
        self._authors = None
        self._citationCount = None
        self._citationStyles = None
        self._citations = None
        self._corpusId = None
        self._embedding = None
        self._externalIds = None
        self._fieldsOfStudy = None
        self._influentialCitationCount = None
        self._isOpenAccess = None
        self._journal = None
        self._openAccessPdf = None
        self._paperId = None
        self._publicationDate = None
        self._publicationTypes = None
        self._publicationVenue = None
        self._referenceCount = None
        self._references = None
        self._s2FieldsOfStudy = None
        self._title = None
        self._tldr = None
        self._venue = None
        self._year = None
        self._init_attributes(data)

    @property
    def abstract(self) -> str:
        '''
        :type: :class:`str`
        '''
        return self._abstract

    @property
    def authors(self) -> list:
        '''
        :type: :class:`list`
        '''
        return self._authors

    @property
    def citationCount(self) -> int:
        '''
        :type: :class:`int`
        '''
        return self._citationCount

    @property
    def citationStyles(self) -> dict:
        '''
        :type: :class:`dict`
        '''
        return self._citationStyles

    @property
    def citations(self) -> list:
        '''
        :type: :class:`list`
        '''
        return self._citations

    @property
    def corpusId(self) -> str:
        '''
        :type: :class:`str`
        '''
        return self._corpusId

    @property
    def embedding(self) -> dict:
        '''
        :type: :class:`dict`
        '''
        return self._embedding

    @property
    def externalIds(self) -> dict:
        '''
        :type: :class:`dict`
        '''
        return self._externalIds

    @property
    def fieldsOfStudy(self) -> list:
        '''
        :type: :class:`list`
        '''
        return self._fieldsOfStudy

    @property
    def influentialCitationCount(self) -> int:
        '''
        :type: :class:`int`
        '''
        return self._influentialCitationCount

    @property
    def isOpenAccess(self) -> bool:
        '''
        :type: :class:`bool`
        '''
        return self._isOpenAccess

    @property
    def journal(self) -> 'Journal.Journal':
        '''
        :type: :class:`Journal.Journal`
        '''
        return self._journal

    @property
    def openAccessPdf(self) -> dict:
        '''
        :type: :class:`dict`
        '''
        return self._openAccessPdf

    @property
    def paperId(self) -> str:
        '''
        :type: :class:`str`
        '''
        return self._paperId

    @property
    def publicationDate(self) -> datetime:
        '''
        :type: :class:`datetime`
        '''
        return self._publicationDate

    @property
    def publicationTypes(self) -> list:
        '''
        :type: :class:`list`
        '''
        return self._publicationTypes

    @property
    def publicationVenue(self) -> \
            'PublicationVenue.PublicationVenue':
        '''
        :type: :class:`PublicationVenue.PublicationVenue`
        '''
        return self._publicationVenue

    @property
    def referenceCount(self) -> int:
        '''
        :type: :class:`int`
        '''
        return self._referenceCount

    @property
    def references(self) -> list:
        '''
        :type: :class:`list`
        '''
        return self._references

    @property
    def s2FieldsOfStudy(self) -> list:
        '''
        :type: :class:`list`
        '''
        return self._s2FieldsOfStudy

    @property
    def title(self) -> str:
        '''
        :type: :class:`str`
        '''
        return self._title

    @property
    def tldr(self) -> 'Tldr.Tldr':
        '''
        :type: :class:`Tldr.Tldr`
        '''
        return self._tldr

    @property
    def url(self) -> str:
        '''
        :type: :class:`str`
        '''
        return self._url

    @property
    def venue(self) -> str:
        '''
        :type: :class:`str`
        '''
        return self._venue

    @property
    def year(self) -> int:
        '''
        :type: :class:`int`
        '''
        return self._year

    def _init_attributes(self, data) -> None:
        self._data = data
        if 'abstract' in data:
            self._abstract = data['abstract']
        if 'authors' in data:
            items = []
            if data['authors'] is not None:
                for item in data['authors']:
                    items.append(Author.Author(item))
            self._authors = items
        if 'citationCount' in data:
            self._citationCount = data['citationCount']
        if 'citationStyles' in data:
            self._citationStyles = data['citationStyles']
        if 'citations' in data:
            items = []
            if data['citations'] is not None:
                for item in data['citations']:
                    items.append(Paper(item))
            self._citations = items
        if 'corpusId' in data:
            self._corpusId = data['corpusId']
        if 'embedding' in data:
            self._embedding = data['embedding']
        if 'externalIds' in data:
            self._externalIds = data['externalIds']
        if 'fieldsOfStudy' in data:
            self._fieldsOfStudy = data['fieldsOfStudy']
        if 'influentialCitationCount' in data:
            self._influentialCitationCount = data['influentialCitationCount']
        if 'isOpenAccess' in data:
            self._isOpenAccess = data['isOpenAccess']
        if 'journal' in data:
            if data['journal'] is not None:
                self._journal = Journal.Journal(data['journal'])
        if 'openAccessPdf' in data:
            self._openAccessPdf = data['openAccessPdf']
        if 'paperId' in data:
            self._paperId = data['paperId']
        if 'publicationDate' in data:
            if data['publicationDate'] is not None:
                self._publicationDate = datetime.strptime(
                    data['publicationDate'], '%Y-%m-%d')
        if 'publicationTypes' in data:
            self._publicationTypes = data['publicationTypes']
        if 'publicationVenue' in data:
            if data['publicationVenue'] is not None:
                self._publicationVenue = PublicationVenue.\
                    PublicationVenue(data['publicationVenue'])
        if 'referenceCount' in data:
            self._referenceCount = data['referenceCount']
        if 'references' in data:
            items = []
            if data['references'] is not None:
                for item in data['references']:
                    items.append(Paper(item))
            self._references = items
        if 's2FieldsOfStudy' in data:
            self._s2FieldsOfStudy = data['s2FieldsOfStudy']
        if 'title' in data:
            self._title = data['title']
        if 'tldr' in data:
            if data['tldr'] is not None:
                self._tldr = Tldr.Tldr(data['tldr'])
        if 'url' in data:
            self._url = data['url']
        if 'venue' in data:
            self._venue = data['venue']
        if 'year' in data:
            self._year = data['year']
