from flask import *
from flask_sqlalchemy import SQLAlchemy
from cockroachdb.sqlalchemy import run_transaction
from sqlalchemy.orm import *
import sqlalchemy.orm
from Models.userModel import User, Messages, Session
from shapely.geometry import Point
import pyproj
from shapely.ops import transform
from functools import partial
from sqlalchemy import *
from geoalchemy2 import *
from geoalchemy2.shape import from_shape
import geocoder
from flask_cors import CORS, cross_origin
from opentok import OpenTok

API_KEY =  "47084464"
API_SECRET = "487b2c632bd7d167f896a425b44603adfe0b4494"
# Define endpoint routes and begin implementing:
# For now lets define a get route to get all messages for a certain location
# And a post route to add messages to the DB.
# DB schema will be as discussed, hold userid, messages join and coordinates.
# Send and recieve as JSONs, client side will convert into message objects

app = Flask(__name__)
cors = CORS(app)
app.config.from_pyfile('app.cfg')
db = SQLAlchemy(app)
sessionmaker = sqlalchemy.orm.sessionmaker(db.engine)
opentok = OpenTok(API_KEY, API_SECRET)

@app.route('/')
def show_all():
    g = geocoder.ip(request.args.get('ip'))
    print(g.latlng)
    userLocation = Point(float(g.lat), float(g.lng))
    return run_transaction(sessionmaker, lambda s: jsonify([z.to_json() for z in s.query(User).filter(functions.ST_DWithin(User.location, from_shape(userLocation, srid=4326), 0.001)).all()]))

@app.route('/newMessage', methods=['POST', 'GET'])
def new_message():
    g = geocoder.ip(request.args.get('ip'))
    userLocation = Point(float(g.lat), float(g.lng))
    user_id = request.args.get('id')
    newMessage = Messages(user_id, request.get_json()['message'], request.get_json()['timestamp'], request.args.get('name'))
    def update_messages(session):
        session.add(newMessage)
    returnMessage = newMessage.to_json()
    run_transaction(sessionmaker, update_messages)
    return jsonify(returnMessage)

@app.route('/register')
def new_user():
    count = run_transaction(sessionmaker, lambda s: s.query(User).count()) + 1
    g = geocoder.ip(request.args.get('ip'))
    userLocation = Point(float(g.lat), float(g.lng))
    run_transaction(sessionmaker, lambda s:s.add(User(count, functions.ST_SetSRID(functions.ST_MakePoint(g.lat, g.lng), 4326), request.args.get('name'))))
    return jsonify(count)

@app.route('/getSession')
def new_token():
    g = geocoder.ip(request.args.get('ip'))
    userLocation = Point(float(g.lat), float(g.lng))
    def query(session):
        res = session.query(Session).filter(functions.ST_DWithin(Session.location, from_shape(userLocation, srid=4326), 1)).first()
        if (res):
            return res.session_token
        else:
            return res

    session_id = run_transaction(sessionmaker, query)
    if (session_id):
        return opentok.generate_token(session_id)
    else:
        session = opentok.create_session()
        count = run_transaction(sessionmaker, lambda s: s.query(Session).count()) + 1
        run_transaction(sessionmaker, lambda s: s.add(Session(count, session.session_id, functions.ST_SetSRID(functions.ST_MakePoint(g.lat, g.lng), 4326))))
        return opentok.generate_token(session.session_id)


app.run()

# INSERT INTO session VALUES (1, 'test', ST_SetSRID(ST_MakePoint(51,-114), 4326));