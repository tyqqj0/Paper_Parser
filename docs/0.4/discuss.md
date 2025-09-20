
## 🧑‍💻 User

非常好，非常好。然后现在的话我现在想就是我自己想了一下，确实就是应该先用别人的这个数据，就用semantic scholar的这个数据吧，我想的话是就做一个简单的这种缓存或者是转发的服务。就是说我后面尽量搞一个semantic scholar的这种API。查我，我后面对，然后搞一个这种API，然后去缓存每一条这个拿到的这个数据。然后缓存之后去。把打给陈建，然后打上一个访问时间。然后比如说我设定一个这个在API层设定一个，这个判断就是如果说之前有过，那我就直接返回之前解析出来的结果，如果说没有的话，我就。我就解析一下去访问一下API，然后再回来再存上，然后这样的话就相当于是一个semantic scholar的这样的一个转发吧。我想先这么做对。你好connected papers我也在发文件去发邮件去问。如果能拿到最好，如果不能拿到的话，我就先先不搞这么复杂，先做一个最简单的。我现在想的是说就是就是我想先把semantic scholar的这个API它有什么东西先了解好。他能不能做到？就是比如说你，你是否了解他能不能做到像这个去查一篇文献的引用和被引都可以吗？不能交管连着查到一系列的。能不能关联着查到一系列的文献？就比如说啊，我查到一篇文献，我，我在一个人一个前端公众号，我们设想一下。就是。比如说我现在啊，用户用户现在有一篇文献在这个浏览器上面。然后的话我自动去解析这个用户提交提交这篇文献是通过一个啊，像这个文献的2K的ID啊。等一下暖或者是它的DOA啊这类的东西。这东西来添加。好，能不能就是实现一个。我。我能获取这篇文献的元数据，比如说作者呀啊作者，然后像摘要啊，关键词呀。然后这类的东西，然后又能获取。网友能在浏览器上推荐出来和所有和这篇文献相关的内容。相关的文献？然后。查。然后对，然后所有的这些相关的文献的内部的关系都能被解析出来。然后我还能去继续根据这个相关的文献。每天去解析新的文献。啊，能做到这样吗？你看一眼可以吗？谢谢。Academic Graph API (1.0)
Download OpenAPI specification:Download

Fetch paper and author data from the Semantic Scholar Academic Graph (S2AG).

Some things to note:

If you are using an API key, it must be set in the header x-api-key (case-sensitive).
We have two different IDs for a single paper:
paperId - string - The primary way to identify papers when using our website or this API
corpusId - int64 - A second way to identify papers. Our datasets use corpusId when pointing to papers.
Other useful resources
Overview
allenai/s2-folks
FAQ in allenai/s2folks
Paper Data
Suggest paper query completions
To support interactive query-completion, return minimal information about papers matching a partial query

Example: https://api.semanticscholar.org/graph/v1/paper/autocomplete?query=semanti

query Parameters
query
required
string
Plain-text partial query string. Will be truncated to first 100 characters.

Responses
200 Batch of papers with default or requested fields
400 Bad query parameters

get
/paper/autocomplete
Response samples
200400
Content type
application/json

Copy
Expand allCollapse all
{
"matches": [
{}
]
}
Get details for multiple papers at once
Fields is a single-value string parameter, not a multi-value one.
It is a query parameter, not to be submitted in the POST request's body.
In python:

r = requests.post(
 'https://api.semanticscholar.org/graph/v1/paper/batch',
 params={'fields': 'referenceCount,citationCount,title'},
 json={"ids": ["649def34f8be52c8b66281af98ae884c09aef38b", "ARXIV:2106.15928"]}
)
print(json.dumps(r.json(), indent=2))

[
{
 "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
 "title": "Construction of the Literature Graph in Semantic Scholar",
 "referenceCount": 27,
 "citationCount": 299
},
{
 "paperId": "f712fab0d58ae6492e3cdfc1933dae103ec12d5d",
 "title": "Reinfection and low cross-immunity as drivers of epidemic resurgence under high seroprevalence: a model-based approach with application to Amazonas, Brazil",
 "referenceCount": 13,
 "citationCount": 0
}
]
Other Examples:

https://api.semanticscholar.org/graph/v1/paper/batch
{"ids":["649def34f8be52c8b66281af98ae884c09aef38b", "ARXIV:2106.15928"]}
Returns details for 2 papers.
Each paper has its paperId and title.
https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,isOpenAccess,openAccessPdf,authors
{"ids":["649def34f8be52c8b66281af98ae884c09aef38b", "ARXIV:2106.15928"]}
Returns all requested info plus paper IDs for 2 papers.

Limitations:
Can only process 500 paper ids at a time.
Can only return up to 10 MB of data at a time.
Can only return up to 9999 citations at a time.
For a list of supported IDs reference the "Details about a paper" endpoint.
query Parameters
fields
string
A comma-separated list of the fields to be returned. See the contents of Response Schema below for a list of all available fields that can be returned. The paperId field is always returned. If the fields parameter is omitted, only the paperId and title will be returned.

Use a period (“.”) for fields that have version numbers or subfields, such as the embedding, authors, citations, and references fields:

When requesting authors, the authorId and name subfields are returned by default. To request other subfields, use the format author.url,author.paperCount, etc. See the Response Schema below for available subfields.
When requesting citations and references, the paperId and title subfields are returned by default. To request other subfields, use the format citations.title,citations.abstract, etc. See the Response Schema below for available subfields.
When requesting embedding, the default Spector embedding version is v1. Specify embedding.specter_v2 to select v2 embeddings.
Examples:
fields=title,url
fields=title,embedding.specter_v2
fields=title,authors,citations.title,citations.abstract
Request Body schema: application/json
ids
Array of strings
Responses
200 List of papers with default or requested fields
400 Bad query parameters

post
/paper/batch
Request samples
Payload
Content type
application/json

Copy
Expand allCollapse all
{
"ids": [
"649def34f8be52c8b66281af98ae884c09aef38b"
]
}
Response samples
200400
Content type
application/json

Copy
Expand allCollapse all
{
"paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
"corpusId": 215416146,
"externalIds": {
"MAG": "3015453090",
"DBLP": "conf/acl/LoWNKW20",
"ACL": "2020.acl-main.447",
"DOI": "10.18653/V1/2020.ACL-MAIN.447",
"CorpusId": 215416146
},
"url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
"title": "Construction of the Literature Graph in Semantic Scholar",
"abstract": "We describe a deployed scalable system for organizing published scientific literature into a heterogeneous graph to facilitate algorithmic manipulation and discovery.",
"venue": "Annual Meeting of the Association for Computational Linguistics",
"publicationVenue": {
"id": "1e33b3be-b2ab-46e9-96e8-d4eb4bad6e44",
"name": "Annual Meeting of the Association for Computational Linguistics",
"type": "conference",
"alternate_names": [],
"url": "https://www.aclweb.org/anthology/venues/acl/"
},
"year": 1997,
"referenceCount": 59,
"citationCount": 453,
"influentialCitationCount": 90,
"isOpenAccess": true,
"openAccessPdf": {
"url": "https://www.aclweb.org/anthology/2020.acl-main.447.pdf",
"status": "HYBRID",
"license": "CCBY",
"disclaimer": "Notice: This snippet is extracted from the open access paper or abstract available at https://aclanthology.org/2020.acl-main.447, which is subject to the license by the author or copyright owner provided with this content. Please go to the source to verify the license and copyright information for your use."
},
"fieldsOfStudy": [
"Computer Science"
],
"s2FieldsOfStudy": [
{},
{},
{}
],
"publicationTypes": [
"Journal Article",
"Review"
],
"publicationDate": "2024-04-29",
"journal": {
"volume": "40",
"pages": "116 - 135",
"name": "IETE Technical Review"
},
"citationStyles": {
"bibtex": "@['JournalArticle', 'Conference']{Ammar2018ConstructionOT,\n author = {Waleed Ammar and Dirk Groeneveld and Chandra Bhagavatula and Iz Beltagy and Miles Crawford and Doug Downey and Jason Dunkelberger and Ahmed Elgohary and Sergey Feldman and Vu A. Ha and Rodney Michael Kinney and Sebastian Kohlmeier and Kyle Lo and Tyler C. Murray and Hsu-Han Ooi and Matthew E. Peters and Joanna L. Power and Sam Skjonsberg and Lucy Lu Wang and Christopher Wilhelm and Zheng Yuan and Madeleine van Zuylen and Oren Etzioni},\n booktitle = {NAACL},\n pages = {84-91},\n title = {Construction of the Literature Graph in Semantic Scholar},\n year = {2018}\n}\n"
},
"authors": [
{}
],
"citations": [
{
"paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
"corpusId": 215416146,
"externalIds": {
"MAG": "3015453090",
"DBLP": "conf/acl/LoWNKW20",
"ACL": "2020.acl-main.447",
"DOI": "10.18653/V1/2020.ACL-MAIN.447",
"CorpusId": 215416146
},
"url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
"title": "Construction of the Literature Graph in Semantic Scholar",
"abstract": "We describe a deployed scalable system for organizing published scientific literature into a heterogeneous graph to facilitate algorithmic manipulation and discovery.",
"venue": "Annual Meeting of the Association for Computational Linguistics",
"publicationVenue": {
"id": "1e33b3be-b2ab-46e9-96e8-d4eb4bad6e44",
"name": "Annual Meeting of the Association for Computational Linguistics",
"type": "conference",
"alternate_names": [],
"url": "https://www.aclweb.org/anthology/venues/acl/"
},
"year": 1997,
"referenceCount": 59,
"citationCount": 453,
"influentialCitationCount": 90,
"isOpenAccess": true,
"openAccessPdf": {},
"fieldsOfStudy": [],
"s2FieldsOfStudy": [],
"publicationTypes": [],
"publicationDate": "2024-04-29",
"journal": {},
"citationStyles": {},
"authors": [
{
"authorId": "1741101",
"name": "Oren Etzioni"
}
]
}
],
"references": [
{
"paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
"corpusId": 215416146,
"externalIds": {},
"url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
"title": "Construction of the Literature Graph in Semantic Scholar",
"abstract": "We describe a deployed scalable system for organizing published scientific literature into a heterogeneous graph to facilitate algorithmic manipulation and discovery.",
"venue": "Annual Meeting of the Association for Computational Linguistics",
"publicationVenue": {},
"year": 1997,
"referenceCount": 59,
"citationCount": 453,
"influentialCitationCount": 90,
"isOpenAccess": true,
"openAccessPdf": {},
"fieldsOfStudy": [],
"s2FieldsOfStudy": [],
"publicationTypes": [],
"publicationDate": "2024-04-29",
"journal": {},
"citationStyles": {},
"authors": []
}
],
"embedding": {
"model": "specter@v0.1.1",
"vector": []
},
"tldr": {
"model": "tldr@v2.0.0",
"text": "This paper reduces literature graph construction into familiar NLP tasks, point out research challenges due to differences from standard formulations of these tasks, and report empirical results for each task."
}
}
Paper relevance search
Examples:

