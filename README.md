# sample_reportbro_fastapi_server

sample code for fastapi and reportbro. They didnt have a sample on their site so I put this up as an example of where I started.

needs a config.json file setting up. A sample file is included. 

Might help people as a starter for using reportBro with fastapi. Note my code is not particularly pythonic and it was written in a rush and not fully tested. It also includes some checks for account security I added in some of the endpoints that are not needed.

It includes:

- setup with sqlalchemy and a mysql database
- 2 tables for storing templates and data
- endpoints to create documents/reprint documents from the db, create templates, view templates by account and an individual template
- It has sentry setup to monitor exceptions and logzero to manage log files
- The fastapi instance has apikeys setup in the header to manage the security using the default fastapi methods
- all environment variables and sensitive stuff is in the config file
