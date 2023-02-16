FROM python:3.11
WORKDIR /finances
COPY requirements.txt /finances/
RUN pip install -r requirements.txt
COPY . /finances
CMD python main.py 