https://api.semanticscholar.org/graph/v1/paper/search?query=covid+vaccination&offset=100&limit=3
Returns with total=576278, offset=100, next=103, and data is a list of 3 papers.
Each paper has its paperId and title.
https://api.semanticscholar.org/graph/v1/paper/search?query=covid&fields=url,abstract,authors
Returns with total=639637, offset=0, next=100, and data is a list of 100 papers.
Each paper has paperId, url, abstract, and a list of authors.
Each author under that list has authorId and name.
https://api.semanticscholar.org/graph/v1/paper/search?query=totalGarbageNonsense
Returns with total=0, offset=0, and data is a list of 0 papers.
https://api.semanticscholar.org/graph/v1/paper/search?query=covid&year=2020-2023&openAccessPdf&fieldsOfStudy=Physics,Philosophy&fields=title,year,authors
Returns with total=8471, offset=0, next=10, and data is a list of 10 papers.
Filters to include only papers published between 2020-2023.
Filters to include only papers with open access PDFs.
Filters to include only papers that have a field of study either matching Physics or Philosophy.
Each paper has the fields paperId, title, year, and authors.

Limitations:
Can only return up to 1,000 relevance-ranked results. For larger queries, see "/search/bulk" or the Datasets API.
Can only return up to 10 MB of data at a time.
query Parameters
query
required
string
A plain-text search query string.

No special query syntax is supported.
Hyphenated query terms yield no matches (replace it with space to find matches)
See our blog post for a description of our search relevance algorithm.

Example: graph/v1/paper/search?query=generative ai

fields
string
A comma-separated list of the fields to be returned. See the contents of the data array in Response Schema below for a list of all available fields that can be returned. The paperId field is always returned. If the fields parameter is omitted, only the paperId and title will be returned.

Use a period (“.”) for fields that have version numbers or subfields, such as the embedding, authors, citations, and references fields:

When requesting authors, the authorId and name subfields are returned by default. To request other subfields, use the format author.url,author.paperCount, etc. See the Response Schema below for available subfields.
When requesting citations and references, the paperId and title subfields are returned by default. To request other subfields, use the format citations.title,citations.abstract, etc. See the Response Schema below for available subfields.
When requesting embedding, the default Spector embedding version is v1. Specify embedding.specter_v2 to select v2 embeddings.
Examples:
fields=title,url
fields=title,embedding.specter_v2
fields=title,authors,citations.title,citations.abstract
publicationTypes
string
Restricts results to any of the following paper publication types:

Review
JournalArticle
CaseReport
ClinicalTrial
Conference
Dataset
Editorial
LettersAndComments
MetaAnalysis
News
Study
Book
BookSection
Use a comma-separated list to include papers with any of the listed publication types.

Example: Review,JournalArticle will return papers with publication types Review and/or JournalArticle.

openAccessPdf
string
Restricts results to only include papers with a public PDF. This parameter does not accept any values.

minCitationCount
string
Restricts results to only include papers with the minimum number of citations.

Example: minCitationCount=200

publicationDateOrYear
string
Restricts results to the given range of publication dates or years (inclusive). Accepts the format <startDate>:<endDate> with each date in YYYY-MM-DD format.

Each term is optional, allowing for specific dates, fixed ranges, or open-ended ranges. In addition, prefixes are supported as a shorthand, e.g. 2020-06 matches all dates in June 2020.

Specific dates are not known for all papers, so some records returned with this filter will have a null value for publicationDate. year, however, will always be present. For records where a specific publication date is not known, they will be treated as if published on January 1st of their publication year.

Examples:

2019-03-05 on March 5th, 2019
2019-03 during March 2019
2019 during 2019
2016-03-05:2020-06-06 as early as March 5th, 2016 or as late as June 6th, 2020
1981-08-25: on or after August 25th, 1981
:2015-01 before or on January 31st, 2015
2015:2020 between January 1st, 2015 and December 31st, 2020
year
string
Restricts results to the given publication year or range of years (inclusive).

Examples:

2019 in 2019
2016-2020 as early as 2016 or as late as 2020
2010- during or after 2010
-2015 before or during 2015
venue
string
Restricts results to papers published in the given venues, formatted as a comma-separated list.

Input could also be an ISO4 abbreviation. Examples include:

Nature
New England Journal of Medicine
Radiology
N. Engl. J. Med.
Example: Nature,Radiology will return papers from venues Nature and/or Radiology.

fieldsOfStudy
string
Restricts results to papers in the given fields of study, formatted as a comma-separated list:

Computer Science
Medicine
Chemistry
Biology
Materials Science
Physics
Geology
Psychology
Art
History
Geography
Sociology
Business
Political Science
Economics
Philosophy
Mathematics
Engineering
Environmental Science
Agricultural and Food Sciences
Education
Law
Linguistics
Example: Physics,Mathematics will return papers with either Physics or Mathematics in their list of fields-of-study.

offset
integer
Default: 0
Used for pagination. When returning a list of results, start with the element at this position in the list.

limit
integer
Default: 100
The maximum number of results to return.
Must be <= 100

Responses
200 Batch of papers with default or requested fields
400 Bad query parameters

get
/paper/search
Response samples
200400
Content type
application/json

Copy
Expand allCollapse all
{
"total": 15117,
"offset": 0,
"next": 0,
"data": [
{}
]
}
Paper bulk search
Behaves similarly to /paper/search, but is intended for bulk retrieval of basic paper data without search relevance:

Text query is optional and supports boolean logic for document matching.
Papers can be filtered using various criteria.
Up to 1,000 papers will be returned in each call.
If there are more matching papers, a continuation "token" will be present.
The query can be repeated with the token param added to efficiently continue fetching matching papers.

Returns a structure with an estimated total matches, batch of matching papers, and a continuation token if more results are available.
Limitations:
Nested paper data, such as citations, references, etc, is not available via this method.
Up to 10,000,000 papers can be fetched via this method. For larger needs, please use the Datasets API to retrieve full copies of the corpus.
query Parameters
query
required
string
Text query that will be matched against the paper's title and abstract. All terms are stemmed in English. By default all terms in the query must be present in the paper.

The match query supports the following syntax:

+ for AND operation
| for OR operation
- negates a term
" collects terms into a phrase
* can be used to match a prefix
( and ) for precedence
~N after a word matches within the edit distance of N (Defaults to 2 if N is omitted)
~N after a phrase matches with the phrase terms separated up to N terms apart (Defaults to 2 if N is omitted)
Examples:

fish ladder matches papers that contain "fish" and "ladder"
fish -ladder matches papers that contain "fish" but not "ladder"
fish | ladder matches papers that contain "fish" or "ladder"
"fish ladder" matches papers that contain the phrase "fish ladder"
(fish ladder) | outflow matches papers that contain "fish" and "ladder" OR "outflow"
fish~ matches papers that contain "fish", "fist", "fihs", etc.
"fish ladder"~3 mathces papers that contain the phrase "fish ladder" or "fish is on a ladder"
token
string
Used for pagination. This string token is provided when the original query returns, and is used to fetch the next batch of papers. Each call will return a new token.

