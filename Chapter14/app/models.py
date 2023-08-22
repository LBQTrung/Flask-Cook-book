from . import db
from flask_login import UserMixin, AnonymousUserMixin
from flask import current_app
from datetime import datetime
from . import login_manager
import requests
from markdown import markdown
import bleach


class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship("User", backref="role")

    @staticmethod
    def insert_roles():
        roles = {
            "User": (
                Permission.FOLLOW | Permission.COMMENT | Permission.WRITE_ARTICLES,
                True,
            ),
            "Moderator": (
                Permission.FOLLOW
                | Permission.COMMENT
                | Permission.WRITE_ARTICLES
                | Permission.MODERATE_COMMENTS,
                False,
            ),
            "Administrator": (0xFF, False),
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return f"<Role {self.name}>"


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    body_html = db.Column(db.Text)

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        from faker import Faker

        fake = Faker()
        user_count = User.query.count()

        for i in range(count):
            random_user = User.query.offset(randint(0, user_count - 1)).first()
            fake_post = Post(
                body=fake.paragraph(),
                timestamp=fake.date_time_this_decade(),
                author=random_user,
            )
            db.session.add(fake_post)
            db.session.commit()

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = [
            "a",
            "abbr",
            "acronym",
            "b",
            "blockquote",
            "code",
            "em",
            "i",
            "li",
            "ol",
            "pre",
            "strong",
            "ul",
            "h1",
            "h2",
            "h3",
            "p",
        ]
        target.body_html = bleach.linkify(
            bleach.clean(
                markdown(value, output_format="html"), tags=allowed_tags, strip=True
            )
        )


db.event.listen(Post.body, "set", Post.on_changed_body)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)

    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)

    avatar_url = db.Column(db.String(200))
    # Relationship fields
    posts = db.relationship("Post", backref="author", lazy="dynamic")
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config["FLASKY_ADMIN"]:
                self.role = Role.query.filter_by(permissions=0xFF).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    def can(self, permissions):
        return (
            self.role is not None
            and (self.role.permissions & permissions) == permissions
        )

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def __repr__(self):
        return f"<User {self.email}>"

    @staticmethod
    def generate_fake(count=100):
        def generate_random_image_url():
            # Sử dụng dịch vụ Lorem Picsum để lấy URL ảnh ngẫu nhiên
            response = requests.get("https://picsum.photos/96/96")
            if response.status_code == 200:
                image_url = response.url
                return image_url
            else:
                return None

        from sqlalchemy.exc import IntegrityError
        from random import seed
        from faker import Faker

        seed()
        fake = Faker()

        for i in range(count):
            fake_user = User(
                email=fake.email(),
                name=fake.name(),
                location=fake.city(),
                about_me=fake.paragraph(),
                avatar_url=generate_random_image_url(),
            )
            db.session.add(fake_user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


from . import login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
