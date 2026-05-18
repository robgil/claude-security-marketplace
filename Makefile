IMAGE ?= claude-security-marketplace-tests

.PHONY: test validate build clean help

help:
	@echo "Targets:"
	@echo "  test      Build the test container and run schema validation (default)"
	@echo "  validate  Alias for 'test'"
	@echo "  build     Build the test container image only"
	@echo "  clean     Remove the test container image"

test: build
	docker run --rm $(IMAGE)

validate: test

build:
	docker build -t $(IMAGE) .

clean:
	-docker image rm $(IMAGE)

.DEFAULT_GOAL := test