fields
string
A comma-separated list of the fields to be returned. See the contents of the data array in Response Schema below for a list of all available fields that can be returned.

The paperId field is always returned. If the fields parameter is omitted, only the paperId and title will be returned.

Examples: https://api.semanticscholar.org/graph/v1/paper/search/bulk?query=covid&fields=venue,s2FieldsOfStudy

sort
string
Provides the option to sort the results by the following fields:

paperId
publicationDate
citationCount
Uses the format field:order. Ties are broken by paperId. The default field is paperId and the default order is asc. Records for which the sort value are not defined will appear at the end of sort, regardless of asc/desc order.

Examples:
publicationDate:asc - return oldest papers first.
citationCount:desc - return most highly-cited papers first.
paperId - return papers in ID order, low-to-high.

Please be aware that if the relevant data changes while paging through results, records can be returned in an unexpected way. The default paperId sort avoids this edge case.
publicationTypes
string
Restricts results to any of the following paper publication types:

Review
JournalArticle
CaseReport
ClinicalTrial
Conference
Dataset
Editorial
LettersAndComments
MetaAnalysis
News
Study
Book
BookSection
Use a comma-separated list to include papers with any of the listed publication types.

Example: Review,JournalArticle will return papers with publication types Review and/or JournalArticle.

openAccessPdf
string
Restricts results to only include papers with a public PDF. This parameter does not accept any values.

minCitationCount
string
Restricts results to only include papers with the minimum number of citations.

Example: minCitationCount=200

publicationDateOrYear
string
Restricts results to the given range of publication dates or years (inclusive). Accepts the format <startDate>:<endDate> with each date in YYYY-MM-DD format.

Each term is optional, allowing for specific dates, fixed ranges, or open-ended ranges. In addition, prefixes are supported as a shorthand, e.g. 2020-06 matches all dates in June 2020.

Specific dates are not known for all papers, so some records returned with this filter will have a null value for publicationDate. year, however, will always be present. For records where a specific publication date is not known, they will be treated as if published on January 1st of their publication year.

Examples:

2019-03-05 on March 5th, 2019
2019-03 during March 2019
2019 during 2019
2016-03-05:2020-06-06 as early as March 5th, 2016 or as late as June 6th, 2020
1981-08-25: on or after August 25th, 1981
:2015-01 before or on January 31st, 2015
2015:2020 between January 1st, 2015 and December 31st, 2020
year
string
Restricts results to the given publication year or range of years (inclusive).

Examples:

2019 in 2019
2016-2020 as early as 2016 or as late as 2020
2010- during or after 2010
-2015 before or during 2015
venue
string
Restricts results to papers published in the given venues, formatted as a comma-separated list.

Input could also be an ISO4 abbreviation. Examples include:

Nature
New England Journal of Medicine
Radiology
N. Engl. J. Med.
Example: Nature,Radiology will return papers from venues Nature and/or Radiology.

fieldsOfStudy
string
Restricts results to papers in the given fields of study, formatted as a comma-separated list:

Computer Science
Medicine
Chemistry
Biology
Materials Science
Physics
Geology
Psychology
Art
History
Geography
Sociology
Business
Political Science
Economics
Philosophy
Mathematics
Engineering
Environmental Science
Agricultural and Food Sciences
Education
Law
Linguistics
Example: Physics,Mathematics will return papers with either Physics or Mathematics in their list of fields-of-study.

Responses
200 Batch of papers with default or requested fields
400 Bad query parameters

get
/paper/search/bulk
Response samples
200400
Content type
application/json

Copy
Expand allCollapse all
{
"total": 15117,
"token": "SDKJFHSDKFHWIEFSFSGHEIURYC",
"data": [
{
"paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
"corpusId": 215416146,
"externalIds": {},
"url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
"title": "Construction of the Literature Graph in Semantic Scholar",
"abstract": "We describe a deployed scalable system for organizing published scientific literature into a heterogeneous graph to facilitate algorithmic manipulation and discovery.",
"venue": "Annual Meeting of the Association for Computational Linguistics",
"publicationVenue": {},
"year": 1997,
"referenceCount": 59,
"citationCount": 453,
"influentialCitationCount": 90,
"isOpenAccess": true,
"openAccessPdf": {},
"fieldsOfStudy": [],
"s2FieldsOfStudy": [],
"publicationTypes": [],
"publicationDate": "2024-04-29",
"journal": {},
"citationStyles": {},
"authors": []
}
]
}
Paper title search
Behaves similarly to /paper/search, but is intended for retrieval of a single paper based on closest title match to given query. Examples:

https://api.semanticscholar.org/graph/v1/paper/search/match?query=Construction of the Literature Graph in Semantic Scholar
Returns a single paper that is the closest title match.
Each paper has its paperId, title, and matchScore as well as any other requested fields.
https://api.semanticscholar.org/graph/v1/paper/search/match?query=totalGarbageNonsense
Returns with a 404 error and a "Title match not found" message.

Limitations:
Will only return the single highest match result.
query Parameters
query
required
string
A plain-text search query string.

No special query syntax is supported.
See our blog post for a description of our search relevance algorithm.

fields
string
A comma-separated list of the fields to be returned. See the contents of the data array in Response Schema below for a list of all available fields that can be returned. The paperId field is always returned. If the fields parameter is omitted, only the paperId and title will be returned.

Use a period (“.”) for fields that have version numbers or subfields, such as the embedding, authors, citations, and references fields:

When requesting authors, the authorId and name subfields are returned by default. To request other subfields, use the format author.url,author.paperCount, etc. See the Response Schema below for available subfields.
When requesting citations and references, the paperId and title subfields are returned by default. To request other subfields, use the format citations.title,citations.abstract, etc. See the Response Schema below for available subfields.
When requesting embedding, the default Spector embedding version is v1. Specify embedding.specter_v2 to select v2 embeddings.
Examples:
fields=title,url
fields=title,embedding.specter_v2
fields=title,authors,citations.title,citations.abstract
publicationTypes
string
Restricts results to any of the following paper publication types:

Review
JournalArticle
CaseReport
ClinicalTrial
Conference
Dataset
Editorial
LettersAndComments
MetaAnalysis
News
Study
Book
BookSection
Use a comma-separated list to include papers with any of the listed publication types.

Example: Review,JournalArticle will return papers with publication types Review and/or JournalArticle.

openAccessPdf
string
Restricts results to only include papers with a public PDF. This parameter does not accept any values.

minCitationCount
string
Restricts results to only include papers with the minimum number of citations.

Example: minCitationCount=200

publicationDateOrYear
string
Restricts results to the given range of publication dates or years (inclusive). Accepts the format <startDate>:<endDate> with each date in YYYY-MM-DD format.

Each term is optional, allowing for specific dates, fixed ranges, or open-ended ranges. In addition, prefixes are supported as a shorthand, e.g. 2020-06 matches all dates in June 2020.

Specific dates are not known for all papers, so some records returned with this filter will have a null value for publicationDate. year, however, will always be present. For records where a specific publication date is not known, they will be treated as if published on January 1st of their publication year.

Examples:

2019-03-05 on March 5th, 2019
2019-03 during March 2019
2019 during 2019
2016-03-05:2020-06-06 as early as March 5th, 2016 or as late as June 6th, 2020
1981-08-25: on or after August 25th, 1981
:2015-01 before or on January 31st, 2015
2015:2020 between January 1st, 2015 and December 31st, 2020
year
string
Restricts results to the given publication year or range of years (inclusive).

Examples:

2019 in 2019
2016-2020 as early as 2016 or as late as 2020
2010- during or after 2010
-2015 before or during 2015
venue
string
Restricts results to papers published in the given venues, formatted as a comma-separated list.

Input could also be an ISO4 abbreviation. Examples include:

Nature
New England Journal of Medicine
Radiology
N. Engl. J. Med.
Example: Nature,Radiology will return papers from venues Nature and/or Radiology.

fieldsOfStudy
string
Restricts results to papers in the given fields of study, formatted as a comma-separated list:

Computer Science
Medicine
Chemistry
Biology
Materials Science
Physics
Geology
Psychology
Art
History
Geography
Sociology
Business
Political Science
Economics
Philosophy
Mathematics
Engineering
Environmental Science
Agricultural and Food Sciences
Education
Law
Linguistics
Example: Physics,Mathematics will return papers with either Physics or Mathematics in their list of fields-of-study.

Responses
200 Best Title match paper with default or requested fields
400 Bad query parameters
404 No title match

get
/paper/search/match
Response samples
200400404
Content type
application/json

Copy
Expand allCollapse all
{
"data": [
{}
]
}
Details about a paper
Examples:

