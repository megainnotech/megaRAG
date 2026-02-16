# PromptGuard Interface Definition Language (IDL)

a shared gRPC/Protobuf contracts repo using:

- Protobuf as the IDL
- Go + official protoc plugins
- Python + betterproto (generated centrally)
- Buf for linting & breaking-change checks
- MkDocs for documentation

## Quick usage

1. Install tools (example):

   ```bash
   # protoc + Go plugins
   go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
   go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

   # Python side
   pip install "betterproto[compiler]" grpcio-tools buf
   ```

2. Generate code:

   ```bash
   make generate
   ```

   This will populate:

   - `gen/go/...` with Go stubs
   - `gen/python/itmx/...` with betterproto Python code

3. Lint & breaking checks:

   ```bash
   buf lint
   buf breaking --against '.git#branch=main'
   ```

4. To publish:

   - Tag the repo (e.g. `v0.1.0`) so Go clients can `go get github.com/itmx/promptguard-idl@v0.1.0`
   - Build + upload the Python package from `pyproject.toml`:

     ```bash
     python -m build
     python -m twine upload dist/*
     ```
