"""
client.py  —  1주차 평문 TCP 채팅 클라이언트 (v2: 양방향 동시)

[목표] 내가 치는 메시지를 보내는 '동시에',
       남이 보낸 메시지도 실시간으로 받아서 출력한다.
       '/quit' 입력 시 종료.
"""

import socket
import threading
import os

# 접속할 서버 주소. 환경변수 SERVER_IP가 있으면 그걸, 없으면 내 컴퓨터(127.0.0.1).
#  - 로컬 테스트: 그냥 실행 → 127.0.0.1 로 접속
#  - GNS3: 노드에 SERVER_IP=192.168.1.10 을 넣으면 그 서버로 접속
HOST = os.environ.get("SERVER_IP", "127.0.0.1")
PORT = 9999

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))
print(f"[접속] 서버 {HOST}:{PORT} 에 연결됨. 메시지 입력(끝내려면 /quit)")


def receive():
    """일꾼 B: 들어오는 메시지를 계속 받아서 출력만 담당."""
    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                print("\n[알림] 서버와 연결이 끊어졌습니다.")
                break
            # \r 로 현재 입력 줄을 지우고 상대 메시지를 깔끔히 출력
            print(f"\r[상대] {data.decode('utf-8')}\n나 > ", end="")
        except OSError:
            break


# 일꾼 B(수신)를 백그라운드로 출근시킨다
recv_thread = threading.Thread(target=receive, daemon=True)
recv_thread.start()

# 일꾼 A(송신): 메인에서 키보드 입력을 받아 전송
while True:
    message = input("나 > ")
    if message == "/quit":
        break
    client_socket.sendall(message.encode("utf-8"))

client_socket.close()
print("[클라이언트] 종료했습니다.")
