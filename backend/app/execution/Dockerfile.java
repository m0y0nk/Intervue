FROM eclipse-temurin:21-jdk-alpine

RUN apk add --no-cache python3 shadow bash

# Create unprivileged user (UID 1000)
RUN groupadd -g 1000 sandbox && useradd -u 1000 -g sandbox -m -s /bin/bash sandbox

WORKDIR /sandbox

COPY java_harness.py /sandbox/harness.py
RUN chown -R sandbox:sandbox /sandbox && chmod 555 /sandbox/harness.py

USER sandbox

ENTRYPOINT ["python3", "/sandbox/harness.py"]
