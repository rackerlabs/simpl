# coding=utf-8
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
#
# pylint: disable=R0903,R0904,C0111,C0103

"""Tests for mongodb module."""

import unittest

import pymongo
import mock
import mongobox
import six

from simpl.db import mongodb


class TestDB(mongodb.SimplDB):

    __collections__ = ('widgets', 'gadgets', 'womps', 'prose')

    def tune(self):
        pass  # bypass async tuning in tests


class TestMongoDB(unittest.TestCase):

    """Test :mod:`simpl.db.mongodb`."""

    @classmethod
    def setUpClass(cls):
        """Fire up a sandboxed mongodb instance."""
        # Enable text search if testing on 2.4
        mongobox.mongobox.DEFAULT_ARGS.extend(
            ['--setParameter', 'textSearchEnabled=true'])
        cls.box = mongobox.MongoBox()
        cls.box.start()

    @classmethod
    def tearDownClass(cls):
        """Stop the sanboxed mongodb instance."""
        if hasattr(cls, 'box') and isinstance(cls.box, mongobox.MongoBox):
            if cls.box.running() is True:
                cls.box.stop()
                cls.box = None

    def setUp(self):
        """Get a client conection to our sandboxed mongodb instance."""
        if hasattr(self, 'box'):
            self.db = TestDB("mongodb://127.0.0.1:%s/test" % self.box.port)
        else:
            self.fail("No sandboxed MongoDB")

    def test_write_read(self):
        self.db.widgets.save("A", {"name": "test A"})
        self.db.widgets.save("B", {"name": "test B"})
        self.db.widgets.save("B2", {"name": "test B"})
        expected = (
            [
                {'name': 'test A'},
                {'name': 'test B'},
                {'name': 'test B'},
            ],
            3
        )
        self.assertEqual(self.db.widgets.list(), expected)

        first = self.db.widgets.list(limit=1, sort=["name"])[0]
        self.assertEqual(first, [{'name': 'test A'}])

        last = self.db.widgets.list(name="test B", limit=1, sort=["-name"])[0]
        self.assertEqual(last, [{'name': 'test B'}])

        self.assertEqual(self.db.widgets.count(), 3)

        self.db.widgets.update('B2', {'name': 'Changed!'})
        result = self.db.widgets.get('B2')
        self.assertEqual(result, {'name': 'Changed!'})

        self.db.widgets.delete("B2")
        updated = (
            expected[0][0:2],
            2
        )
        self.assertEqual(self.db.widgets.list(), updated)
        self.assertTrue(self.db.widgets.exists("A"))
        self.assertFalse(self.db.widgets.exists("B2"))

    def test_multiwrite(self):
        self.db.gadgets.save("A", {"name": "test A"})
        self.db.gadgets.save("B", {"name": "test B"})
        self.db.gadgets.save("B2", {"name": "test B"})
        result = self.db.gadgets.update_multi({'name': 'test X'},
                                              name='test B')
        self.assertEqual(result, 2)
        expected = (
            [
                {'name': 'test A'},
                {'name': 'test X'},
                {'name': 'test X'},
            ],
            3
        )
        self.assertEqual(self.db.gadgets.list(), expected)

    def test_write_dots(self):
        self.db.womps.save("A.B.C", {"name.1": "test.A"})
        self.assertEqual(self.db.womps.get('A.B.C'), {"name.1": "test.A"})

    def test_singleton(self):
        db1 = mongodb.database(
            "mongodb://127.0.0.1:%s/test" % self.box.port,
            db_class=TestDB)
        db2 = mongodb.database(
            "mongodb://127.0.0.1:%s/test" % self.box.port,
            db_class=TestDB)
        db3 = mongodb.database(
            "mongodb://127.0.0.1:%s/OTHER" % self.box.port,
            db_class=TestDB)
        self.assertTrue(db1 is db2)
        self.assertFalse(db1 is db3)

    def test_text_search(self):
        self.db.create_index(
            'prose',
            [("name", pymongo.TEXT),
             ("keywords", pymongo.TEXT)],
            background=False,
            name="idx_a",
            default_language="none")  # include stop words like "Do"
        self.db.create_index('prose', "name", background=False, name="idx_b")

        self.db.prose.save("A", {"name": "John Adams",
                                 "keywords": "economics wealth nations"})
        self.db.prose.save("B", {"name": "Johnny Walker",
                                 "keywords": "whisky health"})
        # Single word
        search = mongodb.build_text_search(['john'])
        result = self.db.prose.list(**search)
        self.assertEqual(result[0][0]['name'], "John Adams")

        # Second word
        search = mongodb.build_text_search(['adams'])
        result = self.db.prose.list(**search)
        self.assertEqual(result[0][0]['name'], "John Adams")

        # Multiple words in search
        search = mongodb.build_text_search(['wealth', 'health'])
        result = self.db.prose.list(**search)
        self.assertEqual(result[1], 2)

        # Keyword
        search = mongodb.build_text_search(['whisky'])
        result = self.db.prose.list(**search)
        self.assertEqual(result[0][0]['name'], "Johnny Walker")

    @mock.patch.object(pymongo.collection.Collection, 'update')
    def test_write_fail(self, mock_update):
        mock_update.return_value = mock.Mock(
            errmsg='bad data',
            get=mock.Mock(return_value=0)
        )
        with six.assertRaisesRegex(self, mongodb.SimplMongoError, 'bad data'):
            self.db.widgets.save("A", {"name": "test A"})


