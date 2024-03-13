# qube-server

This project sets up QubeServer and quelware and LabRAD servers using Docker on Linux systems, configured for QuBE environments.

## Requirements

1. Docker and Docker Compose
2. Linux (not ARM architecture)
3. GitHub token (with access to private repos)

## Getting Started

Clone this repository to your Linux machine:

```bash
git clone https://github.com/qiqb-osaka/qube-server
```

### Configuration

This Docker Compose file requires an environment variable, `GITHUB_TOKEN`. This is a GitHub token which is needed to clone private repos.

You can set this environment variable on your machine, for instance, by adding it to your `.bashrc` file:

```bash
export GITHUB_TOKEN=your-token
```

Alternatively, you can use a `.env` file in the project directory and Docker Compose will automatically use it.

*Be careful not to commit your personal GitHub token to the repository.*

### Building and Running the Services

Navigate to the project directory and build and run the services with Docker Compose:

```bash
cd qube-server
cd lib && sh setup.sh && cd ..

# build all services
docker compose build

# run all services
docker compose up -d

# run a specific service
docker compose up -d labrad

# show logs
docker compose logs -f
```

## Services

This project includes following services:

1. `labrad`: LabRAD server with QuBE device servers installed. The server data is persisted in the `labrad` Docker volume. It communicates over the host's network and listens on port 7682. You can configure the port in the `docker-compose.yml` file.
