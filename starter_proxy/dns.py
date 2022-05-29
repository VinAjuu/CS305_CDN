import socket
import sys
import threading


class DNS():
    ports = []
    port_index = 0
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lock = threading.Lock()

    def __init__(self, file, port):
        f = open(file, "r")
        for line in f:
            self.ports.append(int(line.rstrip()))
        self.server.bind(('localhost', port))
        self.server.listen(100)

    def get_port(self, client):
        self.lock.acquire()
        port = self.ports[self.port_index]
        client.send(str(port).encode('utf-8'))
        self.port_index = (self.port_index + 1) % len(self.ports)
        self.lock.release()
        client.close()

    def start(self):
        while True:
            client, _ = self.server.accept()
            threading.Thread(target=self.get_port, args=(client,)).start()


if __name__ == "__main__":
    dns = DNS(sys.argv[1], int(sys.argv[2]))
    dns.start()