https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b
Returns a paper with its paperId and title.
https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b?fields=url,year,authors
Returns the paper's paperId, url, year, and list of authors.
Each author has authorId and name.
https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b?fields=citations.authors
Returns the paper's paperId and list of citations.
Each citation has its paperId plus its list of authors.
Each author has their 2 always included fields of authorId and name.

Limitations:
Can only return up to 10 MB of data at a time.
path Parameters
paper_id
required
string
The following types of IDs are supported:

<sha> - a Semantic Scholar ID, e.g. 649def34f8be52c8b66281af98ae884c09aef38b
CorpusId:<id> - a Semantic Scholar numerical ID, e.g. CorpusId:215416146
DOI:<doi> - a Digital Object Identifier, e.g. DOI:10.18653/v1/N18-3011
ARXIV:<id> - arXiv.rg, e.g. ARXIV:2106.15928
MAG:<id> - Microsoft Academic Graph, e.g. MAG:112218234
ACL:<id> - Association for Computational Linguistics, e.g. ACL:W12-3903
PMID:<id> - PubMed/Medline, e.g. PMID:19872477
PMCID:<id> - PubMed Central, e.g. PMCID:2323736
URL:<url> - URL from one of the sites listed below, e.g. URL:https://arxiv.org/abs/2106.15928v1
URLs are recognized from the following sites:

semanticscholar.org
arxiv.org
aclweb.org
acm.org
biorxiv.org
query Parameters
fields
string
A comma-separated list of the fields to be returned. See the contents of Response Schema below for a list of all available fields that can be returned. The paperId field is always returned. If the fields parameter is omitted, only the paperId and title will be returned.

Use a period (“.”) for fields that have version numbers or subfields, such as the embedding, authors, citations, and references fields:

When requesting authors, the authorId and name subfields are returned by default. To request other subfields, use the format author.url,author.paperCount, etc. See the Response Schema below for available subfields.
When requesting citations and references, the paperId and title subfields are returned by default. To request other subfields, use the format citations.title,citations.abstract, etc. See the Response Schema below for available subfields.
When requesting embedding, the default Spector embedding version is v1. Specify embedding.specter_v2 to select v2 embeddings.
Examples:
fields=title,url
fields=title,embedding.specter_v2
fields=title,authors,citations.title,citations.abstract
Responses
200 Paper with default or requested fields
400 Bad query parameters
404 Bad paper id

get
/paper/{paper_id}
Response samples
200400404
Content type
application/json

Copy
Expand allCollapse all
{
"paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
"corpusId": 215416146,
"externalIds": {
"MAG": "3015453090",
"DBLP": "conf/acl/LoWNKW20",
"ACL": "2020.acl-main.447",
"DOI": "10.18653/V1/2020.ACL-MAIN.447",
"CorpusId": 215416146
},
"url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
"title": "Construction of the Literature Graph in Semantic Scholar",
"abstract": "We describe a deployed scalable system for organizing published scientific literature into a heterogeneous graph to facilitate algorithmic manipulation and discovery.",
"venue": "Annual Meeting of the Association for Computational Linguistics",
"publicationVenue": {
"id": "1e33b3be-b2ab-46e9-96e8-d4eb4bad6e44",
"name": "Annual Meeting of the Association for Computational Linguistics",
"type": "conference",
"alternate_names": [],
"url": "https://www.aclweb.org/anthology/venues/acl/"
},
"year": 1997,
"referenceCount": 59,
"citationCount": 453,
"influentialCitationCount": 90,
"isOpenAccess": true,
"openAccessPdf": {
"url": "https://www.aclweb.org/anthology/2020.acl-main.447.pdf",
"status": "HYBRID",
"license": "CCBY",
"disclaimer": "Notice: This snippet is extracted from the open access paper or abstract available at https://aclanthology.org/2020.acl-main.447, which is subject to the license by the author or copyright owner provided with this content. Please go to the source to verify the license and copyright information for your use."
},
"fieldsOfStudy": [
"Computer Science"
],
"s2FieldsOfStudy": [
{},
{},
{}
],
"publicationTypes": [
"Journal Article",
"Review"
],
"publicationDate": "2024-04-29",
"journal": {
"volume": "40",
"pages": "116 - 135",
"name": "IETE Technical Review"
},
"citationStyles": {
"bibtex": "@['JournalArticle', 'Conference']{Ammar2018ConstructionOT,\n author = {Waleed Ammar and Dirk Groeneveld and Chandra Bhagavatula and Iz Beltagy and Miles Crawford and Doug Downey and Jason Dunkelberger and Ahmed Elgohary and Sergey Feldman and Vu A. Ha and Rodney Michael Kinney and Sebastian Kohlmeier and Kyle Lo and Tyler C. Murray and Hsu-Han Ooi and Matthew E. Peters and Joanna L. Power and Sam Skjonsberg and Lucy Lu Wang and Christopher Wilhelm and Zheng Yuan and Madeleine van Zuylen and Oren Etzioni},\n booktitle = {NAACL},\n pages = {84-91},\n title = {Construction of the Literature Graph in Semantic Scholar},\n year = {2018}\n}\n"
},
"authors": [
{}
],
"citations": [
{}
],
"references": [
{}
],
"embedding": {
"model": "specter@v0.1.1",
"vector": []
},
"tldr": {
"model": "tldr@v2.0.0",
"text": "This paper reduces literature graph construction into familiar NLP tasks, point out research challenges due to differences from standard formulations of these tasks, and report empirical results for each task."
}
}
Details about a paper's authors
Examples:

https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/authors
Returns with offset=0, and data is a list of all 3 authors.
Each author has their authorId and name
https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/authors?fields=affiliations,papers&limit=2
Returns with offset=0, next=2, and data is a list of 2 authors.
Each author has their authorId, affiliations, and list of papers.
Each paper has its paperId and title.
https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/authors?fields=url,papers.year,papers.authors&offset=2
Returns with offset=2, and data is a list containing the last author.
This author has their authorId, url, and list of papers.
Each paper has its paperId, year, and list of authors.
In that list of authors, each author has their authorId and name.
path Parameters
paper_id
required
string
The following types of IDs are supported:

<sha> - a Semantic Scholar ID, e.g. 649def34f8be52c8b66281af98ae884c09aef38b
CorpusId:<id> - a Semantic Scholar numerical ID, e.g. CorpusId:215416146
DOI:<doi> - a Digital Object Identifier, e.g. DOI:10.18653/v1/N18-3011
ARXIV:<id> - arXiv.rg, e.g. ARXIV:2106.15928
MAG:<id> - Microsoft Academic Graph, e.g. MAG:112218234
ACL:<id> - Association for Computational Linguistics, e.g. ACL:W12-3903
PMID:<id> - PubMed/Medline, e.g. PMID:19872477
PMCID:<id> - PubMed Central, e.g. PMCID:2323736
URL:<url> - URL from one of the sites listed below, e.g. URL:https://arxiv.org/abs/2106.15928v1
URLs are recognized from the following sites:

semanticscholar.org
arxiv.org
aclweb.org
acm.org
biorxiv.org
query Parameters
offset
integer
Default: 0
Used for pagination. When returning a list of results, start with the element at this position in the list.

limit
integer
Default: 100
The maximum number of results to return.
Must be <= 1000

fields
string
A comma-separated list of the fields to be returned. See the contents of the data array in Response Schema below for a list of all available fields that can be returned. The authorId field is always returned. If the fields parameter is omitted, only the authorId and name will be returned.

Use a period (“.”) for subfields of papers.

Examples:

fields=name,affiliations,papers
fields=url,papers.year,papers.authors
Responses
200 List of Authors with default or requested fields
400 Bad query parameters
404 Bad paper id

get
/paper/{paper_id}/authors
Response samples
200400404
Content type
application/json

Copy
Expand allCollapse all
{
"offset": 0,
"next": 0,
"data": [
{}
]
}
Details about a paper's citations
Fetch details about the papers that cite this paper (i.e. papers in whose bibliography this paper appears)

Examples:

Let's suppose that the paper in the examples below has 1600 citations...
https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations
Returns with offset=0, next=100, and data is a list of 100 citations.
Each citation has a citingPaper which contains its paperId and title.
https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations?fields=contexts,intents,isInfluential,abstract&offset=200&limit=10
Returns with offset=200, next=210, and data is a list of 10 citations.
Each citation has contexts, intents, isInfluential, and a citingPaper which contains its paperId and abstract.
https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations?fields=authors&offset=1500&limit=500
Returns with offset=1500, and data is a list of the last 100 citations.
Each citation has a citingPaper which contains its paperId plus a list of authors
The authors under each citingPaper has their authorId and name.
path Parameters
paper_id
required
string
The following types of IDs are supported:

