FROM python:3.12-slim

LABEL io.modelcontextprotocol.server.name="ru.xonta/max"

# Минцифры root: needed only for the operator tools that call platform-api2.max.ru
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
 && (curl -fsSL https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt \
      -o /usr/local/share/ca-certificates/russian_trusted_root_ca.crt && update-ca-certificates || true) \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

ENV PORT=8766 MAX_CA_FILE=/etc/ssl/certs/ca-certificates.crt
EXPOSE 8766

# stdio by default (for catalogs that run the image locally);
# public HTTP: docker run -p 8766:8766 -e XONTA_MAX_HOSTED=1 -e HOST=0.0.0.0 image xonta-max-mcp --http
CMD ["xonta-max-mcp"]
