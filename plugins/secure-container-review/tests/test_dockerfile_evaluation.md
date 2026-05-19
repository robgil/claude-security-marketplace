# Dockerfile Evaluation Tests

## Test Case 1: Secure Dockerfile
```
FROM alpine:latest

RUN apk add --no-cache nodejs npm

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

USER nodejs
CMD ["npm", "start"]
```

Expected Analysis:
- Uses minimal base image (alpine)
- Multi-stage build not used but build dependencies handled properly
- Non-root user usage found (nodejs)
- Network access limited to package installation and runtime

## Test Case 2: Insecure Dockerfile
```
FROM ubuntu:latest

RUN apt-get update && apt-get install -y nodejs npm

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

USER root
CMD ["npm", "start"]
```

Expected Analysis:
- Uses ubuntu base image (larger attack surface)
- No multi-stage build
- Runs as root user (high security risk)
- Network access for package installation and runtime

## Test Case 3: Chainguard Base Image
```
FROM cgr.dev/chainguard/node:latest

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

USER nobody
CMD ["npm", "start"]
```

Expected Analysis:
- Uses Chainguard base image (enhanced security)
- Multi-stage build not used but good usage
- Non-root user usage found (nobody)
- Minimal attack surface from Chainguard image