from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from flask_mail import Mail, Message
import os


app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'planets.db')
app.config['JWT_SECRET_KEY'] = 'super-secret'   # change this later
app.config['MAIL_SERVER'] = 'smtp.mailtrap.io'
app.config['MAIL_USERNAME'] = os.environ['MAIL_USERNAME']
app.config['MAIL_PASSWORD'] = os.environ['MAIL_PASSWORD']


# establish an instance of imported libraries
db = SQLAlchemy(app)
ma = Marshmallow(app)
jwt = JWTManager(app)
mail = Mail(app)


@app.cli.command('db_create')
def db_create():
    db.create_all()
    print("database created!")


@app.cli.command('db_drop')
def db_drop():
    db.drop_all()
    print("database dropped!")


@app.cli.command('db_seed')
def db_seed():
    mercury = Planet(planet_name='Mercury',
                     planet_type='Class D',
                     home_star='sol',
                     mass=3.258e23,
                     radius=1516,
                     distance=35.98e6
                     )

    venus = Planet(planet_name='Venus',
                   planet_type='Class K',
                   home_star='sol',
                   mass=4.867e24,
                   radius=3760,
                   distance=67.24e6
                   )

    earth = Planet(planet_name='Earth',
                   planet_type='Class M',
                   home_star='sol',
                   mass=5.972e25,
                   radius=3959,
                   distance=92.96e6
                   )

    db.session.add(mercury)
    db.session.add(venus)
    db.session.add(earth)

    test_user = User(first_name='William',
                     last_name='Herschel',
                     email='test@test.com',
                     password='Passw0rd')

    db.session.add(test_user)
    db.session.commit()
    print('Database seeded!')


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/super_simple')
def super_simple():
    return jsonify(message='Hello from the planetary API'), 200


@app.route('/not_found')
def not_found():
    return jsonify(message='That resource was not found'), 404


@app.route('/parameters')
def parameters():
    name = request.args.get('name')
    age = int(request.args.get('age'))
    if age < 18:
        return jsonify(message="Sorry " + name + " you are not old enough"), 401
    else:
        return jsonify(message="Welcome " + name + " you are old enough")


# check age of the user
@app.route('/url_variables/<string:name>/<int:age>')
def url_variables(name: str, age: int):
    if age < 18:
        return jsonify(message="Sorry " + name + " you are not old enough"), 401
    else:
        return jsonify(message="Welcome " + name + " you are old enough")


# Retrieve the list of planets from the database
# you can't return json data here -
@app.route('/planets', methods=['GET'])
def planets():
    planets_list = Planet.query.all()
    result = planets_schema.dump(planets_list)  # the result equals the planets list in the planets schema
    return jsonify(result)  # return result (in the previous line) but return it in JSON format using Marshmallow


# add or post new users to the database - but first ensure that users don't already exist
@app.route('/register', methods=['POST'])
def register():
    email = request.form['email']  # what is the email?
    test = User.query.filter_by(email=email).first()  # does this email already exist?
    if test:
        return jsonify(message='That email already exists'), 409  # if yes send a 409 error
    else:
        first_name = request.form['first_name']  # if not start the process of creating a new user
        last_name = request.form['last_name']
        password = request.form['password']
        # instantiate new user
        user = User(first_name=first_name, last_name=last_name, password=password)  # now instantiate that new user
        db.session.add(user)  # add new user to database
        db.session.commit()
        return jsonify(message='user has been created successfully and added to db'), 201


@app.route('/login', methods=['POST'])
def login():
    if request.is_json:
        email = request.json['email']
        password = request.json['password']
    else:
        email = request.form['email']
        password = request.form['password']

    test = User.query.filter_by(email=email, password=password).first()
    if test:
        access_token = create_access_token(identity=email)  # how are we identifying the user - we are using the email
        return jsonify(message="Login successful", access_token=access_token)
    else:
        return jsonify(message="Bad email"), 401


@app.route('/retrieve_password/<string:email>', methods=['GET'])
def retrieve_password(email: str):
    user = User.query.filter_by(email=email).first()
    if user:
        msg = Message("your planetary API password is " + user.password,
                      sender="admin@planetary-api.com",
                      recipients=[email])
        mail.send(msg)
        return jsonify(message="Password sent to " + email)
    else:
        return jsonify(message="That email doesn't exist"), 401


@app.route('/planet_details/<int:planet_id>', methods=['GET'])
def planet_details(planet_id: int):
    planet = Planet.query.filter_by(planet_id=planet_id).first()
    if planet:
        result = planet_schema.dump(planet)
        return jsonify(result)
    else:
        return jsonify(message="That planet does not exist"), 404


# database models
class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    password = Column(String)


class Planet(db.Model):
    __tablename__ = 'planets'
    planet_id = Column(Integer, primary_key=True)
    planet_name = Column(String)
    planet_type = Column(String)
    home_star = Column(String)
    mass = Column(Float)
    radius = Column(Float)
    distance = Column(Float)


# The following code is Marshmallow (ma.)
class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'first_name', 'last_name', 'email', 'password')


class PlanetSchema(ma.Schema):
    class Meta:
        fields = ('planet_id', 'planet_name', 'planet_type', 'home_star', 'mass', 'radius', 'distance')


# instantiation of UserSchema (or structure of the database table called User)
user_schema = UserSchema()
users_schema = UserSchema(many=True)  # allows us to get a collection of records back from the DB

# instantiation of PlanetSchema (or structure of the database table called Planet)
planet_schema = PlanetSchema()
planets_schema = PlanetSchema(many=True)  # allows us to get a collection of records back from the DB

if __name__ == '__main__':
    app.run()

# having an issue with registering users
