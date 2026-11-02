FROM alpine:3.20

RUN apk add --no-cache g++ python3 shadow bash

# Create unprivileged user (UID 1000)
RUN groupadd -g 1000 sandbox && useradd -u 1000 -g sandbox -m -s /bin/bash sandbox

WORKDIR /sandbox

COPY cpp_harness.py /sandbox/harness.py
RUN chown -R sandbox:sandbox /sandbox && chmod 555 /sandbox/harness.py

USER sandbox

ENTRYPOINT ["python3", "/sandbox/harness.py"]
