# 리헨즈 SOOP 게시글 → Discord 알림

`tldn031` 방송국에서 **선수 본인**이 올린 새 글을 매 5분(예약 기준)마다 확인합니다. 방송 시작 알림은 픽가드 등 별도 봇을 이용하세요.

## 배포 (약관과 비공식 API 변경에 주의)

1. GitHub에서 `lehends-soop-alert` **Public** 저장소를 만들고 기본 브랜치를 `main`으로 설정합니다.
2. 이 ZIP 안의 `alert.py`, `README.md`, `.github/workflows/soop-alert.yml`을 **경로를 유지해서** 업로드합니다. ZIP 파일 자체를 그대로 올리면 실행되지 않습니다.
3. Discord 채널 편집 → 연동 → 웹후크 → 새 웹후크 → 웹후크 URL 복사.
4. GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret → 이름: `DISCORD_WEBHOOK_URL`, 값: 복사한 URL.
5. GitHub 저장소 → Actions → `SOOP post notification` → Run workflow → Run workflow. 첫 실행은 현재 게시글 번호를 `state.json`으로 저장하며 **과거 글은 전송하지 않습니다**.
6. Actions 로그에서 `첫 실행` 또는 `새 게시글 없음`을 확인합니다. 이후 새 게시글이 올라오면 임베드 알림이 전송됩니다.

## 주의 사항

- Github Actions 예약 실행은 정확한 5분 간격을 보장하지 않습니다. 장시간 지연·누락 가능성이 있습니다.
- GitHub 공개 저장소에서 60일 동안 활동이 없으면 예약 워크플로가 자동 비활성화될 수 있습니다.
- SOOP API는 공식 보장된 공개 API가 아닙니다. 서버 측에서 403/차단/형식 변경이 발생하면 작동하지 않습니다.
- `state.json`은 공개되어도 되는 마지막 글 번호만 담습니다. 웹훅은 반드시 GitHub **Secret**으로 설정하세요.
- 최초 기준점 기록 또는 이후 상태 저장 커밋에 `contents: write` 권한이 필요합니다. 실패하면 Settings → Actions → General → Workflow permissions에서 Read and write permissions를 확인하세요.
- 응답 목록은 최근 글 10개만 조회하므로 긴 공백 사이 10개 넘게 새 글이 생기면 일부를 놓칠 수 있습니다.
- Discord 메시지 전송 성공 직후 GitHub 상태 기록에 실패하면 같은 글에 대해 중복 알림이 생길 수 있습니다.
- SOOP 게시글에 대한 접근권 및 SOOP 이용약관을 준수하세요.
