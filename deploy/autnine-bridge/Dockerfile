FROM python:3.13-slim
RUN pip install --no-cache-dir cryptography==50.0.2
WORKDIR /app
COPY bridge.py catalog.json chatgpt.jpeg ./
CMD ["python", "bridge.py"]
