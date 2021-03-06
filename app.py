from flask import Flask, render_template, redirect, flash, session

from functools import wraps

from flask_debugtoolbar import DebugToolbarExtension

from models import db, connect_db, User, Note

from forms import RegisterForm, LoginForm, NewNoteForm, UpdateNoteForm


app = Flask(__name__)

app.config['SECRET_KEY'] = "secret"

app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql:///notes"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

connect_db(app)
db.create_all()


def login_required(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        # if user is not logged in, redirect to login page
        if not session.get("username"):
            flash("Access denied")
            return redirect("/login")
        # finally call f. f() now haves access to g.user
        return func(*args, **kwargs)
    return wrap


def auth_required(func):
    @wraps(func)
    def wrap(*args, **kwargs):

        if kwargs['username'] != session.get('username'):
            flash('Access denied')
            return redirect('/login')
        return func(*args, **kwargs)
    return wrap


@app.route('/')
def homepage():
    return redirect('/register')

#####Login Authentication####


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if 'username' in session:
        return redirect(f"/users/{session['username']}")

    if form.validate_on_submit():
        username = form.username.data
        pwd = form.password.data
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        user = User.register(username, pwd, email, first_name, last_name)
        db.session.add(user)
        db.session.commit()
        session["username"] = user.username
        return redirect(f'/users/{user.username}')

    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()

    if 'username' in session:
        return redirect(f"/users/{session['username']}")

    if form.validate_on_submit():
        username = form.username.data
        pwd = form.password.data

        user = User.authenticate(username, pwd)

        if user:
            session["username"] = user.username
            return redirect(f'/users/{user.username}')
        else:
            form.username.errors = ["Invalid username/password"]

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    """ clear info from the session and redirect """

    session.pop("username", None)  # None
    flash('You were logged out')

    return redirect('/')

### User authorization ###


@app.route('/users/<username>')
@login_required
@auth_required
def secret(username):

    user = User.query.get_or_404(username)
    return render_template('secret.html', user=user)


@app.route('/users/<username>/delete', methods=['POST'])  # why not delete?
@login_required
@auth_required
def delete_user(username):
    """ remove user from db and also delete their notes
        redirect to root """

    user = User.query.get_or_404(username)

    db.session.delete(user)
    db.session.commit()

    session.pop("username", None)

    return redirect('/')


@app.route('/users/<username>/notes/add', methods=["GET", "POST"])
@login_required
def add_note(username):
    form = NewNoteForm()

    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data

        note = Note(owner=username, title=title, content=content)

        db.session.add(note)
        db.session.commit()

        return redirect(f"/users/{username}")

    return render_template('create_note.html', form=form)


@app.route('/notes/<int:note_id>/update', methods=["GET", "POST"])
def update_note(note_id):

    note = Note.query.get_or_404(note_id)
    form = UpdateNoteForm(obj=note)

    if note.owner != session.get("username"):
        flash('Not authorized')
        return redirect('/')

    if form.validate_on_submit():
        note.title = form.title.data
        note.content = form.content.data
        db.session.commit()
        return redirect(f"/users/{note.owner}")

    return render_template('update_note.html', form=form)


@app.route('/notes/<int:note_id>/delete', methods=["POST"])
def delete_note(note_id):

    note = Note.query.get_or_404(note_id)
    username = note.owner

    if username != session.get("username"):
        flash('Not authorized')
        return redirect('/')

    db.session.delete(note)
    db.session.commit()

    return redirect(f"/users/{username}")


@app.errorhandler(404)
def error_handler404(e):
    return render_template('404.html')


@app.errorhandler(401)
def error_handler401(e):
    # if usernamne not in session...
    return render_template('401.html')
