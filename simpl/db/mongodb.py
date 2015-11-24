# Copyright (c) 2011-2013 Rackspace Hosting
# All Rights Reserved.
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""MongoDB backend wrapper.

This module exposes the SimplDB class which provides an opinionated backend
implementation that supports using MongoDB. The opinons of the implementation
are:

- we want to just supply a URL to connect to the database.
- we want to use our own "id" fields to key documents (not built-in ObjectId).
  This is to more easily match API IDs and control indexing.
- we want the indexes to be specified in code (in the repo).
- want to perform basic CRUD operations on collections.
- we only want to simple, JSON objects (dicts, lists, strings, booleans, and
  integers)


### Usage

To use this module:
- subclass the SimplDB class and supply your own collection definitions:

  from simpl.db import mongodb

  class MyDB(mongodb.SimplDB):

      __collections__ = ('widgets', 'gadgets')

  db = mongodb.database('mongodb://localhost', db_class=MyDB)
  db.widgets.save("A", {"name": "test A"})
  db.widgets.save("B", {"name": "test B"})
  db.widgets.save("B2", {"name": "test B"})
  print("All:", db.widgets.list())
  print("Last:", db.widgets.list(name="test B", limit=1, sort=["-name"])[0])
  db.widgets.delete("B2")


### Indexing

For more advanced control over indexing, override the `.tune()` method:

    def tune(self):
        conn = self.connection
        conn['widgets'].create_index("keys", background=True)

