"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows, Likes

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        
        user = User.signup("testing", "testing@test.com", "password", None)
        user.id = 94566

        db.session.commit()

        u = User.query.get(user.id)
        self.user=user
        self.user.id=user.id
 

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_message_model(self):
        """Does basic model work?"""
        
        msg = Message(
            text="a warble",
            user_id=self.user.id
        )

        db.session.add(msg)
        db.session.commit()

        # User should have 1 message
        self.assertEqual(len(self.user.messages), 1)
        self.assertEqual(self.user.messages[0].text, "a warble")


    def test_message_likes(self):
        msg1 = Message(
            text="a warble",
            user_id=self.user.id
        )

        msg2 = Message(
            text="a very interesting warble",
            user_id=self.user.id 
        )

        user = User.signup("yetanothertest", "t@email.com", "password", None)
        user.id = 888
        
        db.session.add_all([msg1, msg2, user])
        db.session.commit()

        user.likes.append(msg1)

        db.session.commit()

        likes = Likes.query.filter(Likes.user_id == user.id).all()
        self.assertEqual(len(likes), 1)
        self.assertEqual(likes[0].message_id, msg1.id)


        