"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_user_views.py



import os
from app import app
from unittest import TestCase

from models import db, connect_db, Message, User, Likes, Follows
from bs4 import BeautifulSoup

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        # create test client
        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser.id = 8989
        

        self.user1 = User.signup("abc", "test1@test.com", "password", None)
        self.user1.id = 778
        
        self.user2 = User.signup("efg", "test2@test.com", "password", None)
        self.user2.id = 884
        
        self.user3 = User.signup("hij", "test3@test.com", "password", None)
        self.user4 = User.signup("testing", "test4@test.com", "password", None)

        db.session.commit()

    def tearDown(self):
        resp = super().tearDown()
        db.session.rollback()
        return resp

    def test_users_index(self):
       #test_client is a prebuilt method in flask which makes it easier to quickly test  programs.
        with app.test_client() as client:
            resp = client.get("/users")
            
            self.assertIn("@testuser", str(resp.data))
            self.assertIn("@abc", str(resp.data))
            self.assertIn("@efg", str(resp.data))
            self.assertIn("@hij", str(resp.data))
            self.assertIn("@testing", str(resp.data))

    def test_users_search(self):
         with app.test_client() as client:
            resp = client.get("/users?q=test")

            self.assertIn("@testuser", str(resp.data))
            self.assertIn("@testing", str(resp.data))            

            self.assertNotIn("@abc", str(resp.data))
            self.assertNotIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))

    def test_user_show(self):
        with app.test_client() as client:
            resp = client.get(f"/users/{self.testuser.id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("@testuser", str(resp.data))

    #Add sample message data 
    def setup_likes(self):
        msg1 = Message(text="trending warble", user_id=self.testuser.id)
        msg2 = Message(text="Eating some lunch", user_id=self.testuser.id)
        msg3 = Message(id=9876, text="likable warble", user_id=self.user1.id)
        db.session.add_all([msg1, msg2, msg3])
        db.session.commit()

        like1 = Likes(user_id=self.testuser.id, message_id=9876)

        db.session.add(like1)
        db.session.commit()

    def test_user_show_with_likes(self):
        #call the setup_likes() method to add sample Message data
        self.setup_likes()

        with app.test_client() as client:
            resp = client.get(f"/users/{self.testuser.id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("@testuser", str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)

            # test for a count of 2 messages
            self.assertIn("2", found[0].text)

            # Test for a count of 0 followers
            self.assertIn("0", found[1].text)

            # Test for a count of 0 following
            self.assertIn("0", found[2].text)

            # Test for a count of 1 like
            self.assertIn("1", found[3].text)

    def test_add_like(self):
        msg = Message(id=1984, text="The earth is round", user_id=self.user1.id)
        db.session.add(msg)
        db.session.commit()

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = client.post("/messages/1984/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id==1984).all()
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].user_id, self.testuser.id)

    def test_remove_like(self):
        #call the setup_likes() method to add sample Message data
        self.setup_likes()

        msg = Message.query.filter(Message.text=="likable warble").one()
        self.assertIsNotNone(msg)
        self.assertNotEqual(msg.user_id, self.testuser.id)

        like = Likes.query.filter(
            Likes.user_id==self.testuser.id and Likes.message_id==msg.id
        ).one()

        # Now we are sure that testuser likes the message "likable warble"
        self.assertIsNotNone(like)

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = client.post(f"/messages/{msg.id}/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id==msg.id).all()
            # the like has been deleted
            self.assertEqual(len(likes), 0)

    def test_unauthenticated_like(self):
        #call the setup_likes() method to add sample Message data
        self.setup_likes()

        msg = Message.query.filter(Message.text=="likable warble").one()
        self.assertIsNotNone(msg)

        like_count = Likes.query.count()

        with app.test_client() as client:
            resp = client.post(f"/messages/{msg.id}/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            self.assertIn("Access unauthorized", str(resp.data))

            # The number of likes has not changed since making the request
            self.assertEqual(like_count, Likes.query.count())

    #Add sample Follows data
    def setup_followers(self):
        follower1 = Follows(user_being_followed_id=self.user1.id, user_following_id=self.testuser.id)
        follower2 = Follows(user_being_followed_id=self.user2.id, user_following_id=self.testuser.id)
        follower3 = Follows(user_being_followed_id=self.testuser.id, user_following_id=self.user1.id)

        db.session.add_all([follower1,follower2,follower3])
        db.session.commit()

    def test_user_show_with_follows(self):
        #call the setup_followers() method to add sample Follows data
        self.setup_followers()

        with app.test_client() as client:
            resp = client.get(f"/users/{self.testuser.id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("@testuser", str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)

            # test for a count of 0 messages
            self.assertIn("0", found[0].text)

            # Test for a count of 2 following
            self.assertIn("2", found[1].text)

            # Test for a count of 1 follower
            self.assertIn("1", found[2].text)

            # Test for a count of 0 likes
            self.assertIn("0", found[3].text)

    def test_show_following(self):
        #call the setup_followers() method to add sample Follows data
        self.setup_followers()
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = client.get(f"/users/{self.testuser.id}/following")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("@abc", str(resp.data))
            self.assertIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))
            self.assertNotIn("@testing", str(resp.data))

    def test_show_followers(self):
        #call the setup_followers() method to add sample Follows data
        self.setup_followers()
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = client.get(f"/users/{self.testuser.id}/followers")

            self.assertIn("@abc", str(resp.data))
            self.assertNotIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))
            self.assertNotIn("@testing", str(resp.data))

    def test_unauthorized_following_page_access(self):
        #call the setup_followers() method to add sample Follows data
        self.setup_followers()
        with app.test_client() as client:

            resp = client.get(f"/users/{self.testuser.id}/following", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("@abc", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))

    def test_unauthorized_followers_page_access(self):
        #call the setup_followers() method to add sample Follows data
        self.setup_followers()
        with app.test_client() as client:

            resp = client.get(f"/users/{self.testuser.id}/followers", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("@abc", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))