# Pyshort

This is pyshort, a python based headless link shortener.

  
  
  

## Current features

  

- rest api

- list all urls

- list info for specific url

- create url

- follow redirect

- db migrations

- redis caching on 
- - /url 
- - /r
  
## Future features

- add new route for url edits

- implement cache invalidation after user changes

- implement rabbit-mq for async logging collection
- - investigate rabbit failover (possibly with replicaset behind a service)

- expose usage logs

- implement periodic log cleanup (with custom thresholds?)

- origin country implementation using maxmind open db

- add try/catch wherever possible

- add unit tests






# Notes


## Perform db migrations

- flask db init

- flask db migrate -m "my migrate message"

- flask db upgrade


  

# example calls
Create new url
POST /create_url

    curl -X POST -H "Content-Type: application/json" -d '{"long_url":"https://dnshunt.me", "title":"dnshunt"}' http://localhost:5000/create_url

List all urls
GET /get_urls

    curl -X GET http://localhost:5000/get_urls

Get info about specific url
GET /url/$keyword

    curl -X GET http://localhost:5000/url/dnshunt

Follow url redirect
GET /r/$keyword

    curl -X GET http://localhost:5000/r/dnshunt


Edit existing url 
PUT /update_url/$keyword

    curl -X PUT  -H "Content-Type: application/json"  -d '{"long_url":"https://dnshunt.me/contact", "title":"dnshunt_contact"}' http://localhost:5000/update_url/$KEYWORD
