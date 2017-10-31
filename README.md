# sonaWatchd

sonaWatchd는 controller plan 및 compute plan에 대한 Monitoring 기능을 제공한다.

정보 수집에 필요한 SBAPI는 SSH(key share)를 사용하고, REST API로 정보 조회 기능을 제공한다.
Ubuntu, CentOS 및 Mac OSX 환경을 지원한다.

* 설치방법
ssh key 생성 및 배포를 위해서 setup tool을 사용한다.
  1. 서버 실행 장비에서는 setup/ssh_key_setup.py 파일을 실행시킨다.
  2. 클라이언트 실행 환경에서는 cli/setup/ssh_key_setup.py 파일을 실행시킨다.

* Monitoring Tool 실행
  1. Server
     - 실행
         ./sonawatcher.py start
     - 종료
         ./sonawatcher.py stop
     - 재시작
         ./sonawatcher.py restart

  2. CLI
     - 실행
         ./cli_main.py
     - 종료
          cli main 화면에서 Esc 키 입력