class TestDataScrubbing(unittest.TestCase):

    """Test the code that makes sure data is clean."""

    def test_blanks(self):
        self.assertEqual(mongodb.scrub(''), '')
        self.assertEqual(mongodb.scrub({}), {})
        self.assertEqual(mongodb.scrub([]), [])
        self.assertEqual(mongodb.scrub(0), 0)

    def test_clean(self):
        self.assertEqual(mongodb.scrub(1), 1)
        self.assertEqual(mongodb.scrub("string"), "string")
        self.assertEqual(mongodb.scrub([1]), [1])
        self.assertEqual(mongodb.scrub({'1': 'A'}), {'1': 'A'})
        self.assertEqual(mongodb.scrub(True), True)
        self.assertEqual(mongodb.scrub(False), False)

    def test_invalid(self):
        with self.assertRaises(mongodb.ValidationError):
            mongodb.scrub(self)

    @mock.patch.object(mongodb.json.encoder, 'encode_basestring')
    def test_failsafe(self, mock_encoder):
        mock_encoder.side_effect = Exception("Surprise!")
        with self.assertRaises(mongodb.ValidationError):
            mongodb.scrub('safe')


class TestMongoDBCapabilities(unittest.TestCase):

    """Test MongoDB's capabilities against our driver assumptions.

    We do things like document partial updates and locking with mongodb. The
    way we do that might break with certain versions of MongoDBN, so this test
    module validates that our assumptions and design work as expected.
    """

    @classmethod
    def setUpClass(cls):
        """Fire up a sandboxed mongodb instance."""
        cls.box = mongobox.MongoBox()
        cls.box.start()

    @classmethod
    def tearDownClass(cls):
        """Stop the sanboxed mongodb instance."""
        if hasattr(cls, 'box') and isinstance(cls.box, mongobox.MongoBox):
            if cls.box.running() is True:
                cls.box.stop()
                cls.box = None

    def setUp(self):
        """Get a client conection to our sandboxed mongodb instance."""
        if hasattr(self, 'box'):
            self.client = self.box.client()
        else:
            self.fail("No sandboxed MongoDB")

    def tearDown(self):
        """Disconnect the client."""
        if hasattr(self, 'box'):
            self.client = None

    def test_mongo_instance(self):
        """Verify the mongobox's mongodb instance is working."""
        self.assertTrue(self.client.server_info())

    def test_mongo_object_creation(self):
        """Verify object creation."""
        col = self.client.tdb.c1
        col.save({})
        self.assertIn('tdb', self.client.database_names())
        self.assertIn('c1', self.client.tdb.collection_names())
        self.assertEqual(1, col.count())

    def test_mongo_custom_id(self):
        """Verify assigning IDs."""
        col = self.client.tdb.c2
        col.save({'id': 'our-id'})
        result = col.find_one({'id': 'our-id'})
        self.assertIn('id', result, msg="Our ID was not returned")
        self.assertIn('_id', result, msg="Mongo no longer has an _id field")
        self.assertEqual(len(result), 2, msg="Mongo added unexpected fields")
        self.assertNotEqual(result['id'], result['_id'],
                            msg="Mongo's and our IDs are now the same")
        self.assertEqual(result['id'], 'our-id', msg="Our ID is not intact")

    def test_mongo_projection(self):
        """We can return our IDs with only specific fields."""
        col = self.client.tdb.c3
        col.save({'id': 'our-id', 'name': 'Ziad', 'hide': 'X'})
        result = col.find_one(
            {'id': 'our-id'},
            {
                '_id': 0,
                'hide': 0
            }
        )
        self.assertDictEqual(result, {'id': 'our-id', 'name': 'Ziad'})

    def test_partial_update(self):
        """We can update only specific fields."""
        col = self.client.tdb.c4
        col.save({'id': 'our-id', 'status': 'PLANNED', 'name': 'Ziad'})
        obj = col.find_one({'id': 'our-id'}, {'_id': 0})
        self.assertIn('name', obj, msg="'name' was not saved")

        col.update(
            {'id': 'our-id'},
            {
                '$set': {
                    'status': 'UP'
                }
            }
        )
        obj = col.find_one({'id': 'our-id'}, {'_id': 0})
        self.assertIn('name', obj, msg="'name' was removed by an update")
        self.assertDictEqual(obj, {'id': 'our-id', 'status': 'UP',
                                   'name': 'Ziad'})

    def test_deep_partial_unsupported(self):
        """Mongo update is like a dict.update() - it overwrites whole keys."""
        col = self.client.tdb.c5
        col.save(
            {
                'id': 'our-id',
                'status': 'PLANNED',
                'subobj': {
                    'name': 'Ziad',
                    'status': 'busy',
                }
            }
        )

        col.update(
            {'id': 'our-id'},
            {
                '$set': {
                    'status': 'UP',
                    'subobj': {
                        'status': 'gone fishing'
                    }
                }
            }
        )
        obj = col.find_one({'id': 'our-id'}, {'_id': 0})
        self.assertIn('id', obj, msg="'id' was removed by an update")
        self.assertIn('subobj', obj, msg="'subobj' was removed by an update")
        subobj = obj['subobj']
        self.assertNotIn('name', subobj, msg="Writing partials now works!!!")
        self.assertDictEqual(obj, {
            'id': 'our-id',
            'status': 'UP',
            'subobj': {
                'status': 'gone fishing'
            }
        })

    def test_write_if_zero(self):
        """Verify that syntax for locking an object works."""
        col = self.client.tdb.c6
        col.save(
            {
                'id': 'our-id',
                '_lock': 0
            }
        )
        obj = col.find_and_modify(
            query={
                '$or': [{'_lock': {'$exists': False}}, {'_lock': 0}]
            },
            update={
                '$set': {
                    '_lock': "1",
                }
            },
            fields={'_lock': 0, '_id': 0}
        )
        self.assertEqual(obj['id'], 'our-id')

    def test_write_if_field_not_exists(self):
        """Verify that syntax for locking an object works."""
        col = self.client.tdb.c7
        col.save(
            {
                'id': 'our-id',
            }
        )
        obj = col.find_and_modify(
            query={
                '$or': [{'_lock': {'$exists': False}}, {'_lock': 0}]
            },
            update={
                '$set': {
                    '_lock': "1",
                }
            },
            fields={'_lock': 0, '_id': 0}
        )
        self.assertEqual(obj['id'], 'our-id')

    def test_skip_if_filtered(self):
        """Verify that syntax for locking an object works."""
        col = self.client.tdb.c8
        col.save(
            {
                'id': 'our-id',
                '_lock': 'my-key'
            }
        )
        obj = col.find_and_modify(
            query={
                '$or': [{'_lock': {'$exists': False}}, {'_lock': 0}]
            },
            update={
                '$set': {
                    '_lock': "1",
                }
            },
            fields={'_lock': 0, '_id': 0}
        )
        self.assertIsNone(obj)

if __name__ == '__main__':
    unittest.main()
