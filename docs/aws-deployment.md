# AWS deployment runbook

## Recommended small-project topology

- One EC2 Ubuntu instance running frontend/backend containers.
- Amazon RDS for PostgreSQL with PostGIS where budget permits; otherwise a
  separately backed-up PostGIS container for the college demonstration only.
- S3 and CloudFront for GLB, 3D Tiles, rasters and reports.
- Route 53 plus an ACM/Let's Encrypt certificate for HTTPS.
- CloudWatch for container, API, ETL and freshness alarms.

## EC2 deployment

1. Create an Ubuntu EC2 instance and restrict the security group to SSH from
   your IP plus public 80/443.
2. Install Git and Docker Engine with the Compose plugin.
3. Clone the repository into `/opt/simras`.
4. Copy `.env.example` to `.env`; replace every secret and production hostname.
5. Point `DATABASE_URL` at RDS/PostGIS.
6. Run:

```bash
docker compose -f compose.production.yml up --build -d
docker compose exec backend alembic upgrade head
curl http://127.0.0.1/health
```

7. Configure host Nginx/HTTPS using `infra/nginx/simras.conf` or terminate TLS at an AWS load balancer.
8. Upload verified 3D assets to S3; store their URI, checksum and fidelity metadata.

## CI/CD

The included CI validates backend, ETL, frontend and container builds. Add a
separate protected deployment job only after the AWS target and rollback method
are decided. Prefer OIDC federation from GitHub Actions to AWS instead of long-
lived AWS access keys.

## Backup gate

A backup schedule is not complete until restoration has been tested into a new
database and the API can open a known twin from the restored data.

## Rollback

Tag production images with the Git commit SHA. Retain the previous frontend and
backend image tags. Application rollback and database migration rollback are
separate decisions; never blindly downgrade a schema that already contains new data.
