IMAGE ?= claude-security-marketplace-tests
LOCK_IMAGE ?= cgr.dev/chainguard/python:latest-dev@sha256:33289f14dabce99c0a48744abfa09d417278da1eeb5e028f37977792c51b826f

.PHONY: test validate build clean lock help

help:
	@echo "Targets:"
	@echo "  test      Build the test container and run schema validation (default)"
	@echo "  validate  Alias for 'test'"
	@echo "  build     Build the test container image only"
	@echo "  clean     Remove the test container image"
	@echo "  lock      Regenerate requirements.txt with hashes from requirements.in"

test: build
	docker run --rm $(IMAGE)

validate: test

build:
	docker build -t $(IMAGE) .

clean:
	-docker image rm $(IMAGE)

lock:
	@docker run --rm \
		-v $(CURDIR)/requirements.in:/work/requirements.in:ro \
		-w /work \
		--entrypoint sh \
		$(LOCK_IMAGE) -c '\
			pip install --user --quiet pip-tools >&2 && \
			/home/nonroot/.local/bin/pip-compile \
				--generate-hashes \
				--no-emit-index-url \
				--strip-extras \
				--quiet \
				--output-file=/tmp/out.txt \
				requirements.in >&2 && \
			cat /tmp/out.txt' > requirements.txt

.DEFAULT_GOAL := test
