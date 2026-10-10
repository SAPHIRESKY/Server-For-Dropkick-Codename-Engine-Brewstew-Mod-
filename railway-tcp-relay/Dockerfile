FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY dropkick_room_server.py /app/dropkick_room_server.py
EXPOSE 27666
CMD ["sh", "-c", "python -u /app/dropkick_room_server.py --host 0.0.0.0 --port ${PORT:-27666}"]
