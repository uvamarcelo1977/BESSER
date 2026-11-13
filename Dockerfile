# Use slim variant to reduce image size (200MB smaller).
# Python 3.12 matches the CI matrix; 3.10 was dropped in v7.5.1 because
# ``typing.Self`` (used in the NN metamodel, PEP 673) requires 3.11+.
FROM python:3.12-slim

WORKDIR /app

# No additional system dependencies needed - Python slim has everything for a basic Flask/FastAPI app
# If you need specific system libraries (e.g., for image processing), add them here

# Copy and install dependencies first for better layer caching
COPY requirements.txt ./requirements.txt
COPY besser/utilities/web_modeling_editor/backend/requirements.txt ./backend-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r backend-requirements.txt

# Copy only necessary files
COPY pyproject.toml README.md ./
COPY besser/ ./besser/

# Java runtime + download tools (Alloy semantic consistency checking)
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download Alloy JAR and its MIT license text (must ship alongside the redistributed jar)
RUN mkdir -p /alloy \
    && wget -O /alloy/alloy.jar https://github.com/AlloyTools/org.alloytools.alloy/releases/download/v6.2.0/org.alloytools.alloy.dist.jar \
    && wget -O /alloy/LICENSE https://raw.githubusercontent.com/AlloyTools/org.alloytools.alloy/v6.2.0/LICENSE \
    && test -s /alloy/alloy.jar

# Arch/version independent JAVA_HOME (BESSER resolves $JAVA_HOME/bin/java)
RUN ln -s "$(dirname "$(dirname "$(readlink -f "$(which java)")")")" /usr/lib/jvm/default-java-home
ENV JAVA_HOME=/usr/lib/jvm/default-java-home
ENV BESSER_ALLOY_JAR=/alloy/alloy.jar

# Install BESSER package
RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/app

EXPOSE 9000

CMD ["python", "-m", "besser.utilities.web_modeling_editor.backend.backend"]