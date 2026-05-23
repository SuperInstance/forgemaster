FROM python:3.10-slim

WORKDIR /app

# Install runtime deps
RUN pip install --no-cache-dir numpy flask

# Copy SDK and constraint module
COPY flux-sdk-python/ /app/flux-sdk-python/
COPY flux-vm/src/maritime_constraints.py /app/flux/maritime_constraints.py

# Install the flux-constraint package if setup.py exists
RUN if [ -f /app/flux-sdk-python/setup.py ]; then \
        pip install /app/flux-sdk-python; \
    fi

# Copy API server
COPY api.py /app/flux/api.py

# Create __init__.py so python -m flux.api works
RUN touch /app/flux/__init__.py

EXPOSE 5000

CMD ["python", "-m", "flux.api"]
