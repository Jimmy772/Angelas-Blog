from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import Unauthorized
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
login_manager = LoginManager(app)
Bootstrap(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///blogs.db")

# config 'SQLALCHEMY_BINDS' is being used to create additional databases/tables
# they can be opened as individual dbs or different tables in one db
# You need to use bind keys to open as seperate dbs[__bind_key__ = db_name]
# Check line 39 for demonstation

# app.config['SQLALCHEMY_BINDS'] = {'users': 'sqlite:///user.db', 'comments':'sqlite:///comments.db'}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES


# Parent class to blogpost and Comments
class User(UserMixin, db.Model):
    # __bind_key__ = 'users
    __tablename__ = "User_Data"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    # PARENT RELATIONSHIP WITH BLOGPOST
    posts = relationship("BlogPost", back_populates="author")
    # PARENT RELATIONSHIP WITH COMMENTS
    comments = relationship("Comments", back_populates="comment_author")


# Child class to Usre but parent class to Comments
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    # CHILD RELATIONSHIP WITH USER
    author_id = db.Column(db.Integer, db.ForeignKey("User_Data.id"))
    author = relationship("User", back_populates="posts")
    # PARENT RELATIONSHIP WITH COMMENTS
    comments = relationship("Comments", back_populates="parent_post")


class Comments(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    # CHILD RELATIONSHIP WITH USER
    author_id = db.Column(db.Integer, db.ForeignKey("User_Data.id"))
    comment_author = relationship("User", back_populates="comments")
    # CHILD RELATIONSHIP WITH BLOGPOST
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")



# Create user_loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# create decorator to only allow access to admin account
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id == 1:
            return f(*args, **kwargs)
        else:
            raise Unauthorized(description="This feature is only accessible by the admin account")
    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=request.form["email"]).first()
        if user:
            flash("User already exists. Login instead")
            return redirect(url_for('login'))
        else:
            password = form.password.data
            hashed_pass = generate_password_hash(password,"pbkdf2:sha256",8)
            name = form.name.data
            new_user = User(email=email, password=hashed_pass, name=name)
            db.session.add(new_user)
            db.session.commit()
            user = User.query.filter_by(email=email).first()
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password,password):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Invalid password")
                return redirect(url_for('login'))
        else:
            flash("Invalid email account please try again or create a new one")
            return redirect(url_for('login'))
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods = ["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        new_comment = Comments(text=form.comment.data,
                                comment_author=current_user,
                                parent_post=requested_post)
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods = ["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)

@admin_only
@app.route("/edit-post/<int:post_id>")
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)

@admin_only
@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@admin_only
@app.route("/delete-comment/<int:comment_id>/<int:post_id>", methods=["GET"])
def delete_comment(comment_id,post_id):
    comment_to_delete = Comments.query.get(comment_id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('show_post', post_id=post_id))


if __name__ == "__main__":
    db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
    
