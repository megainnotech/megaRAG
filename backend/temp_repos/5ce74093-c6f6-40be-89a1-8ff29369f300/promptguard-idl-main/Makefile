PROTO_DIR=proto
GO_OUT_DIR=gen/go
PY_OUT_DIR=gen/python
OPENAPI_OUT_DIR=gen/openapi
BUF_EXPORT_DIR=.buf-export


PROTO_FILES := $(shell find $(PROTO_DIR) -name '*.proto')

.PHONY: generate generate-go generate-openapi generate-python lint breaking

generate: generate-go generate-openapi

generate-go:
	rm -rf gen/go
	buf generate --template buf.gen.yaml

generate-py:
	rm -rf $(PY_OUT_DIR) $(BUF_EXPORT_DIR)
	mkdir -p $(PY_OUT_DIR)

	# 1) Export module + deps (including validate/validate.proto)
	buf export . --output $(BUF_EXPORT_DIR)

	# 2) Run betterproto via grpc_tools.protoc on the exported tree
	uv run python -m grpc_tools.protoc \
		-I $(BUF_EXPORT_DIR) \
		--python_betterproto_out=$(PY_OUT_DIR) \
		$(shell find $(BUF_EXPORT_DIR) -name '*.proto')

generate-openapi:
	# OpenAPI is already in buf.gen.yaml as well, so this is optional.
	buf generate --template buf.gen.yaml

lint:
	buf lint

breaking:
	# Compares current branch against main; adjust if needed
	buf breaking --against '.git#branch=main'
