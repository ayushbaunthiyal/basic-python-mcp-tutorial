# Use an official Python runtime as a parent image
# Using 3.13 as required by pyproject.toml
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Install uv package manager
RUN pip install uv

# Copy dependency definition files from the project root
# Docker build context should be the project root (d:/repos/mygit/basic-python-mcp-tutorial)
COPY pyproject.toml uv.lock ./

# Install project dependencies using uv
# Using --system to install globally in the container's Python environment
RUN uv pip install --system -r pyproject.toml

# Copy the .env file from the project root
COPY .env .

# Copy the server application code into the container
COPY server/ ./server/

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable for Python path if needed (usually not necessary with --system install)
# ENV PYTHONPATH "${PYTHONPATH}:/app"

# Run main.py using uvicorn when the container launches in SSE mode
# Binding to 0.0.0.0 makes it accessible from outside the container
CMD ["python", "server/main.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8080"]
