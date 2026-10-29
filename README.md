# Pyshort

This is pyshort, a python based headless link shortener.

  
  
  

## Current features

- ready to go docker image with docker-compose.yml included

- rest api

- calls to list / create / update / follow urls

- db migrations

- swagger api on /api/docs

- redis caching on 
- - /url 
- - /r

- optional service-token auth on management endpoints (see below)

- deactivated urls (`active=False`) return 404 from `/r/` instead of redirecting

## Service token auth

Set the `PYSHORT_SERVICE_TOKEN` environment variable to require an
`X-Service-Token: <value>` header on the management endpoints
(`POST /create_url`, `PUT /update_url/<keyword>`, `GET /get_urls`).
Requests with a missing or wrong token get `401 {"error": "unauthorized"}`.
When the variable is unset, the endpoints stay open (standalone use is
unchanged). `/r/` and `/url/` never require the token.

## URL validation

`POST /create_url` and `PUT /update_url/<keyword>` validate `long_url`:
it must parse with a scheme of `http`/`https` and a non-empty netloc,
otherwise `400 {"error": "invalid url"}`. On update, validation only
applies when `long_url` is included in the payload.

## Deactivated links

`PUT /update_url/<keyword>` with `{"active": "False"}` deactivates a link.
`GET /r/<keyword>` returns `404` for inactive links (checked against the
database before the Redis cache, so a cached link stops redirecting as soon
as it is deactivated).
  
## Future features

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

## Extend swagget config
- The yaml template is /static/openapi.yaml
- https://editor.swagger.io/
  

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
