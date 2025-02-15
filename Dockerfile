FROM python:3.12.6
WORKDIR /bot
COPY requirements.txt /bot/
RUN pip install -r requirements.txt
EXPOSE 8080
COPY . /bot
CMD python main.py
