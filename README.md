# yt-bot

Free YouTube views bot — GitHub Actions pe chalta hai. Browser nahi, sirf requests.

YouTube ke `/api/stats/playback` + `/api/stats/watchtime` telemetry beacons
seedhe bhejta hai. Watchtime beacon me `st=0 & et>=30` set hai, wahi view
register karta hai.

## Setup

1. Public repo banao.
2. Is folder ki saari files upload karo.
3. Settings -> Actions -> General -> Workflow permissions -> **Read and write** -> Save.
4. `urls.txt` me apni video ka link daalo.
5. Actions tab -> "yt-views" -> Run workflow -> views = 20 -> Run.
6. 30-60 min baad YouTube Studio -> Analytics -> Realtime dekho.

## Speed

views.yml me cron badal:

| cron | runs/day | raw views/day |
|---|---|---|
| `*/15` | 96 | ~4,800 |
| `*/10` | 144 | ~7,200 |
| `*/5` | 288 | ~14,400 |

(raw = runs x shards x views. Actual registered isse kam hoga, ~30-50%.)

## Proxy

Default OFF hai. ON karne ke liye:

1. Actions -> "refresh-proxies" -> Run workflow
2. `config.json` me `"use_proxies": true`
3. views.yml me `USE_PROXIES: '1'`

Proxy ke bina saare views GitHub ke Azure IP pool se jaate hain, isliye
YouTube ka dedupe lag jaata hai.

## Limitations

- Watch time ~0 rehta hai (beacon sirf view register karta hai)
- Datacenter IPs pe YouTube ka bharosa kam hai -> kuch views drop hote hain
- GitHub cron 5-30 min late chal sakta hai
- GitHub 60 din inactivity pe scheduled workflows band kar deta hai
  (keepalive workflow isse bachata hai)

## Verify

YouTube Studio -> Analytics -> Realtime -> Views.
Public count 1-6 ghante late update hota hai.
