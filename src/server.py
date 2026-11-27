"""
server.py  —  1주차 평문 TCP 채팅 서버 (v2: 여러 명 접속 + 브로드캐스트)

[목표] 여러 클라이언트를 동시에 받아들이고,
       한 명이 보낸 메시지를 나머지 모두에게 전달한다. (단톡방)
       여전히 암호화 없음 = '평문'.
"""

import socket
import threading  # 여러 손님을 동시에 상대하기 위한 '스레드'

HOST = "0.0.0.0"  # 모든 네트워크 통로에서 접속을 받는다 (localhost + GNS3 둘 다 OK)
PORT = 9999

clients = []  # 현재 접속해 있는 모든 클라이언트 소켓을 담아두는 목록


def broadcast(message, sender_conn):
    """보낸 사람을 뺀 나머지 모든 클라이언트에게 메시지를 전달한다."""
    for client in clients:
        if client is not sender_conn:  # 자기 자신에겐 다시 안 보냄
            try:
                client.sendall(message)
            except OSError:
                pass  # 이미 끊긴 소켓이면 조용히 무시


def handle_client(conn, addr):
    """손님 한 명을 전담하는 직원(스레드). 그 손님 메시지를 계속 받아 뿌린다."""
    print(f"[서버] {addr} 님이 접속했습니다. (현재 {len(clients)}명)")
    while True:
        try:
            data = conn.recv(1024)
            if not data:          # 빈 데이터 = 연결 끊김
                break
            text = data.decode("utf-8")
            print(f"[받음 {addr}] {text}")
            broadcast(data, conn)  # 나머지 모두에게 전달
        except OSError:
            break
    # 손님이 나갔을 때 뒷정리
    print(f"[서버] {addr} 님이 나갔습니다.")
    if conn in clients:
        clients.remove(conn)
    conn.close()


# ── 서버 소켓 준비 (v1과 동일) ──
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen()
print(f"[서버] {HOST}:{PORT} 에서 대기 중... (Ctrl+C 로 종료)")

# ── 손님이 올 때마다 전담 직원(스레드)을 붙여준다 ──
while True:
    conn, addr = server_socket.accept()  # 새 손님 접속을 기다림
    clients.append(conn)                 # 목록에 추가
    thread = threading.Thread(
        target=handle_client, args=(conn, addr), daemon=True
    )
    thread.start()                       # 전담 직원 출근!
