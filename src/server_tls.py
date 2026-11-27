"""
server_tls.py  —  5단계 TLS 암호화 채팅 서버

[목표] server.py(평문)와 똑같이 동작하되, 소켓을 TLS로 감싼다.
       즉 '벌거벗은 평문'을 '옷 입은 암호문'으로 바꿔 보낸다.
       공격자가 같은 방식으로 가로채도 내용을 못 읽는다(7단계 비교의 핵심).

[수업 연결] 소켓은 L3/L4 프로토콜을 쉽게 쓰도록 OS가 준 '통신 콘센트'(1125 강의).
            ssl 모듈이 그 콘센트에 '자물쇠(TLS)'를 덧씌운다.
"""

import socket
import ssl
import threading
import os
import gen_cert  # 시작 시 인증서를 '현장에서' 생성하기 위해 사용

HOST = "0.0.0.0"
PORT = 9999  # 평문판과 같은 포트. 다른 건 '암호화 여부'뿐이다.

HERE = os.path.dirname(os.path.abspath(__file__))
CERT = os.path.join(HERE, "server.crt")   # gen_cert.py 가 만든 인증서
KEY = os.path.join(HERE, "server.key")    # gen_cert.py 가 만든 개인키

clients = []  # 현재 접속한 (암호화된) 클라이언트 소켓 목록


def broadcast(message, sender_conn):
    """보낸 사람을 뺀 나머지 모두에게 전달 (평문판과 동일)."""
    for client in clients:
        if client is not sender_conn:
            try:
                client.sendall(message)
            except OSError:
                pass


def handle_client(conn, addr):
    print(f"[서버-TLS] {addr} 님 접속 (현재 {len(clients)}명)")
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            print(f"[받음 {addr}] {data.decode('utf-8')}")
            broadcast(data, conn)
        except OSError:
            break
    print(f"[서버-TLS] {addr} 님 퇴장")
    if conn in clients:
        clients.remove(conn)
    conn.close()


# ── 인증서 보장: 없으면 지금 생성한다(이미지에 개인키를 굽지 않기 위함) ──
gen_cert.ensure()

# ── TLS 컨텍스트 준비: 인증서 + 개인키를 적재 ──
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile=CERT, keyfile=KEY)

# ── 평범한 TCP 서버 소켓을 먼저 연다 (server.py와 동일) ──
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen()
print(f"[서버-TLS] {HOST}:{PORT} 대기 중 (TLS 암호화)")

while True:
    raw_conn, addr = server_socket.accept()
    try:
        # 접속을 받은 뒤 '그 자리에서' TLS 핸드셰이크로 소켓을 감싼다.
        conn = context.wrap_socket(raw_conn, server_side=True)
    except ssl.SSLError as e:
        print(f"[서버-TLS] 핸드셰이크 실패 {addr}: {e}")
        raw_conn.close()
        continue
    clients.append(conn)
    threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
