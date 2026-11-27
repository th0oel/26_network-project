"""
detector.py  —  4단계 ARP Spoofing 탐지기  [방어 측]

[목표] 네트워크에 흐르는 ARP 응답을 감시하다가, '같은 IP인데 MAC이 갑자기
       다른 값으로 바뀌는' 순간을 잡아 "공격 의심" 경보를 울린다.

[수업 연결]
  - ARP 탐지: 같은 IP에 서로 다른 MAC이 보이면 "누가 속이는 중"이라고 알아챈다(용어정리.md).
  - ARP는 응답을 검증하지 않으므로(0930 강의), 위조 응답과 진짜 응답이 섞여 들어온다.
    => 그 '충돌'을 관찰하는 것이 탐지의 핵심이다.
  - 이 감시도 브로드캐스트 영역(같은 L2) 안에서만 유효하다(1028 강의).
"""

import sys

# IP -> 처음 관찰된 MAC 을 기억하는 매핑 테이블
ip_mac_table = {}


def on_arp(pkt):
    from scapy.all import ARP

    if not pkt.haslayer(ARP):
        return
    arp = pkt[ARP]
    if arp.op != 2:        # op=2(응답)만 본다
        return
    ip = arp.psrc
    mac = arp.hwsrc

    known = ip_mac_table.get(ip)
    if known is None:
        ip_mac_table[ip] = mac
        print(f"[학습] {ip} = {mac}")
    elif known != mac:
        # 같은 IP인데 MAC이 달라짐 = ARP Spoofing 의심
        print("!" * 60)
        print(f"[경보] ARP Spoofing 의심! IP {ip} 의 MAC이 바뀜")
        print(f"       기존 {known}  ->  신규 {mac}")
        print("!" * 60)


def main():
    from scapy.all import sniff

    iface = sys.argv[1] if len(sys.argv) > 1 else None
    print("[탐지] ARP 응답 감시 시작. Ctrl+C 로 종료.")
    sniff(filter="arp", iface=iface, prn=on_arp, store=0)


if __name__ == "__main__":
    main()
