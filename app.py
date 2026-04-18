import os
import time
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from wtforms import FileField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo

from flask import Flask, flash, redirect, render_template, request, session, url_for

upload_folder = os.path.join(os.getcwd(), "static/uploads")
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["UPLOAD_FOLDER"] = upload_folder
app.config["Database"] = "sqlite:///data.db"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "mani123"
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    profile_pic = db.Column(db.String(120), nullable=True)


class Post(db.Model):
    __tablename__ = "Post"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=False)
    user = db.relationship("User", backref="posts")


class Comment(db.Model):
    __tablename__ = "Comment"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("User.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("Post.id"), nullable=False)


class Register(FlaskForm):
    uname = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = StringField("Password", validators=[DataRequired()])
    confirm = StringField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")


class Login(FlaskForm):
    uname = StringField("Username", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    content = StringField("Content", validators=[DataRequired()])
    image = FileField(
        "upload Image",
        validators=[FileAllowed(["jpg", "png"], "Images only!")],
    )
    submit = SubmitField("Create Post")


class EditPostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    content = StringField("Content", validators=[DataRequired()])
    submit = SubmitField("Update Post")


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    posts = Post.query.all()
    return render_template("home.html", posts=posts)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = Login()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.uname.data).first()
        if user and check_password_hash(user.password, form.password.data):
            session["user_id"] = user.id
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        flash("Invalid username or password!", "error")
    return render_template("login.html", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = Register()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(
            username=form.uname.data, email=form.email.data, password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to access the dashboard.", "error")
        return redirect(url_for("login"))
    user = User.query.filter_by(id=session["user_id"]).first()
    posts = Post.query.filter_by(user_id=user.id).all()
    return render_template("dashboard.html", user=user, posts=posts)


@app.route("/create_post", methods=["GET", "POST"])
def create_post():
    if "user_id" not in session:
        flash("Please log in to create a post.", "error")
        return redirect(url_for("login"))
    form = PostForm()
    if form.validate_on_submit():
        # Handle file upload
        image_filename = None
        if form.image.data:
            file = form.image.data
            filename = secure_filename(file.filename)
            # Add timestamp to avoid filename conflicts
            filename = f"{int(time.time())}_{filename}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            image_filename = filename

        new_post = Post(
            title=form.title.data,
            content=form.content.data,
            image=image_filename,
            user_id=session["user_id"],
            created_at=datetime.now(),
        )
        db.session.add(new_post)
        db.session.commit()
        flash("Post created successfully!", "success")
        return redirect(url_for("dashboard"))
    return render_template("create_post.html", form=form)


@app.route("/edit_post/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user_id" not in session:
        flash("Please log in to create a post.", "error")
        return redirect(url_for("login"))
    posts = Post.query.filter_by(id=id, user_id=session["user_id"]).first()
    if not posts:
        flash("Post not found or you don't have permission to edit this post.", "error")
        return redirect(url_for("dashboard"))
    form = EditPostForm()
    if form.validate_on_submit():
        posts.title = form.title.data
        posts.content = form.content.data
        db.session.commit()
        flash("Post updated successfully!", "success")
        return redirect(url_for("dashboard"))
    elif request.method == "GET":
        form.title.data = posts.title
        form.content.data = posts.content
    return render_template("edit_post.html", post=posts, form=form)


@app.route("/delete_post/<int:id>", methods=["POST"])
def delete(id):
    if "user_id" not in session:
        flash("Please log in to delete a post.", "error")
        return redirect(url_for("login"))
    posts = Post.query.filter_by(id=id, user_id=session["user_id"]).first()
    if not posts:
        flash(
            "Post not found or you don't have permission to delete this post.", "error"
        )
        return redirect(url_for("dashboard"))
    db.session.delete(posts)
    db.session.commit()
    flash("Post deleted successfully!", "success")
    return redirect(url_for("dashboard"))


@app.route("/view_post/<int:id>")
def view_post(id):
    post = Post.query.filter_by(id=id).first()
    if not post:
        flash("Post not found.", "error")
        return redirect(url_for("home"))
    return render_template("view_post.html", post=post)


if __name__ == "__main__":
    app.run(debug=True)
