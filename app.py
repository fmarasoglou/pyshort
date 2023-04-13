from flask import Flask, request, jsonify, redirect, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import random
import string
import logging
import json
import redis


## redis connection
redis_db1 = redis.Redis(host='127.0.0.1', port=6379, db=0,decode_responses=True)


# Replace the values in the connection string with your own
# Make sure to specify the correct dialect and driver for your database
connection_string = "postgresql://postgres:postgres@127.0.0.1:5432/pyshort"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = connection_string
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


############## functions
def generate_keyword():
    while True:
        # Generate random string of length between 3 and 8 characters
        keyword = ''.join(random.choice(string.ascii_lowercase) for i in range(random.randint(3, 8)))

        # Check if keyword already exists in database
        if Url.query.filter_by(keyword=keyword).first() is None:
            return keyword

def set_redis_cache(doc_name,json_doc,ttl):
    json_doc = json.dumps(json_doc)

    redis_db1.set(doc_name, json_doc, ex=ttl)
    logging.info(f'cache set for {doc_name}')



def search_redis_cache(doc_name):
    retrieved_doc_str = redis_db1.get(doc_name)
    if retrieved_doc_str is None:
        logging.info(f'cache miss for {doc_name}')
        return("miss")
    retrieved_doc = json.loads(retrieved_doc_str)
    return(retrieved_doc)


# Define a simple database model
class Url(db.Model):
    keyword = db.Column(db.String(8), primary_key=True) # the random short url string
    long_url = db.Column(db.String)
    title = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip = db.Column(db.String(45))
    count = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return '<Url %r>' % self.keyword

class Logs(db.Model):
    click_id = db.Column(db.Integer, primary_key=True)
    click_time = db.Column(db.DateTime, default=datetime.utcnow)
    keyword= db.Column(db.String)
    referrer = db.Column(db.String(200))
    user_agent = db.Column(db.String(255))
    ip = db.Column(db.String(45))
    country_code = db.Column(db.String(2))


    def __repr__(self):
        return '<Logs %r>' % self.name

# Create any tables that do not exist
with app.app_context():
    db.create_all()


# Route to create new urls
@app.route('/create_url', methods=['POST'])
def create_url():
    # Get data from request body
    data = request.json
    long_url = data.get('long_url')
    title = data.get('title')
    ip = request.remote_addr

    # Create new url
    url = Url(long_url=long_url, title=title, ip=ip, keyword=generate_keyword())

    # Add url to database
    db.session.add(url)
    db.session.commit()

    # Return response
    return jsonify({'message': 'Url created successfully', 'data': {
        'keyword': url.keyword,
        'long_url': url.long_url,
        'title': url.title,
        'timestamp': url.timestamp,
        'ip': url.ip,
        'count': url.count,
        'active': url.active
    }})


# Route to retrieve all urls
@app.route('/get_urls', methods=['GET'])
def get_urls():
    # Get all urls from database
    urls = Url.query.all()

    # Create response data
    data = [{
        'keyword': url.keyword,
        'long_url': url.long_url,
        'title': url.title,
        'timestamp': url.timestamp,
        'ip': url.ip,
        'count': url.count,
        'active': url.active
    } for url in urls]

    # Return response
    return jsonify(data)

@app.route('/url/<string:keyword>', methods=['GET'])
def get_url(keyword):
    # Attempt retrieval from redis
    search_redis = search_redis_cache(f'/url/{keyword}')
    
    if search_redis != 'miss':
        return jsonify(search_redis)


    # Retrieve url from database
    url = Url.query.filter_by(keyword=keyword).first()

    if url:
        # Create response data
        data = {
            'keyword': url.keyword,
            'long_url': url.long_url,
            'title': url.title,
            # f-string is used to desirialize datetime stamp
            'timestamp': f"{url.timestamp}",
            'ip': url.ip,
            'count': url.count,
            #capitalized to return true/false as True/False. Needed to successfully post json document in redis cache
            'active': str(url.active).capitalize() 
            
        }

        set_redis_cache(f"/url/{keyword}",data,25)
        return jsonify(data)
    else:
        # Return error message
        logging.warning('/url, Url not found')
        return jsonify({'message': 'Url not found'}), 404


@app.route('/r/<string:keyword>', methods=['GET'])
def redirect_url(keyword):
    # Query redis for a cached URL with the specified keyword
    search_redis = search_redis_cache(f'/r/{keyword}')
    print(search_redis)
    if search_redis != 'miss':
        return redirect(search_redis)
    
    
    # Query the database for a URL with the specified keyword
    url = Url.query.filter_by(keyword=keyword).first()

    # If a URL with the specified keyword exists, redirect to the long URL
    if url is not None:
        # Increment the URL's click count
        url.count += 1
        db.session.commit()

        # Log the click
        log = Logs(keyword=keyword, referrer=request.referrer, user_agent=request.user_agent.string, ip=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        set_redis_cache(f"/r/{keyword}",url.long_url,25)
        return redirect(url.long_url)

    # If no URL with the specified keyword exists, return a 404 error
    else:
        logging.warning('/r, Url not found')
        return jsonify({'message': 'Url not found'}), 404



if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)