<sha> - a Semantic Scholar ID, e.g. 649def34f8be52c8b66281af98ae884c09aef38b
CorpusId:<id> - a Semantic Scholar numerical ID, e.g. CorpusId:215416146
DOI:<doi> - a Digital Object Identifier, e.g. DOI:10.18653/v1/N18-3011
ARXIV:<id> - arXiv.rg, e.g. ARXIV:2106.15928
MAG:<id> - Microsoft Academic Graph, e.g. MAG:112218234
ACL:<id> - Association for Computational Linguistics, e.g. ACL:W12-3903
PMID:<id> - PubMed/Medline, e.g. PMID:19872477
PMCID:<id> - PubMed Central, e.g. PMCID:2323736
URL:<url> - URL from one of the sites listed below, e.g. URL:https://arxiv.org/abs/2106.15928v1
URLs are recognized from the following sites:

semanticscholar.org
arxiv.org
aclweb.org
acm.org
biorxiv.org
query Parameters
publicationDateOrYear
string
Restricts results to the given range of publication dates or years (inclusive). Accepts the format <startDate>:<endDate> with each date in YYYY-MM-DD format.

Each term is optional, allowing for specific dates, fixed ranges, or open-ended ranges. In addition, prefixes are supported as a shorthand, e.g. 2020-06 matches all dates in June 2020.

Specific dates are not known for all papers, so some records returned with this filter will have a null value for publicationDate. year, however, will always be present. For records where a specific publication date is not known, they will be treated as if published on January 1st of their publication year.

Examples:

2019-03-05 on March 5th, 2019
2019-03 during March 2019
2019 during 2019
2016-03-05:2020-06-06 as early as March 5th, 2016 or as late as June 6th, 2020
1981-08-25: on or after August 25th, 1981
:2015-01 before or on January 31st, 2015
2015:2020 between January 1st, 2015 and December 31st, 2020
offset
integer
Default: 0
Used for pagination. When returning a list of results, start with the element at this position in the list.

limit
integer
Default: 100
The maximum number of results to return.
Must be <= 1000

fields
string
A comma-separated list of the fields to be returned. See the contents of the data array in Response Schema below for a list of all available fields that can be returned. If the fields parameter is omitted, only the paperId and title will be returned.

Request fields nested within citedPaper the same way as fields like contexts.

Examples:

fields=contexts,isInfluential
fields=contexts,title,authors
Responses
200 Batch of citations with default or requested fields
400 Bad query parameters
404 Bad paper id

get
/paper/{paper_id}/citations
Response samples
200400404
Content type
application/json

