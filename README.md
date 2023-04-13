
# Welcome to StackEdit!

  

This is pyshort, a python based headless link shortener.

  
  
  

## Desired deliverables

  

- rest api

- list all urls

- list info for specific url

- create url

- follow redirect

- db migrations

- redis caching

- usage logs

  
  
  
  

# Notes

  

## Perform db migrations

- flask db init

- flask db migrate -m "my migrate message"

- flask db upgrade

  
  

# example calls

POST /create_url

    curl -X POST -H "Content-Type: application/json" -d '{"long_url":"**https://dnshunt.me**", "title":"**dnshunt**"}' http://localhost:5000/create_url


GET /get_urls

    curl -X GET http://localhost:5000/get_urls

GET /url/$keyword

    curl -X GET http://localhost:5000/url/**dnshunt**

GET /r/$keyword

    curl -X GET http://localhost:5000/r/**dnshunt**
