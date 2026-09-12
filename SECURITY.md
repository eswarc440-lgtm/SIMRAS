# Security policy

Do not report credentials or restricted infrastructure records in a public issue.
Rotate any secret that was committed or exposed; removing it from Git history is
not sufficient. Production deployments must replace all example secrets, enable
HTTPS, restrict CORS, isolate the database, authenticate write/ingestion routes
and use a managed secret store. The included administrator API key is a small-
project control, not a complete identity and access management system.