Copy
Expand allCollapse all
{
"offset": 0,
"next": 0,
"data": [
{}
]
}
Details about a paper's references
Fetch details about the papers cited by this paper (i.e. appearing in this paper's bibliography)

Examples:

Let's suppose that the paper in the examples below has 1600 references...
https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/references
Returns with offset=0, next=100, and data is a list of 100 references.
Each reference has a citedPaper which contains its paperId and title.
https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/references?fields=contexts,intents,isInfluential,abstract&offset=200&limit=10
Returns with offset=200, next=210, and data is a list of 10 references.
Each reference has contexts, intents, isInfluential, and a citedPaper which contains its paperId and abstract.
https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/references?fields=authors&offset=1500&limit=500
Returns with offset=1500, and data is a list of the last 100 references.
Each reference has a citedPaper which contains its paperId plus a list of authors
The authors under each citedPaper has their authorId and name.
path Parameters
paper_id
required
string
The following types of IDs are supported:

<sha> - a Semantic Scholar ID, e.g. 649def34f8be52c8b66281af98ae884c09aef38b
CorpusId:<id> - a Semantic Scholar numerical ID, e.g. CorpusId:215416146
DOI:<doi> - a Digital Object Identifier, e.g. DOI:10.18653/v1/N18-3011
ARXIV:<id> - arXiv.rg, e.g. ARXIV:2106.15928
MAG:<id> - Microsoft Academic Graph, e.g. MAG:112218234
ACL:<id> - Association for Computational Linguistics, e.g. ACL:W12-3903
PMID:<id> - PubMed/Medline, e.g. PMID:19872477
PMCID:<id> - PubMed Central, e.g. PMCID:2323736
URL:<url> - URL from one of the sites listed below, e.g. URL:https://arxiv.org/abs/2106.15928v1
URLs are recognized from the following sites:

semanticscholar.org
arxiv.org
aclweb.org
acm.org
biorxiv.org
query Parameters
offset
integer
Default: 0
Used for pagination. When returning a list of results, start with the element at this position in the list.

limit
integer
Default: 100
The maximum number of results to return.
Must be <= 1000

fields
string
A comma-separated list of the fields to be returned. See the contents of the data array in Response Schema below for a list of all available fields that can be returned. If the fields parameter is omitted, only the paperId and title will be returned.

Request fields nested within citedPaper the same way as fields like contexts.

Examples:

fields=contexts,isInfluential
fields=contexts,title,authors
Responses
200 Batch of references with default or requested fields
400 Bad query parameters
404 Bad paper id

---
## 🤖 Assistant

非常好！你的思路完全正确，并且Semantic Scholar的API**完全可以**实现你设想的核心功能。你的想法——先做一个缓存/转发服务——是一个非常务实和高效的第一步。

我仔细阅读了你提供的API文档，现在帮你把你的设想和S2 API的能力完全对应起来，并梳理出一个清晰的执行流程。

### 结论：S2 API 能满足你当前的核心需求

**总的来说，Semantic Scholar API可以让你做到：**

1. **用各种ID查文献：** 你可以使用DOI, ArXiv ID, URL等多种标识符，准确地找到一篇特定的文献。
2. **获取丰富的元数据：** 你可以获取文献的标题、摘要、作者、年份、关键词（`fieldsOfStudy`）等所有你需要的基础信息。
3. **获取完整的引用关系：** 你可以清晰地得到：
 * 一篇文献**引用了**谁 (References)。
 * 一篇文献**被谁引用了** (Citations)。
4. **递归构建图谱：** 因为你能获取到所有相关文献的ID，你完全可以递归地调用API，不断扩大你的文献关系图。

---

### 基于S2 API实现你设想功能的完整流程 (A Cookbook)

我们来模拟一下你描述的用户场景，并把它分解成具体的API调用步骤。

**场景：** 用户在浏览器上打开一篇文献的页面，你的系统（比如通过浏览器插件或手动输入URL/DOI）拿到了这篇“种子文献”的ID。

**Step 1: 统一入口，获取核心文献信息**

* **你的需求：** 用户通过URL或DOI提交一篇文献，获取它的元数据（作者、摘要、关键词等）。
* **S2 API解决方案：** 使用 `GET /paper/{paper_id}` 这个endpoint。
* **具体做法：**
 * `paper_id`支持多种格式，完全符合你的需求：`DOI:10.18653/v1/N18-3011` 或 `URL:https://arxiv.org/abs/2106.15928v1`。
 * 为了获取所有你需要的元数据，你需要使用 `fields` 参数。一个典型的请求会是这样：
 ```
 GET https://api.semanticscholar.org/graph/v1/paper/DOI:10.18653/v1/N18-3011?fields=title,abstract,authors,year,fieldsOfStudy,url
 ```
 * **结果：** 你拿到了这篇“种子文献”的所有基础信息。

**Step 2: 获取所有直接相关的文献（一度关系）**

* **你的需求：** 在浏览器上推荐出所有和这篇文献相关的内容。最直接的“相关”就是引用和被引。
* **S2 API解决方案：** 使用两个专门的endpoint：
 1. `GET /paper/{paper_id}/references`：获取“种子文献”的**参考文献列表**。
 2. `GET /paper/{paper_id}/citations`：获取**引用了“种子文献”的文献列表**。
* **具体做法：**
 * 分别调用这两个API。同样，你可以用`fields`参数来指定返回的文献需要包含哪些信息（比如`fields=title,authors,year`）。
 * **结果：** 你得到了两个文献列表：一个是它引用的，一个引用它的。现在你的“待展示文献池”里有了“种子文献”和它所有的“一度关系”文献。

**Step 3: 构建子图，解析所有相关文献的内部关系**

* **你的需求：** “所有这些相关的文献的内部的关系都能被解析出来”。这是最关键的一步，也是你之前自研时觉得最复杂的地方。
* **S2 API解决方案：** 使用 `POST /paper/batch` 这个**极其强大**的批量查询接口。
* **具体做法：**
 1. **收集ID：** 将Step 1和Step 2中获取到的**所有**文献的`paperId`收集起来，形成一个ID列表，比如 `["id_seed", "id_ref1", "id_ref2", "id_cite1", ...]`。
 2. **批量查询：** 调用`POST /paper/batch`接口。在请求体（JSON）中传入这个ID列表，并且在`params`中指定你需要为**每一篇**文献都获取它的参考文献列表，即`fields=references`。
 ```python
 # 伪代码
 paper_ids = ["id_seed", "id_ref1", "id_cite1", ...]
 response = requests.post(
 'https://api.semanticscholar.org/graph/v1/paper/batch',
 params={'fields': 'references.title'}, # 请求每个文献的参考文献列表（及其标题）
 json={"ids": paper_ids}
 )
 papers_with_references = response.json()
 ```
 3. **在你的后端构建图：** 你现在拿到了你“文献池”里每一篇文献的参考文献列表。你可以在你的后端（比如用你之前设计的图数据库）进行遍历：
 * 对于文献池里的每一篇文献`P`，遍历它的`references`列表。
 * 对于`P`的每一个引用`R`，检查`R`的`paperId`是否也在你的“文献池”ID列表中。
 * 如果`R`也在，就在你的图数据库中，画一条从`P`到`R`的边。
 * 这样，你就构建出了这个子集内部完整的引用关系图！

**Step 4: 缓存与递归**

* **你的后端服务（缓存/转发）：**
 * 在以上每一步API调用后，都将结果（文献元数据、引用关系等）存入你自己的数据库（比如Redis做缓存，图数据库做永久存储）。
 * 下次请求同一篇文献时，直接从你的数据库返回，避免重复调用S2 API。这正是你设想的，非常正确！
* **递归扩展：**
 * “我还能去继续根据这个相关的文献，每天去解析新的文献。” -> **完全可以。**
 * 当用户在你的前端图谱上点击了任何一个节点（比如`id_ref1`），这个`id_ref1`就成了新的“种子文献”。你只需要重复 **Step 2** 和 **Step 3** 的过程，就可以获取`id_ref1`的“新邻居”，并把它们添加到你的图谱中，实现图的动态扩展。

---

### 总结与建议

1. **你的方案完全可行：** 你设想的“缓存转发服务”+“前端图谱展示”，配合S2的API，可以完美实现一个类似Connected Papers基础功能的原型。
2. **从简单开始：** 你的想法很对，“先不搞这么复杂”。先用S2的`citations`和`references`把**直接引用关系图**构建出来。这已经是巨大的进步了。
3. **关于Connected Papers：** 就算拿不到它的API，你也不用担心。Connected Papers的核心优势之一是除了直接引用，还能计算“语义相关性”（可能是基于共引、文献耦合或者文本向量相似度）。S2 API也提供了`embedding`字段（文本向量），这为你以后自研更高级的“相关性”推荐算法留下了可能性。**先把基于直接引用的图做好，就已经能解决80%的问题了。**

你现在的思路非常清晰，技术路径也完全打通了。放心大胆地去推进吧！

---
## 🧑‍💻 User

非常好 然后现在现在正在犹豫就是要怎么去做这个后端的服务器有两种方法，我觉得第一个是说我就是。尽量去复刻这个。啊，这个整个。请问ticks color的这个那个。查啊，这整个数据库的一个数据结构，就比如说我把它土啊什么都给他，我把他的土。同数据结构，然后包括什么所有的引用啊，所有的这些数据结构都复刻出来，然后的话。对，第一个是这种的一个方式去做。第二个的话就是。我。我只去缓存每次的访问。就比如说我用了一个。 API查询。比如说我通过某些的这个东西来查询这个。查某一个Dom来查询一篇文献我就缓存这个已经查询过的DOI。然后去把这个定位相关的内容给返回，把第二次再访问这个DOI的时候就直接放回你觉得这样怎么样？这两种方法。应该怎么做呢？

---
## 🤖 Assistant

这是个非常好的问题，直接关系到你项目初期的架构选型和开发效率。这两种方案，我称之为**“数据模型复刻”**和**“API请求缓存”**，各有优劣。

**结论先行：我强烈推荐你从方案二“API请求缓存”入手，并逐步向一个“混合模型”演进。**

为什么呢？我们来详细分析一下。

---

### 方案一：数据模型复刻 (Deep Integration)

* **做法：** 在你的后端数据库（如MySQL, PostgreSQL, 或你提到的图数据库）里，创建与Semantic Scholar（S2）几乎一模一样的表结构/节点-边模型。比如创建`papers`表，`authors`表，`citations`表等。当通过S2 API获取数据后，将其拆解并分别存入这些对应的表中。
* **优点：**
 1. **数据结构清晰，掌控力强：** 你拥有一个完全结构化的本地数据库。可以进行非常复杂和灵活的本地查询，比如“查找所有2020年后由某个作者发表的、引用数超过100的计算机科学论文”。这种查询是无法通过简单的API缓存实现的。
 2. **性能潜力高：** 一旦数据本地化，后续的各种分析、计算（比如你的双推荐系统模型训练）都可以在本地高效进行，无需再依赖外部API。
 3. **解耦性好：** 你的上层应用完全与S2解耦。未来如果想换成其他数据源，或者混合多个数据源，理论上只需要修改数据注入的ETL过程即可。
* **缺点 (致命的)：**
 1. **前期工作量巨大：** 这是最大的问题。你需要设计数据库schema，写大量的数据插入、更新逻辑。S2的数据模型相当复杂（嵌套的JSON，各种ID），完美复刻费时费力。这会让你在项目初期就陷入繁重的“数据管道工”工作中，迟迟看不到产品原型。
 2. **数据同步与一致性难题：** S2的数据是动态更新的（比如引用数会变）。你怎么保证你本地的数据和S2同步？定期全量更新？还是增量更新？这会引入非常复杂的维护逻辑。
 3. **过早优化是万恶之源：** 在项目初期，你还不完全确定最终需要哪些数据、以何种形式使用。过早地设计一个“完美”的数据库模型，很可能会在后期发现设计不合理，需要重构，成本极高。

---

### 方案二：API请求缓存 (Lightweight Proxy)

* **做法：** 将用户的每一次API请求（比如 `GET /paper/DOI:xxxx?fields=...`）作为一个整体。用请求的URL或其哈希值作为`key`，将S2返回的整个JSON结果作为`value`，存入一个简单的Key-Value存储中（比如 Redis）。
* **优点：**
 1. **极快实现，立竿见影：** 这个方案的实现非常简单。你几乎只需要写一个中间件：检查Redis里有没有`key` -> 有就返回`value` -> 没有就请求S2 API -> 存入Redis并设置一个过期时间（比如24小时）-> 返回结果。你几小时内就能搭好这个服务。
 2. **完美满足V1需求：** 对于你当前构建原型、展示功能的阶段，这个方案完全足够。你的前端只需要和你的代理服务通信，它感受不到后端是实时请求还是缓存。
 3. **自动处理数据更新：** 由于你给缓存设置了过期时间（TTL, Time-To-Live），数据会自动“刷新”，天然地解决了与S2数据同步的初步问题。
 4. **需求驱动，逐步演进：** 这种方式让你能快速搭建起应用。在使用的过程中，你会发现哪些数据是真正高频、需要深度加工的。到那时，你再针对性地把**这部分**数据进行结构化存储（即方案一的思路），这就是自然的演进。
* **缺点：**
 1. **查询能力受限：** 你无法对缓存的JSON进行复杂的结构化查询。你只能原样取回。想实现“查找某个作者的所有论文”？你得把这个作者的每一篇论文都请求并缓存一遍才行。
 2. **存储冗余：** 不同的API请求可能会返回部分重叠的数据（比如两篇论文都引用了同一篇文献），这些数据会被重复存储在不同的缓存条目里。
 3. **不适合离线分析：** 由于数据是非结构化的JSON块，直接拿来进行模型训练或深度分析很困难。

---

### 我的建议：一个务实的“混合演进”路线图

**Phase 1: 马上动手，采用方案二**

1. **搭建一个轻量级的代理（Proxy）/缓存（Cache）服务。** 技术栈可以是 Python (Flask/FastAPI) + Redis。
2. **定义你的API接口。** 你的前端/客户端只和你的服务打交道，接口可以设计得和你自己的业务逻辑更贴近。比如，你可以设计一个`/api/v1/graph_from_seed`接口，它接收一个DOI，内部去调用S2的多个API，组合结果后一次性返回给前端。
3. **实现核心的缓存逻辑。** 每个对S2的请求都用其URL+参数作为Key缓存起来，设置一个合理的TTL（比如1天或1周）。
4. **目标：** 在**一周内**，让你的前端能够基于这个后端服务，跑起一个可交互的文献图谱原型。

**Phase 2: 需求驱动，引入结构化存储（融合方案一）**

当你跑起来之后，你会发现一些问题，比如：

* “我想在图谱上展示每个作者的所有论文，每次都重新API查询太慢了。”
* “我想基于用户收藏的文献，做一些离线的推荐计算。”

这时候，就是引入结构化存储的最佳时机了。

1. **增加一个持久化数据库。** 比如PostgreSQL（JSONB字段很好用）或者你擅长的图数据库（如Neo4j）。
2. **识别核心实体：** 你会发现，`Paper`和`Author`是最核心的实体。为它们创建独立的表或节点类型。
3. **异步数据落地：** 当你的代理服务从S2获取到新的文献数据时，除了存入Redis缓存，同时**异步地**（比如通过一个消息队列）将这份JSON数据解析，并存入你的结构化数据库中。
 * 比如，解析出`paperId`, `title`, `author_list`等核心字段，存入`Papers`表。
 * 解析出`authorId`, `name`等，存入`Authors`表（注意去重）。
 * 解析出`citations`和`references`，在图数据库中创建`CITES`关系。
4. **“双读”策略：** 当一个请求进来时：
 * 先查Redis缓存（最快）。
 * 如果缓存没有，再查你的**结构化数据库**。
 * 如果结构化数据库也没有，最后才去请求S2 API。

**这个混合模型的好处是：**

* **平滑过渡：** 你不是一次性重构，而是在可用系统的基础上逐步增强。
* **各取所长：** Redis负责热点数据的高速访问，结构化数据库负责数据的沉淀、深度查询和分析。
* **风险可控：** 你只对自己真正需要的数据进行结构化，避免了初期过度设计带来的巨大浪费。

**一句话总结：用“API请求缓存”快速启动，证明产品价值；然后用“数据模型复刻”逐步构建你自己的核心数据资产。**

---
## 🧑‍💻 User

我现在想的是，初步的话，就用noe4j来做，因为还暂时拿不到api，不涉及到数据量，现在想的是，先考虑输入的处理，你看这个应该是semantic scholar返回的数据的全部吧：
paperId
string
Semantic Scholar’s primary unique identifier for a paper.

corpusId
integer
Semantic Scholar’s secondary unique identifier for a paper.

externalIds
object
An object that contains the paper’s unique identifiers in external sources. The external sources are limited to: ArXiv, MAG, ACL, PubMed, Medline, PubMedCentral, DBLP, and DOI.

url
string
URL of the paper on the Semantic Scholar website.

title
string
Title of the paper.

abstract
string
The paper's abstract. Note that due to legal reasons, this may be missing even if we display an abstract on the website.

venue
string
The name of the paper’s publication venue.

publicationVenue
object
An object that contains the following information about the journal or conference in which this paper was published: id (the venue’s unique ID), name (the venue’s name), type (the type of venue), alternate_names (an array of alternate names for the venue), and url (the venue’s website).

year
integer
The year the paper was published.

referenceCount
integer
The total number of papers this paper references.

citationCount
integer
The total number of papers that references this paper.

influentialCitationCount
integer
A subset of the citation count, where the cited publication has a significant impact on the citing publication. Determined by Semantic Scholar’s algorithm: https://www.semanticscholar.org/faq#influential-citations.

isOpenAccess
boolean
Whether the paper is open access. More information here: https://www.openaccess.nl/en/what-is-open-access.

openAccessPdf
object
An object that contains the following parameters: url (a link to the paper’s PDF), status (the type of open access https://en.wikipedia.org/wiki/Open_access#Colour_naming_system), the paper's license, and a legal disclaimer.

fieldsOfStudy
Array of strings
A list of the paper’s high-level academic categories from external sources. The possible fields are: Computer Science, Medicine, Chemistry, Biology, Materials Science, Physics, Geology, Psychology, Art, History, Geography, Sociology, Business, Political Science, Economics, Philosophy, Mathematics, Engineering, Environmental Science, Agricultural and Food Sciences, Education, Law, and Linguistics.

s2FieldsOfStudy
Array of objects
An array of objects. Each object contains the following parameters: category (a field of study. The possible fields are the same as in fieldsOfStudy), and source (specifies whether the category was classified by Semantic Scholar or by an external source. More information on how Semantic Scholar classifies papers https://blog.allenai.org/announcing-s2fos-an-open-source-academic-field-of-study-classifier-9d2f641949e5)

publicationTypes
Array of strings
The type of this publication.

publicationDate
string
The date when this paper was published, in YYYY-MM-DD format.

journal
object
An object that contains the following parameters, if available: name (the journal name), volume (the journal’s volume number), and pages (the page number range)

citationStyles
object
The BibTex bibliographical citation of the paper.

authors
Array of objects (Author Info)
citations
Array of objects (Paper Info)
references
Array of objects (Paper Info)
embedding
object (Embedding)
tldr
object (Tldr) 有这几个id都可以代表这个文献对吧：
paperId
string
Semantic Scholar’s primary unique identifier for a paper.

corpusId
integer
Semantic Scholar’s secondary unique identifier for a paper.

externalIds
object
An object that contains the paper’s unique identifiers in external sources. The external sources are limited to: ArXiv, MAG, ACL, PubMed, Medline, PubMedCentral, DBLP, and DOI.

url
string
URL of the paper on the Semantic Scholar website.

title
string
Title of the paper.，包括标题，现在想的是，这个就还是类似于之前的alias假名系统？这些东西能代表一个文献？对不对，然后考虑一下输出，输出我看了一下一共基本上是三类，一类是文献查询的自动化变体：https://api.semanticscholar.org/graph/v1/paper/autocomplete，https://api.semanticscholar.org/graph/v1/paper/batch，一类是搜索方法：https://api.semanticscholar.org/graph/v1/paper/search，https://api.semanticscholar.org/graph/v1/paper/search/bulk，https://api.semanticscholar.org/graph/v1/paper/search/match，还有一类是文献查询：https://api.semanticscholar.org/graph/v1/paper/{paper_id}，https://api.semanticscholar.org/graph/v1/paper/{paper_id}/authors，https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations，https://api.semanticscholar.org/graph/v1/paper/{paper_id}/references，我认为，第一个版本是不是可以做两件事，非常简单，第一个是建立新的api端口，全部和s2看齐。第二个是，底层链接上访问s2的接口，第三个是实现一个非常简单清晰的数据结构(以paperid&title代表一个文献？然后每个文献挂载三部分数据，元数据(除了后两者以外的全部东西)，citations和references)，然后实现最基础的https://api.semanticscholar.org/graph/v1/paper/{paper_id}的cache，然后还有第二类的转发(直接调s2api不cache)？你怎么看？说说你的想法？

---
## 🤖 Assistant

你这个初步的想法非常棒，既有战略思考，又非常落地，完全抓住了重点。我们来逐点分析和细化一下，我可以确认你的理解是完全正确的。

### 1. 核心实体与别名系统 (输入处理)

你对文献标识符的理解非常准确。

> 有这几个id都可以代表这个文献对吧：
> `paperId`
> `corpusId`
> `externalIds` (DOI, ArXiv, etc.)
> `url`
> `title`
>
> 这个就还是类似于之前的alias假名系统？这些东西能代表一个文献？对不对？

**完全正确！** 这就是你之前构思的“别名系统”的完美实践。在你的Neo4j图数据库里，你可以这样设计：

* **核心节点类型：** 创建一个 `Paper` 节点。
* **主键：** 使用 `paperId` 作为这个节点的**唯一主键**。这是一个在你的系统中永远不变的、权威的ID。
* **属性：** 将`title`, `abstract`, `year`, `citationCount` 等元数据作为 `Paper` 节点的属性存储起来。
* **别名/索引：**
 * 将`corpusId`, `DOI`, `ArXiv` 等所有`externalIds`里的ID，以及`url`，都作为 `Paper` 节点的**属性**，并且为这些属性**创建索引**。
 * 这样，当用户输入任何一个ID（比如一个DOI），你都能通过索引快速地在Neo4j中找到那个唯一的`Paper`节点。
 * **关于 `title`**：`title` 也可以用来查找，但它不是唯一的，所以通常用来做模糊搜索，而不是精确匹配。你可以为 `title` 创建全文索引（full-text index）来实现这个功能。

**Neo4j Cypher 伪代码示例：**

```cypher
// 当从S2获取一篇新论文数据时，创建或更新节点
MERGE (p:Paper {paperId: 's2_paper_id_string'})
ON CREATE SET
    p.corpusId = 12345,
    p.doi = 'doi_string',
    p.arxiv = 'arxiv_string',
    p.title = 'Paper Title',
    p.abstract = '...',
    p.year = 2023
ON MATCH SET
    p.citationCount = 42 // 如果论文已存在，只更新可变数据
```

这样，你的“别名系统”就自然而然地建立起来了。

---

### 2. V1版本的功能规划 (输出处理)

你的三步走计划非常清晰和务实，我完全赞同。我们来细化一下每个点。

> 第一个版本是不是可以做两件事，非常简单
> 1. 建立新的api端口，全部和s2看齐。
> 2. 底层链接上访问s2的接口
> 3. 实现一个非常简单清晰的数据结构(以paperid&title代表一个文献？然后每个文献挂载三部分数据，元数据(除了后两者以外的全部东西)，citations和references)，然后实现最基础的`https://api.semanticscholar.org/graph/v1/paper/{paper_id}`的cache，然后还有第二类的转发(直接调s2api不cache)？

这绝对是最佳的第一步！我们把这个思路整理成一个可执行的Action Plan:

#### Action Plan for V1:

**目标：** 构建一个具有缓存能力的、对前端友好的S2 API代理服务。

**1. API设计：接口看齐，但不完全照搬**

* **你的提议：“全部和S2看齐”** - 这在初期是个好主意，可以减少你的设计成本。
* **我的建议：稍作封装。** 我建议你的API不要100%复制S2的。只暴露你V1阶段**真正需要**的接口。这会让你的系统更简洁，也方便未来扩展。

 * **要实现的 (带Cache):**
 * `GET /api/v1/paper/{paper_id}`: 这是核心中的核心。内部调用S2的同名接口。`paper_id`可以是S2支持的任何格式（DOI, ArXiv...）。
 * （可选，但推荐）`GET /api/v1/paper/{paper_id}/graph`: 这个接口可以封装得更高级。它内部调用S2的`/citations`和`/references`，然后将一度关系的邻居节点信息一次性返回给前端。**这比让前端自己调用三次API要高效得多。**

 * **要实现的 (只转发，不Cache):**
 * `GET /api/v1/search?query=...`: 这个接口直接将请求转发给S2的`/paper/search`。因为搜索结果是动态的，且每次查询可能都不同，初期不缓存是明智的选择。
 * `GET /api/v1/autocomplete?query=...`: 同理，直接转发。

 * **暂时不实现的：**
 * `POST /paper/batch`, `/paper/search/bulk` 等批量接口，可以在你的服务**内部使用**，但初期不必暴露给前端。

**2. 数据结构设计 (在Neo4j中)**

* **你的提议：** `paperid`&`title`代表文献，挂载三部分数据（元数据，citations，references）。
* **我的细化 (Neo4j最佳实践)：**
 * **节点 (Node):** `Paper` 节点，用 `paperId` 做唯一标识。包含所有**元数据**属性（title, abstract, year...）。
 * **关系 (Relationship):**
 * `CITES` 关系。如果论文A引用了论文B，就在Neo4j里创建一条 `(A)-[:CITES]->(B)` 的关系。
 * `citations` 和 `references` 这两个数组，就不需要作为一个大的JSON字段存在节点上了。**它们被转化成了图中的`CITES`关系**，这正是图数据库的威力所在！

**3. 缓存与转发逻辑**

* **核心逻辑 (针对 `GET /api/v1/paper/{paper_id}`):**
 1. 接收请求，解析出`paper_id` (比如 `DOI:xxxx`)。
 2. **查询Neo4j:** `MATCH (p:Paper {doi: 'xxxx'}) RETURN p`。
 3. **命中缓存 (Hit):**
 * 如果Neo4j中找到了这个`Paper`节点，太棒了！
 * 再查询它的邻居：`MATCH (p:Paper {doi: 'xxxx'})-[:CITES]->(ref) RETURN ref` 和 `MATCH (p:Paper {doi: 'xxxx'})<-[:CITES]-(cite) RETURN cite`。
 * 组合数据，返回给前端。
 4. **未命中缓存 (Miss):**
 * 如果Neo4j中没有，说明这是第一次请求。
 * 调用S2 API: `GET https://api.semanticscholar.org/graph/v1/paper/DOI:xxxx?fields=...,citations,references`。一次性把所有一度关系都拿回来。
 * **解析并存入Neo4j：**
 * 创建或更新这篇“种子论文”的`Paper`节点。
 * 遍历返回的`citations`和`references`数组。对其中的每一篇论文，也在Neo4j里创建对应的`Paper`节点（如果不存在的话），并创建`CITES`关系。
 * 这个过程就是“扩图”。
 * 将刚从S2获取的数据返回给前端。


* **转发逻辑 (针对 `/search` 和 `/autocomplete`)**
 * 非常简单，就是做一个纯粹的HTTP代理。收到请求，原封不动地发给S2，收到S2的响应，再原封不动地返回给前端。

---

### 总结你的想法 + 我的建议

你的计划非常好，方向完全正确。总结下来就是：

1. **后端服务：** 用 FastAPI/Flask + Neo4j。
2. **API层：** 设计一组对前端友好的、经过封装的API（如`/paper/{id}/graph`），而不是完全照搬S2。对于搜索类API，做纯转发。
3. **数据模型：** 以`Paper`为核心节点，`paperId`为主键，各种外部ID为索引属性。文献间关系用`CITES`边来表示。
4. **核心工作流：** 实现“Cache Miss -> 请求S2 -> 扩充Neo4j图 -> 返回数据”的核心逻辑。

这个计划**完美地平衡了**初期开发的**速度**和未来系统的**可扩展性**。你没有陷入“复刻完整S2数据库”的泥潭，而是从一个最小可用产品（MVP）出发，同时又为你未来构建复杂的知识图谱打下了坚实的数据基础。

我觉得你现在可以充满信心地开始写代码了。这个方案非常可靠。

---
## 🧑‍💻 User

我想快速实现一下一个最小版本。想设计一下后端结构，fastapi+redis+neo4j?你觉得可以吗？然后应该以什么架构来做？应该怎么考虑？任务？查询？怎么设计？用什么做初始化？

---
## 🤖 Assistant

非常好！"快速实现一个最小版本"是绝对正确的策略。你选择的技术栈 **FastAPI + Redis + Neo4j** 堪称黄金组合，非常适合这个项目：

* **FastAPI:** 性能高，开发快，自带API文档（Swagger UI），非常适合做API服务。
* **Redis:** 速度极快的Key-Value数据库，用作高速缓存层，降低对Neo4j和外部API的访问压力。
* **Neo4j:** 专业的图数据库，完美匹配你处理文献引用关系的需求。

下面我为你设计一个清晰、可落地的后端架构和实施步骤。

---

### 架构设计：分层解耦的代理服务

我们将整个后端看作一个智能代理，它有三个层次：**接口层、逻辑/缓存层、数据层**。

```
+-------------------------------------------------------------+
|                     用户/前端 (Client)                      |
+---------------------------------^---------------------------+
                                  | HTTP请求
                                  |
+---------------------------------v---------------------------+
|    [接口层] FastAPI - API Endpoints                         |
|    - /api/v1/paper/{paper_id}                               |
|    - /api/v1/search?query=...                               |
+---------------------------------^---------------------------+
                                  | 调用服务
                                  |
+---------------------------------v---------------------------+
|    [逻辑/缓存层] Service Layer (核心逻辑)                     |
|                                                             |
|    1. 查 Redis 缓存？ --(Hit)--> 返回                       |
|          |                                                  |
|          | (Miss)                                           |
|          v                                                  |
|    2. 查 Neo4j 持久化数据？ --(Hit)--> 存入Redis, 返回     |
|          |                                                  |
|          | (Miss)                                           |
|          v                                                  |
|    3. 请求 Semantic Scholar API --(Success)-->               |
|          |                         |                        |
|          | (Fail)                  v                        |
|          v                  4. [异步任务] ARQ               |
|    返回错误                  - 解析数据                     |
|                               - 存入 Neo4j                   |
|                               - 存入 Redis                   |
+---------------------------------^---------------------------+
                                  | 读/写
                                  |
+-----------------v----------------------+--------------------+
| [数据层]                             |                    |
| +----------------+  +----------------+  +----------------+ |
| |     Redis      |  |     Neo4j      |  | Semantic Scholar| |
| | (高速缓存)     |  | (图数据持久化)   |  | (外部数据源)   | |
| +----------------+  +----------------+  +----------------+ |
+-------------------------------------------------------------+
```

### 核心组件和职责

1. **FastAPI (接口层):**
 * **职责:** 接收HTTP请求，验证输入参数，调用逻辑层的服务，并返回标准的HTTP响应。它不应该包含复杂的业务逻辑。
 * **设计:**
 * `main.py`: FastAPI应用实例。
 * `routers/paper.py`: 定义所有与论文相关的路由，如`/paper/{paper_id}`。
 * `routers/search.py`: 定义所有搜索相关的路由。

2. **Service Layer (逻辑层):**
 * **职责:** 实现核心业务逻辑。这是你的大脑。它协调Redis, Neo4j, 和S2 API的调用。
 * **设计:**
 * `services/paper_service.py`: 包含如 `get_paper_details` 这样的函数。这个函数会依次检查Redis、Neo4j，最后才请求S2。
 * `clients/s2_client.py`: 封装所有对Semantic Scholar API的直接调用。这样便于统一管理API Key、错误处理和请求头。

3. **Redis (缓存层):**
 * **职责:** 缓存**API的最终响应结果**。Key可以是请求的唯一标识（如`s2:paper:DOI:xxxx:fields=title,abstract`），Value就是S2返回的JSON字符串。
 * **目的:** 对完全相同的请求，实现毫秒级响应。

4. **Neo4j (数据持久化层):**
 * **职责:** 存储结构化的图数据。`Paper`节点和它们之间的`CITES`关系。
 * **目的:**
 * 作为比Redis更持久的“二级缓存”。
 * 让你能够执行图查询，这是Redis做不到的。比如“找到这篇论文的两度引文”。
 * 为未来的复杂分析打下基础。

5. **ARQ (异步任务处理器):**
 * **职责:** 处理耗时的S2 API调用和后续的数据处理流程。
 * **目的:** **让API请求快速返回**。将"从S2获取数据"这个慢操作（网络请求）扔给ARQ在后台执行，API立即返回任务ID，用户可以通过轮询或WebSocket获取结果。这能极大地提升用户体验。
