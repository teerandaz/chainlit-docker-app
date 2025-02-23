FROM python:3.9-slim

WORKDIR /app

# Copy your dependency file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chainlit globally (if not already in requirements.txt)
RUN pip install chainlit

# Copy your project files
COPY . .

# Set the default command (adjust "your_script.py" to your actual entry point)
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
