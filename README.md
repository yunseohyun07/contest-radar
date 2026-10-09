# 대회 레이더

알고리즘 대회, 해커톤, IT 공모전, CTF·AI 대회를 한 화면에 모아 보여주는 개인용 웹앱이에요.

- **자동 수집:** 매일 오전 6시와 오후 6시(한국 시간)에 GitHub가 대회 정보를 새로 모아요.
- **출처:** Codeforces, AtCoder, LeetCode, CTFtime, 링커리어(모든 분야 중 IT 관련 제목), 콘테스트코리아(학문·과학·IT, 아이디어·창업 분야 중 IT 관련·대학생 참가 가능), 연례 대회 목록(`collector/annual.json`, 직접 관리)
- **중복 정리:** 링커리어와 콘테스트코리아에 같은 대회가 있으면 하나만 보여줘요.
- **기능:** 마감 임박 순 목록, 종류별 필터, 검색, 관심 대회 저장, 캘린더, 대회 상세, 캘린더 알림(3일 전·하루 전)

## 폴더 구조

```
collector/collect.py      대회 수집기 (파이썬 기본 라이브러리만 사용)
site/                     웹앱 (그대로 올리면 동작, 빌드 필요 없음)
  index.html, app.js, style.css
  data/contests.json      수집된 대회 목록 (자동으로 바뀜)
  feeds/*.ics             캘린더 구독용 파일 (자동으로 바뀜)
  ics/<대회>.ics          대회 하나를 내 캘린더에 추가하는 파일 (자동으로 바뀜)
tests/                    수집기 테스트 + 실제 사이트 응답 샘플
tools/preview_data.py     인터넷 없이 샘플 데이터로 화면 확인할 때 사용
.github/workflows/        GitHub 자동 실행 설정
```

## GitHub에 올리기 (처음 한 번만)

1. [github.com](https://github.com)에서 **New repository**를 누르고 이름을 `contest-radar`로, 공개 범위는 **Public**으로 만들어요. (무료 계정은 Public 저장소만 GitHub Pages를 쓸 수 있어요.)
2. [GitHub Desktop](https://desktop.github.com)을 설치하고 로그인한 다음 **File → Add Local Repository**로 이 폴더를 선택해요. "저장소가 아니다"라고 나오면 **create a repository**를 누르고, 그다음 **Publish repository**를 눌러 1번에서 만든 저장소로 올려요.
   - `.github` 폴더는 Finder에서 숨겨져 보이지 않지만 GitHub Desktop이 함께 올려줘요.
3. GitHub 저장소 페이지에서 **Settings → Pages → Build and deployment → Source**를 **GitHub Actions**로 바꿔요.
4. **Actions** 탭 → **대회 수집 및 배포** → **Run workflow**를 눌러요. 1~2분 뒤 초록 체크가 뜨면 끝이에요.
5. 앱 주소는 `https://<내 GitHub 아이디>.github.io/contest-radar/` 예요. 폰 Safari에서 열고 **공유 → 홈 화면에 추가**를 누르면 앱처럼 쓸 수 있어요.

## 고장 났을 때

- 앱 위쪽에 노란 경고가 뜨면 어떤 사이트에서 수집이 실패한 거예요. 실패한 사이트는 지난번 정보를 그대로 보여줘요.
- **관심 → 데이터 상태**에서 출처별 성공/실패와 마지막 성공 시간을 볼 수 있어요.
- 자세한 오류는 GitHub 저장소의 **Actions** 탭에서 실패한 실행을 눌러 보면 나와요. 대부분은 사이트 구조가 바뀐 경우라서 `collector/collect.py`의 해당 사이트 부분을 고치면 돼요.

## 내 컴퓨터에서 확인하기

```bash
python3 -m unittest discover tests     # 수집기 테스트
python3 collector/collect.py           # 실제로 수집 (인터넷 필요)
cd site && python3 -m http.server 8000 # http://localhost:8000 에서 화면 확인
```

## 참고

- 관심 대회와 필터 설정은 기기(브라우저)마다 따로 저장돼요. 폰과 PC 사이에 자동으로 공유되지는 않아요.
- 링커리어 수집은 개인 사용 목적이에요. 사이트에 부담이 가지 않도록 하루 두 번, 페이지마다 쉬어 가며 가져와요.
- Kaggle(로그인 키 필요)은 아직 넣지 않았어요.
- 연례 대회 일정이 새로 공지되면 `collector/annual.json`의 events에 날짜를 추가하면 돼요.
