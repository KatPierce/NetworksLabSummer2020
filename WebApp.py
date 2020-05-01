from flask import Flask, render_template, request
import requests
import re
import ssl
import socket
from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings()
app = Flask(__name__)

m = {}


def refresh_data():
    data = open("./data/urls.txt", 'r').read().strip().split('\n')
    if data.count('') > 0:
        data.remove('')
    return data


@app.route("/", methods=['POST', 'GET'])
def index():
    error = 0
    data = refresh_data()
    # Search string
    query = request.args.get('q')
    results = None
    if query:
        results = search(query, data)
    if "remove" in request.form:
        url_to_remove = request.form["remove"]
        if data.count(url_to_remove) > 0:
            remove_url(url_to_remove, data)
    if "add" in request.form:
        page = request.form['add']
        error = add_page(page)
    data = refresh_data()
    return render_template('index.html', urls=data, results=results, error=error)


def search(query, data):
    results = {}
    for url in data:
        soup = BeautifulSoup(m[url], "html.parser")
        tags = [tag for tag in soup.find_all(['a', 'p', 'title'])]  # В каких тегах ищем
        found = []
        for i in tags:
            if re.findall(re.escape(query), i.getText()):
                found.append(i.getText())
        if len(found) > 0:
            results[url] = found
    return results


def remove_url(url_to_remove, data):
    data.remove(url_to_remove)
    del m[url_to_remove]
    new_data = open("./data/urls.txt", 'w')
    for url in data:
        new_data.write(url + '\n')
    new_data.close()


def add_page(url):
    response = http_request(url)
    # response = requests.get(url, verify=False).text
    if response == 1:
        return "The url is not correct"
    status = response.split("\r\n\r\n")[0].split(' ')[1]
    if int(status.strip()) != 200:
        return "The url is not correct"
    urls = open("./data/urls.txt", 'r').read().split('\n')
    if url not in urls:
        data = open("./data/urls.txt", 'a')
        data.write(url + '\n')
        data.close()
        m[url] = ''.join(i for i in response.split("\r\n\r\n")[1:])
        return 0
    else:
        return "Was already added"


def http_request(url):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    info = re.findall("^(.*)://([A-Za-z0-9\-\.]+)[:]?([0-9]+)?(.*)$", url)  # парсим url
    if info:
        if info[0][2] == "":  # если не указан порт
            protocols = {'http': 80, 'https': 443}
            port = protocols[info[0][0]]
        else:
            port = info[0][2]  # если есть в url
    else:
        return 1
    path = info[0][3]
    if info[0][3] == "":
        path = "/"
    s.connect((info[0][1], port))
    if info[0][0] == "https":
        s = ssl.wrap_socket(s, keyfile=None, certfile=None, server_side=False, cert_reqs=ssl.CERT_NONE,
                            ssl_version=ssl.PROTOCOL_SSLv23)
    s.send(("GET %s HTTP/1.1\r\nHost: %s:%s\r\nConnection: close\r\n\r\n" % (path, info[0][1], port)).encode())
    response = b""
    while True:
        new = s.recv(4096)
        if not new:
            s.close()
            break
        response = response + new
    return response.decode("utf8", "ignore")


def update_map():
    urls = open("./data/urls.txt", 'r').read().split('\n')
    urls.pop()
    for url in urls:
        response = http_request(url)
        m[url] = ''.join(i for i in response.split("\r\n\r\n")[1:])


if __name__ == "__main__":
    update_map()
    app.run(debug=True)
