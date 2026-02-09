FROM node:18-slim

# Install Python and pip for MkDocs
RUN apt-get update && apt-get install -y python3 python3-pip git && \
    rm -rf /var/lib/apt/lists/*

# Install MkDocs and common plugins
RUN pip3 install mkdocs mkdocs-material mkdocs-mermaid2-plugin pymdown-extensions --break-system-packages

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3001

CMD ["npm", "run", "dev"]
