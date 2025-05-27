FROM python:3.12-alpine
LABEL maintainer="lcalzado@altice.com.do"
WORKDIR /vpn_monitor
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./vpn_monitor .
RUN adduser -D ip
USER ip
EXPOSE 5000
ENV FLASK_APP=vpn_monitor.py
CMD ["python3", "vpn_monitor.py"]
