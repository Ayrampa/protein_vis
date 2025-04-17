FROM python

# Set the working directory
WORKDIR /flask_app

# Install required packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add your application code
COPY . .
EXPOSE 5050
# Run your application
CMD ["python", "llama.py"]


