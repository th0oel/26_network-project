"""
client_tls.py  —  5단계 TLS 암호화 채팅 클라이언트

[목표] client.py(평문)와 똑같이 보내고 받되, 서버의 인증서를 '신뢰'하고
       TLS 핸드셰이크를 한 뒤 통신한다. 자체서명이라 CA 대신 server.crt를
       직접 신뢰 목록에 넣는다.

[수업 연결] 인증서로 '이 서버가 진짜'인지 확인(용어정리.md). 확인이 끝나면
            오가는 데이터는 전부 암호문이라 중간에서 가로채도 못 읽는다.
"""

import socket
import ssl
import threading
import os

HOST = os.environ.get("SERVER_IP", "127.0.0.1")
PORT = 9999

HERE = os.path.dirname(os.path.abspath(__file__))
CERT = os.path.join(HERE, "server.crt")   # 서버의 자체서명 인증서를 신뢰

# ── TLS 컨텍스트 구성 ──
# 서버 인증서 파일이 있으면 '검증(인증)'까지 수행하고,
# 없으면(이미지에 키를 굽지 않는 구성) '검증 없이 암호화만' 수행한다.
#   - 두 경우 모두 통신 내용은 암호화되어 MITM 도청을 막는다(프로젝트 핵심).
#   - 실제 서비스라면 공인 CA 인증서로 항상 검증해야 한다.
if os.path.exists(CERT):
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.load_verify_locations(CERT)
    HOSTNAME = "localhost"            # 인증서의 CN=localhost 와 일치
    print("[TLS] 서버 인증서를 검증합니다.")
else:
    context = ssl._create_unverified_context()   # 암호화만(실습 전용)
    HOSTNAME = None
    print("[TLS] 인증서 파일이 없어 검증 없이 암호화만 수행합니다(실습).")

raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket = context.wrap_socket(raw_socket, server_hostname=HOSTNAME)
client_socket.connect((HOST, PORT))
print(f"[접속-TLS] {HOST}:{PORT} 에 암호화 연결됨. (/quit 로 종료)")


def receive():
    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                print("\n[알림] 서버와 연결이 끊어졌습니다.")
                break
            print(f"\r[상대] {data.decode('utf-8')}\n나 > ", end="")
        except OSError:
            break


threading.Thread(target=receive, daemon=True).start()

while True:
    message = input("나 > ")
    if message == "/quit":
        break
    client_socket.sendall(message.encode("utf-8"))

client_socket.close()
print("[클라이언트-TLS] 종료했습니다.")
