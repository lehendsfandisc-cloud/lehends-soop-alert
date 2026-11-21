#!/usr/bin/env python3
"""SOOP station posts -> Discord webhook. Python standard library only."""
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

CHANNEL_ID = os.getenv('SOOP_CHANNEL_ID', 'tldn031')
STATE_FILE = Path(os.getenv('STATE_FILE', 'state.json'))
WEBHOOK = os.getenv('DISCORD_WEBHOOK_URL', '').strip()
API_ROOT = 'https://api-channel.sooplive.com/v1.1/channel'
MAX_POSTS = 10


def load_state():
    if not STATE_FILE.exists():
        return None
    obj = json.loads(STATE_FILE.read_text(encoding='utf-8'))
    if obj.get('channel_id') != CHANNEL_ID:
        raise ValueError('저장된 상태의 채널 ID가 현재 설정과 다릅니다.')
    return int(obj['last_post_no'])


def save_state(last_no):
    tmp = STATE_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps({'channel_id': CHANNEL_ID, 'last_post_no': last_no}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(STATE_FILE)


def request_json(url, *, data=None, headers=None, timeout=20):
    h = {'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (compatible; SOOPPostDiscordNotifier/1.0)'}
    if headers:
        h.update(headers)
    req = Request(url, data=data, headers=h, method='POST' if data is not None else 'GET')
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode('utf-8')
        return json.loads(body) if body.strip() else None


def fetch_posts():
    params = {
        'perPage': str(MAX_POSTS), 'startDate': '', 'endDate': '',
        'field': 'title,contents,user_nick,user_id,hashtags', 'keyword': '',
        'type': 'all', 'orderBy': 'reg_date', 'page': '1', 'bbsNo': '',
    }
    url = f'{API_ROOT}/{CHANNEL_ID}/board?{urlencode(params)}'
    data = request_json(url)
    if not isinstance(data, dict) or not isinstance(data.get('contents'), list):
        raise ValueError(f'SOOP 게시판 응답 형식이 예상과 다릅니다: {str(data)[:300]}')
    posts = data['contents'] + (data.get('noticeData') if isinstance(data.get('noticeData'), list) else [])
    own = []
    for p in posts:
        if not isinstance(p, dict) or str(p.get('userId')) != CHANNEL_ID:
            continue
        try:
            number = int(p['titleNo'])
        except (KeyError, TypeError, ValueError):
            continue
        if number <= 0:
            continue
        own.append({'number': number, 'title': str(p.get('titleName') or '새 게시글').strip()[:256]})
    # Deduplicate sticky notices and normal posts
    return sorted({p['number']: p for p in own}.values(), key=lambda p: p['number'])


def send_discord(post):
    if not WEBHOOK.startswith('https://discord.com/api/webhooks/') and not WEBHOOK.startswith('https://discordapp.com/api/webhooks/'):
        raise ValueError('DISCORD_WEBHOOK_URL이 올바른 Discord 웹훅 주소가 아닙니다.')
    post_url = f'https://www.sooplive.com/station/{CHANNEL_ID}/post/{post["number"]}'
    payload = {
        'username': '리헨즈 SOOP 알리미',
        'allowed_mentions': {'parse': []},
        'embeds': [{
            'title': '📝 리헨즈 선수님의 새 게시글',
            'description': post['title'].replace('@', '@\u200b'),
            'url': post_url,
            'color': 0x5865F2,
            'footer': {'text': 'SOOP · tldn031'},
        }],
    }
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = Request(WEBHOOK, data=body, headers={'Content-Type': 'application/json', 'User-Agent': 'SOOPPostDiscordNotifier/1.0'}, method='POST')
    for attempt in range(3):
        try:
            with urlopen(req, timeout=20) as response:
                if response.status not in (200, 204):
                    raise RuntimeError(f'Discord 응답 코드 {response.status}')
            print('알림 전송 성공:', post['number'], post['title'])
            return
        except HTTPError as err:
            if err.code == 429 and attempt < 2:
                retry_after = 3
                try:
                    retry_after = min(15, max(1, float(json.loads(err.read())['retry_after'])))
                except Exception:
                    pass
                time.sleep(retry_after)
                continue
            if 500 <= err.code < 600 and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise
        except (URLError, TimeoutError):
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise


def main():
    if not WEBHOOK:
        raise ValueError('GitHub Actions Secret DISCORD_WEBHOOK_URL을 설정해주세요.')
    posts = fetch_posts()
    if not posts:
        # Avoid silently establishing a zero baseline on API outages/empty responses.
        print('선수 본인 게시글을 찾지 못했습니다. 기존 상태를 유지합니다.')
        return
    baseline = load_state()
    newest = posts[-1]['number']
    if baseline is None:
        save_state(newest)
        print(f'첫 실행: 게시글 번호 {newest}를 기준점으로 저장했습니다. 과거 게시글 알림은 보내지 않습니다.')
        return
    fresh = [p for p in posts if p['number'] > baseline]
    if not fresh:
        print(f'새 게시글 없음 (기준 번호 {baseline}, 현재 최대 {newest})')
        return
    # Limit unexpected mass notifications if many posts appeared between polls.
    for post in fresh:
        send_discord(post)
        save_state(post['number'])
    print(f'{len(fresh)}개의 새 게시글 처리 완료')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {type(exc).__name__}: {exc}', file=sys.stderr)
        sys.exit(1)
