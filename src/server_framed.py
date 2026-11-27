"""
server_framed.py  —  구조화된 메시지(헤더) 채팅 서버  [평문 server.py의 발전형]

글자를 그대로 흘려보내던 평문 서버와 달리, protocol.py의 머리말(헤더)로
포장된 메시지를 주고받는다. 헤더의 '본문 길이' 덕분에 메시지 경계가 정확히
나뉘고, '종류(CHAT/JOIN/LEAVE)'와 '보낸사람'을 구분할 수 있다.
암호화는 여전히 없다(본문은 평문) — 그 역할은 TLS 단계(server_tls.py)가 맡는다.
여기서 더해지는 것은 '구조'다.
"""

import socket
import threading
import os
import protocol as P

HOST = "0.0.0.0"
PORT = int(os.environ.get("CHAT_PORT", "9999"))

clients = {}                 # conn -> 이름
lock = threading.Lock()      # clients 목록을 여러 스레드가 동시에 건드리지 않도록


def broadcast(data, sender_conn=None):
    """포장된 메시지(data)를 보낸 사람을 뺀 모두에게 전달한다."""
    with lock:
        targets = list(clients.keys())
    for c in targets:
        if c is not sender_conn:
            try:
                c.sendall(data)
            except OSError:
                pass


def handle_client(conn, addr):
    """손님 한 명 전담 스레드. 첫 메시지는 입장(JOIN)으로 약속해 이름을 얻는다."""
    try:
        first = P.recv_message(conn)
    except ValueError as e:
        print(f"[서버] {addr} {e}")
        conn.close()
        return
    if first is None:
        conn.close()
        return

    _, name, _ = first
    with lock:
        clients[conn] = name
    print(f"[서버] {name}({addr[0]}) 입장. 현재 {len(clients)}명")
    broadcast(P.encode(P.T_JOIN, name, f"{name} 님이 입장했습니다."), conn)

    while True:
        try:
            msg = P.recv_message(conn)
        except ValueError as e:
            print(f"[서버] {addr} {e}")
            break
        if msg is None:
            break
        mtype, sender, body = msg
        print(f"[받음 {P.TYPE_NAME.get(mtype, '?')} {sender}] {body}")
        # 받은 내용을 그대로 다시 포장해 전달(보낸사람/종류 보존)
        broadcast(P.encode(P.T_CHAT, sender, body), conn)

    with lock:
        name = clients.pop(conn, "?")
    print(f"[서버] {name} 퇴장. 현재 {len(clients)}명")
    broadcast(P.encode(P.T_LEAVE, name, f"{name} 님이 나갔습니다."))
    conn.close()


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"[서버] {HOST}:{PORT} 대기 중 (구조화 메시지 모드). Ctrl+C 로 종료")
    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[서버] 종료합니다.")
    finally:
        s.close()


if __name__ == "__main__":
    main()
