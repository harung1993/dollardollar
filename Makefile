# Variables
IMAGE_NAME := dollardollar
REGISTRY := gitea.yanello.net/marcus
VERSION := dev
IMAGE_TAG := $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
LATEST_TAG := $(REGISTRY)/$(IMAGE_NAME):latest

# Build Docker image
.PHONY: build
build:
	docker buildx build -t $(IMAGE_TAG) -t $(LATEST_TAG) .

# Push Docker image to registry
.PHONY: push
push:
	docker push $(IMAGE_TAG)
	docker push $(LATEST_TAG)

# Build and push in one command
.PHONY: build-push
build-push: build push

