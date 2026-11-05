# 실제 VM 구성과 운영

2026-11-05에 두 VM의 실제 구성을 완료하고, Ubuntu 32/32·Kali API 8/8·Firefox 화면 8/8 검증을 통과했습니다.
새 팀원은 [처음 설치 순서](TEAM_SETUP.md)를 사용하세요.

## 현재 구성

| 구분 | Ubuntu 웹서버 | Kali 공격자 |
|---|---|---|
| OS | Ubuntu Server 24.04.5 LTS | Kali 2026.3 공식 VMware 이미지 |
| Host-only IP | 192.168.67.20/24 | 192.168.67.10/24 |
| 인터페이스 | ens37 | eth1 |
| 역할 | Nginx/Flask/Gunicorn/PostgreSQL Docker | Firefox/Burp/sqlmap/HTTP 검증 |
| 소스·검증 | /home/lab/minishop | /home/kali/verify_minishop.py |
| NAT | 기존 ens33 192.168.186.128 유지 | eth0 연결 해제·자동 연결 비활성화 |

VMnet1 호스트 주소는 192.168.67.1/24, DHCP 범위는 192.168.67.128~254입니다.
실험용 고정 주소 10/20은 DHCP 범위 밖입니다. Ubuntu 주소에 대해 ARP 중복 검사를 수행했고,
Kali는 NetworkManager의 중복 주소 검사를 거쳐 활성화했습니다.
Host-only 전용 NIC에는 기본 게이트웨이·DNS를 지정하지 않았습니다.

Ubuntu의 기존 NAT netplan 파일과 기존 웹서비스 5000은 보존했습니다.
별도 `/etc/netplan/90-minishop-lab.yaml`에 ens37만 추가했습니다.
두 VM의 변경 전 VMX와 라이브러리 등록 파일은 Windows 소스의 `results/vm/`에 백업했습니다.

## VMware에서 열기

- Ubuntu: VMware 라이브러리의 `MiniShop - Ubuntu (Web)`, 작업 폴더의 `vms/ubuntu/Ubuntu 64-bit.vmx`.
- Kali: VMware 라이브러리의 `MiniShop - Kali (Attacker)`, 작업 폴더의 `vms/kali/kali-linux-2026.3-vmware-amd64.vmx`.
- 작업 폴더 최상위의 `Ubuntu - Web Server.lnk`, `Kali - Attacker.lnk`로도 열 수 있습니다.
- Kali 기본 OS 로그인은 공식 이미지의 `kali` / `kali`. Host-only 실험용입니다.
- Ubuntu는 기존 `lab` 계정과 사용자가 로컬 입력창에 제공한 비밀번호를 사용합니다.
  비밀번호는 코드·문서·Git에 저장하지 않습니다.

Windows 작업 폴더는 `Downloads/minishop`이며 소스는 `project`, VM은 `vms`, 설치 이미지는 `downloads` 아래에 모았습니다.
기존 Ubuntu와 새 Kali의 전체 파일을 이동했고, 이동 전후 파일 수와 크기가 일치함을 확인했습니다.
기존 게스트 데이터와 UUID·MAC은 유지하고 VMware 라이브러리·ISO 경로를 갱신했습니다.
공식 Kali 이미지 SHA-256은 다운로드 후 검증했습니다.

## Ubuntu 서버 명령

```sh
cd /home/lab/minishop
docker compose ps
python3 scripts/verify_environment.py --no-build
python3 scripts/demo_credentials.py
docker compose down
docker compose up -d --wait
```

`down`은 데이터 볼륨을 유지합니다. 안전 모드 복귀는 `python3 scripts/restore_safe.py`입니다.
홈페이지 주소는 `http://192.168.67.20:18080/`입니다. `/products`는 기본 JSON API입니다.
Windows Docker Desktop은 이 서버 실행에 사용하지 않습니다.

## Kali 확인

```sh
ip -br address
ip route
curl -i http://192.168.67.20:18080/products
curl -i http://192.168.67.20:18080/health/orders
nc -vz -w 2 192.168.67.20 5432
```

HTTP는 200, PostgreSQL 직접 접속은 실패해야 합니다.
Kali 기본 경로가 없고 192.168.67.0/24 경로만 있어야 현재 실험용 연결 상태와 같습니다.
Firefox에서 서비스 주소를 열거나 Burp의 브라우저로 같은 주소를 요청합니다.
Burp/sqlmap/Firefox 실행 파일을 확인했으며, SQLi 취약 쿼리·공격 스크립트 구현은 다음 단계입니다.

패키지 다운로드가 필요할 때 Kali에서 기존 NAT 프로필을 일시적으로 활성화할 수 있습니다.

```sh
sudo nmcli connection up 'Wired connection 1'
# 다운로드를 마친 뒤 실험 상태로 복귀:
sudo nmcli connection modify 'Wired connection 1' connection.autoconnect no
sudo nmcli device disconnect eth0
```

## 실제 증거 위치

- Ubuntu: `results/20261105T180102_KST/`, `results/latest.json`.
- Windows 복사본: `results/vm/ubuntu-results/`, `results/vm/ubuntu-validation.json`.
- Kali 출발 검사: `results/vm/kali-validation.json`.
- 최종 환경 검증 개요: [validation.md](validation.md).

기존 Windows Docker의 검증 결과는 과거 기록입니다. 최종 실행 대상은 위 Ubuntu VM이며,
VM 사이 HTTP·인가·DB 포트 검증은 Kali VM에서 실제 실행했습니다.

## Kali 커서 표시 수정

마우스 장치와 VMware Tools는 인식됐으나 로그인 화면에서 포인터가 보이지 않는 증상에 대해,
현재 Xorg/modesetting 드라이버의 소프트웨어 커서를 활성화했습니다.

- 설정: `/etc/X11/xorg.conf.d/99-minishop-software-cursor.conf`, `Option "SWcursor" "true"`.
- 실행 스크립트: `scripts/fix_kali_pointer.sh`.
- 현재 로그인 화면에는 LightDM 재시작으로 적용. 활성 사용자 데스크톱은 없는 상태에서 수행했습니다.
- Xorg 로그에서 옵션 적용을 확인하고, 실제 VM 캡처에서 화살표 커서 표시를 확인했습니다.
- 로컬 증거: `results/vm/kali-pointer-before.png`, `kali-pointer-after.png`.

설정은 다음 부팅에도 Xorg가 읽습니다. 되돌리려면 해당 설정 파일을 `.conf.disabled`로 이름을 바꾸고
작업을 저장한 뒤 Kali를 재부팅합니다. Ubuntu 웹서비스와 실험 네트워크 설정은 변경하지 않았습니다.
