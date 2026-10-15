# demo-hosting Specification

## Purpose
Keeps the public hosted demo safe and cheap to run: model use has a hard ceiling, the hosted database is reachable as its provider gives it, and a deploy can only publish committed files.

## Requirements
### Requirement: Model use is capped per hour and per day
When an hourly or daily limit on model calls is configured, sending a demo request SHALL be refused with status 429 and a plain explanation once the model calls recorded in the last hour or the last 24 hours reach that limit. A refused request SHALL store nothing. With no limit configured, submissions SHALL never be refused for volume.

#### Scenario: Hourly limit reached
- **WHEN** an hourly limit of 3 is set and 3 model calls were recorded in the last hour
- **THEN** sending a demo request answers 429 with an explanation, and no booking request is stored

#### Scenario: Daily limit reached
- **WHEN** a daily limit of 5 is set and 5 model calls were recorded in the last 24 hours, none in the last hour
- **THEN** sending a demo request answers 429 with an explanation

#### Scenario: Only recent model calls count
- **WHEN** an hourly limit of 3 is set and the recorded spans are 3 model calls older than an hour plus tool and code spans from the last hour
- **THEN** a demo request is accepted

#### Scenario: No limit configured
- **WHEN** no limits are set and many model calls were recorded recently
- **THEN** a demo request is accepted

### Requirement: The Try page explains a reached limit
When sending a demo request is refused with status 429, the Try page SHALL show the server's explanation instead of suggesting that the API is down.

#### Scenario: Limit message shown
- **WHEN** sending a request answers 429 with an explanation
- **THEN** the error shown is that explanation

### Requirement: Hosted database URLs work as given
A `DATABASE_URL` carrying the libpq options `sslmode` and `channel_binding`, as hosted Postgres providers give it, SHALL work for the async driver: `sslmode` becomes the driver's `ssl` option with the same value, `channel_binding` is dropped, and other options are kept.

#### Scenario: A hosted connection string
- **WHEN** the URL ends in `?sslmode=require&channel_binding=require`
- **THEN** the async URL requires SSL through `ssl=require` and has no `sslmode` or `channel_binding` option

#### Scenario: A local connection string
- **WHEN** the URL has no query options
- **THEN** the async URL is unchanged apart from the driver name

### Requirement: A deploy publishes only committed files
The deploy bundle SHALL contain exactly the files committed at `HEAD`, with the Space's Dockerfile and README in place of the repository's root ones. Uncommitted files, ignored files (such as `.env`), and private working notes SHALL never be included.

#### Scenario: Bundle contents
- **WHEN** the deploy bundle is built from a checkout that also has `.env` and an untracked file
- **THEN** the bundle holds the committed files plus the Space Dockerfile and README, and neither `.env` nor the untracked file