This module works with the :mod:`rest` module which parses query params into
mongodb-compatible queries (including text search for `q=` params) and uses the
cursor call results (iterable, count) to return paginated results with a known
collection count.
"""

from __future__ import print_function

import copy
import json

try:
    import eventlet
except ImportError:
    pass
try:
    import mongo_proxy
except ImportError:
    mongo_proxy = None
import pymongo
from pymongo.son_manipulator import SONManipulator

from simpl import log
from simpl import secrets

LOG = log.getLogger(__name__)


class SimplDBError(Exception):

    """Any DB Exception."""


class SimplMongoError(SimplDBError):

    """MongoDB Exception."""


class ValidationError(Exception):

    """Failed Input Validation."""


def scrub(data):
    """Verify and clean data. Raise error if input fails."""
    # blanks, Nones, and empty strings can stay as is
    if not data:
        return data
    if isinstance(data, (int, float)):
        return data
    if isinstance(data, list):
        return [scrub(entry) for entry in data]
    if isinstance(data, dict):
        return {scrub(key): scrub(value) for key, value in data.items()}
    try:
        return json.encoder.encode_basestring(data)[1:-1]
    except TypeError as exc:
        raise ValidationError("Input '%s' is not a permitted type: %s" % (data,
                                                                          exc))
    except Exception as exc:
        raise ValidationError("Input '%s' not permitted: %s" % (data, exc))


def build_text_search(strings, name_field='name'):
    """Build mongodb query that performs text search for string(s).

    This is the backend implementation of the front-end search box on a list.
    It performs text search on a text index and a regex search on a `name`
    field. The value(s) for this are parsed by `rest.process_params` from the
    `q` query param.

    :param list strings: strings to search on.
    :keyword str name: field to search on in addition to search index.

    For example, searching the following collection for 'john':

    #  Name    Description (in text index)
    -  ------  ---------------------------
    1  John    Big boss
    2  Johnny  Boss' son
    3  Thomas  John's first employee
    4  Henry   He quit

    Search returns all records except the last one:
    #1 - match on name
    #2 - partial match on name
    #3 - text index match on description

    >>> import pprint
    >>> pprint.pprint(build_text_search(['john']))
    {'$or': [{'$text': {'$search': 'john'}},
             {'name': {'$options': 'i', '$regex': 'john'}}]}

    >>> import pprint
    >>> pprint.pprint(build_text_search(['john', 'tom'], name_field='objName'))
    {'$or': [{'$text': {'$search': 'john tom'}},
             {'$or': [{'objName': {'$options': 'i', '$regex': 'john'}},
                      {'objName': {'$options': 'i', '$regex': 'tom'}}]}]}
    """
    assert isinstance(strings, list)

    text_search = {'$text': {'$search': ' '.join(strings)}}

    searches = [{name_field: {'$regex': s, '$options': 'i'}} for s in strings]
    if len(searches) == 1:
        name_search = searches[0]
    else:
        name_search = {'$or': searches}

    return {'$or': [text_search, name_search]}


class SimplDB(object):

    """Database wrapper.

    This Database wrapper by default disables a SONManipulator that is
    normally enabled through pymongo by default. That manipulator
    is found at pymongo.son_manipulator.ObjectIdInjector

    With the injector disabled, if you were to write a document,
    have manipulate=True AND *not* provide an _id, you wouldn't
    see an insert confirmation, and pymongo does not
    inform you of the objectid for the document that was inserted.

    We think the purpose of that manipulator was to enable pymongo
    to always return a write confirmation that was associated with a
    particular object id, where that object id could be generated
    *by* pymongo (using ObjectIdInjector) *before* inserting the document.

    This caused a couple problems:
        1. When performing a partial update of a document,
           if you did not provide the _id with the data,
           pymongo would generate a new one, and whatever
           document you were pointing to (based on a spec)
           would have its _id overwritten.
        2. Typically, we would not reach (1), because a
           partial update will make use of the $set operator,
           (or any operator) and pymongo would add the _id to
           that set of data, creating a document that would
           look something like this:
                * {'$set': {'data.to.update': 'yes'},
                   '_id': ObjectId('530264af09df64dd0235b155')}
           where you would receive the following error:

            pymongo.errors.OperationFailure: Modifiers and non-modifiers
                                             cannot be mixed

    To bypass all customized '_id' and data manipulation, instantiate the class
    with:

        db = SimpDB("mongodb://localhost:27017", disable_id_injector=False,
                    manipulators=(,))

    """

    __collections__ = tuple()

    def __init__(self, connection_string, disable_id_injector=True,
                 manipulators=None):
        """Initialize database wrapper.

        :param str connection_string: a full mongodb URL (supports creds too).
        :keyword bool disable_id_injector: see class docs for detailed info.
        :keyword list manipulators: a list of manipulator instances to add to
            each connection instance. Default is None, which sets two
            manipulators for handling JSON serialization and keys with "." in
            their name. To disable adding any manilutors, pass in a blank
            iterable (ex. [] or (,)).
        """
        self.connection_string = connection_string
        self.safe_connection_string = secrets.hide_url_password(
            self.connection_string)
        parsed = pymongo.uri_parser.parse_uri(self.connection_string)
        self.database_name = parsed['database']
        self.disable_id_injector = disable_id_injector
        self.manipulators = manipulators
        if self.manipulators is None:
            self.manipulators = [
                KeyTransform(".", "_dot_"),
                ObjectSerializer(),
            ]
        self._client = None
        self._connection = None
        if eventlet:
            self.client_lock = eventlet.semaphore.Semaphore()
            eventlet.spawn_n(self.tune)
        else:
            self.tune()

    def _set_client(self):
        """Set client property if not set."""
        if self._client is None:
            if mongo_proxy:
                self._client = mongo_proxy.MongoProxy(
                    pymongo.MongoClient(self.connection_string),
                    logger=LOG)
            else:
                LOG.warning("MongoDBProxy not imported. AutoReconnect "
                            "is not enabled.")
                self._client = mongo_proxy.MongoProxy(
                    pymongo.MongoClient(self.connection_string),
                    logger=LOG)
            LOG.debug("Created new connection to MongoDB: %s",
                      self.safe_connection_string)

    @property
    def client(self):
        """Return a lazy-instantiated pymongo client.

        When running with eventlet, connection causes IO and can result in more
        than one MongoDB client getting instantiatied, so we wrap the code in
        a semaphore to make sure only one mongodb client is instantiated per
        SimplDB class.
        """
        if eventlet:
            with self.client_lock:
                self._set_client()
        else:
            self._set_client()
        return self._client

    @property
    def connection(self):
        """Connect to and return mongodb database object."""
        if self._connection is None:

            self._connection = self.client[self.database_name]

            if self.disable_id_injector:
                incoming = self._connection._Database__incoming_manipulators
                for manipulator in incoming:
                    if isinstance(manipulator,
                                  pymongo.son_manipulator.ObjectIdInjector):
                        incoming.remove(manipulator)
                        LOG.debug("Disabling %s on mongodb connection to "
                                  "'%s'.",
                                  manipulator.__class__.__name__,
                                  self.database_name)
                        break

            for manipulator in self.manipulators:
                self._connection.add_son_manipulator(manipulator)
            LOG.info("Connected to mongodb on %s (database=%s)",
                     self.safe_connection_string, self.database_name)

        return self._connection

    def create_index(self, collection, index_name, **kwargs):
        """Safely attempt to create index."""
        try:
            self.connection[collection].create_index(index_name, **kwargs)
        except Exception as exc:
            LOG.warn("Error tuning mongodb database: %s", exc)

    def tune(self):
        """Documenting & Automating Index Creation."""
        LOG.debug("Tuning database")

        #
        # Audit Logs (port coming to simpl)
        #
        self.create_index('audits', "event",
                          background=True,
                          name="audits_event")

    def __getattr__(self, key):
        """Access the Collection attribute of the database connector."""
        if key in self.__collections__:
            return Collection(self.connection, key.lower())
        else:
            raise AttributeError("SimplDB does not have attribute '%s'" % key)


class Collection(object):

    """Wrapper for a collection."""

    def __init__(self, connection, collection_name):
        """Initialize collection wrapper."""
        self.connection = connection
        self.collection_name = collection_name
        self._collection = self.connection[collection_name]

    def save(self, key, data):
        """Create or Save a document in a collection.

        :returns: count of records added/updated
        """
        write = data.copy()
        write['_id'] = key
        response = self._collection.update({'_id': key}, write, upsert=True,
                                           manipulate=True)
        if response.get('ok') != 1:
            raise SimplMongoError("Error saving document '%s': %s" %
                                  (key, response.errmsg))
        LOG.debug("DB WRITE: %s.%s", self.collection_name, response)
        return response.get('n')

    def update_multi(self, data, **kwargs):
        """Partial update (by kwarg filter) of document(s).

        The filter to match documents is built from kwargs.
        Requires at least one kwarg to build a filter.

        'data' AND/OR kwarg filter(s) may contain dot notation
        fields, in order to specify nested values in the documents, e.g.

            collection.update({'datatowrite': 'yes'},
                              **{'my.nested.field': 'match!'})

        The dictionary provided as 'data' will update only
        those corresponding fields and subfields in the database
        document, without clobbering other fields and
        subfields.
        """
        if not kwargs:
            raise TypeError("update() requires at least one "
                            "kwarg to build a filter (0 given).")

        spec = kwargs
        write = data.copy()

        response = self._collection.update(
            spec, {'$set': write}, multi=True, upsert=False, manipulate=True)

        if response.get('ok') != 1:
            raise SimplMongoError("Error updating document '%s': %s" %
                                  (spec.get('_id'), response.errmsg))
        LOG.debug("DB UPDATE: %s.%s", self.collection_name, response)
        return response.get('n')

    def update(self, key, data):
        """Update document by key with partial data.

        Updates the document matching _id=<key> with 'data'
            Where 1st argument 'key' is <key>

        'data' may contain dot notation fields in
        order to specify nested values in the documents, e.g.

            collection.update(<document_key>,
                              {'my.nested.field': 'match!'})

        The dictionary provided as 'data' will update only
        those corresponding fields and subfields in the database
        document, without clobbering other fields and
        subfields.

        :returns: count of records added/updated
        """
        if key:
            spec = {'_id': key}

        write = data.copy()

        response = self._collection.update(
            spec, {'$set': write}, multi=False, upsert=False, manipulate=True)

        if response.get('ok') != 1:
            raise SimplMongoError("Error updating document '%s': %s" %
                                  (spec.get('_id'), response.errmsg))
        LOG.debug("DB UPDATE: %s.%s", self.collection_name, response)
        return response.get('n')

    def count(self):
        """Number of documents in a collection."""
        return self._collection.count()

    # pylint: disable=E0202
    def list(self, offset=0, limit=0, fields=None, sort=None, **kwargs):
        """Return filtered list of documents in a collection.

        For text-based search, we support searching on a name/string field by
        regex and text index. So strings passed in to a r=text search are
        used to filter collections by text index and regex on a named field.

        :param offset: for pagination, which record to start attribute
        :param limit: for pagination, how many records to return
        :param fields: list of field names to return (otherwise returns all)
        :param sort: list of fields to sort by (prefix with '-' for descending)
        :param kwargs: key/values to find (only supports equality for now)

        :returns: a tuple of the list of documents and the total count
        """
        try:
            cursor = self._cursor(offset=offset, limit=limit, fields=fields,
                                  sort=sort, **kwargs)
            return list(cursor), cursor.count()
        except pymongo.errors.OperationFailure as exc:
            # This is workaround for mongodb v2.4 and 'q' filter params
            try:
                kwargs['$or'][0]['$text']['$search']
            except (KeyError, IndexError):
                raise exc
            LOG.warn("Falling back to hard-coded mongo v2.4 search behavior")
            kwargs = self.search_alternative(limit, **kwargs)
            LOG.debug("Modified kwargs: %s", kwargs)
            cursor = self._cursor(offset=offset, limit=limit, fields=fields,
                                  sort=sort, **kwargs)
            return list(cursor), cursor.count()

    def search_alternative(self, limit, **kwargs):
        """Replace $search with $in for mongodb v2.4.

        This is a workaround for mongo v2.4 not supporting the $search keyword.
        This workaround is hardcoded specifically for the 'q' query param. The
        text search is executed first and the ids of the found documents are
        used to replace the $search filter with a $in filter.
        """
        search_term = kwargs['$or'][0]['$text']['$search']
        response = self._collection.database.command(
            'text', self._collection.name,
            search=search_term,
            project={'_id': 1},
            limit=limit
        )
        id_list = [e['obj']['_id'] for e in response['results']]
        kwargs['$or'][0] = {'_id': {'$in': id_list}}
        return kwargs

    def _cursor(self, offset=0, limit=0, fields=None, sort=None, **kwargs):
        """Return a cursor on a filtered list of documents in a collection.

        :param offset: for pagination, which record to start attribute
        :param limit: for pagination, how many records to return
        :param fields: list of field names to return (otherwise returns all)
        :param sort: list of fields to sort by (prefix with '-' for descending)
        :param kwargs: key/values to find (only supports equality for now)

        :returns: a tuple of a cursor on documents and the total count

        Note: close the cursor after using it if you don't exhaust it
        """
        projection = {'_id': False}
        if fields:
            projection.update({field: True for field in fields})
        results = self._collection.find(kwargs, projection)
        if sort:
            sort_pairs = sort[:]
            for index, field in enumerate(sort):
                if field[0] == "-":
                    sort_pairs[index] = (field[1:], pymongo.DESCENDING)
                else:
                    sort_pairs[index] = (field, pymongo.ASCENDING)
            results.sort(sort_pairs)
        results.skip(offset or 0).limit(limit or 0)
        return results

    def delete(self, key):
        """Delete a document by id."""
        assert key, "A key must be supplied for delete operations"
        self._collection.remove(spec_or_id={'_id': key})
        LOG.debug("DB REMOVE: %s.%s", self.collection_name, key)

    def exists(self, key):
        """True if a document exists."""
        try:
            return self._collection.find_one({'_id': key}) is not None
        except StopIteration:
            return False

    def get(self, key):
        """Get a document by id."""
        doc = self._collection.find_one({'_id': key})
        if doc:
            doc.pop('_id')
            return doc


class KeyTransform(SONManipulator):

    """Transforms keys going to database and restores them coming out.

    This allows keys with dots in them to be used (but does break searching on
    them unless the find command also uses the transform).

    Example & test:
        # To allow `.` (dots) in keys
        import pymongo
        client = pymongo.MongoClient("mongodb://localhost")
        db = client['delete_me']
        db.add_son_manipulator(KeyTransform(".", "_dot_"))
        db['mycol'].remove()
        db['mycol'].update({'_id': 1}, {'127.0.0.1': 'localhost'}, upsert=True,
                           manipulate=True)
        print db['mycol'].list().next()
        print db['mycol'].list({'127_dot_0_dot_0_dot_1': 'localhost'}).next()

    Note: transformation could be easily extended to be more complex.
    """

    def __init__(self, replace, replacement):
        """Initialize KeyTransform."""
        self.replace = replace
        self.replacement = replacement

    def transform_key(self, key):
        """Transform key for saving to database."""
        return key.replace(self.replace, self.replacement)

    def revert_key(self, key):
        """Restore transformed key returning from database."""
        return key.replace(self.replacement, self.replace)

    def transform_incoming(self, son, collection):
        """Recursively replace all keys that need transforming."""
        return self._transform_incoming(copy.deepcopy(son), collection)

    def _transform_incoming(self, son, collection, skip=0):
        """Recursively replace all keys that need transforming."""
        skip = 0 if skip < 0 else skip
        if isinstance(son, dict):
            for (key, value) in son.items():
                if key.startswith('$'):
                    if isinstance(value, dict):
                        skip = 2
                    else:
                        pass  # allow mongo to complain
                if self.replace in key:
                    k = key if skip else self.transform_key(key)
                    son[k] = self._transform_incoming(
                        son.pop(key), collection, skip=skip - 1)
                elif isinstance(value, dict):  # recurse into sub-docs
                    son[key] = self._transform_incoming(value, collection,
                                                        skip=skip - 1)
                elif isinstance(value, list):
                    son[key] = [
                        self._transform_incoming(k, collection, skip=skip - 1)
                        for k in value
                    ]
            return son
        elif isinstance(son, list):
            return [self._transform_incoming(item, collection, skip=skip - 1)
                    for item in son]
        else:
            return son

    def transform_outgoing(self, son, collection):
        """Recursively restore all transformed keys."""
        if isinstance(son, dict):
            for (key, value) in son.items():
                if self.replacement in key:
                    k = self.revert_key(key)
                    son[k] = self.transform_outgoing(son.pop(key), collection)
                elif isinstance(value, dict):  # recurse into sub-docs
                    son[key] = self.transform_outgoing(value, collection)
                elif isinstance(value, list):
                    son[key] = [self.transform_outgoing(item, collection)
                                for item in value]
            return son
        elif isinstance(son, list):
            return [self.transform_outgoing(item, collection)
                    for item in son]
        else:
            return son


class ObjectSerializer(SONManipulator):

    """Serialize Simpl objects in the database layer."""

    def transform_incoming(self, son, collection):
        """Recursively replace all keys that need transforming.

        This will serialize all objects that have a
        serialize method before sending them to mongo.

        """
        for (key, value) in son.items():
            if isinstance(value, dict):  # Make sure we recurse into sub-docs
                son[key] = self.transform_incoming(value, collection)
            elif hasattr(value, 'serialize'):
                LOG.debug("Serializing object: %s", value)
                son[key] = value = value.serialize()
        return son


def database(connection_string, db_class=SimplDB):
    """Return database singleton instance.

    This function will always return the same database instance for the same
    connection_string. It stores instances in a dict saved as an attribute of
    this function.
    """
    if not hasattr(database, "singletons"):
        database.singletons = {}
    if connection_string not in database.singletons:
        instance = db_class(connection_string)
        database.singletons[connection_string] = instance
    return database.singletons[connection_string]


def params_to_mongo(query_params):
    """Convert HTTP query params to mongodb query syntax.

    Converts the parse query params into a mongodb spec.

    :param dict query_params: return of func:`rest.process_params`
    """
    if not query_params:
        return {}
    for key, value in query_params.items():
        if isinstance(value, list):
            query_params[key] = {'$in': value}
    return query_params
