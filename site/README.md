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

## 記事生成フロー

1. `content/{lab}/{slug}.md` にMarkdownで記事を書く（下記フォーマット参照）
2. `pip install pyyaml markdown --break-system-packages`（初回のみ）
3. `python3 build.py` を実行
4. 以下が自動生成される
   - `labs/{lab}/{slug}.html` … 記事詳細ページ（関連記事付き）
   - `labs/{lab}.html` … 研究所トップの記事一覧（自動更新）
   - `sns/{slug}.txt` … SNS投稿文ドラフト
5. `git add . && git commit -m "add: {slug}" && git push`

### Markdownフォーマット

```markdown
---
title: 記事タイトル
lab: career            # career / ai / childcare / english / money のいずれか
category: 転職判断      # 記事カテゴリタグ
description: 検索結果やSNSに表示される要約（100字程度）
date: 2026-07-03
tags: [転職, 意思決定]
affiliate: false        # アフィリエイトリンクを含む場合はtrue
---

ここから本文をMarkdownで記述。## で見出し、通常の段落、箇条書きなどが使える。
```

Claude Codeへの依頼例:
> 「content/ai/ に、ChatGPTとClaudeの比較記事を書いて。書いたらbuild.pyを実行してpushして」

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
