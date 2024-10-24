#!/bin/bash

# Check if version is provided
if [ -z "$1" ]; then
    echo "Version argument missing! Usage: ./build_and_push.sh <version>"
    exit 1
fi

VERSION=$1

# Define your Docker repository (change to your Docker Hub username)
DOCKER_REPO="srxdhxr/step3"

# Build Docker image with version tag
docker build -t $DOCKER_REPO:$VERSION .

# Push Docker image to Docker Hub
docker push $DOCKER_REPO:$VERSION
