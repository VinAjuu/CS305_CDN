import re
import sys
import time
import requests
from flask import Flask, Response
from socket import *
log_path = None
alpha = None
listen_port = None
dns_port = None
content_server_port = None
log = None
bitrates_with_port = dict()
throughput_with_port = dict()
app = Flask(__name__)


def init():
    global log_path, alpha, listen_port, dns_port, content_server_port, log

    log_path = sys.argv[1]
    alpha = float(sys.argv[2])
    listen_port = int(sys.argv[3])
    dns_port = int(sys.argv[4])
    if len(sys.argv) > 5:
        content_server_port = int(sys.argv[5])
    log = open(log_path, 'w')




@app.route('/index.html')
def init_page():
    return Response(requests.get('http://localhost:' + str(get_port()) + '/index.html'))


@app.route("/swfobject.js")
def get_js():
    return Response(requests.get('http://localhost:' + str(get_port()) + '/swfobject.js'))


@app.route("/StrobeMediaPlayback.swf")
def get_swf():
    return Response(requests.get('http://localhost:' + str(get_port()) + '/StrobeMediaPlayback.swf'))


def get_port():
    if content_server_port:
        port = content_server_port
    else:
        port = request_dns()
    return port


@app.route("/vod/<file_name>")
def get_video(file_name: str):
    global log_path, alpha, listen_port, dns_port, content_server_port, log
    if file_name == 'big_buck_bunny.f4m':
        # record bitrate option in a server port.
        # Convert request to nolist f4m file
        server_port = get_port()
        f4m_file = requests.get('http://localhost:' + str(server_port) + '/vod/big_buck_bunny.f4m')
        record_bitrate_with_port(server_port, f4m_file)
        return Response(requests.get('http://localhost:' + str(server_port) + '/vod/big_buck_bunny_nolist.f4m'))
    else:
        server_port = get_port()
        if server_port not in bitrates_with_port:
            f4m_file = requests.get('http://localhost:' + str(server_port) + '/vod/big_buck_bunny.f4m')
            record_bitrate_with_port(server_port, f4m_file)

        number = file_name.split("Seg")[1].split('-Frag')
        seq = number[0]
        frag = number[1]

        throughput_current = get_throughput(server_port)
        for bitrate_tmp in bitrates_with_port[server_port]:
            if throughput_current >= bitrate_tmp * 1.5:
                bitrate = bitrate_tmp

        ts = time.time()
        video_chunk_response = requests.get(
            'http://localhost:' + str(server_port) + '/vod/' + str(bitrate) + 'Seg' + str(seq) + '-Frag' + str(frag))
        tf = time.time()

        throughput_new = int(video_chunk_response.headers.get('Content-Length')) / (tf - ts) / 1024
        throughput_current = alpha * throughput_new + (1 - alpha) * throughput_current
        throughput_with_port[server_port] = throughput_current
        log.write(
            str(ts) + ' ' + str(tf - ts) + ' ' + str(throughput_new) + ' ' + str(throughput_current) + ' ' + str(
                bitrate) + ' ' + str(server_port) + ' ' + str(bitrate) + 'Seg' + str(seq) + '-Frag' + str(
                frag) + '\n')

        return Response(video_chunk_response)


def request_dns():
    """
    Request dns server here.
    """

    dns_client = socket(AF_INET, SOCK_STREAM)
    dns_client.connect(('127.0.0.1', dns_port))
    dns_client.send("".encode('utf-8'))
    res = dns_client.recvfrom(100)
    return bytes.decode(res[0])


def get_throughput(port):
    """
    Calculate throughput here.
    """
    if port not in throughput_with_port:
        # get the throughput for lowest bitrate
        throughput_with_port[port] = bitrates_with_port[port][0] * 1.5 + 0.1
    return throughput_with_port[port]


def record_bitrate_with_port(port, f4m_file):
    bitrates_list = []
    bitrate_from_file = re.finditer(r'bitrate="\d+', f4m_file.text)
    for bitrate in bitrate_from_file:
        bitrates_list.append(int(bitrate.group().split("bitrate=\"")[1]))
    bitrates_list.sort()
    bitrates_with_port[port] = bitrates_list


if __name__ == '__main__':
    init()
    app.run(host='0.0.0.0', port=listen_port)
