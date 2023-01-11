"""User model tests."""

# run these tests like:
#
#    
#    FLASK_ENV=production python -m unittest test_user_model.py


import os
# from flask_bcrypt import Bcrypt
from unittest import TestCase
from sqlalchemy import exc
from models import db, User, Message, Follows

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

        self.user1 = User.signup("testuser1", "test1@test.com", "password", None)
        self.user2 = User.signup("testuser2", "test2@test.com", "password", None)
        self.user3 = User.signup("testuser3", "test3@test.com", "password", None)

        
        db.session.add_all([self.user1, self.user2, self.user3])
        db.session.commit()
        from flask_bcrypt import Bcrypt
        self.bcrypt = Bcrypt()

        self.client = app.test_client()

    def tearDown(self):
        """Clean up any fouled transaction."""
        db.session.rollback()
        db.drop_all()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    # # # # # # # # # # # # # # #  # 
    # Test following functionality # 
    # # # # # # # # # # # # # # #  # 

    def test_user_following(self):
        """Test if a user is following another user works as intended"""
        self.user1.following.append(self.user2)
        self.user1.following.append(self.user3)
        db.session.commit()
        self.assertTrue(self.user1.is_following(self.user2))
        self.assertTrue(self.user1.is_following(self.user3))
        self.assertFalse(self.user2.is_following(self.user1))
        self.assertFalse(self.user3.is_following(self.user1))

    
    def test_user_follows(self):
        """Test if following a user and being followed works as intended"""
        follow = Follows(user_being_followed_id=self.user1.id, user_following_id = self.user2.id)
        db.session.add(follow)
        db.session.commit()

        self.assertEqual(len(self.user2.followers), 0)
        self.assertEqual(len(self.user1.followers), 1)
        self.assertEqual(len(self.user2.following), 1)
        self.assertEqual(len(self.user1.following), 0)

        self.assertEqual(self.user1.followers[0].id, self.user2.id)
        self.assertEqual(self.user2.following[0].id, self.user1.id)

    def test_is_following(self):
        """Additonal is_following() function on Class Model"""
        self.user1.following.append(self.user2)
        db.session.commit()

        self.assertTrue(self.user1.is_following(self.user2))
        self.assertFalse(self.user2.is_following(self.user1))

    def test_is_followed_by(self):
        """Additonal is_followed_by() function on Class Model"""
        self.user1.following.append(self.user2)
        db.session.commit()

        self.assertTrue(self.user2.is_followed_by(self.user1))
        self.assertFalse(self.user1.is_followed_by(self.user2))
    

    # # # # # # # # # # # # # # # # # # 
    # Test if User can like a message #
    # # # # # # # # # # # # # # # # # # 

    def test_user_likes_message(self):
        """Test that a user can like a message and it will be added to the list of liked messages"""
        message = Message(text="Test message", user=self.user1)
        db.session.add(message)
        db.session.commit()
        # Test that user1 has no likes initially
        self.assertEqual(len(self.user1.likes), 0)
        # Add message to the likes of the user1
        self.user1.likes.append(message)
        db.session.commit()
        # Test that there is a like now and the message is in the list of likes
        self.assertEqual(len(self.user1.likes), 1)
        self.assertEqual(self.user1.likes[0].text, "Test message")


    # # # # # # # # # # # # # # # # # # #
    # Test if user sign up functionality #
    # # # # # # # # # # # # # # # # # # #

    def test_valid_signup(self):
        u_test = User.signup("testtesttest", "testtest@test.com", "password", None)
        db.session.add(u_test)
        db.session.commit()

        u_test = User.query.filter_by(username="testtesttest").first()
        self.assertIsNotNone(u_test)
        self.assertEqual(u_test.username, "testtesttest")
        self.assertEqual(u_test.email, "testtest@test.com")
        self.assertNotEqual(u_test.password, "password")
        # Bcrypt strings should start with $2b$
        self.assertTrue(u_test.password.startswith("$2b$"))

    def test_invalid_username_signup(self):
            invalid = User.signup(None, "test@test.com", "password", None)
            db.session.add(invalid)
            with self.assertRaises(exc.IntegrityError) as context:
                db.session.commit()

    def test_invalid_email_signup(self):
            invalid = User.signup("testtest", None, "password", None)
            db.session.add(invalid)
            with self.assertRaises(exc.IntegrityError) as context:
                db.session.commit()

    def test_invalid_password_signup(self):
            with self.assertRaises(ValueError) as context:
                User.signup("testtest", "email@email.com", "", None)
            
            with self.assertRaises(ValueError) as context:
                User.signup("testtest", "email@email.com", None, None)

    # # # # # # # # # # # # # # # # # # # # #
    # Test User Authentication funcionality #
    # # # # # # # # # # # # # # # # # # # # #

    def test_valid_authentication(self):
        u = User.authenticate(self.user1.username, "password")
        self.assertIsNotNone(u)
        self.assertEqual(u.id, self.user1.id)
    
    def test_invalid_username(self):
        self.assertFalse(User.authenticate("badusername", "password"))

    def test_wrong_password(self):
        self.assertFalse(User.authenticate(self.user1.username, "badpassword"))

    def test_password_hashing(self):
        """Test that a plaintext password is hashed"""
        u = User.signup("testuser", "test@test.com", "password123", "/static/images/default-pic.png")
        self.assertNotEqual(u.password, "password123")
        self.assertTrue(self.bcrypt.check_password_hash(u.password, "password123"))


