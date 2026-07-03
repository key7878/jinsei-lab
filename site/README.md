# 人生ラボ

人生をより良くするためのAIライフプラットフォーム。
キャリア・AI・育児・英語・お金の5つの研究所から成る静的サイト。

## 構成

```
/
├── index.html          トップページ（研究所カタログ）
├── style.css            共通スタイル
├── labs/
│   ├── career.html      キャリア研究所
│   ├── ai.html           AI研究所
│   ├── childcare.html   育児研究所
│   ├── english.html     英語研究所
│   └── money.html       お金研究所
└── generate_labs.py     研究所ページの生成スクリプト（テンプレ管理用）
```

記事コンテンツを追加する際は `generate_labs.py` の `LABS` 配列に
`articles` を追記して再実行するか、`labs/*.html` を直接編集してください。

## デプロイ手順（GitHub → Cloudflare Pages）

### 1. GitHubリポジトリ作成
1. https://github.com/new でリポジトリ作成（例: `jinsei-lab`）
2. Public / Private どちらでも可（Cloudflare Pagesはどちらも連携可）
3. ローカルにこのフォルダをpush:

```bash
cd jinsei-lab
git init
git add .
git commit -m "Initial commit: MVP site skeleton"
git branch -M main
git remote add origin https://github.com/<your-username>/jinsei-lab.git
git push -u origin main
```

### 2. Cloudflare Pagesと連携
1. Cloudflareダッシュボード → **Workers & Pages** → **Create application** → **Pages** → **Connect to Git**
2. 先ほどのリポジトリを選択
3. ビルド設定:
   - Framework preset: **None**
   - Build command: 空欄のまま
   - Build output directory: `/`（ルート直下にhtmlがあるため）
4. **Save and Deploy**

### 3. 独自ドメイン接続
1. デプロイ完了後、Pagesプロジェクトの **Custom domains** タブへ
2. `mylifejinseilab.com` を追加
3. 同一Cloudflareアカウント内のドメインなら自動でDNS設定される

これで `git push` するたびに自動デプロイされる状態になります。
