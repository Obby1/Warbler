import os
import pdb

from flask import Flask, render_template, request, flash, redirect, session, g, url_for
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from flask_bcrypt import check_password_hash
from forms import UserAddForm, LoginForm, MessageForm, ProfileForm
from models import db, connect_db, User, Message, Likes

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)
# python -m pdb app.py

##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""
    # left below as get request (not get or 404) since we want g.user to return None 
    #   if no session of current user
    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""


    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""
    # pdb.set_trace()
    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""
    do_logout()
    return redirect(url_for("login"))


########################
# General user routes:###
#########################

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.filter_by(id=user_id).first()
    following = user.following
    return render_template('users/following.html', user=user, following=following)



@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', followed_user=user.following, user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""
    user_id = g.user.id
    user = User.query.get_or_404(user_id)
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    form = ProfileForm()
    if form.validate_on_submit():
        if not check_password_hash(user.password, form.password.data):
            flash("Incorrect password", "danger")
            return redirect("/users/profile")
            # Update the user's information in the database
        g.user.username = form.username.data
        g.user.email = form.email.data
        g.user.image_url = form.image_url.data
        g.user.header_image_url = form.header_image_url.data
        g.user.bio = form.bio.data
        g.user.location = form.location.data
        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(f"/users/{g.user.id}")
    return render_template("users/edit.html", form=form, form_type="Edit", user=user)



@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user and related messages."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
        
    # Find all messages with a user_id matching the one you're trying to delete
    messages = Message.query.filter_by(user_id=g.user.id)
    
    # Delete those messages
    for message in messages:
        db.session.delete(message)
        
    do_logout()

    db.session.delete(g.user)
    db.session.commit()
    flash("User and User Warbles Deleted", "danger")
    return redirect("/signup")



###################
# Messages routes:#
###################

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""
    # new - needs commit with comments
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)

    if msg.user_id != g.user.id:
        # if message owner's user id is not the same as logged in user's user id
        flash("Access unauthorized.", "danger")
        return redirect("/")

    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


############################
# Homepage and error pages#
###########################


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        followed_users = [user.id for user in g.user.following]
        followed_users.append(g.user.id)
        messages = (Message
                    .query
                    .filter(Message.user_id.in_(followed_users))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())
        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')


################
# Like routes:##
################
@app.route('/users/add_like/<int:message_id>', methods=['POST'])
def add_like(message_id):
        if not g.user:
            flash("Access unauthorized. You must be logged in to like a warble.", "danger")
            return redirect("/login")
        message = Message.query.get_or_404(message_id)
        #check if user already like the message
        existing_like = Likes.query.filter_by(user_id=g.user.id, message_id=message_id).first()
        if existing_like:
            #if already liked, remove the like
            db.session.delete(existing_like)
            flash("You have unliked the warble.", "success")
        else:
            #if warble hasn't been liked, add like to join table
            like = Likes(user_id = g.user.id, message_id= message_id)
            db.session.add(like)
            flash("You have liked the warble", "success")
        # flash("You have unliked the warble.", "success")
        db.session.commit()
        return redirect(f"/messages/{message_id}")


@app.route('/users/<int:user_id>/likes', methods=['GET'])
def show_likes(user_id):
    """show messages user has liked"""
    # Get the user
    user = User.query.filter_by(id=user_id).first()

    # Get the list of messages the user has liked
    messages = user.likes
    return render_template('messages/likes.html', user=user, likes=messages)




##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req


# To Do:
# If following no one, display all warbles OR separate tab for viewing all warbles vs viewing
#   warbles from people you follow
# Change search to include user's and messages as well
# Change add_like route to be neutral since it's used for adding and removing likes


# Further Study
# There are lots of areas of further study.

# You won???t have time to do all of these. Instead, pick those that seem most interesting to you.

# Custom 404 Page
# Learn how to add a custom 404 page, and make one.

# Add AJAX
# There are two areas where AJAX would really benefit this site:

# When you like/unlike a warble, you shouldn???t have to refresh the page
# You should be able to compose a warble via a popup modal that is available on every page via the navigation bar button.
# DRY Up the Templates
# There???s a lot of repetition in this app!

# Here are some ideas to clean up repetition:

# Learn about the {% include %} statement in Jinja and use this to not have the forms be so repetitive.
# Learn about the {% macro %} and {% import %} statements in Jinja; you can use these to be even more clever, and get rid of a lot of repetition in the user detail, followers, followed_user pages, and more.
# DRY Up the Authorization
# Advanced but interesting

# In many routes, there are a few lines that check for is-a-user-logged-in. You could solve this by writing your own ???decorator???, like ???@app.route???, but that checks if the g.user object is not null and, if not, flashes and redirects.

# You???ll need to do some searching and reading about Python decorators to do this.

# DRY Up the URLs
# Throughout the app, there are many, many places where URLs for the app are hardcoded throughout ??? consider the number of places that refer to URLs like /users/[user-id].

# Flask has a nice feature, url_for(), which can produce the correct URL when given a view function name. This allows you to not use the URLs directly in other routes/templates, and makes it easier in the future if you even needed to move URLs around (say, is /users/[user-id] needed to change to /users/detail/[user-id].

# Learn about this feature and use it throughout the site.

# Optimize Queries
# In some places, Warbler may be making far more queries than it needs: the homepage can use more than 75 queries!

# Using the Flask-DebugToolbar, audit query usage and fix some of the worst offenders.

# Make a Change Password Form
# Make a form with three fields:

# current password
# new password
# new password again, for confirmation
# If the user is logged in and they provide the right password and their new passwords match, change their password.

# Hint: do this by making a new method on the User class, rather than hard-coding stuff about password hashing in the view function.

# Allow ???Private??? Accounts
# Add a feature that allows a user to make their account ???private???. A private account should normally only the profile page without messages.

# You can follow a private account ??? but that user will need to approve your follow. At the point you are successfully following a private account, you should then be able to see their messages.

# Note: this will require some schema changes and thoughtful design. Can you do this in a way that doesn???t sprinkle (even more) if conditions around? Can you add any useful functions on the User or Message classes?

# Add Admin Users
# Add a feature for ???admin users??? ??? these are users that have a new field on their model set to true.

# Admin users can:

# delete any user???s messages
# delete any user
# edit a user profile; when an admin user edits a profile, they should be able to see and set the ???admin??? field to make another user an admin
# User Blocking
# Add a feature where users can block other users:

# when viewing a user page, there should be a block/unblock button
# blocked users view the blocker in any way
# Direct Messages
# Add a feature of ???direct messages??? ??? users being able to send private messages to another user, visible only to that user.

# There are lots of possibilities on how far you want to take this one.