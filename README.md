# UNO Championship

2~8명이 브라우저에서 플레이하는 파이썬 우노 게임입니다. 같은 방에서 라운드를 반복해 먼저 3승을 거두면 우승합니다. 새 라운드를 열 때 추가 규칙 여섯 개 중 두 개를 무작위로 뽑으며, 바로 앞 라운드와 두 규칙이 모두 같은 조합은 제외합니다.

## 1. Windows에서 먼저 실행하기

1. ZIP 파일을 우클릭하고 **모두 압축 풀기**를 선택합니다. 압축을 푼 뒤 `server.py`, `game.py`, `index.html`이 들어 있는 폴더를 엽니다.
2. 탐색기 주소창에 `powershell`을 입력하고 Enter를 눌러 그 폴더에서 PowerShell을 엽니다.
3. `py --version`으로 Python 3.10 이상이 설치되어 있는지 확인합니다. Python이 없으면 [python.org](https://www.python.org/downloads/windows/)에서 설치합니다. `py`가 없고 `python --version`이 작동하면 아래 명령의 `py`를 `python`으로 바꿉니다.
4. 아래 명령을 실행합니다. 이 방법은 추가 패키지 설치가 필요 없습니다.

   ```powershell
   py server.py
   ```

5. 브라우저에서 `http://127.0.0.1:8000`을 엽니다. 닉네임을 입력하고 **새 방 만들기**를 누릅니다. 같은 PC에서 시험하려면 시크릿 창에도 같은 주소를 열고, 다른 닉네임과 방 코드로 **방 참가하기**를 누릅니다.
6. 방장 화면에서 **라운드 시작**을 누릅니다. 서버를 끄려면 PowerShell에서 `Ctrl+C`를 누릅니다.

## 2. 같은 Wi-Fi에서 친구와 플레이하기

1. 위 서버가 실행 중이면 `Ctrl+C`로 종료합니다. 아래 명령으로 다시 실행합니다.

   ```powershell
   py server.py --host 0.0.0.0 --port 8000
   ```

2. 다른 PowerShell 창에서 `ipconfig`를 실행합니다. 현재 연결에 사용하는 **무선 LAN 어댑터 Wi-Fi** 또는 **이더넷 어댑터**의 IPv4 주소를 찾습니다. 예를 들어 서버 PC의 IPv4 주소가 `192.168.0.24`라면 친구가 입력할 주소는 `http://192.168.0.24:8000`입니다. 방장은 `http://127.0.0.1:8000`을 열어도 됩니다.
3. 친구에게 주소와 방 코드를 알려줍니다. Windows 방화벽 창이 뜨면 신뢰하는 **개인 네트워크**에서 Python 접속을 허용합니다.
4. 내 PC에서는 되고 친구 PC에서는 접속이 안 된다면, 두 기기가 같은 네트워크인지 확인합니다. 학교·게스트 Wi-Fi는 기기 간 접속을 차단할 수 있으므로 3번의 인터넷 서버를 이용합니다. 집의 개인 네트워크에서 방화벽이 막는 경우에만 **관리자 권한 PowerShell**에서 아래 명령으로 로컬 서브넷의 TCP 8000을 허용할 수 있습니다.

   ```powershell
   New-NetFirewallRule -DisplayName "UNO Championship LAN" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -Profile Private -RemoteAddress LocalSubnet
   ```

## 3. 다른 집에서도 접속할 수 있는 인터넷 서버 만들기

Render에 서버를 배포하면 친구는 `https://…onrender.com` 주소로 들어올 수 있습니다. 공유기 설정이 필요 없고, 배포 후에는 내 컴퓨터를 꺼도 됩니다.

1. [GitHub](https://github.com/new)에서 새 저장소를 만듭니다. 이름 예시는 `uno-championship`입니다. **Add a README file**을 선택하면 바로 파일을 올릴 수 있는 저장소가 생깁니다.
2. 저장소 화면에서 **Add file → Upload files**를 누릅니다. 압축을 푼 폴더 **안의 파일들**을 올리고 **Commit changes**를 누릅니다. 저장소 첫 화면에서 `server.py`, `game.py`, `requirements.txt`, `index.html`, `app.js`, `style.css`가 바로 보여야 합니다. ZIP 자체나 바깥 폴더째 올리면 아래 설정으로 실행되지 않습니다.
3. [Render 대시보드](https://dashboard.render.com/)에 로그인합니다. **New → Web Service**를 누르고 GitHub 계정을 연결한 뒤 방금 만든 저장소를 선택합니다. 목록에 없으면 Render의 GitHub 저장소 접근 권한에 해당 저장소를 추가합니다.
4. 아래 설정을 입력합니다. 서비스 이름은 원하는 이름을 쓰고, 무료로 시작하려면 **Instance Type → Free**를 선택합니다.

   | 항목 | 입력값 |
   | --- | --- |
   | Language / Runtime | `Python 3` |
   | Branch | `main` 또는 파일을 올린 브랜치 |
   | Root Directory | 비워 두기 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `python serve_public.py` |
   | Health Check Path (선택) | `/health` |

5. **Deploy Web Service**를 누르고 상태가 **Live**가 될 때까지 기다립니다. 대시보드 상단의 `https://…onrender.com` 주소를 열어 방을 만든 뒤 친구에게 **그 주소와 방 코드**를 보냅니다.
6. 배포에 실패하면 **Logs**를 봅니다. `requirements.txt`나 `server`를 찾을 수 없다는 오류는 저장소 최상위에 파일을 올렸는지, 올바른 브랜치를 골랐는지 확인합니다. 게임 방은 한 프로세스의 메모리에 있으므로 같은 서비스를 여러 인스턴스로 복제하면 플레이어가 서로 다른 방 목록을 보게 됩니다.

Render 무료 서비스는 요청 없이 15분이 지나면 절전 상태에 들어갑니다. 첫 접속에서 서버가 깨어날 때까지 1분 정도 걸릴 수 있습니다. 서버 재시작·재배포·절전으로 방과 승수가 초기화됩니다. 서버가 유지되는 동안 같은 탭을 새로고침하면 원래 자리에 돌아옵니다. 라운드 도중 **방 나가기**를 누르면 그 라운드는 종료되고, 남은 사람이 2명 이상이면 다음 라운드를 열 수 있습니다.

## 카드 내는 법

- 현재 카드와 색 또는 숫자·기호가 같으면 낼 수 있습니다. 와일드는 다음 색을 고르며, `+4`는 현재 색 카드가 손에 없을 때만 서버가 허용합니다.
- 기본 뽑기에서는 한 장을 뽑습니다. 낼 수 있으면 그 카드만 내거나 턴을 넘깁니다. 낼 수 없으면 자동으로 턴이 넘어갑니다.
- 카드 한 장이 남을 때는 카드를 내기 전에 **이 카드와 함께 UNO 외치기**를 체크합니다. 놓치면 다른 사람이 다음 카드 내기·뽑기·턴 넘기기 전에 **UNO 지적**을 눌러 2장을 받게 할 수 있습니다. 손패 교환·회전 후에는 0이나 7을 낸 사람의 손패를 기준으로 처리합니다.
- 2인 게임에서 방향 전환은 상대 턴을 건너뜁니다. 마지막 카드를 내면 즉시 라운드가 끝나므로 마지막 카드의 추가 효과는 생략합니다. 첫 공개 카드는 숫자 카드입니다. `+4`의 적법 여부는 서버에서 검사하며, 별도 도전 절차는 없습니다.

| 추가 규칙 | 효과 |
| --- | --- |
| 공격 누적 | `+2`에는 `+2`, `+4`에는 `+4`로 대응할 수 있습니다. `+4`의 색 제한은 그대로 적용됩니다. 공격을 받으면 누적된 장수를 뽑고 턴을 넘깁니다. |
| 0 카드 돌리기 | 전원이 손패를 진행 방향의 다음 사람에게 넘깁니다. |
| 7 카드 교환 | 지정한 상대 한 명과 손패 전체를 맞바꿉니다. |
| 나올 때까지 뽑기 | 뽑기를 시작하면 낼 수 있는 카드가 나올 때까지 뽑고, 그 카드를 내거나 턴을 넘깁니다. |
| 9장 스타트 | 각자 9장으로 라운드를 시작합니다. |
| 더블 스킵 | 건너뛰기 카드로 상대를 최대 두 명까지 건너뜁니다. |

## 참고 문서

- [Render 웹 서비스](https://render.com/docs/web-services) · [무료 인스턴스 동작](https://render.com/docs/free)
- [GitHub에 파일 올리기](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)
- [Waitress 실행 명령](https://docs.pylonsproject.org/projects/waitress/en/latest/runner.html) · [Windows 방화벽 명령](https://learn.microsoft.com/powershell/module/netsecurity/new-netfirewallrule)
- [Mattel 우노 기본 규칙](https://service.mattel.com/instruction_sheets/43001%20Deluxe%20UNO.PDF)
